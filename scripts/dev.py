#!/usr/bin/env python3
"""开发模式运行器 — 监听文件变更自动重启应用。

用法:
    python scripts/dev.py                     # 正常开发模式
    python scripts/dev.py --mock              # Mock 模式（离线预览）
    python scripts/dev.py --mock --wizard     # Mock + 强制显示设置向导
    python scripts/dev.py --wizard            # 真实 API + 强制显示设置向导

    dev.py 会将自身不认识的参数全部透传给应用。
    应用支持的参数: --mock, --wizard

依赖:
    watchdog >= 3.0  (pip install watchdog)
    如未安装 watchdog，降级为轮询模式。
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

# dev.py 自身识别的参数（不传给应用）
_DEV_ARGS = {"--help", "-h"}

# 应用识别的参数（dev.py 也关心，用于显示摘要）
_APP_ARGS = {"--mock", "--wizard"}


def get_app_args() -> list[str]:
    """提取要传给应用的命令行参数（排除 dev.py 自身参数）。"""
    return [a for a in sys.argv[1:] if a not in _DEV_ARGS]


def run_app(app_args: list[str] | None = None) -> subprocess.Popen:
    """启动应用进程。"""
    if app_args is None:
        app_args = get_app_args()
    cmd = [sys.executable, str(ROOT / "deepseek_api_monitor.py"), *app_args]
    print(f"[dev]  启动: {' '.join(cmd)}")
    return subprocess.Popen(
        cmd,
        cwd=str(ROOT),
        env={**os.environ, "PYTHONPATH": str(ROOT)},
    )


def watch_with_polling(app_args: list[str]) -> None:
    """轮询模式 — 每秒检查文件变更。"""
    print("[dev] ℹ watchdog 未安装，使用轮询模式（每秒检查变更）")

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
    proc = run_app(app_args)

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

                print("[dev]  关闭旧进程...")
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()

                time.sleep(DEBOUNCE_SECONDS)
                proc = run_app(app_args)
    except KeyboardInterrupt:
        print("\n[dev] ⏹ 停止开发服务器...")
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()


def watch_with_watchdog(app_args: list[str]) -> None:
    """使用 watchdog 库监听文件变更。"""
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer

    proc = run_app(app_args)
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
                proc = run_app(app_args)

    handler = ReloadHandler()
    observer = Observer()
    for watch_path in WATCH_DIRS:
        if watch_path.is_dir():
            observer.schedule(handler, str(watch_path), recursive=True)
        elif watch_path.is_file():
            observer.schedule(handler, str(watch_path.parent), recursive=False)
    observer.start()

    print("[dev] 👀 监听文件变更，修改 Python 文件后自动重启...")
    print("    按 Ctrl+C 停止\n")

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
    app_args = get_app_args()

    print("=" * 50)
    print(" DeepSeek API Monitor — 开发模式")
    print("=" * 50)
    if "--mock" in app_args:
        print("  🎭 Mock API   — 使用模拟数据")
    else:
        print("  🌐 真实 API  — 从配置文件读取 API Key")
    if "--wizard" in app_args:
        print("  🧙 强制向导   — 启动时显示设置向导")
    print("  👀 自动重载   — 修改代码自动重启")

    try:
        from watchdog.observers import Observer  # noqa: F401
        watch_with_watchdog(app_args)
    except ImportError:
        watch_with_polling(app_args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
