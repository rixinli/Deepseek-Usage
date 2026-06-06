"""首次运行设置向导 — 引导用户完成初始配置。

当检测到无已有配置或未设置 API Key 时自动弹出。
"""

from __future__ import annotations

import threading
import tkinter as tk
import webbrowser
from collections.abc import Callable
from tkinter import messagebox, ttk

from .monitor import get_api_quota


# ── 步骤定义 ────────────────────────────────────────────────

_STEPS = [
    {"title": "欢迎", "icon": "🎉"},
    {"title": "API Key", "icon": "🔑"},
    {"title": "偏好设置", "icon": "⚙️"},
    {"title": "完成", "icon": "✅"},
]

# ── 字体常量 ────────────────────────────────────────────────
# 统一管理字体，确保 tk 控件与 ttk 控件字体一致

_FONT_FAMILY = "Arial"          # 界面字体
_FONT_MONO = "Consolas"         # 等宽字体（API Key 输入）
_FONT_SIZE_NORMAL = 10          # 正文/按钮字号
_FONT_SIZE_SMALL = 9            # 辅助信息字号
_FONT_SIZE_TITLE = 14           # 页面标题字号
_FONT_SIZE_LARGE = 18           # 欢迎页大字
_FONT_SIZE_STEP = 9             # 步骤条字号
_FONT_SIZE_LINK = 9             # 链接字号
_FONT_SIZE_BTN = 10             # 导航按钮字号
_FONT_SIZE_BTN_SMALL = 9        # 小按钮（跳过/显示/测试）字号


