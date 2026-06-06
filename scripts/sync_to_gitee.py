"""将 GitHub Release 的构建产物同步到 Gitee Release。

用法:
    python scripts/sync_to_gitee.py <tag> <release_body_file> <asset_dir>

需要环境变量:
    GITEE_TOKEN -- Gitee 个人访问令牌

依赖:
    requests
"""

import json
import os
import sys
import time
from pathlib import Path

import requests

OWNER = "Rixinlouis"
REPO = "Deepseek-Usage"
BASE = f"https://gitee.com/api/v5/repos/{OWNER}/{REPO}/releases"


def create_release(token: str, tag: str, body: str) -> int:
    """创建 Gitee Release，返回 release_id。若已存在则复用。"""
    resp = requests.get(BASE, params={"access_token": token})
    resp.raise_for_status()
    releases = resp.json()
    existing = next((rel for rel in releases if rel.get("tag_name") == tag), None)
    if existing:
        print(f"Release already exists (id={existing['id']}), reusing")
        return existing["id"]

    print(f"Creating release for {tag}...")
    resp = requests.post(
        BASE,
        json={
            "access_token": token,
            "tag_name": tag,
            "name": f"DeepSeek API Monitor {tag}",
            "body": body,
            "target_commitish": "main",
            "prerelease": False,
        },
    )
    resp.raise_for_status()
    release_id = resp.json()["id"]
    print(f"Release created (id={release_id})")
    return release_id


def upload_file(token: str, release_id: int, filepath: Path) -> bool:
    """上传单个文件到 Gitee Release（使用 requests multipart）。"""
    url = f"{BASE}/{release_id}/attach_files"
    fname = filepath.name
    fsize_mb = filepath.stat().st_size / (1024 * 1024)

    print(f"  Uploading {fname} ({fsize_mb:.1f} MB)...", end=" ", flush=True)
    t0 = time.time()

    try:
        with open(filepath, "rb") as f:
            resp = requests.post(
                url,
                data={"access_token": token},
                files={"file": (fname, f)},
                timeout=600,
            )
        elapsed = time.time() - t0
        if resp.status_code in (200, 201):
            print(f"[OK] ({elapsed:.0f}s)")
            return True
        else:
            print(f"[FAIL] HTTP {resp.status_code}: {resp.text[:200]}")
            return False
    except requests.RequestException as e:
        print(f"[FAIL] {e}")
        return False


def main():
    if len(sys.argv) < 4:
        print(f"Usage: {sys.argv[0]} <tag> <release_body_file> <asset_dir>")
        sys.exit(1)

    token = os.environ.get("GITEE_TOKEN", "")
    if not token:
        print("[FAIL] GITEE_TOKEN environment variable not set")
        sys.exit(1)

    tag = sys.argv[1]
    body_file = Path(sys.argv[2])
    asset_dir = Path(sys.argv[3])

    if not body_file.exists():
        print(f"[FAIL] Body file not found: {body_file}")
        sys.exit(1)
    if not asset_dir.is_dir():
        print(f"[FAIL] Asset dir not found: {asset_dir}")
        sys.exit(1)

    body = body_file.read_text(encoding="utf-8")

    # 1. 创建 release
    release_id = create_release(token, tag, body)

    # 2. 上传文件（按大小排序，先小后大，跳过 .sha256）
    assets = sorted(
        [f for f in asset_dir.iterdir() if f.is_file() and f.suffix != ".sha256"],
        key=lambda f: f.stat().st_size,
    )
    print(f"\nUploading {len(assets)} file(s) to release #{release_id}...")
    failed = []
    for asset in assets:
        if not upload_file(token, release_id, asset):
            failed.append(asset.name)

    if failed:
        print(f"\n[WARN] {len(failed)} file(s) failed: {', '.join(failed)}")
        sys.exit(1)
    else:
        print(f"\n[OK] All {len(assets)} files uploaded")
        print(f"https://gitee.com/{OWNER}/{REPO}/releases")


if __name__ == "__main__":
    main()
