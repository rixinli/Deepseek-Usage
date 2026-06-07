"""将构建产物推送到 Gitee 的 dist 分支 + 创建/更新 Release。

大文件通过 git push 传输（可靠、支持断点续传），绕过 Gitee API 附件上传限制。
国内用户从 Gitee raw 链接满速下载。

用法:
    python scripts/sync_to_gitee.py <tag> <asset_dir> [--body "<markdown>"]

需要环境变量:
    GITEE_TOKEN -- Gitee 个人访问令牌（用于创建 Release 和 git push）
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

OWNER = "Rixinlouis"
REPO = "Deepseek-Usage"
GITEE_HTTPS = f"https://gitee.com/{OWNER}/{REPO}.git"
API_BASE = f"https://gitee.com/api/v5/repos/{OWNER}/{REPO}"
RELEASES_API = f"{API_BASE}/releases"

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    """运行命令，失败则打印诊断并退出。"""
    result = subprocess.run(cmd, capture_output=True, text=True, **kwargs)
    if result.returncode != 0:
        print(f"[FAIL] {' '.join(cmd)}")
        if result.stdout:
            print(result.stdout[-500:])
        if result.stderr:
            print(result.stderr[-500:])
        sys.exit(result.returncode)
    return result


def api_get(path: str, token: str) -> dict | None:
    """Gitee API GET，返回 JSON 或 None（404）。"""
    import requests

    resp = requests.get(f"{API_BASE}{path}", params={"access_token": token})
    if resp.status_code == 404:
        return None
    if resp.status_code not in (200, 201):
        print(f"[FAIL] GET {path} -> {resp.status_code}: {resp.text[:300]}")
        sys.exit(1)
    return resp.json()


def api_post(path: str, token: str, body: dict) -> dict:
    """Gitee API POST，成功返回 JSON。"""
    import requests

    body["access_token"] = token
    resp = requests.post(f"{API_BASE}{path}", json=body)
    if resp.status_code not in (200, 201):
        print(f"[FAIL] POST {path} -> {resp.status_code}: {resp.text[:300]}")
        sys.exit(1)
    return resp.json()


def api_patch(path: str, token: str, body: dict) -> dict:
    """Gitee API PATCH，成功返回 JSON。"""
    import requests

    body["access_token"] = token
    resp = requests.patch(f"{API_BASE}{path}", json=body)
    if resp.status_code not in (200, 201):
        print(f"[FAIL] PATCH {path} -> {resp.status_code}: {resp.text[:300]}")
        sys.exit(1)
    return resp.json()


# ---------------------------------------------------------------------------
# release body builders
# ---------------------------------------------------------------------------


def build_default_body(tag: str, assets: list[Path]) -> str:
    """生成与 GitHub Release 格式一致的正文（Gitee 下载链接版）。"""
    # 文件列表
    links = []
    for asset in sorted(assets, key=lambda f: f.stat().st_size):
        url = f"https://gitee.com/{OWNER}/{REPO}/raw/dist/{asset.name}"
        fsize_mb = asset.stat().st_size / (1024 * 1024)
        links.append(f"- [{asset.name}]({url}) ({fsize_mb:.1f} MB)")

    links_block = "\n".join(links) if links else "_（无附件）_"

    return f"""## DeepSeek API 额度监控 {tag}

### \U0001f4e6 下载

{links_block}

- **安装包** (`*_Setup.exe`): 双击运行，标准 Windows 安装向导（推荐 ✨）
  - 可选择安装路径，创建快捷方式，配置自动保存
- **便携版** (`DeepSeek_API_Monitor_portable.zip`): 解压即用，无需安装
  - 配置保存在 EXE 同级目录

### ✨ 更新内容

