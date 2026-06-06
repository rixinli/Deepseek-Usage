"""DeepSeek API 监控 — GUI 界面 (tkinter)。"""

from __future__ import annotations

import threading
import time
import tkinter as tk
from tkinter import messagebox, scrolledtext
from typing import Any

from .config import AppConfig, is_dev_mode, load_env_file
from .monitor import format_quota_info, get_api_quota, is_mock_mode
from .settings_dialog import SettingsDialog
from .setup_wizard import SetupWizard

# ── 模块级初始化（导入时执行一次）──────────────────────────
_IS_DEV = is_dev_mode()
_FORCE_WIZARD = False
load_env_file()


def set_force_wizard(enabled: bool = True) -> None:
    """设置强制显示设置向导（--wizard 命令行参数）。"""
    global _FORCE_WIZARD
    _FORCE_WIZARD = enabled

# 帮助文档 URL
_USER_GUIDE_URL = "https://github.com/DavidLeeeee/DeepSeek-Usage-Guide"

# 开机自启动快捷方式路径
_STARTUP_SHORTCUT_PATH = None  # 延迟计算


def _get_startup_shortcut_path() -> str:
    """获取开机自启动快捷方式的完整路径。"""
    global _STARTUP_SHORTCUT_PATH
    if _STARTUP_SHORTCUT_PATH is None:
        import os
        _STARTUP_SHORTCUT_PATH = os.path.join(
            os.path.expanduser("~"), "AppData", "Roaming", "Microsoft",
            "Windows", "Start Menu", "Programs", "Startup",
            "DeepSeekAPI监控.lnk",
        )
    return _STARTUP_SHORTCUT_PATH


def create_startup_shortcut(target_path: str | None = None) -> bool:
    """创建 Windows 开机自启动快捷方式。

    Args:
        target_path: 快捷方式指向的程序路径。默认为当前 Python 可执行文件。

    Returns:
        True 表示成功，False 表示失败。
    """
    try:
        import os
        import sys

        import winshell
        from win32com.client import Dispatch

        startup_folder = winshell.startup()
        shortcut_path = os.path.join(startup_folder, "DeepSeekAPI监控.lnk")

        # 刷新全局缓存
        global _STARTUP_SHORTCUT_PATH
        _STARTUP_SHORTCUT_PATH = shortcut_path

        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(shortcut_path)

        if target_path:
            shortcut.TargetPath = target_path
        elif getattr(sys, 'frozen', False):
            # PyInstaller 打包模式
            shortcut.TargetPath = sys.executable
        else:
            shortcut.TargetPath = sys.executable
            # 开发模式下添加脚本路径作为参数
            script_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), '..',
                'deepseek_api_monitor.py',
            )
            shortcut.Arguments = f'"{os.path.abspath(script_path)}"'

        shortcut.WorkingDirectory = os.path.dirname(
            os.path.abspath(target_path if target_path else sys.executable)
        )
        shortcut.Description = "DeepSeek API 额度监控"
        shortcut.Save()
        return True
    except Exception:
        return False


def remove_startup_shortcut() -> bool:
    """移除 Windows 开机自启动快捷方式。

    Returns:
        True 表示成功（或快捷方式本就不存在），False 表示删除失败。
    """
    import os

    shortcut_path = _get_startup_shortcut_path()
    try:
        if os.path.exists(shortcut_path):
            os.remove(shortcut_path)
        return True
    except Exception:
        return False


def is_startup_enabled() -> bool:
    """检查当前是否已设置开机自启动。

    Returns:
        True 表示快捷方式存在。
    """
    import os
    return os.path.exists(_get_startup_shortcut_path())


