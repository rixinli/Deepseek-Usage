r"""配置管理模块 — 统一处理 .env / config.ini / 默认值。

优先级 (从高到低):
    1. 操作系统环境变量 (os.environ)
    2. .env 文件  (开发模式，通过 python-dotenv 加载到 os.environ)
    3. config.ini 文件
    4. 硬编码默认值

配置文件路径:
    - 便携模式 (EXE 目录可写):   配置存储在 EXE 同级目录
    - 安装模式 (Program Files):  配置存储在 %APPDATA%\DeepSeek API Monitor\

注意: .env 文件通过 load_dotenv() 会将值写入 os.environ，
      因此第 1 和第 2 在代码中表现为同一来源。
"""

from __future__ import annotations

import configparser
import os
import shutil
import sys
from pathlib import Path


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
    自动检测便携/安装模式，选择合适的配置存储路径。
    """

    # 默认值
    DEFAULT_BASE_URL = "https://api.deepseek.com"
    DEFAULT_REFRESH_INTERVAL = 120
    MIN_REFRESH_INTERVAL = 30
    MAX_REFRESH_INTERVAL = 600

    CONFIG_DIR_NAME = "DeepSeek API Monitor"
    CONFIG_FILE_NAME = "deepseek_config.ini"

    # ── 模式检测 ──────────────────────────────────────────

    @staticmethod
    def get_exe_dir() -> Path:
        """获取 EXE 所在目录（打包模式）或当前工作目录（开发模式）。"""
        if getattr(sys, 'frozen', False):
            return Path(sys.executable).parent
        return Path.cwd()

    @staticmethod
    def is_portable_mode() -> bool:
        """检测是否为便携模式（EXE 目录可写 → 便携；不可写 → 安装模式）。

        开发模式始终视为便携模式。
        """
        if not getattr(sys, 'frozen', False):
            return True
        exe_dir = AppConfig.get_exe_dir()
        try:
            probe = exe_dir / '.write_test'
            probe.touch()
            probe.unlink()
            return True
        except (PermissionError, OSError):
            return False

    @staticmethod
    def get_portable_config_path() -> Path:
        """便携模式配置路径：EXE 同级目录（打包）或 CWD（开发）。"""
        return AppConfig.get_exe_dir() / AppConfig.CONFIG_FILE_NAME

    @staticmethod
    def get_installed_config_path() -> Path:
        """安装模式配置路径：%APPDATA%\\DeepSeek API Monitor\\deepseek_config.ini"""
        appdata = os.environ.get('APPDATA', '')
        if not appdata:
            # 备用：手动构造 %APPDATA% 路径
            try:
                home = Path.home()
            except RuntimeError:
                home = Path(os.environ.get('USERPROFILE', os.environ.get('HOMEPATH', '')))
            appdata = str(home / 'AppData' / 'Roaming')
        return Path(appdata) / AppConfig.CONFIG_DIR_NAME / AppConfig.CONFIG_FILE_NAME

    # ── 初始化 ────────────────────────────────────────────

    def __init__(self, config_file: str | None = None):
        self._portable_path = self.get_portable_config_path()
        self._installed_path = self.get_installed_config_path()
        self._portable_mode = self.is_portable_mode()

        # 如果显式传入了 config_file，使用传入的路径（测试/特殊场景）
        # 否则根据模式自动选择
        if config_file is not None:
            self.config_file = config_file
        else:
            self.config_file = str(
                self._portable_path if self._portable_mode else self._installed_path
            )

        # 从环境变量读取（env 文件已通过 load_env_file() 预先加载到 os.environ）
        self.api_key: str = os.environ.get("DEEPSEEK_API_KEY", "")
        self.base_url: str = os.environ.get("DEEPSEEK_BASE_URL", self.DEFAULT_BASE_URL)
        self.refresh_interval: int = int(
            os.environ.get("DEEPSEEK_REFRESH_INTERVAL", str(self.DEFAULT_REFRESH_INTERVAL))
        )
        # 用户偏好设置（默认值）
        self.startup_enabled: bool = False
        self.startup_asked: bool = False
        self.auto_monitor: bool = False

    # ── INI 文件读取 ──────────────────────────────────────

    def _load_from_file(self, path: str) -> bool:
        """从指定 INI 文件加载配置（仅在 env 未设置对应字段时生效）。

        返回 True 表示成功加载，False 表示文件不存在或读取失败。
        """
        if not os.path.exists(path):
            return False
        config = configparser.ConfigParser()
        try:
            config.read(path)
            # API 配置 — 仅在 env 未设置时覆盖
            if not self.api_key:
                self.api_key = config.get('API', 'api_key', fallback='')
            saved_interval = config.getint('API', 'refresh_interval', fallback=None)
            if saved_interval and not os.environ.get("DEEPSEEK_REFRESH_INTERVAL"):
                self.refresh_interval = saved_interval

            # 用户偏好设置
            if config.has_section('Settings'):
                self.startup_enabled = config.getboolean(
                    'Settings', 'startup_enabled', fallback=False
                )
                self.startup_asked = config.getboolean(
                    'Settings', 'startup_asked', fallback=False
                )
                self.auto_monitor = config.getboolean(
                    'Settings', 'auto_monitor', fallback=False
                )
            return True
        except Exception:
            return False

    def _migrate_config(self, source: str, dest: str) -> bool:
        """将配置文件从旧路径迁移到新路径。失败时静默返回 False。"""
        try:
            Path(dest).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest)
            return True
        except Exception:
            return False

    def load_ini_fallback(self) -> None:
        """从配置文件加载（仅在 env 未设置对应字段时生效）。

        自动检测便携/安装模式，优先读取模式对应的路径。
        安装模式下，如果便携路径存在旧配置，自动迁移到 %APPDATA%。
        """
        preferred = Path(self.config_file)
        alternative = (
            self._installed_path if self._portable_mode else self._portable_path
        )

        # 1. 优先路径
        if self._load_from_file(str(preferred)):
            return

        # 2. 备选路径（兼容旧版本 / 模式切换）
        if self._load_from_file(str(alternative)):
            # 安装模式下：发现旧便携配置 → 迁移到 %APPDATA%
            if not self._portable_mode:
                self._migrate_config(str(alternative), str(preferred))
            return

        # 3. 无已有配置 — 使用默认值，后续首次保存时自动创建

    # ── 保存 ──────────────────────────────────────────────

    def save(self, api_key: str | None = None, refresh_interval: int | None = None) -> bool:
        """保存配置到 config.ini。

        仅更新传入的非 None 字段，未传入的字段保持当前值。

        Returns:
            True 表示成功，False 表示失败。
        """
        config = configparser.ConfigParser()

        # 读取现有配置（如果存在），以便保留未修改的字段
        if os.path.exists(self.config_file):
            try:
                config.read(self.config_file)
            except Exception:
                pass

        # 更新 API 配置
        if not config.has_section('API'):
            config.add_section('API')
        _api_key = api_key if api_key is not None else self.api_key
        _interval = refresh_interval if refresh_interval is not None else self.refresh_interval
        config.set('API', 'api_key', _api_key)
        config.set('API', 'refresh_interval', str(_interval))

        # 更新用户偏好设置
        if not config.has_section('Settings'):
            config.add_section('Settings')
        config.set('Settings', 'startup_enabled', str(self.startup_enabled).lower())
        config.set('Settings', 'startup_asked', str(self.startup_asked).lower())
        config.set('Settings', 'auto_monitor', str(self.auto_monitor).lower())

        # 更新内存中的值
        if api_key is not None:
            self.api_key = api_key
        if refresh_interval is not None:
            self.refresh_interval = refresh_interval

        try:
            # 确保目标目录存在（安装模式下 %APPDATA% 目录可能尚未创建）
            config_path = Path(self.config_file)
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(str(config_path), 'w') as f:
                config.write(f)
            return True
        except Exception:
            return False

    # ── 验证 ──────────────────────────────────────────────

    def validate_interval(self, interval: int) -> str | None:
        """验证刷新间隔是否合法。

        Returns:
            None 表示合法，否则返回错误消息。
        """
        if interval < self.MIN_REFRESH_INTERVAL:
            return f"刷新间隔不能小于 {self.MIN_REFRESH_INTERVAL} 秒"
        if interval > self.MAX_REFRESH_INTERVAL:
            return f"刷新间隔不能大于 {self.MAX_REFRESH_INTERVAL} 秒"
        return None
