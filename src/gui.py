"""DeepSeek API 监控 — GUI 界面 (tkinter)。"""

import threading
import time
import tkinter as tk
from tkinter import messagebox, scrolledtext

from .config import AppConfig, is_dev_mode, load_env_file
from .monitor import format_quota_info, get_api_quota

# ── 模块级初始化（导入时执行一次）──────────────────────────
_IS_DEV = is_dev_mode()
load_env_file()


class DeepSeekAPIMonitor:
    """DeepSeek API 额度监控 GUI 应用。"""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("DeepSeek API 额度监控")
        self.root.geometry("650x550")

        self.config = AppConfig()
        self.config.load_ini_fallback()

        self.monitoring = False

        self.setup_ui()

        # 自动开始监控（如果有 API key）
        if self.config.api_key:
            self.root.after(500, self.auto_start_monitoring)

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

        mode_text = "v2.1 dev" if _IS_DEV else "v2.1"
        tk.Label(
            frame, text=mode_text, font=("Arial", 8), fg="gray",
        ).pack(side=tk.RIGHT, padx=5)

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
                    0, lambda e=exc: self.status_var.set(f"❌ 获取数据失败: {str(e)}")
                )

        threading.Thread(target=fetch_data, daemon=True).start()

    def _update_display(self, data: dict) -> None:
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
        self.start_btn.config(state=state)
        self.stop_btn.config(state=tk.NORMAL if state == tk.DISABLED else tk.DISABLED)
        self.refresh_btn.config(state=state)
        self.api_key_entry.config(state=state)
        self.interval_entry.config(state=state)
        self.save_btn.config(state=state)

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
