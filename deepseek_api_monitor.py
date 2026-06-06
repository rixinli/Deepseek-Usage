#!/usr/bin/env python3
"""DeepSeek API 额度监控 — 应用入口。

开发模式: 从 src/ 导入模块。
打包模式: PyInstaller 将 src/ 作为 hidden import 打包。

启动逻辑:
    - 所有开机自启动管理已移至 GUI 内部（设置对话框 + 首次运行提示）
    - 本文件仅负责创建窗口并启动 tkinter 主循环

命令行参数:
    --mock      使用模拟 API 数据运行（离线预览，无需真实 API Key）
"""

import sys
import tkinter as tk
from pathlib import Path

# 确保 src/ 在 sys.path 中（兼容不同运行方式）
_SRC_DIR = Path(__file__).resolve().parent / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from src.monitor import set_mock_mode  # noqa: E402


def main() -> None:
    """应用程序主入口。"""
    # 解析命令行参数
    if "--mock" in sys.argv:
        set_mock_mode(True)
        print("[DEV] Mock API 模式已启用 — 使用模拟数据运行")

    root = tk.Tk()

    # 尝试设置窗口图标
    try:
        icon_path = Path(__file__).resolve().parent / "icon.ico"
        if icon_path.exists():
            root.iconbitmap(default=str(icon_path))
    except Exception:
        pass

    # 创建应用（GUI 内部处理所有启动逻辑）
    from src.gui import DeepSeekAPIMonitor  # noqa: E402
    DeepSeekAPIMonitor(root)

    # 启动主循环
    root.mainloop()


if __name__ == "__main__":
    main()
