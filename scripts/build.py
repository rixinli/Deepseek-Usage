#!/usr/bin/env python3
"""构建脚本 — 使用 PyInstaller 打包为 Windows EXE。"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC_FILE = ROOT / "DeepSeek_API_Monitor.spec"


def main() -> int:
    print("=" * 50)
    print(" DeepSeek API Monitor — Build Script")
    print("=" * 50)

    print(f"\n[1/2] Cleaning old builds...")
    for d in ["build", "dist"]:
        path = ROOT / d
        if path.exists():
            import shutil
            shutil.rmtree(path)
            print(f"  Removed {d}/")

    print(f"\n[2/2] Running PyInstaller...")
    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller", str(SPEC_FILE)],
        cwd=str(ROOT),
    )

    if result.returncode == 0:
        exe_path = ROOT / "dist" / "DeepSeek_API_Monitor.exe"
        if exe_path.exists():
            print(f"\n✅ Build successful: {exe_path}")
            return 0
        else:
            print("\n⚠️  PyInstaller finished but EXE not found")
            return 1
    else:
        print(f"\n❌ Build failed (exit code {result.returncode})")
        return result.returncode


if __name__ == "__main__":
    sys.exit(main())
