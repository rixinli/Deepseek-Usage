"""tests/test_config.py — 配置管理模块测试。"""

import os
import sys
from pathlib import Path
from unittest.mock import patch, mock_open

import pytest

# 确保 src/ 在 path 中
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from config import is_dev_mode, AppConfig


class TestIsDevMode:
    """is_dev_mode() 测试。"""

    def test_dev_mode(self):
        """非 frozen 时返回 True。"""
        assert is_dev_mode() is True

    @patch('config.getattr')
    def test_frozen_mode(self, mock_getattr):
        """frozen=True 时返回 False。"""
        mock_getattr.return_value = True
        with patch.object(sys, 'frozen', True, create=True):
            # sys.frozen 是 PyInstaller 打包标志
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


class TestConfigIniFallback:
    """config.ini 回退逻辑测试。"""

    INI_CONTENT = "[API]\napi_key = sk-from-ini\nrefresh_interval = 300\n"

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
            # env 优先，不会被 ini 覆盖
            assert cfg.api_key == "sk-from-env"
            assert cfg.refresh_interval == 60

    def test_ini_missing_file_no_error(self):
        """config.ini 不存在时不应报错。"""
        with patch.dict(os.environ, {}, clear=True):
            cfg = AppConfig(config_file="nonexistent.ini")
            cfg.load_ini_fallback()  # 不应抛出异常
            assert cfg.api_key == ""  # 保持默认


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
        # 验证写入了 api_key
        calls = handle.write.call_args_list
        combined = "".join(c.args[0] for c in calls)
        assert "sk-save-test" in combined
        assert "180" in combined

    def test_save_failure(self):
        """写入失败时返回 False。"""
        cfg = AppConfig(config_file="test_save.ini")
        with patch("builtins.open", side_effect=PermissionError):
            result = cfg.save(api_key="sk-test", refresh_interval=120)
        assert result is False
