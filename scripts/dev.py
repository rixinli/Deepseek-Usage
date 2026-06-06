#!/usr/bin/env python3
"""开发模式运行器 — 监听文件变更自动重启应用。

用法:
    python scripts/dev.py              # 正常开发模式（需要 .env 中的 API Key）
    python scripts/dev.py --mock       # Mock 模式（离线预览，无需 API Key）

依赖:
    watchdog >= 3.0  (pip install watchdog)
    如未安装 watchdog，降级为手动重启模式。
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WATCH_DIRS = [
    ROOT / "src",
    ROOT / "deepseek_api_monitor.py",
]
DEBOUNCE_SECONDS = 0.5  # 防抖间隔（秒）


def run_app(mock: bool = False) -> subprocess.Popen:
    """启动应用进程。"""
    cmd = [sys.executable, str(ROOT / "deepseek_api_monitor.py")]
    if mock:
        cmd.append("--mock")
    print(f"[dev]  启动: {' '.join(cmd)}")
    return subprocess.Popen(
        cmd,
        cwd=str(ROOT),
        env={**os.environ, "PYTHONPATH": str(ROOT)},
    )


def watch_with_polling(mock: bool) -> None:
    """轮询模式 — 每秒检查文件变更。"""
    print("[dev] ℹ watchdog 未安装，使用轮询模式（每秒检查变更）")

    # 记录初始修改时间
    def get_mtimes() -> dict[str, float]:
        result = {}
        for watch_path in WATCH_DIRS:
            if watch_path.is_dir():
                for f in watch_path.rglob("*.py"):
                    result[str(f)] = f.stat().st_mtime
            elif watch_path.is_file():
                result[str(watch_path)] = watch_path.stat().st_mtime
        return result

    last_mtimes = get_mtimes()
    proc = run_app(mock)

    try:
        while True:
            time.sleep(1)
            current_mtimes = get_mtimes()
            if current_mtimes != last_mtimes:
                changed = [
                    f for f in current_mtimes
                    if f not in last_mtimes or current_mtimes[f] != last_mtimes[f]
                ]
                print(f"\n[dev] 🔄 检测到文件变更: {changed[:3]}...")
                last_mtimes = current_mtimes

                # 关闭旧进程
                print("[dev]  关闭旧进程...")
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()

                # 重新启动
                time.sleep(DEBOUNCE_SECONDS)
                proc = run_app(mock)
    except KeyboardInterrupt:
        print("\n[dev] ⏹ 停止开发服务器...")
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()


def watch_with_watchdog(mock: bool) -> None:
    """使用 watchdog 库监听文件变更。"""
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer

    proc = run_app(mock)
    last_restart = 0.0

    class ReloadHandler(FileSystemEventHandler):
        def on_modified(self, event):
            nonlocal last_restart
            if event.src_path.endswith(".py"):
                now = time.time()
                if now - last_restart < DEBOUNCE_SECONDS:
                    return
                last_restart = now
                print(f"\n[dev] 🔄 检测到变更: {event.src_path}")

                nonlocal proc
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()

                time.sleep(DEBOUNCE_SECONDS)
                proc = run_app(mock)

    handler = ReloadHandler()
    observer = Observer()
    for watch_path in WATCH_DIRS:
        if watch_path.is_dir():
            observer.schedule(handler, str(watch_path), recursive=True)
        elif watch_path.is_file():
            observer.schedule(handler, str(watch_path.parent), recursive=False)
    observer.start()

    print("[dev] 👀 监听文件变更，修改 Python 文件后自动重启...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[dev] ⏹ 停止开发服务器...")
        observer.stop()
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
    observer.join()


def main() -> int:
    """主入口。"""
    mock = "--mock" in sys.argv

    print("=" * 50)
    print(" DeepSeek API Monitor — 开发模式")
    print("=" * 50)
    if mock:
        print("  🎭 Mock API 模式 (离线预览，无需 API Key)")

    try:
        from watchdog.observers import Observer  # noqa: F401
        watch_with_watchdog(mock)
    except ImportError:
        watch_with_polling(mock)

    return 0


if __name__ == "__main__":
    sys.exit(main())
