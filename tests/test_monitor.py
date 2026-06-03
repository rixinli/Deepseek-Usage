"""tests/test_monitor.py — API 监控核心逻辑测试。"""

import sys
from pathlib import Path
from unittest.mock import patch, Mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from monitor import get_api_quota, format_quota_info


# ── get_api_quota 测试 ────────────────────────────────────

class TestGetApiQuota:
    """API 调用测试。"""

    def test_no_api_key(self):
        """未提供 API key 时应返回错误。"""
        result = get_api_quota("")
        assert "error" in result
        assert "API Key" in result["error"]

    @patch("monitor.requests.get")
    def test_success_response(self, mock_get):
        """HTTP 200 返回正常数据。"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "is_available": True,
            "balance_infos": [
                {
                    "currency": "CNY",
                    "total_balance": "110.00",
                    "granted_balance": "10.00",
                    "topped_up_balance": "100.00",
                }
            ],
        }
        mock_get.return_value = mock_response

        result = get_api_quota("sk-test")

        assert result["is_available"] is True
        assert result["_endpoint"] == "https://api.deepseek.com/user/balance"
        assert len(result["balance_infos"]) == 1

    @patch("monitor.requests.get")
    def test_401_unauthorized(self, mock_get):
        """HTTP 401 应返回明确的错误信息。"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        result = get_api_quota("sk-invalid")

        assert "error" in result
        assert "无效" in result["error"] or "过期" in result["error"]

    @patch("monitor.requests.get")
    def test_500_server_error(self, mock_get):
        """HTTP 500 应返回错误和响应片段。"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_get.return_value = mock_response

        result = get_api_quota("sk-test")

        assert result["error"].startswith("请求失败 (HTTP 500)")
        assert "note" in result

    @patch("monitor.requests.get")
    def test_network_error(self, mock_get):
        """网络异常应捕获并返回错误。"""
        import requests
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")

        result = get_api_quota("sk-test")

        assert "error" in result
        assert "网络错误" in result["error"]

    @patch("monitor.requests.get")
    def test_custom_base_url(self, mock_get):
        """自定义 base_url 应反映在 _endpoint 中。"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"is_available": True, "balance_infos": []}
        mock_get.return_value = mock_response

        result = get_api_quota("sk-test", base_url="https://api.deepseek.com")

        assert result["_endpoint"] == "https://api.deepseek.com/user/balance"


# ── format_quota_info 测试 ────────────────────────────────

class TestFormatQuotaInfo:
    """额度格式化测试。"""

    def test_format_error(self):
        """错误数据应包含错误信息。"""
        data = {"error": "API Key 无效或已过期"}
        text = format_quota_info(data)
        assert "API Key 无效或已过期" in text
        assert "❌" in text

    def test_format_error_with_note(self):
        """带 note 的错误应显示提示。"""
        data = {"error": "请求失败 (HTTP 500)", "note": "响应: Internal Error"}
        text = format_quota_info(data)
        assert "HTTP 500" in text
        assert "Internal Error" in text

    def test_format_success_cny(self):
        """正常 CNY 余额格式化。"""
        data = {
            "is_available": True,
            "balance_infos": [
                {
                    "currency": "CNY",
                    "total_balance": "110.00",
                    "granted_balance": "10.00",
                    "topped_up_balance": "100.00",
                }
            ],
            "_endpoint": "https://api.deepseek.com/user/balance",
        }
        text = format_quota_info(data)

        assert "✅ 可用" in text
        assert "¥110.00" in text
        assert "¥10.00" in text
        assert "¥100.00" in text
        assert "CNY" in text

    def test_format_unavailable(self):
        """余额不足状态。"""
        data = {
            "is_available": False,
            "balance_infos": [],
            "_endpoint": "https://api.deepseek.com/user/balance",
        }
        text = format_quota_info(data)
        assert "⚠️ 余额不足" in text

    def test_format_no_balance_infos(self):
        """无 balance_infos 时显示原始数据。"""
        data = {
            "is_available": True,
            "balance_infos": [],
            "_endpoint": "https://api.deepseek.com/user/balance",
        }
        text = format_quota_info(data)
        assert "📋 原始数据" in text

    def test_format_contains_timestamp(self):
        """输出应包含时间戳。"""
        text = format_quota_info({"is_available": True, "balance_infos": []})
        assert "⏰ 更新时间" in text

    def test_format_usd_currency(self):
        """非 CNY 货币的符号处理。"""
        data = {
            "is_available": True,
            "balance_infos": [
                {
                    "currency": "USD",
                    "total_balance": "50.00",
                    "granted_balance": "10.00",
                    "topped_up_balance": "40.00",
                }
            ],
        }
        text = format_quota_info(data)
        assert "$50.00" in text
        assert "USD" in text
