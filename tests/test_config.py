"""tests/test_config.py — 配置管理模块测试。"""

import os
import sys
from pathlib import Path
from unittest.mock import patch, mock_open

import pytest

# 确保项目根目录在 path 中，以便 `from src.xxx import ...` 正确解析
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.config import is_dev_mode, AppConfig


class TestIsDevMode:
    """is_dev_mode() 测试。"""

    def test_dev_mode(self):
        """非 frozen 时返回 True。"""
        assert is_dev_mode() is True

    @patch('src.config.getattr')
    def test_frozen_mode(self, mock_getattr):
        """frozen=True 时返回 False。"""
        mock_getattr.return_value = True
        with patch.object(sys, 'frozen', True, create=True):
            assert is_dev_mode() is False


class TestAppConfigDefaults:
    """AppConfig 默认值测试。"""

    def test_defaults(self):
        """未设置任何 env 时使用默认值。"""
        with patch.dict(os.environ, {}, clear=True):
            cfg = AppConfig()
            assert cfg.api_key == ""
            assert cfg.base_url == "https://api.deepseek.com"
            assert cfg.refresh_interval == 120

    def test_env_overrides_defaults(self):
        """环境变量覆盖默认值。"""
        env = {
            "DEEPSEEK_API_KEY": "sk-test-env",
            "DEEPSEEK_BASE_URL": "https://custom.api.com",
            "DEEPSEEK_REFRESH_INTERVAL": "60",
        }
        with patch.dict(os.environ, env, clear=True):
            cfg = AppConfig()
            assert cfg.api_key == "sk-test-env"
            assert cfg.base_url == "https://custom.api.com"
            assert cfg.refresh_interval == 60

    def test_startup_defaults(self):
        """startup_enabled / startup_asked / auto_monitor 默认均为 False。"""
        with patch.dict(os.environ, {}, clear=True):
            cfg = AppConfig()
            assert cfg.startup_enabled is False
            assert cfg.startup_asked is False
            assert cfg.auto_monitor is False


class TestConfigIniFallback:
    """config.ini 回退逻辑测试。"""

    INI_CONTENT = "[API]\napi_key = sk-from-ini\nrefresh_interval = 300\n"

    INI_WITH_SETTINGS = (
        "[API]\napi_key = sk-from-ini\nrefresh_interval = 300\n"
        "[Settings]\nstartup_enabled = true\nstartup_asked = true\nauto_monitor = true\n"
    )

    def test_ini_fills_when_env_empty(self):
        """env 为空时，config.ini 提供值。"""
        with patch.dict(os.environ, {}, clear=True):
            cfg = AppConfig(config_file="test_config.ini")
            with patch("builtins.open", mock_open(read_data=self.INI_CONTENT)):
                with patch("os.path.exists", return_value=True):
                    cfg.load_ini_fallback()
            assert cfg.api_key == "sk-from-ini"
            assert cfg.refresh_interval == 300

    def test_ini_does_not_override_env(self):
        """env 已有值时，config.ini 不覆盖。"""
        env = {"DEEPSEEK_API_KEY": "sk-from-env", "DEEPSEEK_REFRESH_INTERVAL": "60"}
        with patch.dict(os.environ, env, clear=True):
            cfg = AppConfig(config_file="test_config.ini")
            with patch("builtins.open", mock_open(read_data=self.INI_CONTENT)):
                with patch("os.path.exists", return_value=True):
                    cfg.load_ini_fallback()
            assert cfg.api_key == "sk-from-env"
            assert cfg.refresh_interval == 60

    def test_ini_missing_file_no_error(self):
        """config.ini 不存在时不应报错。"""
        with patch.dict(os.environ, {}, clear=True):
            cfg = AppConfig(config_file="nonexistent.ini")
            cfg.load_ini_fallback()
            assert cfg.api_key == ""

    def test_ini_loads_settings_section(self):
        """config.ini 的 [Settings] 节应正确加载。"""
        with patch.dict(os.environ, {}, clear=True):
            cfg = AppConfig(config_file="test_config.ini")
            with patch("builtins.open", mock_open(read_data=self.INI_WITH_SETTINGS)):
                with patch("os.path.exists", return_value=True):
                    cfg.load_ini_fallback()
            assert cfg.startup_enabled is True
            assert cfg.startup_asked is True
            assert cfg.auto_monitor is True

    def test_ini_without_settings_section(self):
        """没有 [Settings] 节时保持默认值。"""
        with patch.dict(os.environ, {}, clear=True):
            cfg = AppConfig(config_file="test_config.ini")
            with patch("builtins.open", mock_open(read_data=self.INI_CONTENT)):
                with patch("os.path.exists", return_value=True):
                    cfg.load_ini_fallback()
            assert cfg.startup_enabled is False
            assert cfg.startup_asked is False
            assert cfg.auto_monitor is False


