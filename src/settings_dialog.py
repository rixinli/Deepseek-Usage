"""设置对话框 — 独立的偏好设置窗口。

提供 API Key 管理、刷新间隔调整、开机自启动开关等功能。
"""

import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable

from .monitor import get_api_quota


class SettingsDialog:
    """偏好设置对话框 (Toplevel)。"""

    def __init__(
        self,
        parent: tk.Tk,
        api_key: str = "",
        base_url: str = "https://api.deepseek.com",
        refresh_interval: int = 120,
        startup_enabled: bool = False,
        auto_monitor: bool = False,
        on_save: Callable | None = None,
        on_test_connection: Callable | None = None,
    ):
        """初始化设置对话框。

        Args:
            parent: 父窗口。
            api_key: 当前 API Key。
            base_url: API Base URL。
            refresh_interval: 当前刷新间隔（秒）。
            startup_enabled: 当前开机自启动状态。
            auto_monitor: 当前启动时自动监控状态。
            on_save: 保存回调，接收 (api_key, interval, startup, auto_monitor) 参数。
            on_test_connection: 测试连接回调（可选，用于自定义测试逻辑）。
        """
        self.parent = parent
        self.base_url = base_url
        self.on_save = on_save
        self.on_test_connection = on_test_connection

        # 保存初始值（用于取消时恢复）
        self.initial_api_key = api_key
        self.initial_interval = refresh_interval
        self.initial_startup = startup_enabled
        self.initial_auto_monitor = auto_monitor

        # 当前编辑中的值
        self.api_key = api_key
        self.refresh_interval = refresh_interval
        self.startup_enabled = startup_enabled
        self.auto_monitor = auto_monitor

        # 创建对话框窗口
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("偏好设置")
        self.dialog.geometry("520x400")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)  # 设为父窗口的子窗口
        self.dialog.grab_set()  # 模态

        # 居中显示
        self._center_window()

        self._build_ui()

        # 等待窗口关闭
        parent.wait_window(self.dialog)

    # ── 窗口定位 ─────────────────────────────────────────────

    def _center_window(self) -> None:
        """将对话框居中于父窗口。"""
        self.dialog.update_idletasks()
        pw, ph = self.parent.winfo_width(), self.parent.winfo_height()
        px, py = self.parent.winfo_rootx(), self.parent.winfo_rooty()
        dw = 520
        dh = 400
        x = px + (pw - dw) // 2
        y = py + (ph - dh) // 2
        self.dialog.geometry(f"{dw}x{dh}+{x}+{y}")

    # ── UI 构建 ─────────────────────────────────────────────

    def _build_ui(self) -> None:
        """构建对话框 UI。"""
        # 使用 Notebook 分标签页
        notebook = ttk.Notebook(self.dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 标签页1: API 设置
        api_frame = ttk.Frame(notebook, padding=10)
        notebook.add(api_frame, text="API 设置")
        self._build_api_tab(api_frame)

        # 标签页2: 通用设置
        general_frame = ttk.Frame(notebook, padding=10)
        notebook.add(general_frame, text="通用设置")
        self._build_general_tab(general_frame)

        # 底部按钮
        self._build_bottom_buttons()

    def _build_api_tab(self, parent: ttk.Frame) -> None:
        """构建 API 设置标签页。"""
        # API Key 输入
        key_frame = ttk.Frame(parent)
        key_frame.pack(fill=tk.X, pady=(10, 5))

        ttk.Label(key_frame, text="API Key:").pack(anchor=tk.W)

        entry_frame = ttk.Frame(key_frame)
        entry_frame.pack(fill=tk.X, pady=(5, 0))

        self.api_key_var = tk.StringVar(value=self.api_key)
        self.api_key_entry = ttk.Entry(
            entry_frame, textvariable=self.api_key_var, show="*", width=50,
        )
        self.api_key_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.show_key = False
        self.toggle_key_btn = ttk.Button(
            entry_frame, text="👁 显示", command=self._toggle_key_visibility, width=8,
        )
        self.toggle_key_btn.pack(side=tk.LEFT, padx=(5, 0))

        # 提示
        ttk.Label(
            parent, text="获取 API Key: https://platform.deepseek.com/api_keys",
            foreground="gray", font=("", 8),
        ).pack(anchor=tk.W, pady=(2, 10))

        # 测试连接按钮
        test_frame = ttk.Frame(parent)
        test_frame.pack(fill=tk.X, pady=5)

        self.test_btn = ttk.Button(
            test_frame, text="🔍 测试连接", command=self._test_connection,
        )
        self.test_btn.pack(side=tk.LEFT)

        self.test_status_var = tk.StringVar(value="")
        ttk.Label(
            test_frame, textvariable=self.test_status_var, foreground="gray",
        ).pack(side=tk.LEFT, padx=(10, 0))

        # 刷新间隔
        interval_frame = ttk.Frame(parent)
        interval_frame.pack(fill=tk.X, pady=(20, 10))

        ttk.Label(interval_frame, text="刷新间隔（秒）:").pack(anchor=tk.W)

        spin_frame = ttk.Frame(interval_frame)
        spin_frame.pack(fill=tk.X, pady=(5, 0))

        self.interval_var = tk.IntVar(value=self.refresh_interval)
        self.interval_spinbox = ttk.Spinbox(
            spin_frame, from_=30, to=600, increment=10,
            textvariable=self.interval_var, width=8,
        )
        self.interval_spinbox.pack(side=tk.LEFT)

        ttk.Label(
            spin_frame, text="范围: 30-600 秒，推荐 120-300 秒",
            foreground="gray", font=("", 8),
        ).pack(side=tk.LEFT, padx=(10, 0))

    def _build_general_tab(self, parent: ttk.Frame) -> None:
        """构建通用设置标签页。"""
        # 开机自启动
        self.startup_var = tk.BooleanVar(value=self.startup_enabled)
        startup_cb = ttk.Checkbutton(
            parent,
            text="开机自动启动（登录 Windows 时自动运行）",
            variable=self.startup_var,
        )
        startup_cb.pack(anchor=tk.W, pady=(15, 5))

        ttk.Label(
            parent,
            text="启用后，软件会在 Windows 启动时自动运行到系统托盘。",
            foreground="gray", font=("", 8), wraplength=450,
        ).pack(anchor=tk.W, padx=(25, 0))

        # 启动时自动监控
        self.auto_monitor_var = tk.BooleanVar(value=self.auto_monitor)
        auto_monitor_cb = ttk.Checkbutton(
            parent,
            text="启动时自动开始监控",
            variable=self.auto_monitor_var,
        )
        auto_monitor_cb.pack(anchor=tk.W, pady=(20, 5))

        ttk.Label(
            parent,
            text="启用后，打开软件时将自动开始定时刷新 API 额度信息。",
            foreground="gray", font=("", 8), wraplength=450,
        ).pack(anchor=tk.W, padx=(25, 0))

    def _build_bottom_buttons(self) -> None:
        """构建底部操作按钮。"""
        btn_frame = ttk.Frame(self.dialog)
        btn_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.status_var = tk.StringVar(value="")
        ttk.Label(
            btn_frame, textvariable=self.status_var, foreground="gray",
            font=("", 8),
        ).pack(side=tk.LEFT, padx=(0, 10))

        cancel_btn = ttk.Button(
            btn_frame, text="取消", command=self._on_cancel, width=10,
        )
        cancel_btn.pack(side=tk.RIGHT, padx=(5, 0))

        save_btn = ttk.Button(
            btn_frame, text="保存", command=self._on_save, width=10,
        )
        save_btn.pack(side=tk.RIGHT)

    # ── 交互逻辑 ───────────────────────────────────────────

    def _toggle_key_visibility(self) -> None:
        """切换 API Key 的显示/隐藏状态。"""
        self.show_key = not self.show_key
        if self.show_key:
            self.api_key_entry.config(show="")
            self.toggle_key_btn.config(text="🔒 隐藏")
        else:
            self.api_key_entry.config(show="*")
            self.toggle_key_btn.config(text="👁 显示")

    def _test_connection(self) -> None:
        """测试 API Key 连接是否有效。"""
        api_key = self.api_key_var.get().strip()
        if not api_key:
            self.test_status_var.set("⚠️ 请先输入 API Key")
            return

        self.test_btn.config(state=tk.DISABLED)
        self.test_status_var.set("🔄 正在测试连接...")
        self.dialog.update()

        def do_test() -> None:
            try:
                data = get_api_quota(api_key, self.base_url)
                if "error" in data:
                    self.dialog.after(
                        0, lambda: self.test_status_var.set(f"❌ {data['error']}")
                    )
                else:
                    self.dialog.after(
                        0, lambda: self.test_status_var.set("✅ 连接成功！API Key 有效")
                    )
            except Exception as exc:
                self.dialog.after(
                    0,
                    lambda e: self.test_status_var.set(f"❌ 测试失败: {str(e)}"),  # type: ignore[misc]
                    exc,
                )
            finally:
                self.dialog.after(
                    0, lambda: self.test_btn.config(state=tk.NORMAL)  # type: ignore[misc]
                )

        threading.Thread(target=do_test, daemon=True).start()

    def _on_save(self) -> None:
        """保存设置。"""
        api_key = self.api_key_var.get().strip()
        if not api_key:
            messagebox.showwarning("警告", "请输入 API Key", parent=self.dialog)
            return

        try:
            interval = int(self.interval_var.get())
        except ValueError:
            messagebox.showerror("错误", "刷新间隔必须是数字", parent=self.dialog)
            return

        if interval < 30 or interval > 600:
            messagebox.showwarning(
                "警告", "刷新间隔范围: 30-600 秒", parent=self.dialog,
            )
            return

        # 更新实例变量
        self.api_key = api_key
        self.refresh_interval = interval
        self.startup_enabled = self.startup_var.get()
        self.auto_monitor = self.auto_monitor_var.get()

        # 回调通知主窗口
        if self.on_save:
            self.on_save(api_key, interval, self.startup_enabled, self.auto_monitor)

        self.dialog.destroy()

    def _on_cancel(self) -> None:
        """取消设置（恢复初始值）。"""
        self.dialog.destroy()
