"""将 GitHub Release 的构建产物同步到 Gitee Release。

用法:
    python scripts/sync_to_gitee.py <tag> <release_body_file> <asset_dir>

需要环境变量:
    GITEE_TOKEN — Gitee 个人访问令牌
"""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

OWNER = "Rixinlouis"
REPO = "Deepseek-Usage"
BASE = f"https://gitee.com/api/v5/repos/{OWNER}/{REPO}/releases"


def create_release(token: str, tag: str, body: str) -> int:
    """创建 Gitee Release，返回 release_id。若已存在则复用。"""
    # 先查是否已存在
    req = urllib.request.Request(f"{BASE}?access_token={token}")
    with urllib.request.urlopen(req) as r:
        releases = json.loads(r.read())
    existing = next((rel for rel in releases if rel.get("tag_name") == tag), None)
    if existing:
        print(f"Release already exists (id={existing['id']}), reusing")
        return existing["id"]

    # 创建新 release
    print(f"Creating release for {tag}...")
    payload = json.dumps({
        "access_token": token,
        "tag_name": tag,
        "name": f"DeepSeek API Monitor {tag}",
        "body": body,
        "target_commitish": "main",
        "prerelease": False,
    }).encode()
    req = urllib.request.Request(BASE, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        resp = json.loads(r.read())
    release_id = resp["id"]
    print(f"Release created (id={release_id})")
    return release_id


def upload_file(token: str, release_id: int, filepath: Path) -> bool:
    """上传单个文件到 Gitee Release。"""
    import http.client
    import mimetypes

    boundary = "----GiteeUploadBoundary2026"
    filename = filepath.name.encode("utf-8")
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    file_data = filepath.read_bytes()

    body_parts = [
        f"--{boundary}".encode(),
        f'Content-Disposition: form-data; name="access_token"'.encode(),
        b"",
        token.encode(),
        f"--{boundary}".encode(),
        f'Content-Disposition: form-data; name="file"; filename="{filename.decode()}"'.encode(),
        f"Content-Type: {content_type}".encode(),
        b"",
        file_data,
        f"--{boundary}--".encode(),
    ]
    body = b"\r\n".join(body_parts)

    url = f"{BASE}/{release_id}/attach_files"
    req = urllib.request.Request(url, data=body)
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")

    try:
        with urllib.request.urlopen(req) as r:
            resp = json.loads(r.read())
        print(f"  ✅ {filename.decode()} ({len(file_data)} bytes)")
        return True
    except urllib.error.HTTPError as e:
        print(f"  ❌ {filename.decode()} failed: {e.code} {e.reason}")
        body = e.read().decode(errors="replace")
        print(f"     {body[:300]}")
        return False


def main():
    if len(sys.argv) < 4:
        print(f"Usage: {sys.argv[0]} <tag> <release_body_file> <asset_dir>")
        sys.exit(1)

    token = os.environ.get("GITEE_TOKEN", "")
    if not token:
        print("❌ GITEE_TOKEN environment variable not set")
        sys.exit(1)

    tag = sys.argv[1]
    body_file = Path(sys.argv[2])
    asset_dir = Path(sys.argv[3])

    if not body_file.exists():
        print(f"❌ Body file not found: {body_file}")
        sys.exit(1)
    if not asset_dir.is_dir():
        print(f"❌ Asset dir not found: {asset_dir}")
        sys.exit(1)

    body = body_file.read_text(encoding="utf-8")

    # 1. 创建 release
    release_id = create_release(token, tag, body)

    # 2. 上传文件
    assets = sorted(
        [f for f in asset_dir.iterdir() if f.is_file() and f.suffix != ".sha256"],
        key=lambda f: f.stat().st_size,
    )
    print(f"Uploading {len(assets)} file(s)...")
    for asset in assets:
        upload_file(token, release_id, asset)

    print(f"✅ Done: https://gitee.com/{OWNER}/{REPO}/releases")


if __name__ == "__main__":
    main()