class TestValidateInterval:
    """refresh_interval 验证测试。"""

    def setup_method(self):
        self.cfg = AppConfig()

    def test_valid_interval(self):
        """合法值返回 None。"""
        assert self.cfg.validate_interval(120) is None
        assert self.cfg.validate_interval(30) is None
        assert self.cfg.validate_interval(600) is None

    def test_too_small(self):
        """小于最小值返回错误信息。"""
        msg = self.cfg.validate_interval(10)
        assert msg is not None
        assert "不能小于" in msg

    def test_too_large(self):
        """大于最大值返回错误信息。"""
        msg = self.cfg.validate_interval(999)
        assert msg is not None
        assert "不能大于" in msg


class TestSaveConfig:
    """配置保存测试。"""

    def test_save_writes_expected_content(self):
        """保存应写入正确的 INI 格式。"""
        cfg = AppConfig(config_file="test_save.ini")
        m_open = mock_open()
        with patch("builtins.open", m_open):
            result = cfg.save(api_key="sk-save-test", refresh_interval=180)
        assert result is True
        handle = m_open()
        calls = handle.write.call_args_list
        combined = "".join(c.args[0] for c in calls)
        assert "sk-save-test" in combined
        assert "180" in combined

    def test_save_writes_settings_section(self):
        """保存应写入 [Settings] 节。"""
        cfg = AppConfig(config_file="test_save.ini")
        cfg.startup_enabled = True
        cfg.startup_asked = True
        cfg.auto_monitor = True
        m_open = mock_open()
        with patch("builtins.open", m_open):
            result = cfg.save(api_key="sk-test", refresh_interval=120)
        assert result is True
        handle = m_open()
        calls = handle.write.call_args_list
        combined = "".join(c.args[0] for c in calls)
        assert "startup_enabled = true" in combined
        assert "startup_asked = true" in combined
        assert "auto_monitor = true" in combined

    def test_save_partial_none_params(self):
        """传入 None 参数时不覆盖现有值。"""
        cfg = AppConfig(config_file="test_save.ini")
        cfg.api_key = "existing-key"
        cfg.refresh_interval = 200
        with patch("builtins.open", mock_open()):
            result = cfg.save()  # 不传参数
        assert result is True
        # 内存值不变
        assert cfg.api_key == "existing-key"
        assert cfg.refresh_interval == 200

    def test_save_failure(self):
        """写入失败时返回 False。"""
        cfg = AppConfig(config_file="test_save.ini")
        with patch("builtins.open", side_effect=PermissionError):
            result = cfg.save(api_key="sk-test", refresh_interval=120)
        assert result is False

    def test_save_updates_memory_values(self):
        """save() 成功时应更新内存中的值。"""
        cfg = AppConfig(config_file="test_save.ini")
        with patch("builtins.open", mock_open()):
            cfg.save(api_key="sk-new", refresh_interval=300)
        assert cfg.api_key == "sk-new"
        assert cfg.refresh_interval == 300