class SetupWizard:
    """首次运行设置向导 (多页 Toplevel 对话框)。

    页面顺序: 欢迎 → API Key → 偏好设置 → 完成
    """

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
        self.parent = parent
        self.base_url = base_url
        self.on_complete = on_complete

        self.api_key = api_key
        self.refresh_interval = refresh_interval
        self.startup_enabled = False
        self.auto_monitor = False

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("欢迎使用 DeepSeek API 额度监控")
        self.dialog.geometry("560x520")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self._center_window()
        self._build_ui()
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_close)

        parent.wait_window(self.dialog)

    # ── 窗口定位 ─────────────────────────────────────────────

    def _center_window(self) -> None:
        self.dialog.update_idletasks()
        pw = self.parent.winfo_width()
        ph = self.parent.winfo_height()
        px = self.parent.winfo_rootx()
        py = self.parent.winfo_rooty()
        dw, dh = 560, 520
        x = px + (pw - dw) // 2
        y = py + (ph - dh) // 2
        self.dialog.geometry(f"{dw}x{dh}+{x}+{y}")

    # ── 顶部步骤条 ──────────────────────────────────────────

    def _build_step_bar(self, parent: tk.Frame) -> None:
        """构建顶部步骤指示条（左侧步骤名 + 右侧步骤圆点）。"""
        bar = tk.Frame(parent, bg="#f0f0f0", height=48)
        bar.pack(fill=tk.X, pady=(0, 0))
        bar.pack_propagate(False)

        # 左侧：步骤标题
        self.step_title_var = tk.StringVar(value="🎉 欢迎")
        title_label = tk.Label(
            bar, textvariable=self.step_title_var,
            font=(_FONT_FAMILY, _FONT_SIZE_TITLE, "bold"), bg="#f0f0f0", fg="#333",
        )
        title_label.pack(side=tk.LEFT, padx=16, pady=10)

        # 右侧：步骤圆点 (○ ○ ● ○)
        self.step_dots_frame = tk.Frame(bar, bg="#f0f0f0")
        self.step_dots_frame.pack(side=tk.RIGHT, padx=16, pady=12)

        self.step_dot_labels: list[tk.Label] = []
        for i, step in enumerate(_STEPS):
            label = tk.Label(
                self.step_dots_frame,
                text=f" {step['icon']} {i+1}. {step['title']} ",
                font=(_FONT_FAMILY, _FONT_SIZE_STEP),
                bg="#f0f0f0",
                fg="#999" if i > 0 else "#007bff",
            )
            label.pack(side=tk.LEFT, padx=1)
            self.step_dot_labels.append(label)

        # 分隔线
        sep = tk.Frame(parent, bg="#ddd", height=1)
        sep.pack(fill=tk.X)

    # ── UI 构建 ─────────────────────────────────────────────

    def _build_ui(self) -> None:
        # 主容器 — 用 pack 确保按钮区域始终可见
        outer = tk.Frame(self.dialog)
        outer.pack(fill=tk.BOTH, expand=True)

        # 顶部步骤条
        self._build_step_bar(outer)

        # 中间内容区（固定高度，不挤压按钮区）
        content_area = tk.Frame(outer, height=340)
        content_area.pack(fill=tk.BOTH, expand=False, padx=0, pady=0)
        content_area.pack_propagate(False)

        self.notebook = ttk.Notebook(content_area)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.pages: list[ttk.Frame] = []
        for _ in range(4):
            page = ttk.Frame(self.notebook)
            self.notebook.add(page, text="")
            self.pages.append(page)

        self._build_welcome_page()
        self._build_api_key_page()
        self._build_preferences_page()
        self._build_complete_page()

        # 底部按钮栏（独立区域，确保始终可见）
        self._build_bottom_bar(outer)

        self.current_page = self.PAGE_WELCOME
        self._show_page(self.PAGE_WELCOME)

    # ── 底部按钮栏 ──────────────────────────────────────────

    def _build_bottom_bar(self, parent: tk.Frame) -> None:
        """构建底部按钮栏 — 始终固定在对话框底部。"""
        sep = tk.Frame(parent, bg="#ddd", height=1)
        sep.pack(fill=tk.X)

        bar = tk.Frame(parent, bg="#fafafa", height=56)
        bar.pack(fill=tk.X, side=tk.BOTTOM)
        bar.pack_propagate(False)

        # 左侧：跳过按钮
        self.skip_btn = tk.Button(
            bar, text="跳过设置", command=self._on_close,
            font=(_FONT_FAMILY, _FONT_SIZE_BTN_SMALL), fg="#999", bg="#fafafa",
            relief=tk.FLAT, cursor="hand2",
            activebackground="#f0f0f0", activeforeground="#666",
        )
        self.skip_btn.pack(side=tk.LEFT, padx=16, pady=12)

        # 右侧按钮组
        btn_group = tk.Frame(bar, bg="#fafafa")
        btn_group.pack(side=tk.RIGHT, padx=12, pady=10)

        # 上一步按钮
        self.back_btn = tk.Button(
            btn_group, text="◀ 上一步", command=self._on_back,
            font=(_FONT_FAMILY, _FONT_SIZE_BTN), width=10,
            bg="#e9ecef", fg="#333",
            relief=tk.FLAT, cursor="hand2",
            activebackground="#dee2e6",
        )
        self.back_btn.pack(side=tk.LEFT, padx=(0, 8))

        # 下一步 / 完成按钮（主按钮，显眼）
        self.next_btn = tk.Button(
            btn_group, text="下一步 ▶", command=self._on_next,
            font=(_FONT_FAMILY, _FONT_SIZE_BTN, "bold"), width=12,
            bg="#007bff", fg="white",
            relief=tk.FLAT, cursor="hand2",
            activebackground="#0069d9", activeforeground="white",
        )
        self.next_btn.pack(side=tk.LEFT)

    # ── 页面构建 ────────────────────────────────────────────

    def _build_welcome_page(self) -> None:
        page = self.pages[self.PAGE_WELCOME]
        content = ttk.Frame(page, padding=30)
        content.pack(fill=tk.BOTH, expand=True)

        ttk.Label(content, text="🎉 欢迎使用", font=(_FONT_FAMILY, _FONT_SIZE_LARGE, "bold")).pack(pady=(10, 5))
        ttk.Label(content, text="DeepSeek API 额度监控", font=(_FONT_FAMILY, _FONT_SIZE_TITLE)).pack(pady=(0, 20))

        features = [
            "📊 实时监控 DeepSeek API 账户余额和用量",
            "🔄 定时自动刷新，无需手动查询",
            "🚀 支持开机自启动，后台静默运行",
            "💾 配置持久化保存，一次设置永久生效",
        ]
        for f in features:
            ttk.Label(content, text=f, font=(_FONT_FAMILY, _FONT_SIZE_NORMAL)).pack(anchor=tk.W, pady=6, padx=20)

        ttk.Label(
            content, text="\n此向导将引导您完成初始配置。",
            font=(_FONT_FAMILY, _FONT_SIZE_SMALL), foreground="gray",
        ).pack(pady=(20, 0))

    def _build_api_key_page(self) -> None:
        page = self.pages[self.PAGE_API_KEY]
        content = ttk.Frame(page, padding=30)
        content.pack(fill=tk.BOTH, expand=True)

        ttk.Label(content, text="🔑 配置 API Key", font=(_FONT_FAMILY, _FONT_SIZE_TITLE, "bold")).pack(pady=(10, 5))
        ttk.Label(
            content,
            text="请输入您的 DeepSeek API Key，可从 DeepSeek 开放平台获取。",
            font=(_FONT_FAMILY, _FONT_SIZE_NORMAL), wraplength=460,
        ).pack(pady=(0, 15))

        # API Key 输入
        entry_frame = ttk.Frame(content)
        entry_frame.pack(fill=tk.X, pady=5, padx=10)

        self.wizard_api_var = tk.StringVar(value=self.api_key)
        self.wizard_api_entry = ttk.Entry(
            entry_frame, textvariable=self.wizard_api_var,
            show="*", width=40, font=(_FONT_MONO, _FONT_SIZE_NORMAL),
        )
        self.wizard_api_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.wizard_show_key = False
        self.wizard_toggle_btn = tk.Button(
            entry_frame, text="👁 显示", command=self._wizard_toggle_key,
            font=(_FONT_FAMILY, _FONT_SIZE_BTN_SMALL), width=8,
            bg="#e9ecef", fg="#333", relief=tk.FLAT, cursor="hand2",
            activebackground="#dee2e6",
        )
        self.wizard_toggle_btn.pack(side=tk.LEFT, padx=(8, 0))

        # 链接 — 点击打开浏览器访问 DeepSeek API Key 页面
        link = tk.Label(
            content,
            text="🔗 获取 API Key",
            fg="#007bff", font=(_FONT_FAMILY, _FONT_SIZE_LINK, "underline"), cursor="hand2",
        )
        link.bind("<Button-1>", lambda e: webbrowser.open("https://platform.deepseek.com/api_keys"))
        link.pack(anchor=tk.W, padx=10, pady=(8, 20))

        # 测试连接
        test_frame = ttk.Frame(content)
        test_frame.pack(fill=tk.X, pady=5, padx=10)

        self.wizard_test_btn = tk.Button(
            test_frame, text="🔍 测试连接", command=self._wizard_test_connection,
            font=(_FONT_FAMILY, _FONT_SIZE_BTN_SMALL),
            bg="#e9ecef", fg="#333", relief=tk.FLAT, cursor="hand2",
            activebackground="#dee2e6",
        )
        self.wizard_test_btn.pack(side=tk.LEFT)

        self.wizard_test_status = tk.StringVar(value="")
        ttk.Label(
            test_frame, textvariable=self.wizard_test_status,
            foreground="gray", font=(_FONT_FAMILY, _FONT_SIZE_SMALL),
        ).pack(side=tk.LEFT, padx=(10, 0))

    def _build_preferences_page(self) -> None:
        page = self.pages[self.PAGE_PREFERENCES]

        # 外层容器 — 标题和说明不滚动
        outer = ttk.Frame(page)
        outer.pack(fill=tk.BOTH, expand=True)

        ttk.Label(outer, text="⚙️ 偏好设置", font=(_FONT_FAMILY, _FONT_SIZE_TITLE, "bold")).pack(pady=(10, 5))
        ttk.Label(outer, text="根据您的使用习惯进行设置。", font=(_FONT_FAMILY, _FONT_SIZE_NORMAL)).pack(pady=(0, 5))

        # 可滚动的中间区域 — Canvas + Scrollbar + 内部 Frame
        canvas_frame = ttk.Frame(outer)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        canvas = tk.Canvas(canvas_frame, highlightthickness=0, borderwidth=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable = ttk.Frame(canvas)

        # 更新滚动区域 + 让内部 Frame 宽度跟随 Canvas
        def _configure_canvas(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        scrollable.bind("<Configure>", _configure_canvas)

        def _configure_frame(event):
            canvas.itemconfig(canvas_window_id, width=event.width)
        canvas.bind("<Configure>", _configure_frame)

        canvas_window_id = canvas.create_window((0, 0), window=scrollable, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 保存 canvas 引用供 _update_scroll_binding 使用
        self._prefs_canvas = canvas

        # --- 以下内容放入 scrollable ---
        pad_frame = ttk.Frame(scrollable, padding=(30, 5, 30, 20))
        pad_frame.pack(fill=tk.BOTH, expand=True)

        # 刷新间隔
        f1 = ttk.LabelFrame(pad_frame, text="🔄 刷新间隔", padding=12)
        f1.pack(fill=tk.X, pady=6)

        self.wizard_interval_var = tk.IntVar(value=self.refresh_interval)
        sf = ttk.Frame(f1)
        sf.pack(fill=tk.X)
        spinbox = ttk.Spinbox(sf, from_=30, to=600, increment=10,
                              textvariable=self.wizard_interval_var, width=7)
        spinbox.pack(side=tk.LEFT)
        # 为 Spinbox 设置字体（ttk 控件需通过 style 配置）
        style = ttk.Style()
        style.configure("Wizard.TSpinbox", font=(_FONT_FAMILY, _FONT_SIZE_NORMAL))
        spinbox.configure(style="Wizard.TSpinbox")
        ttk.Label(sf, text="  秒（推荐 120-300）", font=(_FONT_FAMILY, _FONT_SIZE_SMALL), foreground="gray").pack(side=tk.LEFT)

        # 开机自启动
        f2 = ttk.LabelFrame(pad_frame, text="🚀 开机自启动", padding=12)
        f2.pack(fill=tk.X, pady=6)

        self.wizard_startup_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            f2, text="Windows 登录时自动启动本软件",
            variable=self.wizard_startup_var,
        ).pack(anchor=tk.W)

        # 自动监控
        f3 = ttk.LabelFrame(pad_frame, text="📊 自动监控", padding=12)
        f3.pack(fill=tk.X, pady=6)

        self.wizard_auto_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            f3, text="启动软件后自动开始监控 API 额度",
            variable=self.wizard_auto_var,
        ).pack(anchor=tk.W)

    def _build_complete_page(self) -> None:
        page = self.pages[self.PAGE_COMPLETE]
        content = ttk.Frame(page, padding=30)
        content.pack(fill=tk.BOTH, expand=True)

        ttk.Label(content, text="✅ 设置完成", font=(_FONT_FAMILY, _FONT_SIZE_LARGE, "bold")).pack(pady=(10, 10))

        self.wizard_summary_var = tk.StringVar(value="")
        ttk.Label(
            content, textvariable=self.wizard_summary_var,
            font=(_FONT_MONO, _FONT_SIZE_NORMAL), justify=tk.LEFT,
        ).pack(pady=(5, 10))

        ttk.Label(
            content,
            text="点击下方「保存并开始使用」完成设置。\n"
                 "您可以随时在菜单「设置 > 偏好设置」中修改以上配置。",
            font=(_FONT_FAMILY, _FONT_SIZE_SMALL), foreground="gray", justify=tk.CENTER,
        ).pack(pady=(10, 0))

    # ── 页面导航 ─────────────────────────────────────────────

    def _show_page(self, index: int) -> None:
        self.current_page = index
        self.notebook.select(index)
        self._update_step_indicators()
        self._update_buttons()
        self._update_scroll_binding()

    def _update_step_indicators(self) -> None:
        """更新步骤条：标题 + 高亮当前步骤。"""
        step = _STEPS[self.current_page]
        self.step_title_var.set(f"{step['icon']} {step['title']}")

        for i, label in enumerate(self.step_dot_labels):
            if i == self.current_page:
                label.config(fg="#007bff", font=(_FONT_FAMILY, _FONT_SIZE_STEP, "bold"))
            elif i < self.current_page:
                label.config(fg="#28a745", font=(_FONT_FAMILY, _FONT_SIZE_STEP))
            else:
                label.config(fg="#999", font=(_FONT_FAMILY, _FONT_SIZE_STEP))

    def _update_buttons(self) -> None:
        """更新导航按钮状态。"""
        # 上一步：首页隐藏
        if self.current_page == self.PAGE_WELCOME:
            self.back_btn.pack_forget()
        else:
            self.back_btn.pack(side=tk.LEFT, padx=(0, 8), before=self.next_btn)

        # 下一步 / 完成按钮
        if self.current_page == self.PAGE_COMPLETE:
            self.next_btn.config(
                text="保存",
                command=self._on_finish,
                bg="#28a745",
                activebackground="#218838",
            )
        else:
            self.next_btn.config(
                text="下一步 ▶",
                command=self._on_next,
                bg="#007bff",
                activebackground="#0069d9",
            )

        # 跳过按钮：仅在首页和 API Key 页显示
        if self.current_page <= self.PAGE_API_KEY:
            self.skip_btn.pack(side=tk.LEFT, padx=16, pady=12)
        else:
            self.skip_btn.pack_forget()

    # ── 滚动绑定管理 ─────────────────────────────────────────

    def _update_scroll_binding(self) -> None:
        """页面切换时管理偏好设置页的鼠标滚轮绑定。"""
        # 先解绑所有页面的滚轮事件（避免全局污染）
        self.dialog.unbind_all("<MouseWheel>")
        # 仅在偏好设置页启用滚轮
        if self.current_page == self.PAGE_PREFERENCES and hasattr(self, "_prefs_canvas"):
            canvas = self._prefs_canvas
            def _on_mousewheel(event):
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            self.dialog.bind_all("<MouseWheel>", _on_mousewheel)

    # ── 导航事件 ─────────────────────────────────────────────

    def _on_back(self) -> None:
        if self.current_page > self.PAGE_WELCOME:
            self._show_page(self.current_page - 1)

    def _on_next(self) -> None:
        if self.current_page == self.PAGE_API_KEY:
            api_key = self.wizard_api_var.get().strip()
            if not api_key:
                messagebox.showwarning(
                    "提示",
                    "请输入您的 DeepSeek API Key 以继续。\n\n"
                    "如果还没有 API Key，请访问:\n"
                    "https://platform.deepseek.com/api_keys",
                    parent=self.dialog,
                )
                return
            self.api_key = api_key

        elif self.current_page == self.PAGE_PREFERENCES:
            self.refresh_interval = self.wizard_interval_var.get()
            self.startup_enabled = self.wizard_startup_var.get()
            self.auto_monitor = self.wizard_auto_var.get()
            self._update_summary()

        self._show_page(self.current_page + 1)

    def _update_summary(self) -> None:
        startup = "✓ 是" if self.startup_enabled else "✗ 否"
        auto = "✓ 是" if self.auto_monitor else "✗ 否"
        key_preview = (
            self.api_key[:8] + "..." + self.api_key[-4:]
            if len(self.api_key) > 16 else self.api_key
        )
        self.wizard_summary_var.set(
            f"  API Key:     {key_preview}\n"
            f"  刷新间隔:    {self.refresh_interval} 秒\n"
            f"  开机自启动:  {startup}\n"
            f"  自动监控:    {auto}"
        )

    def _on_finish(self) -> None:
        if self.on_complete:
            self.on_complete(
                self.api_key, self.refresh_interval,
                self.startup_enabled, self.auto_monitor,
            )
        self.dialog.destroy()

    def _on_close(self) -> None:
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

    # ── API Key 交互 ─────────────────────────────────────────

    def _wizard_toggle_key(self) -> None:
        self.wizard_show_key = not self.wizard_show_key
        if self.wizard_show_key:
            self.wizard_api_entry.config(show="")
            self.wizard_toggle_btn.config(text="🔒 隐藏")
        else:
            self.wizard_api_entry.config(show="*")
            self.wizard_toggle_btn.config(text="👁 显示")

    def _wizard_test_connection(self) -> None:
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
                    self.dialog.after(0, lambda: self.wizard_test_status.set(
                        f"❌ 连接失败: {data['error']}"
                    ))
                else:
                    self.dialog.after(0, lambda: self.wizard_test_status.set(
                        "✅ 连接成功！API Key 有效"
                    ))
            except Exception as exc:
                self.dialog.after(0, lambda e: self.wizard_test_status.set(
                    f"❌ 网络错误: {str(e)}"
                ), exc)
            finally:
                self.dialog.after(0, lambda: self.wizard_test_btn.config(state=tk.NORMAL))

        threading.Thread(target=do_test, daemon=True).start()
