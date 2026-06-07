"""本地一键发布脚本 - 构建、GitHub Release、Gitee 镜像。

用法:
    python scripts/release.py <version>

示例:
    python scripts/release.py 2.5.0
    python scripts/release.py 2.5.0 --skip-build   # 产物已存在，只发布
    python scripts/release.py 2.5.0 --skip-gitee    # 只发 GitHub

需要:
    - gh CLI 已登录（用于创建 GitHub Release）
    - GITEE_TOKEN 环境变量（用于 Gitee Release）
    - Inno Setup 6 已安装（路径 C:\Program Files (x86)\Inno Setup 6\ISCC.exe）
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
INSTALLER_OUT = DIST / "installer"
GITEE_OWNER = "Rixinlouis"
GITEE_REPO = "Deepseek-Usage"

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def run(cmd: str | list[str], **kwargs) -> subprocess.CompletedProcess:
    """运行命令，打印实时输出，失败时退出。"""
    if isinstance(cmd, str):
        cmd = cmd.split()
    print(f"  → {' '.join(cmd[:6])}{'...' if len(cmd) > 6 else ''}")
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT, **kwargs)
    if result.returncode != 0:
        print(f"\n[FAIL] {' '.join(cmd)}")
        if result.stderr:
            print(result.stderr[-800:])
        if result.stdout:
            print(result.stdout[-400:])
        sys.exit(result.returncode)
    return result


def confirm(msg: str) -> bool:
    """向用户确认操作。"""
    ans = input(f"\n{msg} [y/N] ").strip().lower()
    return ans in ("y", "yes")


# ---------------------------------------------------------------------------
# version
# ---------------------------------------------------------------------------


def get_current_version() -> str:
    """从 pyproject.toml 读取当前版本。"""
    content = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'version\s*=\s*"([^"]+)"', content)
    if not m:
        print("[FAIL] Cannot find version in pyproject.toml")
        sys.exit(1)
    return m.group(1)


def bump_version(new_version: str):
    """更新 pyproject.toml 和 installer/setup.iss 中的版本号。"""
    # pyproject.toml
    pyproject = ROOT / "pyproject.toml"
    content = pyproject.read_text(encoding="utf-8")
    content = re.sub(
        r'version\s*=\s*"[^"]*"',
        f'version = "{new_version}"',
        content,
        count=1,
    )
    pyproject.write_text(content, encoding="utf-8")

    # setup.iss
    setup_iss = ROOT / "installer" / "setup.iss"
    content = setup_iss.read_text(encoding="utf-8")
    content = re.sub(
        r'#define MyAppVersion "[^"]*"',
        f'#define MyAppVersion "{new_version}"',
        content,
        count=1,
    )
    setup_iss.write_text(content, encoding="utf-8")

    print(f"  Version bumped: {get_current_version()} -> {new_version}")


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------


def run_tests():
    """运行 pytest。"""
    print("\n--- Running tests ---")
    run([sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"])


def build_exe():
    """PyInstaller 构建 EXE。"""
    print("\n--- Building EXE ---")
    run([sys.executable, "-m", "PyInstaller", "DeepSeek_API_Monitor.spec"])
    exe = DIST / "DeepSeek_API_Monitor.exe"
    if not exe.exists():
        print(f"[FAIL] EXE not found: {exe}")
        sys.exit(1)
    size_mb = exe.stat().st_size / (1024 * 1024)
    print(f"  [OK] {exe.name} ({size_mb:.1f} MB)")


def build_portable_zip(version: str) -> Path:
    """创建便携版 ZIP。"""
    print("\n--- Creating portable ZIP ---")
    exe = DIST / "DeepSeek_API_Monitor.exe"
    config_example = ROOT / "deepseek_config.ini.example"

    # 复制 config 模板到 dist
    shutil.copy2(config_example, DIST / config_example.name)

    zip_name = DIST / f"DeepSeek_API_Monitor_v{version}_portable.zip"
    # 删除旧的
    if zip_name.exists():
        zip_name.unlink()

    run([
        "powershell", "-Command",
        f"Compress-Archive -Path '{exe}', '{DIST / config_example.name}' "
        f"-DestinationPath '{zip_name}'"
    ])
    size_mb = zip_name.stat().st_size / (1024 * 1024)
    print(f"  [OK] {zip_name.name} ({size_mb:.1f} MB)")
    return zip_name


def build_installer(version: str) -> Path:
    """使用 Inno Setup 构建安装包。"""
    print("\n--- Building installer ---")

    iscc_paths = [
        Path("C:/Program Files (x86)/Inno Setup 6/ISCC.exe"),
        Path("C:/Program Files/Inno Setup 6/ISCC.exe"),
        Path("E:/Inno Setup 6/ISCC.exe"),
    ]
    iscc = next((p for p in iscc_paths if p.exists()), None)
    if not iscc:
        print("[FAIL] Inno Setup 6 not found. Install from https://jrsoftware.org/isinfo.php")
        sys.exit(1)

    run([str(iscc), "installer/setup.iss"])

    installers = sorted(INSTALLER_OUT.glob("*_Setup.exe"))
    if not installers:
        print("[FAIL] No installer found in dist/installer/")
        sys.exit(1)

    installer = installers[0]
    size_mb = installer.stat().st_size / (1024 * 1024)
    print(f"  [OK] {installer.name} ({size_mb:.1f} MB)")
    return installer


def generate_sha256(assets: list[Path]):
    """生成 SHA256SUMS.txt。"""
    print("\n--- Generating SHA256 checksums ---")
    lines = []
    for f in assets:
        result = subprocess.run(
            ["certutil", "-hashfile", str(f), "SHA256"],
            capture_output=True, text=True, cwd=ROOT,
        )
        # certutil 输出格式: 第一行 "SHA256 hash of ...", 第二行是哈希值
        hash_val = result.stdout.strip().split("\n")[1].strip().lower()
        lines.append(f"{hash_val}  {f.name}")

    sums_file = DIST / "SHA256SUMS.txt"
    sums_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("  [OK] SHA256SUMS.txt")
    for line in lines:
        print(f"    {line}")


# ---------------------------------------------------------------------------
# GitHub Release
# ---------------------------------------------------------------------------


def create_github_release(version: str, assets: list[Path], body: str):
    """使用 GitHub API 创建 Release（无需 gh CLI）。"""
    print("\n--- Creating GitHub Release ---")
    tag = f"v{version}"
    github_token = os.environ.get("GITHUB_TOKEN", "")
    if not github_token:
        print("[FAIL] GITHUB_TOKEN environment variable not set")
        print("  Create one at: https://github.com/settings/tokens")
        print("  Then: set GITHUB_TOKEN=ghp_xxxx")
        sys.exit(1)

    import requests

    owner = "rixinli"
    repo = "Deepseek-Usage"
    api = f"https://api.github.com/repos/{owner}/{repo}"

    # 1. 创建 Release
    resp = requests.post(
        f"{api}/releases",
        headers={
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json",
        },
        json={
            "tag_name": tag,
            "name": f"DeepSeek API Monitor {tag}",
            "body": body,
            "draft": False,
            "prerelease": False,
        },
    )
    if resp.status_code not in (200, 201):
        print(f"[FAIL] Create release: {resp.status_code}")
        print(resp.text[:500])
        sys.exit(1)

    release = resp.json()
    upload_url = release["upload_url"].split("{")[0]
    print(f"  Release created: {release['html_url']}")

    # 2. 上传附件
    for asset in assets:
        name = asset.name
        content_type = "application/octet-stream"
        print(f"  Uploading {name} ({asset.stat().st_size / 1e6:.1f} MB)...")

        with open(asset, "rb") as f:
            resp = requests.post(
                upload_url,
                headers={
                    "Authorization": f"Bearer {github_token}",
                    "Accept": "application/vnd.github+json",
                    "Content-Type": content_type,
                },
                params={"name": name},
                data=f,
                timeout=600,  # 10 min for large files
            )
        if resp.status_code in (200, 201):
            print(f"    [OK] {resp.json().get('browser_download_url', '?')}")
        else:
            print(f"    [FAIL] {resp.status_code}: {resp.text[:200]}")
            sys.exit(1)

    print(f"  [OK] GitHub Release complete")


def build_release_body(version: str, is_gitee: bool = False) -> str:
    """生成 Release 正文。"""
    owner = "rixinli"
    repo = "Deepseek-Usage"

    if is_gitee:
        owner = GITEE_OWNER
        repo = GITEE_REPO
        download_url = f"https://gitee.com/{GITEE_OWNER}/{GITEE_REPO}/releases"
    else:
        download_url = f"https://github.com/{owner}/{repo}/releases/tag/v{version}"

    return f"""## DeepSeek API 额度监控 {version}

