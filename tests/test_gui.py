"""tests/test_gui.py — GUI 交互逻辑测试。

注意: 这些测试 mock 了 tkinter，不创建真实窗口。
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock

import pytest

# 确保项目根目录在 path 中
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Mock tkinter 模块，避免创建真实 GUI
sys.modules['tkinter'] = MagicMock()
sys.modules['tkinter.ttk'] = MagicMock()
sys.modules['tkinter.scrolledtext'] = MagicMock()
sys.modules['tkinter.messagebox'] = MagicMock()

from src.gui import DeepSeekAPIMonitor


@pytest.fixture
def root_mock():
    """创建一个 mock 的 tk.Tk 实例。"""
    root = MagicMock()
    root.title = MagicMock()
    root.geometry = MagicMock()
    return root


def _make_minimal_app(root_mock):
    """构造最小化 DeepSeekAPIMonitor 实例用于测试。"""
    app = DeepSeekAPIMonitor.__new__(DeepSeekAPIMonitor)
    app.root = root_mock
    app.config = MagicMock()
    app.config.api_key = ""
    app.config.base_url = "https://api.deepseek.com"
    app.config.refresh_interval = 120
    app.config.startup_enabled = False
    app.config.startup_asked = False
    app.config.auto_monitor = False
    app.config.validate_interval = lambda x: (None if 30 <= x <= 600 else "invalid")
    app.config.save = MagicMock(return_value=True)
    app.monitoring = False
    return app


@pytest.fixture
def app(root_mock):
    """创建 DeepSeekAPIMonitor 实例（mock 环境）。"""
    return _make_minimal_app(root_mock)


class TestTogglePassword:
    """密码显示/隐藏测试。"""

    def test_toggle_show(self, app):
        """默认隐藏 → 第一次切换 → 显示。"""
        app.show_pwd = False
        app.api_key_entry = MagicMock()
        app.toggle_btn = MagicMock()

        app.toggle_password()

        assert app.show_pwd is True
        app.api_key_entry.config.assert_called_with(show="")

    def test_toggle_hide(self, app):
        """已显示 → 切换 → 隐藏。"""
        app.show_pwd = True
        app.api_key_entry = MagicMock()
        app.toggle_btn = MagicMock()

        app.toggle_password()

        assert app.show_pwd is False
        app.api_key_entry.config.assert_called_with(show="*")


class TestSaveSettings:
    """设置保存测试。"""

    def test_save_with_valid_input(self, app):
        """正常输入应保存成功。"""
        app.api_key_entry = MagicMock()
        app.api_key_entry.get.return_value = "sk-test-valid"
        app.interval_var = MagicMock()
        app.interval_var.get.return_value = "120"
        app.status_var = MagicMock()

        with patch('src.gui.messagebox.showinfo'):
            app.save_settings()

        assert app.config.api_key == "sk-test-valid"
        app.config.save.assert_called_once()

    def test_save_empty_key(self, app):
        """空 API key 应弹出警告。"""
        app.api_key_entry = MagicMock()
        app.api_key_entry.get.return_value = ""
        app.interval_var = MagicMock()
        app.interval_var.get.return_value = "120"

        with patch('src.gui.messagebox.showwarning') as mock_warn:
            app.save_settings()
            mock_warn.assert_called_once()

    def test_save_invalid_interval(self, app):
        """非法间隔值应报错。"""
        app.api_key_entry = MagicMock()
        app.api_key_entry.get.return_value = "sk-test"
        app.interval_var = MagicMock()
        app.interval_var.get.return_value = "abc"

        with patch('src.gui.messagebox.showerror') as mock_err:
            app.save_settings()
            mock_err.assert_called_once()

    def test_save_interval_too_small(self, app):
        """间隔过小应警告。"""
        app.api_key_entry = MagicMock()
        app.api_key_entry.get.return_value = "sk-test"
        app.interval_var = MagicMock()
        app.interval_var.get.return_value = "10"
        app.config.validate_interval = lambda x: "不能小于" if x < 30 else None

        with patch('src.gui.messagebox.showwarning') as mock_warn:
            app.save_settings()
            mock_warn.assert_called_once()


class TestMonitoringState:
    """监控状态切换测试。"""

    def test_start_sets_monitoring_flag(self, app):
        """start_monitoring 应设置 monitoring=True。"""
        app.api_key_entry = MagicMock()
        app.api_key_entry.get.return_value = "sk-test"
        app.interval_var = MagicMock()
        app.interval_var.get.return_value = "120"
        app.status_var = MagicMock()
        app._set_controls_state = MagicMock()
        app.update_timer = MagicMock()
        app.refresh_once = MagicMock()

        app.start_monitoring()

        assert app.monitoring is True

    def test_stop_clears_monitoring_flag(self, app):
        """stop_monitoring 应设置 monitoring=False。"""
        app.monitoring = True
        app.status_var = MagicMock()
        app.timer_label = MagicMock()
        app._set_controls_state = MagicMock()

        app.stop_monitoring()

        assert app.monitoring is False


class TestAutoStart:
    """自动启动逻辑测试。"""

    def test_auto_start_with_key(self, app):
        """有 API key 时应自动启动。"""
        app.config.api_key = "sk-test"
        app.start_monitoring = MagicMock()

        app.auto_start_monitoring()

        app.start_monitoring.assert_called_once()

    def test_auto_start_without_key(self, app):
        """无 API key 时不应启动。"""
        app.config.api_key = ""
        app.start_monitoring = MagicMock()

        app.auto_start_monitoring()

        app.start_monitoring.assert_not_called()


class TestSettingsDialogCallback:
    """设置对话框回调测试。"""

    def test_on_settings_saved_updates_config(self, root_mock):
        """_on_settings_saved 应更新配置并保存。"""
        app = _make_minimal_app(root_mock)
        app.api_key_entry = MagicMock()
        app.interval_var = MagicMock()
        app.status_var = MagicMock()
        app._refresh_status_bar = MagicMock()

        with patch("src.gui.is_startup_enabled", return_value=True):
            app._on_settings_saved(
                api_key="sk-new-key",
                interval=300,
                startup_enabled=True,
                auto_monitor=True,
            )

        assert app.config.api_key == "sk-new-key"
        assert app.config.refresh_interval == 300
        assert app.config.startup_enabled is True
        assert app.config.auto_monitor is True
        app.config.save.assert_called_once_with("sk-new-key", 300)
        app.api_key_entry.delete.assert_called()
        app.interval_var.set.assert_called_with("300")


class TestStartupPrompt:
    """首次启动提示测试。"""

    def test_ask_startup_sets_asked_flag(self, root_mock):
        """询问后应设置 startup_asked = True。"""
        app = _make_minimal_app(root_mock)
        app.status_var = MagicMock()

        app._ask_startup_on_first_run()

        assert app.config.startup_asked is True
        app.config.save.assert_called()


class TestAboutDialog:
    """关于对话框测试。"""

    def test_show_about_does_not_crash(self, app):
        """show_about 不应抛出异常。"""
        with patch('src.gui.messagebox.showinfo') as mock_info:
            app._show_about()
            mock_info.assert_called_once()
            args = mock_info.call_args[0]
            assert "DeepSeek" in args[0] or "DeepSeek" in args[1]
