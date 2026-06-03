#!/usr/bin/env python3
"""DeepSeek API 额度监控 — 应用入口。

开发模式: 从 src/ 导入模块。
打包模式: PyInstaller 将 src/ 作为 hidden import 打包。
"""

import os
import sys
import tkinter as tk
from tkinter import messagebox
from pathlib import Path

# 确保 src/ 在 sys.path 中（兼容不同运行方式）
_SRC_DIR = Path(__file__).resolve().parent / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from src.config import is_dev_mode, load_env_file
from src.gui import DeepSeekAPIMonitor


def create_startup_shortcut() -> bool:
    """创建 Windows 开机自启动快捷方式。"""
    try:
        import winshell
        from win32com.client import Dispatch

        startup_folder = winshell.startup()
        shortcut_path = os.path.join(startup_folder, "DeepSeekAPI监控.lnk")

        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.TargetPath = sys.executable
        shortcut.Arguments = f'"{os.path.abspath(__file__)}"'
        shortcut.WorkingDirectory = os.path.dirname(os.path.abspath(__file__))
        shortcut.Description = "DeepSeek API 额度监控"
        shortcut.Save()

        return True
    except Exception:
        return False


def main() -> None:
    """应用程序主入口。"""
    root = tk.Tk()

    try:
        root.iconbitmap(default='icon.ico')
    except Exception:
        pass

    app = DeepSeekAPIMonitor(root)

    # 开机自启动提示
    startup_path = os.path.join(
        os.path.expanduser("~"), "AppData", "Roaming", "Microsoft",
        "Windows", "Start Menu", "Programs", "Startup", "DeepSeekAPI监控.lnk",
    )
    if not os.path.exists(startup_path):
        response = messagebox.askyesno(
            "开机自启动",
            "是否设置开机自启动？\n设置后软件会在系统启动时自动运行。",
        )
        if response:
            if create_startup_shortcut():
                messagebox.showinfo("成功", "已设置开机自启动！")
            else:
                messagebox.showwarning(
                    "提示", "设置开机自启动失败，您可以手动创建快捷方式到启动文件夹。",
                )

    root.mainloop()


if __name__ == "__main__":
    main()
