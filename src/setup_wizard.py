"""首次运行设置向导 — 引导用户完成初始配置。

当检测到无已有配置或未设置 API Key 时自动弹出。
"""

from __future__ import annotations

import threading
import tkinter as tk
from collections.abc import Callable
from tkinter import messagebox, ttk

from .monitor import get_api_quota


class SetupWizard:
    """首次运行设置向导 (多页 Toplevel 对话框)。

    页面顺序: 欢迎 → API Key → 偏好设置 → 完成
    """

    # 页面索引常量
    PAGE_WELCOME = 0
    PAGE_API_KEY = 1
    PAGE_PREFERENCES = 2
    PAGE_COMPLETE = 3

    def __init__(
        self,
        parent: tk.Tk,
        api_key: str = "",
        base_url: str = "https://api.deepseek.com",
        refresh_interval: int = 120,
        on_complete: Callable | None = None,
    ):
        """初始化设置向导。

        Args:
            parent: 父窗口。
            api_key: 当前 API Key（通常为空）。
            base_url: API Base URL。
            refresh_interval: 当前刷新间隔。
            on_complete: 完成回调，接收 (api_key, interval, startup_enabled, auto_monitor)。
        """
        self.parent = parent
        self.base_url = base_url
        self.on_complete = on_complete

        # 用户选择的值
        self.api_key = api_key
        self.refresh_interval = refresh_interval
        self.startup_enabled = False
        self.auto_monitor = False

        # 创建对话框
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("欢迎使用 DeepSeek API 额度监控")
        self.dialog.geometry("540x440")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self._center_window()
        self._build_ui()

        # 拦截窗口关闭按钮（视为取消）
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_close)

        parent.wait_window(self.dialog)

    # ── 窗口定位 ─────────────────────────────────────────────

    def _center_window(self) -> None:
        """将对话框居中于父窗口。"""
        self.dialog.update_idletasks()
        pw = self.parent.winfo_width()
        ph = self.parent.winfo_height()
        px = self.parent.winfo_rootx()
        py = self.parent.winfo_rooty()
        dw, dh = 540, 440
        x = px + (pw - dw) // 2
        y = py + (ph - dh) // 2
        self.dialog.geometry(f"{dw}x{dh}+{x}+{y}")

    # ── UI 构建 ─────────────────────────────────────────────

    def _build_ui(self) -> None:
        """构建向导 UI 框架。"""
        # 主容器
        main = ttk.Frame(self.dialog, padding=15)
        main.pack(fill=tk.BOTH, expand=True)

        # 步骤指示器
        self.step_var = tk.StringVar(value="步骤 1 / 4")
        ttk.Label(
            main, textvariable=self.step_var,
            font=("", 9), foreground="gray",
        ).pack(anchor=tk.E, pady=(0, 5))

        # 页面容器（Notebook 隐藏标签栏）
        self.notebook = ttk.Notebook(main)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # 创建四个页面
        self.pages: list[ttk.Frame] = []
        for _ in range(4):
            page = ttk.Frame(self.notebook)
            self.notebook.add(page, text="")
            self.pages.append(page)

        self._build_welcome_page()
        self._build_api_key_page()
        self._build_preferences_page()
        self._build_complete_page()

        # 导航按钮
        self._build_navigation(main)

        # 显示第一页
        self.current_page = self.PAGE_WELCOME
        self._show_page(self.PAGE_WELCOME)

    def _build_welcome_page(self) -> None:
        """构建欢迎页。"""
        page = self.pages[self.PAGE_WELCOME]
        content = ttk.Frame(page, padding=20)
        content.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            content, text="🎉 欢迎使用",
            font=("Arial", 18, "bold"),
        ).pack(pady=(30, 10))

        ttk.Label(
            content, text="DeepSeek API 额度监控",
            font=("Arial", 14),
        ).pack(pady=(0, 20))

        features = [
            "📊 实时监控 DeepSeek API 账户余额",
            "🔄 定时自动刷新，无需手动查询",
            "🚀 支持开机自启动，静默运行",
            "💾 配置持久化保存，一次设置永久生效",
        ]
        for f in features:
            ttk.Label(
                content, text=f, font=("", 10),
            ).pack(anchor=tk.W, pady=3, padx=40)

        ttk.Label(
            content,
            text="\n此向导将帮助您完成初始设置。",
            font=("", 9), foreground="gray",
        ).pack(pady=(20, 0))

    def _build_api_key_page(self) -> None:
        """构建 API Key 输入页。"""
        page = self.pages[self.PAGE_API_KEY]
        content = ttk.Frame(page, padding=20)
        content.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            content, text="🔑 配置 API Key",
            font=("Arial", 14, "bold"),
        ).pack(pady=(20, 10))

        ttk.Label(
            content,
            text="请输入您的 DeepSeek API Key。\n"
                 "您可以从 DeepSeek 开放平台获取。",
            font=("", 10), wraplength=460,
        ).pack(pady=(0, 15))

        # API Key 输入
        entry_frame = ttk.Frame(content)
        entry_frame.pack(fill=tk.X, pady=5, padx=20)

        self.wizard_api_var = tk.StringVar(value=self.api_key)
        self.wizard_api_entry = ttk.Entry(
            entry_frame, textvariable=self.wizard_api_var,
            show="*", width=40, font=("Consolas", 10),
        )
        self.wizard_api_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.wizard_show_key = False
        self.wizard_toggle_btn = ttk.Button(
            entry_frame, text="👁 显示",
            command=self._wizard_toggle_key, width=8,
        )
        self.wizard_toggle_btn.pack(side=tk.LEFT, padx=(5, 0))

        # 获取 API Key 链接
        ttk.Label(
            content,
            text="🔗 获取 API Key: https://platform.deepseek.com/api_keys",
            foreground="#007bff", font=("", 8, "underline"),
            cursor="hand2",
        ).pack(anchor=tk.W, padx=20, pady=(5, 15))

        # 测试连接区域
        test_frame = ttk.Frame(content)
        test_frame.pack(fill=tk.X, pady=5, padx=20)

        self.wizard_test_btn = ttk.Button(
            test_frame, text="🔍 测试连接",
            command=self._wizard_test_connection,
        )
        self.wizard_test_btn.pack(side=tk.LEFT)

        self.wizard_test_status = tk.StringVar(value="")
        ttk.Label(
            test_frame, textvariable=self.wizard_test_status,
            foreground="gray", font=("", 8),
        ).pack(side=tk.LEFT, padx=(10, 0))

    def _build_preferences_page(self) -> None:
        """构建设置偏好页。"""
        page = self.pages[self.PAGE_PREFERENCES]
        content = ttk.Frame(page, padding=20)
        content.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            content, text="⚙️ 偏好设置",
            font=("Arial", 14, "bold"),
        ).pack(pady=(20, 10))

        ttk.Label(
            content,
            text="根据您的使用习惯，选择以下设置。",
            font=("", 10),
        ).pack(pady=(0, 20))

        # 刷新间隔
        interval_frame = ttk.LabelFrame(content, text="刷新间隔", padding=10)
        interval_frame.pack(fill=tk.X, padx=10, pady=5)

        self.wizard_interval_var = tk.IntVar(value=self.refresh_interval)
        spin_frame = ttk.Frame(interval_frame)
        spin_frame.pack(fill=tk.X)

        ttk.Spinbox(
            spin_frame, from_=30, to=600, increment=10,
            textvariable=self.wizard_interval_var, width=8,
        ).pack(side=tk.LEFT)

        ttk.Label(
            spin_frame,
            text="  秒（推荐 120-300 秒）",
            font=("", 9), foreground="gray",
        ).pack(side=tk.LEFT)

        # 开机自启动
        startup_frame = ttk.LabelFrame(content, text="开机自启动", padding=10)
        startup_frame.pack(fill=tk.X, padx=10, pady=5)

        self.wizard_startup_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            startup_frame,
            text="Windows 登录时自动启动本软件",
            variable=self.wizard_startup_var,
        ).pack(anchor=tk.W)

        # 自动监控
        auto_frame = ttk.LabelFrame(content, text="自动监控", padding=10)
        auto_frame.pack(fill=tk.X, padx=10, pady=5)

        self.wizard_auto_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            auto_frame,
            text="启动软件后自动开始监控",
            variable=self.wizard_auto_var,
        ).pack(anchor=tk.W)

    def _build_complete_page(self) -> None:
        """构建完成页。"""
        page = self.pages[self.PAGE_COMPLETE]
        content = ttk.Frame(page, padding=20)
        content.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            content, text="✅ 设置完成",
            font=("Arial", 18, "bold"),
        ).pack(pady=(30, 15))

        self.wizard_summary_var = tk.StringVar(value="")
        ttk.Label(
            content, textvariable=self.wizard_summary_var,
            font=("Consolas", 10), justify=tk.LEFT,
        ).pack(pady=(0, 15))

        ttk.Label(
            content,
            text="点击「完成」按钮开始使用。\n"
                 "您可以随时在「设置 > 偏好设置」中修改以上配置。",
            font=("", 9), foreground="gray", justify=tk.CENTER,
        ).pack(pady=(10, 0))

    def _build_navigation(self, parent: ttk.Frame) -> None:
        """构建底部导航按钮。"""
        nav_frame = ttk.Frame(parent)
        nav_frame.pack(fill=tk.X, pady=(10, 0))

        # 提示信息
        self.wizard_nav_hint = tk.StringVar(value="")
        ttk.Label(
            nav_frame, textvariable=self.wizard_nav_hint,
            font=("", 8), foreground="gray",
        ).pack(side=tk.LEFT)

        self.back_btn = ttk.Button(
            nav_frame, text="◀ 上一步", command=self._on_back, width=10,
        )
        self.back_btn.pack(side=tk.RIGHT, padx=(5, 0))

        self.next_btn = ttk.Button(
            nav_frame, text="下一步 ▶", command=self._on_next, width=12,
        )
        self.next_btn.pack(side=tk.RIGHT)

    # ── 页面导航 ─────────────────────────────────────────────

    def _show_page(self, index: int) -> None:
        """切换到指定页面。"""
        self.current_page = index
        self.notebook.select(index)
        self._update_navigation()
        self._update_step()

    def _update_step(self) -> None:
        """更新步骤指示器。"""
        labels = ["步骤 1 / 4 — 欢迎", "步骤 2 / 4 — API Key",
                  "步骤 3 / 4 — 偏好设置", "步骤 4 / 4 — 完成"]
        self.step_var.set(labels[self.current_page])

    def _update_navigation(self) -> None:
        """更新导航按钮状态。"""
        # 上一步按钮
        if self.current_page == self.PAGE_WELCOME:
            self.back_btn.config(state=tk.DISABLED)
        else:
            self.back_btn.config(state=tk.NORMAL)

        # 下一步 / 完成按钮
        if self.current_page == self.PAGE_COMPLETE:
            self.next_btn.config(text="✨ 完成", command=self._on_finish)
            self.wizard_nav_hint.set("")
        else:
            self.next_btn.config(text="下一步 ▶", command=self._on_next)
            self.wizard_nav_hint.set("")

    # ── 导航事件 ─────────────────────────────────────────────

    def _on_back(self) -> None:
        """返回上一步。"""
        if self.current_page > self.PAGE_WELCOME:
            self._show_page(self.current_page - 1)

    def _on_next(self) -> None:
        """进入下一步。"""
        if self.current_page == self.PAGE_API_KEY:
            # 验证 API Key 不为空
            api_key = self.wizard_api_var.get().strip()
            if not api_key:
                messagebox.showwarning(
                    "提示", "请输入您的 DeepSeek API Key 以继续。\n\n"
                           "如果您还没有 API Key，请访问:\n"
                           "https://platform.deepseek.com/api_keys",
                    parent=self.dialog,
                )
                return
            # 保存用户输入
            self.api_key = api_key

        elif self.current_page == self.PAGE_PREFERENCES:
            # 保存用户选择
            self.refresh_interval = self.wizard_interval_var.get()
            self.startup_enabled = self.wizard_startup_var.get()
            self.auto_monitor = self.wizard_auto_var.get()
            # 更新完成页的摘要
            self._update_summary()

        self._show_page(self.current_page + 1)

    def _update_summary(self) -> None:
        """更新完成页的配置摘要。"""
        startup = "是" if self.startup_enabled else "否"
        auto = "是" if self.auto_monitor else "否"
        key_preview = (
            self.api_key[:8] + "..." + self.api_key[-4:]
            if len(self.api_key) > 16 else self.api_key
        )
        summary = (
            f"API Key:      {key_preview}\n"
            f"刷新间隔:     {self.refresh_interval} 秒\n"
            f"开机自启动:   {startup}\n"
            f"自动监控:     {auto}"
        )
        self.wizard_summary_var.set(summary)

    def _on_finish(self) -> None:
        """完成设置，保存并关闭。"""
        if self.on_complete:
            self.on_complete(
                self.api_key,
                self.refresh_interval,
                self.startup_enabled,
                self.auto_monitor,
            )
        self.dialog.destroy()

    def _on_close(self) -> None:
        """关闭窗口（用户点击 X）。"""
        # 如果已经完成了设置（在第4页点击完成），正常关闭
        # 否则询问是否跳过
        if self.current_page == self.PAGE_COMPLETE:
            self._on_finish()
        else:
            if messagebox.askyesno(
                "跳过设置？",
                "您可以稍后在「设置 > 偏好设置」中配置 API Key。\n\n"
                "确定要跳过设置向导吗？",
                parent=self.dialog,
            ):
                self.dialog.destroy()

    # ── API Key 页面交互 ─────────────────────────────────────

    def _wizard_toggle_key(self) -> None:
        """切换 API Key 显示/隐藏。"""
        self.wizard_show_key = not self.wizard_show_key
        if self.wizard_show_key:
            self.wizard_api_entry.config(show="")
            self.wizard_toggle_btn.config(text="🔒 隐藏")
        else:
            self.wizard_api_entry.config(show="*")
            self.wizard_toggle_btn.config(text="👁 显示")

    def _wizard_test_connection(self) -> None:
        """测试 API Key 连接。"""
        api_key = self.wizard_api_var.get().strip()
        if not api_key:
            self.wizard_test_status.set("⚠️ 请先输入 API Key")
            return

        self.wizard_test_btn.config(state=tk.DISABLED)
        self.wizard_test_status.set("🔄 正在测试连接...")
        self.dialog.update()

        def do_test() -> None:
            try:
                data = get_api_quota(api_key, self.base_url)
                if "error" in data:
                    self.dialog.after(
                        0, lambda: self.wizard_test_status.set(
                            f"❌ 连接失败: {data['error']}"
                        )
                    )
                else:
                    self.dialog.after(
                        0, lambda: self.wizard_test_status.set(
                            "✅ 连接成功！API Key 有效"
                        )
                    )
            except Exception as exc:
                self.dialog.after(
                    0,
                    lambda e: self.wizard_test_status.set(f"❌ 网络错误: {str(e)}"),
                    exc,
                )
            finally:
                self.dialog.after(
                    0, lambda: self.wizard_test_btn.config(state=tk.NORMAL)
                )

        threading.Thread(target=do_test, daemon=True).start()
