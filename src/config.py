"""配置管理模块 — 统一处理 .env / config.ini / 默认值。

优先级 (从高到低):
    1. 操作系统环境变量 (os.environ)
    2. .env 文件  (开发模式，通过 python-dotenv 加载到 os.environ)
    3. config.ini 文件
    4. 硬编码默认值

注意: .env 文件通过 load_dotenv() 会将值写入 os.environ，
      因此第 1 和第 2 在代码中表现为同一来源。
"""

import configparser
import os
import sys
from pathlib import Path
from typing import Optional


def is_dev_mode() -> bool:
    """检测是否为开发模式（非 PyInstaller 打包）。"""
    return not getattr(sys, 'frozen', False)


def load_env_file() -> None:
    """开发模式下从 .env 文件加载环境变量。"""
    if not is_dev_mode():
        return
    try:
        from dotenv import load_dotenv
        env_path = Path(__file__).resolve().parent.parent / '.env'
        if env_path.exists():
            load_dotenv(env_path)
    except ImportError:
        pass  # python-dotenv 未安装


class AppConfig:
    """应用配置管理器。

    组合了 env + config.ini 的读取逻辑，对外提供统一的配置接口。
    """

    # 默认值
    DEFAULT_BASE_URL = "https://api.deepseek.com"
    DEFAULT_REFRESH_INTERVAL = 120
    MIN_REFRESH_INTERVAL = 30
    MAX_REFRESH_INTERVAL = 600

    def __init__(self, config_file: str = "deepseek_config.ini"):
        self.config_file = config_file
        # 从环境变量读取（env 文件已通过 load_env_file() 预先加载到 os.environ）
        self.api_key: str = os.environ.get("DEEPSEEK_API_KEY", "")
        self.base_url: str = os.environ.get("DEEPSEEK_BASE_URL", self.DEFAULT_BASE_URL)
        self.refresh_interval: int = int(
            os.environ.get("DEEPSEEK_REFRESH_INTERVAL", str(self.DEFAULT_REFRESH_INTERVAL))
        )

    def load_ini_fallback(self) -> None:
        """从 config.ini 加载配置（仅在 env 未设置对应字段时生效）。

        此方法应在 load_env_file() 之后调用。
        """
        if not os.path.exists(self.config_file):
            return
        config = configparser.ConfigParser()
        try:
            config.read(self.config_file)
            if not self.api_key:
                self.api_key = config.get('API', 'api_key', fallback='')
            saved_interval = config.getint('API', 'refresh_interval', fallback=None)
            if saved_interval and not os.environ.get("DEEPSEEK_REFRESH_INTERVAL"):
                self.refresh_interval = saved_interval
        except Exception:
            pass

    def save(self, api_key: str, refresh_interval: int) -> bool:
        """保存配置到 config.ini。

        Returns:
            True 表示成功，False 表示失败。
        """
        config = configparser.ConfigParser()
        config['API'] = {
            'api_key': api_key,
            'refresh_interval': str(refresh_interval),
        }
        try:
            with open(self.config_file, 'w') as f:
                config.write(f)
            return True
        except Exception:
            return False

    def validate_interval(self, interval: int) -> Optional[str]:
        """验证刷新间隔是否合法。

        Returns:
            None 表示合法，否则返回错误消息。
        """
        if interval < self.MIN_REFRESH_INTERVAL:
            return f"刷新间隔不能小于 {self.MIN_REFRESH_INTERVAL} 秒"
        if interval > self.MAX_REFRESH_INTERVAL:
            return f"刷新间隔不能大于 {self.MAX_REFRESH_INTERVAL} 秒"
        return None