查看 [CHANGELOG.md](https://github.com/DavidLeeeee/DeepSeek-Usage/blob/main/CHANGELOG.md) 了解完整更新日志。

### \U0001f4d6 使用说明

查看 [用户指南](https://github.com/DavidLeeeee/DeepSeek-Usage/blob/main/docs/USER_GUIDE_CN.md)。

### \U0001f527 系统要求

- Windows 10 / 11
- 无需安装 Python

---

\u{1f916} Generated with [Claude Code](https://claude.com/claude-code)
"""


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Sync build artifacts to Gitee Release")
    parser.add_argument("tag", help="Release tag, e.g. v2.4.3")
    parser.add_argument("asset_dir", type=Path, help="Directory containing build artifacts")
    parser.add_argument("--body", default=None, help="Custom release body (markdown)")
    args = parser.parse_args()

    tag: str = args.tag
    asset_dir: Path = args.asset_dir
    token: str = os.environ.get("GITEE_TOKEN", "")

    if not token:
        print("[FAIL] GITEE_TOKEN environment variable not set")
        sys.exit(1)

    if not asset_dir.is_dir():
        print(f"[FAIL] Asset dir not found: {asset_dir}")
        sys.exit(1)

    # 收集产物（排除 .sha256 校验文件）
    assets = sorted(
        [f for f in asset_dir.iterdir() if f.is_file() and f.suffix != ".sha256"],
        key=lambda f: f.stat().st_size,
    )

    if not assets:
        print("[WARN] No assets found in asset_dir, will create release without downloads")

    print(f"=== Syncing release {tag} to Gitee ===")
    print(f"  Assets ({len(assets)}):")
    for a in assets:
        fsize_mb = a.stat().st_size / (1024 * 1024)
        print(f"    {a.name} ({fsize_mb:.1f} MB)")

    # ── 1. 推送构建产物到 Gitee dist 分支 ──────────────────────────
    print("\n--- Step 1: Push artifacts to Gitee dist branch ---")
    dist_dir = Path("_gitee_dist")
    if dist_dir.exists():
        shutil.rmtree(dist_dir)

    dist_dir.mkdir()
    for asset in assets:
        shutil.copy2(asset, dist_dir / asset.name)

    run(["git", "init"], cwd=dist_dir)
    run(["git", "checkout", "-b", "dist"], cwd=dist_dir)
    run(["git", "remote", "add", "gitee", GITEE_HTTPS], cwd=dist_dir)
    run(["git", "add", "."], cwd=dist_dir)
    run(["git", "commit", "-m", f"Release {tag}"], cwd=dist_dir)

    # 用 credential store 认证（比 URL 内嵌更可靠）
    cred_path = Path.home() / ".git-credentials"
    cred_path.write_text(f"https://{OWNER}:{token}@gitee.com\n")

    # git 对大文件传输比 API 上传可靠得多
    print("  Pushing to Gitee dist branch (may take a while for large files)...")
    try:
        run(["git", "-c", "credential.helper=store", "push", "gitee", "dist", "--force"], cwd=dist_dir)
    except SystemExit:
        print("[WARN] First push attempt failed, retrying...")
        time.sleep(2)
        run(["git", "-c", "credential.helper=store", "push", "gitee", "dist", "--force"], cwd=dist_dir)
    print("[OK] Artifacts pushed to dist branch")

    # ── 2. 构建 Release 正文 ──────────────────────────────────────
    # 生成 Gitee 下载链接（dist 分支 raw URL）
    download_links = []
    for asset in sorted(assets, key=lambda f: f.stat().st_size):
        url = f"https://gitee.com/{OWNER}/{REPO}/raw/dist/{asset.name}"
        fsize_mb = asset.stat().st_size / (1024 * 1024)
        download_links.append(f"- [{asset.name}]({url}) ({fsize_mb:.1f} MB)")

    links_block = "\n".join(download_links) if download_links else "_（无附件）_"

    # 标题 + 下载链接（脚本生成，始终包含）
    header = f"""## DeepSeek API 额度监控 {tag}

### \U0001f4e6 下载

{links_block}
"""

    # --body 提供其余内容（更新日志、使用说明、系统要求等），
    # 未传时使用完整默认模板
    if args.body:
        body = header + "\n" + args.body
    else:
        body = build_default_body(tag, assets)

    # ── 3. 创建或更新 Gitee Release ───────────────────────────────
    print(f"\n--- Step 2: Create/update Gitee release for {tag} ---")

    existing = api_get(f"/releases/tags/{tag}", token)
    release_data = {
        "tag_name": tag,
        "name": f"DeepSeek API Monitor {tag}",
        "body": body,
        "target_commitish": "main",
        "prerelease": False,
    }

    if existing:
        release_id = existing.get("id")
        print(f"  Updating existing release id={release_id}...")
        result = api_patch(f"/releases/{release_id}", token, release_data)
        print(f"[OK] Release updated: {result.get('html_url', '?')}")
    else:
        print("  Creating new release...")
        result = api_post("/releases", token, release_data)
        print(f"[OK] Release created: {result.get('html_url', '?')}")

    # ── 4. 清理 ──────────────────────────────────────────────────
    shutil.rmtree(dist_dir)
    print(f"\n[OK] Done: https://gitee.com/{OWNER}/{REPO}/releases")


if __name__ == "__main__":
    main()
