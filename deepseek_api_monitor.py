# deepseek_api_monitor.py
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import requests
import json
from datetime import datetime
import threading
import time
import os
import sys
from pathlib import Path
import configparser 

# ============================================================
# 环境变量加载 — 开发模式下从 .env 文件读取敏感信息
# 打包后的 EXE 没有 python-dotenv，会自动跳过，改用 config.ini
# ============================================================
_IS_DEV = not getattr(sys, 'frozen', False)  # PyInstaller 打包后 sys.frozen = True

if _IS_DEV:
    try:
        from dotenv import load_dotenv
        _env_path = Path(__file__).resolve().parent / '.env'
        if _env_path.exists():
            load_dotenv(_env_path)
    except ImportError:
        pass  # python-dotenv 未安装

class DeepSeekAPIMonitor:
    def __init__(self, root):
        self.root = root
        self.root.title("DeepSeek API 额度监控")
        self.root.geometry("650x550")
        
        # 配置文件路径
        self.config_file = "deepseek_config.ini"
        
        # API 配置 — 优先级: 环境变量 > config.ini > UI 输入
        self.api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        self.base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self.monitoring = False
        self.refresh_interval = int(os.environ.get("DEEPSEEK_REFRESH_INTERVAL", "120"))

        # 加载 config.ini（作为兜底，不会覆盖已从环境变量读取的值）
        self.load_config()
        
        self.setup_ui()
        
        # 自动开始监控
        if self.api_key:
            self.root.after(500, self.auto_start_monitoring)
    
    def load_config(self):
        """加载 config.ini — 仅作为兜底，不会覆盖环境变量 (.env) 的值"""
        if not os.path.exists(self.config_file):
            return
        config = configparser.ConfigParser()
        try:
            config.read(self.config_file)
            # 只在尚未设置时才读取（环境变量优先级更高）
            if not self.api_key:
                self.api_key = config.get('API', 'api_key', fallback='')
            saved_interval = config.getint('API', 'refresh_interval', fallback=None)
            if saved_interval and not os.environ.get("DEEPSEEK_REFRESH_INTERVAL"):
                self.refresh_interval = saved_interval
        except Exception:
            pass
    
    def save_config(self):
        """保存配置到文件"""
        config = configparser.ConfigParser()
        config['API'] = {
            'api_key': self.api_key,
            'refresh_interval': str(self.refresh_interval)
        }
        
        try:
            with open(self.config_file, 'w') as f:
                config.write(f)
            return True
        except Exception as e:
            messagebox.showerror("保存配置失败", str(e))
            return False
    
    def setup_ui(self):
        # 主框架
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # API Key 输入框
        key_frame = tk.Frame(main_frame)
        key_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(key_frame, text="API Key:", font=("Arial", 10)).pack(side=tk.LEFT)
        
        self.api_key_entry = tk.Entry(key_frame, width=50, show="*")
        self.api_key_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.api_key_entry.insert(0, self.api_key)
        
        # 保存按钮（眼睛图标显示/隐藏密码）
        self.show_pwd = False
        self.toggle_btn = tk.Button(key_frame, text="👁", command=self.toggle_password, width=3)
        self.toggle_btn.pack(side=tk.LEFT, padx=2)
        
        # 设置框架
        settings_frame = tk.LabelFrame(main_frame, text="监控设置", padx=10, pady=10)
        settings_frame.pack(fill=tk.X, pady=10)
        
        # 刷新间隔设置
        interval_frame = tk.Frame(settings_frame)
        interval_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(interval_frame, text="刷新间隔（秒）:").pack(side=tk.LEFT)
        
        self.interval_var = tk.StringVar(value=str(self.refresh_interval))
        self.interval_entry = tk.Spinbox(
            interval_frame, 
            from_=30, 
            to=600, 
            textvariable=self.interval_var,
            width=10,
            increment=10
        )
        self.interval_entry.pack(side=tk.LEFT, padx=5)
        
        tk.Label(interval_frame, text="（推荐120-300秒）").pack(side=tk.LEFT, padx=10)
        
        # 控制按钮
        btn_frame = tk.Frame(settings_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        self.start_btn = tk.Button(
            btn_frame, 
            text="▶ 开始监控", 
            command=self.start_monitoring, 
            bg="#28a745", 
            fg="white",
            width=12
        )
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = tk.Button(
            btn_frame, 
            text="⏹ 停止监控", 
            command=self.stop_monitoring, 
            bg="#dc3545", 
            fg="white",
            width=12,
            state=tk.DISABLED
        )
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        self.refresh_btn = tk.Button(
            btn_frame, 
            text="🔄 立即刷新", 
            command=self.refresh_once,
            width=12
        )
        self.refresh_btn.pack(side=tk.LEFT, padx=5)
        
        self.save_btn = tk.Button(
            btn_frame, 
            text="💾 保存设置", 
            command=self.save_settings,
            bg="#007bff", 
            fg="white",
            width=10
        )
        self.save_btn.pack(side=tk.LEFT, padx=5)
        
        # 定时器信息
        self.timer_label = tk.Label(settings_frame, text="⏱ 下次刷新: 等待中...", font=("Arial", 9))
        self.timer_label.pack(pady=5)
        
        # 额度显示区域
        info_frame = tk.LabelFrame(main_frame, text="API 额度信息", padx=10, pady=10)
        info_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # 创建文本框和滚动条
        text_frame = tk.Frame(info_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        self.info_text = scrolledtext.ScrolledText(
            text_frame, 
            width=70, 
            height=15, 
            font=("Consolas", 10),
            bg="#1e1e1e",  # 深色背景
            fg="#00ff00",  # 绿色文字
            insertbackground="white"
        )
        self.info_text.pack(fill=tk.BOTH, expand=True)
        
        # 设置标签样式
        self.info_text.tag_config("header", foreground="#00ff00", font=("Consolas", 10, "bold"))
        self.info_text.tag_config("info", foreground="#00ff00")
        self.info_text.tag_config("error", foreground="#ff4444")
        self.info_text.tag_config("success", foreground="#00ff00")
        
        # 状态栏
        status_frame = tk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=5)
        
        self.status_var = tk.StringVar()
        self.status_var.set("✅ 系统就绪")
        status_bar = tk.Label(
            status_frame, 
            textvariable=self.status_var, 
            bd=1, 
            relief=tk.SUNKEN, 
            anchor=tk.W,
            font=("Arial", 9)
        )
        status_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 版本 & 运行模式
        mode_text = "v2.0 dev" if _IS_DEV else "v2.0"
        tk.Label(status_frame, text=mode_text, font=("Arial", 8), fg="gray").pack(side=tk.RIGHT, padx=5)

        # 开发模式下提示配置来源
        if _IS_DEV and self.api_key:
            self.status_var.set("✅ 系统就绪 (配置来源: .env)")
    
    def toggle_password(self):
        """切换密码显示/隐藏"""
        self.show_pwd = not self.show_pwd
        if self.show_pwd:
            self.api_key_entry.config(show="")
            self.toggle_btn.config(text="🔒")
        else:
            self.api_key_entry.config(show="*")
            self.toggle_btn.config(text="👁")
    
    def save_settings(self):
        """保存设置"""
        api_key = self.api_key_entry.get().strip()
        if not api_key:
            messagebox.showwarning("警告", "请输入 API Key")
            return
        
        try:
            interval = int(self.interval_var.get())
            if interval < 30:
                messagebox.showwarning("警告", "刷新间隔不能小于30秒")
                return
        except ValueError:
            messagebox.showerror("错误", "刷新间隔必须是数字")
            return
        
        self.api_key = api_key
        self.refresh_interval = interval
        
        if self.save_config():
            self.status_var.set("✅ 设置已保存")
            messagebox.showinfo("成功", "设置已成功保存到配置文件")
    
    def auto_start_monitoring(self):
        """自动启动监控"""
        if self.api_key:
            self.start_monitoring()
    
    def get_api_quota(self):
        """获取API额度信息"""
        if not self.api_key:
            return {"error": "请先输入 API Key"}
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            # 官方接口: GET /user/balance
            # 文档: https://api-docs.deepseek.com/zh-cn/api/get-user-balance
            endpoint = f"{self.base_url}/user/balance"

            response = requests.get(
                endpoint,
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                data['_endpoint'] = endpoint
                return data
            elif response.status_code == 401:
                return {"error": "API Key 无效或已过期"}
            else:
                return {
                    "error": f"请求失败 (HTTP {response.status_code})",
                    "note": f"响应: {response.text[:200]}"
                }

        except requests.exceptions.RequestException as e:
            return {"error": f"网络错误: {str(e)}"}
    
    def format_quota_info(self, data):
        """格式化额度信息"""
        output = []
        
        # 添加时间戳
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        output.append(f"{'='*50}")
        output.append(f"📊 DeepSeek API 额度监控")
        output.append(f"⏰ 更新时间: {current_time}")
        output.append(f"{'='*50}\n")
        
        if "error" in data:
            output.append(f"❌ 错误: {data['error']}")
            if "note" in data:
                output.append(f"📝 提示: {data['note']}")
            return "\n".join(output)
        
        # 显示API端点
        if "_endpoint" in data:
            output.append(f"🔗 API端点: {data['_endpoint']}")
        
        # 解析并显示额度信息
        # 官方返回格式:
        # {
        #   "is_available": true,
        #   "balance_infos": [
        #     {"currency": "CNY", "total_balance": "110.00",
        #      "granted_balance": "10.00", "topped_up_balance": "100.00"}
        #   ]
        # }

        # 账户是否可用
        is_available = data.get("is_available")
        if is_available is not None:
            status = "✅ 可用" if is_available else "⚠️ 余额不足"
            output.append(f"📊 账户状态: {status}")

        balance_infos = data.get("balance_infos", [])
        if balance_infos:
            for info in balance_infos:
                currency = info.get("currency", "N/A")
                currency_symbol = "¥" if currency == "CNY" else "$"

                total_balance = info.get("total_balance", "N/A")
                granted_balance = info.get("granted_balance", "N/A")
                topped_up_balance = info.get("topped_up_balance", "N/A")

                output.append(f"\n💳 币种: {currency}")
                output.append(f"💰 总余额: {currency_symbol}{total_balance}")
                output.append(f"🎁 赠送余额: {currency_symbol}{granted_balance}")
                output.append(f"💵 充值余额: {currency_symbol}{topped_up_balance}")
        else:
            output.append("\n📋 原始数据:")
            output.append(json.dumps(data, indent=2, ensure_ascii=False))
        
        return "\n".join(output)
    
    def update_display(self, data):
        """更新显示"""
        self.info_text.delete(1.0, tk.END)
        formatted_info = self.format_quota_info(data)
        self.info_text.insert(1.0, formatted_info)
        self.info_text.see(tk.END)
    
    def update_timer(self):
        """更新定时器显示"""
        if self.monitoring:
            remaining = self.refresh_interval - (time.time() % self.refresh_interval)
            if remaining < 0:
                remaining = self.refresh_interval
            self.timer_label.config(text=f"⏱ 下次刷新: {int(remaining)} 秒后")
            self.root.after(1000, self.update_timer)
    
    def refresh_once(self):
        """刷新一次额度信息"""
        if not self.api_key:
            self.status_var.set("⚠️ 请先输入 API Key")
            return
        
        self.status_var.set("🔄 正在获取额度信息...")
        self.root.update()
        
        def fetch_data():
            try:
                data = self.get_api_quota()
                self.root.after(0, self.update_display, data)
                
                if "error" not in data:
                    self.root.after(0, lambda: self.status_var.set("✅ 数据已更新"))
                else:
                    self.root.after(0, lambda: self.status_var.set(f"❌ {data['error']}"))
            except Exception as e:
                self.root.after(0, lambda: self.status_var.set(f"❌ 获取数据失败: {str(e)}"))
        
        threading.Thread(target=fetch_data, daemon=True).start()
    
    def monitoring_loop(self):
        """监控循环"""
        while self.monitoring:
            self.api_key = self.api_key_entry.get().strip()
            if self.api_key:
                data = self.get_api_quota()
                self.root.after(0, self.update_display, data)
                
                if "error" not in data:
                    self.root.after(0, lambda: self.status_var.set(f"✅ 监控中 - 每{self.refresh_interval}秒自动更新"))
                else:
                    self.root.after(0, lambda: self.status_var.set(f"⚠️ 监控中 - {data['error']}"))
            
            # 等待指定间隔
            for _ in range(self.refresh_interval):
                if not self.monitoring:
                    break
                time.sleep(1)
    
    def start_monitoring(self):
        """开始监控"""
        api_key = self.api_key_entry.get().strip()
        if not api_key:
            messagebox.showwarning("警告", "请输入 API Key")
            return
        
        try:
            interval = int(self.interval_var.get())
            if interval < 30:
                messagebox.showwarning("警告", "刷新间隔不能小于30秒")
                return
            self.refresh_interval = interval
        except ValueError:
            messagebox.showerror("错误", "刷新间隔必须是数字")
            return
        
        self.api_key = api_key
        
        # 保存设置
        self.save_settings()
        
        self.monitoring = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.refresh_btn.config(state=tk.DISABLED)
        self.api_key_entry.config(state=tk.DISABLED)
        self.interval_entry.config(state=tk.DISABLED)
        self.save_btn.config(state=tk.DISABLED)
        
        self.status_var.set(f"🔄 开始监控 - 每{self.refresh_interval}秒自动更新")
        
        # 启动定时器更新
        self.update_timer()
        
        # 启动监控线程
        threading.Thread(target=self.monitoring_loop, daemon=True).start()
        
        # 立即刷新一次
        self.refresh_once()
    
    def stop_monitoring(self):
        """停止监控"""
        self.monitoring = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.refresh_btn.config(state=tk.NORMAL)
        self.api_key_entry.config(state=tk.NORMAL)
        self.interval_entry.config(state=tk.NORMAL)
        self.save_btn.config(state=tk.NORMAL)
        
        self.timer_label.config(text="⏱ 监控已停止")
        self.status_var.set("⏹️ 监控已停止")

def create_startup_shortcut():
    """创建开机自启动快捷方式"""
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
    except:
        return False

if __name__ == "__main__":
    root = tk.Tk()
    
    # 尝试设置图标（如果有的话）
    try:
        root.iconbitmap(default='icon.ico')
    except:
        pass
    
    app = DeepSeekAPIMonitor(root)
    
    # 提醒用户可以使用开机自启动
    if not os.path.exists(os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "Microsoft", "Windows", "Start Menu", "Programs", "Startup", "DeepSeekAPI监控.lnk")):
        response = messagebox.askyesno(
            "开机自启动",
            "是否设置开机自启动？\n设置后软件会在系统启动时自动运行。"
        )
        if response:
            if create_startup_shortcut():
                messagebox.showinfo("成功", "已设置开机自启动！")
            else:
                messagebox.showwarning("提示", "设置开机自启动失败，您可以手动创建快捷方式到启动文件夹。")
    
    root.mainloop()