"""API 监控核心逻辑 — 与 GUI 无关的纯函数。

所有函数均为无副作用的纯函数（除了 get_api_quota 涉及的 HTTP 调用），
方便进行单元测试。
"""

import json
from datetime import datetime
from typing import Any

import requests


def get_api_quota(
    api_key: str,
    base_url: str = "https://api.deepseek.com",
    timeout: int = 10,
) -> dict[str, Any]:
    """获取 DeepSeek API 额度信息。

    Args:
        api_key: DeepSeek API Key。
        base_url: API 基础 URL。
        timeout: HTTP 请求超时秒数。

    Returns:
        字典，包含以下可能的键：
        - 成功时: is_available, balance_infos, _endpoint
        - 失败时: error, note (可选)
    """
    if not api_key:
        return {"error": "请先输入 API Key"}

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        endpoint = f"{base_url}/user/balance"
        response = requests.get(endpoint, headers=headers, timeout=timeout)

        if response.status_code == 200:
            data: dict[str, Any] = response.json()
            data['_endpoint'] = endpoint
            return data
        elif response.status_code == 401:
            return {"error": "API Key 无效或已过期"}
        else:
            return {
                "error": f"请求失败 (HTTP {response.status_code})",
                "note": f"响应: {response.text[:200]}",
            }
    except requests.exceptions.RequestException as e:
        return {"error": f"网络错误: {str(e)}"}


# ── 货币符号映射 ──────────────────────────────────────────
_CURRENCY_SYMBOLS = {
    "CNY": "¥",
    "USD": "$",
    "EUR": "€",
}


def format_quota_info(data: dict[str, Any]) -> str:
    """将 API 返回的原始数据格式化为人类可读的文本。

    Args:
        data: get_api_quota() 返回的字典。

    Returns:
        格式化后的多行文本。
    """
    lines = []

    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    lines.append(f"{'=' * 50}")
    lines.append("📊 DeepSeek API 额度监控")
    lines.append(f"⏰ 更新时间: {current_time}")
    lines.append(f"{'=' * 50}\n")

    # 错误处理
    if "error" in data:
        lines.append(f"❌ 错误: {data['error']}")
        if "note" in data:
            lines.append(f"📝 提示: {data['note']}")
        return "\n".join(lines)

    # API 端点
    if "_endpoint" in data:
        lines.append(f"🔗 API端点: {data['_endpoint']}")

    # 账户状态
    is_available = data.get("is_available")
    if is_available is not None:
        status = "✅ 可用" if is_available else "⚠️ 余额不足"
        lines.append(f"📊 账户状态: {status}")

    # 余额详情
    balance_infos = data.get("balance_infos", [])
    if balance_infos:
        for info in balance_infos:
            currency = info.get("currency", "N/A")
            symbol = _CURRENCY_SYMBOLS.get(currency, "")

            total_balance = info.get("total_balance", "N/A")
            granted_balance = info.get("granted_balance", "N/A")
            topped_up_balance = info.get("topped_up_balance", "N/A")

            lines.append(f"\n💳 币种: {currency}")
            lines.append(f"💰 总余额: {symbol}{total_balance}")
            lines.append(f"🎁 赠送余额: {symbol}{granted_balance}")
            lines.append(f"💵 充值余额: {symbol}{topped_up_balance}")
    else:
        lines.append("\n📋 原始数据:")
        lines.append(json.dumps(data, indent=2, ensure_ascii=False))

    return "\n".join(lines)