### \U0001f4e6 下载

- **安装包** (`*_Setup.exe`): 双击运行，标准 Windows 安装向导（推荐 ✨）
  - 可选择安装路径，创建快捷方式，配置自动保存
- **便携版** (`*_portable.zip`): 解压即用，无需安装
  - 配置保存在 EXE 同级目录

| 文件 | 说明 |
|------|------|
| `DeepSeek_API_Monitor_v{version}_Setup.exe` | Windows 安装包 |
| `DeepSeek_API_Monitor_v{version}_portable.zip` | 便携版 |
| `SHA256SUMS.txt` | 校验文件 |

### ✨ 更新内容

查看 [CHANGELOG.md](https://github.com/{owner}/{repo}/blob/main/CHANGELOG.md) 了解完整更新日志。

### \U0001f4d6 使用说明

查看 [用户指南](https://github.com/{owner}/{repo}/blob/main/docs/USER_GUIDE_CN.md)。

### \U0001f527 系统要求

- Windows 10 / 11
- 无需安装 Python

---

\U0001f916 Generated with [Claude Code](https://claude.com/claude-code)
"""


# ---------------------------------------------------------------------------
# Gitee mirror
# ---------------------------------------------------------------------------


def mirror_to_gitee(version: str, assets: list[Path], body: str):
    """将源码、产物、Release 镜像到 Gitee。"""
    gitee_token = os.environ.get("GITEE_TOKEN", "")
    if not gitee_token:
        print("\n[SKIP] GITEE_TOKEN not set, skipping Gitee mirror")
        return

    print("\n--- Mirroring to Gitee ---")
    tag = f"v{version}"

    import requests

    # 1. 验证 token，获取登录名
    user_resp = requests.get(
        f"https://gitee.com/api/v5/user?access_token={gitee_token}"
    )
    if user_resp.status_code != 200:
        print(f"  [WARN] Token invalid (HTTP {user_resp.status_code}), skipping Gitee")
        return
    gitee_login = user_resp.json().get("login", GITEE_OWNER)
    print(f"  Authenticated as: {gitee_login}")

    # 2. 推送源码 main 分支 + tags
    print("\n  --- Push source to Gitee ---")
    run(["git", "remote", "add", "gitee", f"https://gitee.com/{gitee_login}/{GITEE_REPO}.git"])
    # credential store
    cred_path = Path.home() / ".git-credentials"
    old_cred = cred_path.read_text(encoding="utf-8") if cred_path.exists() else ""
    cred_path.write_text(f"https://{gitee_login}:{gitee_token}@gitee.com\n")
    run(["git", "config", "--global", "credential.helper", "store"])

    run(["git", "push", "gitee", "main", "--force"])
    run(["git", "push", "gitee", tag, "--force"])
    print("  [OK] Source + tag mirrored")

    # 3. 推送产物到 dist 分支
    print("\n  --- Push artifacts to Gitee dist branch ---")
    dist_dir = ROOT / "_gitee_dist"
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    dist_dir.mkdir()

    for asset in assets:
        shutil.copy2(asset, dist_dir / asset.name)

    # 写 .gitkeep 排除的 README
    (dist_dir / ".gitkeep").touch()

    subprocess.run(["git", "init"], capture_output=True, text=True, cwd=dist_dir)
    subprocess.run(
        ["git", "config", "user.email", "release@deepseek-monitor.local"],
        capture_output=True, text=True, cwd=dist_dir,
    )
    subprocess.run(
        ["git", "config", "user.name", "Release Script"],
        capture_output=True, text=True, cwd=dist_dir,
    )
    subprocess.run(
        ["git", "checkout", "-b", "dist"],
        capture_output=True, text=True, cwd=dist_dir,
    )
    subprocess.run(
        ["git", "remote", "add", "gitee", f"https://gitee.com/{gitee_login}/{GITEE_REPO}.git"],
        capture_output=True, text=True, cwd=dist_dir,
    )
    subprocess.run(["git", "add", "."], capture_output=True, text=True, cwd=dist_dir)
    subprocess.run(
        ["git", "commit", "-m", f"Release {tag}"],
        capture_output=True, text=True, cwd=dist_dir,
    )

    # 带重试的 push
    for attempt in range(1, 4):
        print(f"    Push attempt {attempt}/3...")
        result = subprocess.run(
            ["git", "push", "gitee", "dist", "--force"],
            capture_output=True, text=True, cwd=dist_dir,
            timeout=300,
        )
        if result.returncode == 0:
            break
        if attempt < 3:
            print(f"    Retrying in 5s...")
            time.sleep(5)
    else:
        print("[FAIL] Failed to push dist branch after 3 attempts")
        print(result.stderr[-500:])
        sys.exit(1)

    print("  [OK] dist branch updated")

    # 4. 创建/更新 Gitee Release
    print("\n  --- Create Gitee Release ---")
    api_base = f"https://gitee.com/api/v5/repos/{gitee_login}/{GITEE_REPO}"

    # 下载链接
    download_links = []
    for asset in sorted(assets, key=lambda f: f.stat().st_size):
        url = f"https://gitee.com/{gitee_login}/{GITEE_REPO}/raw/dist/{asset.name}"
        fsize_mb = asset.stat().st_size / (1024 * 1024)
        download_links.append(f"- [{asset.name}]({url}) ({fsize_mb:.1f} MB)")

    gitee_body = f"""## DeepSeek API 额度监控 v{version}

### \U0001f4e6 下载

{chr(10).join(download_links)}

{body}
"""

    # 检查是否已有 release
    existing = requests.get(
        f"{api_base}/releases/tags/{tag}",
        params={"access_token": gitee_token},
    )

    release_data = {
        "tag_name": tag,
        "name": f"DeepSeek API Monitor {tag}",
        "body": gitee_body,
        "target_commitish": "main",
        "prerelease": False,
    }

    if existing.status_code == 200:
        rid = existing.json()["id"]
        resp = requests.patch(
            f"{api_base}/releases/{rid}",
            json={"access_token": gitee_token, **release_data},
        )
        print(f"  [OK] Release updated (id={rid})")
    else:
        resp = requests.post(
            f"{api_base}/releases",
            json={"access_token": gitee_token, **release_data},
        )
        if resp.status_code in (200, 201):
            print(f"  [OK] Release created (id={resp.json().get('id', '?')})")
        else:
            print(f"  [WARN] Release creation failed: {resp.status_code} {resp.text[:300]}")

    # 清理
    shutil.rmtree(dist_dir)
    # 恢复旧 credentials
    if old_cred:
        cred_path.write_text(old_cred)

    print(f"\n  [OK] Gitee: https://gitee.com/{gitee_login}/{GITEE_REPO}/releases")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Local release script")
    parser.add_argument("version", help="Version to release, e.g. 2.5.0")
    parser.add_argument("--skip-build", action="store_true", help="Skip build, use existing dist/")
    parser.add_argument("--skip-gitee", action="store_true", help="Skip Gitee mirror")
    parser.add_argument("--skip-tests", action="store_true", help="Skip pytest")
    parser.add_argument("--dry-run", action="store_true", help="Print steps without executing")
    parser.add_argument("--yes", "-y", action="store_true", help="Skip all confirmations")
    args = parser.parse_args()

    version: str = args.version
    tag = f"v{version}"
    old_version = get_current_version()

    print("=" * 60)
    print(f"  Release v{version}  (current: v{old_version})")
    print("=" * 60)

    # ── 0. 前置检查 ──────────────────────────────────────────────
    print("\n--- Prerequisites ---")

    # git clean
    result = subprocess.run(
        "git status --porcelain", capture_output=True, text=True, shell=True, cwd=ROOT
    )
    if result.stdout.strip():
        print("[WARN] Uncommitted changes:")
        print(result.stdout)
        if not args.yes and not confirm("Continue with uncommitted changes?"):
            sys.exit(0)

    # on main branch
    result = subprocess.run(
        "git branch --show-current", capture_output=True, text=True, shell=True, cwd=ROOT
    )
    branch = result.stdout.strip()
    if branch != "main":
        if not args.yes and not confirm(f"You are on '{branch}', not 'main'. Continue?"):
            sys.exit(0)

    print("  [OK]")

    if args.dry_run:
        print("\n[Dry run — no actions taken]")
        return

    # ── 1. Bump version ──────────────────────────────────────────
    if version != old_version:
        print("\n--- Bumping version ---")
        bump_version(version)

    # ── 2. Tests ─────────────────────────────────────────────────
    if not args.skip_tests:
        run_tests()

    # ── 3. Build ─────────────────────────────────────────────────
    assets: list[Path] = []
    if not args.skip_build:
        build_exe()
        assets.append(build_portable_zip(version))
        assets.append(build_installer(version))
        generate_sha256(assets)
    else:
        # 使用已有产物
        print("\n--- Using existing build artifacts ---")
        exe = DIST / "DeepSeek_API_Monitor.exe"
        zips = sorted(DIST.glob("*_portable.zip"))
        installers = sorted(INSTALLER_OUT.glob("*_Setup.exe"))
        if exe.exists() and zips and installers:
            assets = [zips[-1], installers[-1]]  # portable ZIP, Setup
            sums = DIST / "SHA256SUMS.txt"
            if sums.exists():
                assets.append(sums)
            print(f"  Found {len(assets)} existing artifacts")
        else:
            print("[FAIL] Build artifacts not found. Run without --skip-build first.")
            sys.exit(1)

    # ── 4. 构建 Release body ─────────────────────────────────────
    body = build_release_body(version, is_gitee=False)

    # ── 5. Commit + Tag + Push ───────────────────────────────────
    print("\n--- Commit and push ---")
    run(["git", "add", "-A"])
    # 只有有变更时才 commit（构建产物在 .gitignore 里，可能没有变更）
    result = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        capture_output=True, cwd=ROOT,
    )
    if result.returncode != 0:
        run(["git", "commit", "-m", f"release: v{version}"])
    else:
        print("  (no changes to commit)")
    run(["git", "tag", "-f", "-a", tag, "-m", f"v{version}"])
    run(["git", "push", "origin", "main", "--tags"])
    print("  [OK] Pushed to GitHub")

    # ── 6. GitHub Release ────────────────────────────────────────
    create_github_release(version, assets, body)

    # ── 7. Gitee mirror ──────────────────────────────────────────
    if not args.skip_gitee:
        mirror_to_gitee(version, assets, body)

    # ── Done ─────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print(f"  Release v{version} complete!")
    print(f"  GitHub: https://github.com/rixinli/Deepseek-Usage/releases/tag/{tag}")
    print(f"  Gitee:  https://gitee.com/{GITEE_OWNER}/{GITEE_REPO}/releases")
    print("=" * 60)


if __name__ == "__main__":
    main()