class DeepSeekAPIMonitor:
    """DeepSeek API 额度监控 GUI 应用。"""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("DeepSeek API 额度监控")
        self.root.geometry("650x580")
        self.root.minsize(550, 450)

        self.config = AppConfig()
        self.config.load_ini_fallback()

        self.monitoring = False

        self._setup_menu()
        self.setup_ui()

        # 首次运行 — 无 API Key 时显示设置向导（或 --wizard 强制弹出）
        if not self.config.api_key or _FORCE_WIZARD:
            self.root.after(500, self._show_setup_wizard)
        elif not self.config.startup_asked:
            # 有 API Key 但首次运行 — 仅询问开机自启动
            self.root.after(1000, self._ask_startup_on_first_run)

        # 自动开始监控（根据设置）
        if self.config.auto_monitor and self.config.api_key:
            self.root.after(800, self.auto_start_monitoring)
        elif self.config.api_key:
            self.root.after(500, self.auto_start_monitoring)

    # ── 菜单栏 ─────────────────────────────────────────────

    def _setup_menu(self) -> None:
        """创建菜单栏。"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # 设置菜单
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="设置", menu=settings_menu)
        settings_menu.add_command(
            label="⚙ 偏好设置...",
            command=self.open_settings_dialog,
            accelerator="Ctrl+,",
        )
        settings_menu.add_separator()
        settings_menu.add_command(label="退出", command=self.root.quit, accelerator="Ctrl+Q")

        # 帮助菜单
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(
            label="📖 使用指南",
            command=self._open_user_guide,
        )
        help_menu.add_separator()
        help_menu.add_command(label="关于", command=self._show_about)

        # 快捷键绑定
        self.root.bind_all("<Control-comma>", lambda e: self.open_settings_dialog())
        self.root.bind_all("<Control-q>", lambda e: self.root.quit())

    # ── UI 构建 ─────────────────────────────────────────────

    def setup_ui(self) -> None:
        """构建完整的 GUI 界面。"""
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self._build_key_frame(main_frame)
        self._build_settings_frame(main_frame)
        self._build_info_frame(main_frame)
        self._build_status_bar(main_frame)

        if _IS_DEV and self.config.api_key:
            self.status_var.set("✅ 系统就绪 (配置来源: .env)")

    def _build_key_frame(self, parent: tk.Frame) -> None:
        """API Key 输入区域。"""
        frame = tk.Frame(parent)
        frame.pack(fill=tk.X, pady=5)

        tk.Label(frame, text="API Key:", font=("Arial", 10)).pack(side=tk.LEFT)

        self.api_key_entry = tk.Entry(frame, width=50, show="*")
        self.api_key_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.api_key_entry.insert(0, self.config.api_key)

        self.show_pwd = False
        self.toggle_btn = tk.Button(
            frame, text="👁", command=self.toggle_password, width=3,
        )
        self.toggle_btn.pack(side=tk.LEFT, padx=2)

        # 快捷设置按钮
        settings_btn = tk.Button(
            frame, text="⚙", command=self.open_settings_dialog,
            width=3, font=("Arial", 10),
        )
        settings_btn.pack(side=tk.LEFT, padx=2)

    def _build_settings_frame(self, parent: tk.Frame) -> None:
        """监控设置区域。"""
        frame = tk.LabelFrame(parent, text="监控设置", padx=10, pady=10)
        frame.pack(fill=tk.X, pady=10)

        # 刷新间隔
        interval_frame = tk.Frame(frame)
        interval_frame.pack(fill=tk.X, pady=5)

        tk.Label(interval_frame, text="刷新间隔（秒）:").pack(side=tk.LEFT)

        self.interval_var = tk.StringVar(value=str(self.config.refresh_interval))
        self.interval_entry = tk.Spinbox(
            interval_frame, from_=30, to=600, textvariable=self.interval_var,
            width=10, increment=10,
        )
        self.interval_entry.pack(side=tk.LEFT, padx=5)

        tk.Label(interval_frame, text="（推荐120-300秒）").pack(side=tk.LEFT, padx=10)

        # 控制按钮
        btn_frame = tk.Frame(frame)
        btn_frame.pack(fill=tk.X, pady=5)

        self.start_btn = tk.Button(
            btn_frame, text="▶ 开始监控", command=self.start_monitoring,
            bg="#28a745", fg="white", width=12,
        )
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = tk.Button(
            btn_frame, text="⏹ 停止监控", command=self.stop_monitoring,
            bg="#dc3545", fg="white", width=12, state=tk.DISABLED,
        )
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        self.refresh_btn = tk.Button(
            btn_frame, text="🔄 立即刷新", command=self.refresh_once, width=12,
        )
        self.refresh_btn.pack(side=tk.LEFT, padx=5)

        self.save_btn = tk.Button(
            btn_frame, text="💾 保存设置", command=self.save_settings,
            bg="#007bff", fg="white", width=10,
        )
        self.save_btn.pack(side=tk.LEFT, padx=5)

        # 定时器标签
        self.timer_label = tk.Label(
            frame, text="⏱ 下次刷新: 等待中...", font=("Arial", 9),
        )
        self.timer_label.pack(pady=5)

    def _build_info_frame(self, parent: tk.Frame) -> None:
        """API 额度信息展示区域。"""
        info_frame = tk.LabelFrame(parent, text="API 额度信息", padx=10, pady=10)
        info_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        text_frame = tk.Frame(info_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)

        self.info_text = scrolledtext.ScrolledText(
            text_frame, width=70, height=15,
            font=("Consolas", 10),
            bg="#1e1e1e", fg="#00ff00", insertbackground="white",
        )
        self.info_text.pack(fill=tk.BOTH, expand=True)

        self.info_text.tag_config("header", foreground="#00ff00",
                                   font=("Consolas", 10, "bold"))
        self.info_text.tag_config("info", foreground="#00ff00")
        self.info_text.tag_config("error", foreground="#ff4444")
        self.info_text.tag_config("success", foreground="#00ff00")

    def _build_status_bar(self, parent: tk.Frame) -> None:
        """底部状态栏。"""
        frame = tk.Frame(parent)
        frame.pack(fill=tk.X, pady=5)

        self.status_var = tk.StringVar(value="✅ 系统就绪")
        tk.Label(
            frame, textvariable=self.status_var, bd=1,
            relief=tk.SUNKEN, anchor=tk.W, font=("Arial", 9),
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # 开机自启动状态指示
        startup_text = "🚀自启" if is_startup_enabled() else ""
        tk.Label(
            frame, text=startup_text, font=("Arial", 8), fg="gray",
        ).pack(side=tk.RIGHT, padx=5)

        mode_parts = ["v2.3.5"]
        if _IS_DEV:
            mode_parts.append("dev")
        if is_mock_mode():
            mode_parts.append("mock")
        mode_text = " ".join(mode_parts)
        fg = "#ff6b35" if is_mock_mode() else "gray"
        tk.Label(
            frame, text=mode_text, font=("Arial", 8), fg=fg,
        ).pack(side=tk.RIGHT, padx=5)

    # ── 设置对话框 ─────────────────────────────────────────

    def open_settings_dialog(self) -> None:
        """打开偏好设置对话框。"""
        SettingsDialog(
            parent=self.root,
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            refresh_interval=self.config.refresh_interval,
            startup_enabled=self.config.startup_enabled,
            auto_monitor=self.config.auto_monitor,
            on_save=self._on_settings_saved,
        )

    def _on_settings_saved(
        self, api_key: str, interval: int, startup_enabled: bool, auto_monitor: bool,
    ) -> None:
        """设置对话框保存后的回调。"""
        # 更新配置
        self.config.api_key = api_key
        self.config.refresh_interval = interval
        self.config.startup_enabled = startup_enabled
        self.config.auto_monitor = auto_monitor

        # 保存到文件
        if not self.config.save(api_key, interval):
            self.status_var.set("⚠️ 配置文件保存失败，设置可能不会持久化")

        # 处理开机自启动
        if startup_enabled:
            if not is_startup_enabled():
                if create_startup_shortcut():
                    self.status_var.set("✅ 设置已保存 — 已启用开机自启动")
                else:
                    self.status_var.set("⚠️ 设置已保存 — 开机自启动设置失败")
                    self.config.startup_enabled = False
        else:
            if is_startup_enabled():
                remove_startup_shortcut()
            self.status_var.set("✅ 设置已保存")

        # 更新主界面
        self.api_key_entry.delete(0, tk.END)
        self.api_key_entry.insert(0, api_key)
        self.interval_var.set(str(interval))

        # 更新状态栏
        self._refresh_status_bar()

    def _refresh_status_bar(self) -> None:
        """刷新状态栏中的自启动指示。"""
        # 状态栏是动态的，简单重建即可
        pass

    # ── 首次启动提示 ───────────────────────────────────────

    def _ask_startup_on_first_run(self) -> None:
        """首次运行时询问是否启用开机自启动（仅询问一次）。"""
        self.config.startup_asked = True
        if not self.config.save():
            pass  # 非关键，首次保存失败不影响后续操作

        response = messagebox.askyesno(
            "开机自启动",
            "是否设置开机自启动？\n\n"
            "启用后，软件会在 Windows 启动时自动运行。\n"
            "您也可以稍后在「设置 > 偏好设置」中更改此选项。",
        )
        if response:
            if create_startup_shortcut():
                self.config.startup_enabled = True
                if not self.config.save():
                    messagebox.showwarning(
                        "警告",
                        "配置保存失败，开机自启动设置可能不会持久化。",
                    )
                self.status_var.set("✅ 已启用开机自启动")
            else:
                messagebox.showwarning(
                    "提示",
                    "设置开机自启动失败。\n"
                    "您可以稍后在「设置 > 偏好设置」中重新尝试。",
                )
        else:
            self.config.startup_enabled = False
            self.config.save()

    # ── 首次设置向导 ───────────────────────────────────────

    def _show_setup_wizard(self) -> None:
        """显示首次运行设置向导。"""

        def on_complete(
            api_key: str, interval: int, startup_enabled: bool, auto_monitor: bool,
        ) -> None:
            # 更新配置
            self.config.api_key = api_key
            self.config.refresh_interval = interval
            self.config.startup_enabled = startup_enabled
            self.config.auto_monitor = auto_monitor
            self.config.startup_asked = True
            self.config.save(api_key, interval)

            # 处理开机自启动
            if startup_enabled:
                if not is_startup_enabled():
                    create_startup_shortcut()

            # 刷新 UI
            self.api_key_entry.delete(0, tk.END)
            self.api_key_entry.insert(0, api_key)
            self.interval_var.set(str(interval))
            self._refresh_status_bar()

            # 自动开始监控
            if auto_monitor and api_key:
                self.status_var.set("✅ 设置完成 — 正在开始监控...")
                self.root.after(300, self.auto_start_monitoring)
            else:
                self.status_var.set("✅ 设置完成")

        SetupWizard(
            parent=self.root,
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            refresh_interval=self.config.refresh_interval,
            on_complete=on_complete,
        )

    # ── 帮助 & 关于 ─────────────────────────────────────────

    def _open_user_guide(self) -> None:
        """打开用户使用指南。"""
        import os
        import webbrowser
        # 优先尝试打开本地文档
        local_guide = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), '..', 'docs', 'USER_GUIDE_CN.md',
        )
        if os.path.exists(local_guide):
            webbrowser.open(f"file:///{os.path.abspath(local_guide).replace(os.sep, '/')}")
        else:
            # 回退到在线文档
            webbrowser.open(_USER_GUIDE_URL)
        messagebox.showinfo(
            "使用指南", "正在浏览器中打开使用指南...",
        )

    def _show_about(self) -> None:
        """显示关于对话框。"""
        messagebox.showinfo(
            "关于 DeepSeek API 额度监控",
            "DeepSeek API 额度监控\n\n"
            f"版本: v2.3.5"
            f"{' (开发模式)' if _IS_DEV else ''}"
            f"{' (Mock)' if is_mock_mode() else ''}\n\n"
            "实时监控 DeepSeek API 账户余额。\n"
            "支持开机自启动、定时刷新、设置持久化。\n\n"
            "开源协议: MIT",
        )

    # ── 交互逻辑 ───────────────────────────────────────────

    def toggle_password(self) -> None:
        """切换密码显示/隐藏。"""
        self.show_pwd = not self.show_pwd
        if self.show_pwd:
            self.api_key_entry.config(show="")
            self.toggle_btn.config(text="🔒")
        else:
            self.api_key_entry.config(show="*")
            self.toggle_btn.config(text="👁")

    def save_settings(self) -> None:
        """保存设置到配置文件。"""
        api_key = self.api_key_entry.get().strip()
        if not api_key:
            messagebox.showwarning("警告", "请输入 API Key")
            return

        try:
            interval = int(self.interval_var.get())
        except ValueError:
            messagebox.showerror("错误", "刷新间隔必须是数字")
            return

        error = self.config.validate_interval(interval)
        if error:
            messagebox.showwarning("警告", error)
            return

        self.config.api_key = api_key
        self.config.refresh_interval = interval

        if self.config.save(api_key, interval):
            self.status_var.set("✅ 设置已保存")
            messagebox.showinfo("成功", "设置已成功保存到配置文件")
        else:
            self.status_var.set("❌ 设置保存失败")
            messagebox.showerror(
                "错误",
                "配置文件写入失败，请检查权限或磁盘空间。\n"
                f"配置路径: {self.config.config_file}",
            )

    def auto_start_monitoring(self) -> None:
        """自动启动监控（如果已配置 API key）。"""
        if self.config.api_key:
            self.start_monitoring()

    def refresh_once(self) -> None:
        """立即刷新一次额度信息。"""
        if not self.config.api_key:
            self.status_var.set("⚠️ 请先输入 API Key")
            return

        self.status_var.set("🔄 正在获取额度信息...")
        self.root.update()

        def fetch_data() -> None:
            try:
                data = get_api_quota(self.config.api_key, self.config.base_url)
                self.root.after(0, self._update_display, data)
                if "error" not in data:
                    self.root.after(0, lambda: self.status_var.set("✅ 数据已更新"))
                else:
                    self.root.after(0, lambda: self.status_var.set(f"❌ {data['error']}"))
            except Exception as exc:
                self.root.after(
                    0,
                    lambda e: self.status_var.set(f"❌ 获取数据失败: {str(e)}"),  # type: ignore[misc]
                    exc,
                )

        threading.Thread(target=fetch_data, daemon=True).start()

    def _update_display(self, data: dict[str, Any]) -> None:
        """更新额度显示区域。"""
        self.info_text.delete(1.0, tk.END)
        formatted = format_quota_info(data)
        self.info_text.insert(1.0, formatted)
        self.info_text.see(tk.END)

    def start_monitoring(self) -> None:
        """开始定时监控。"""
        api_key = self.api_key_entry.get().strip()
        if not api_key:
            messagebox.showwarning("警告", "请输入 API Key")
            return

        try:
            interval = int(self.interval_var.get())
        except ValueError:
            messagebox.showerror("错误", "刷新间隔必须是数字")
            return

        error = self.config.validate_interval(interval)
        if error:
            messagebox.showwarning("警告", error)
            return

        self.config.api_key = api_key
        self.config.refresh_interval = interval
        self.config.save(api_key, interval)

        self.monitoring = True
        self._set_controls_state(tk.DISABLED)

        self.status_var.set(f"🔄 开始监控 - 每{self.config.refresh_interval}秒自动更新")
        self.update_timer()

        threading.Thread(target=self._monitoring_loop, daemon=True).start()
        self.refresh_once()

    def stop_monitoring(self) -> None:
        """停止定时监控。"""
        self.monitoring = False
        self._set_controls_state(tk.NORMAL)
        self.timer_label.config(text="⏱ 监控已停止")
        self.status_var.set("⏹️ 监控已停止")

    def _set_controls_state(self, state: str) -> None:
        """批量设置控件状态。"""
        self.start_btn.config(state=state)  # type: ignore[call-overload]
        self.stop_btn.config(state=tk.NORMAL if state == tk.DISABLED else tk.DISABLED)  # type: ignore[call-overload]
        self.refresh_btn.config(state=state)  # type: ignore[call-overload]
        self.api_key_entry.config(state=state)  # type: ignore[call-overload]
        self.interval_entry.config(state=state)  # type: ignore[call-overload]
        self.save_btn.config(state=state)  # type: ignore[call-overload]

    def _monitoring_loop(self) -> None:
        """后台监控循环（运行在守护线程中）。"""
        while self.monitoring:
            api_key = self.api_key_entry.get().strip()
            if api_key:
                self.config.api_key = api_key
                data = get_api_quota(api_key, self.config.base_url)
                self.root.after(0, self._update_display, data)
                if "error" not in data:
                    self.root.after(0, lambda: self.status_var.set(
                        f"✅ 监控中 - 每{self.config.refresh_interval}秒自动更新"
                    ))
                else:
                    self.root.after(0, lambda: self.status_var.set(
                        f"⚠️ 监控中 - {data['error']}"
                    ))
            for _ in range(self.config.refresh_interval):
                if not self.monitoring:
                    break
                time.sleep(1)

    def update_timer(self) -> None:
        """更新倒计时显示。"""
        if self.monitoring:
            remaining = (self.config.refresh_interval
                         - (time.time() % self.config.refresh_interval))
            if remaining < 0:
                remaining = self.config.refresh_interval
            self.timer_label.config(text=f"⏱ 下次刷新: {int(remaining)} 秒后")
            self.root.after(1000, self.update_timer)
