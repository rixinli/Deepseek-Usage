# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.0] — 2026-06-03

### Added
- 项目模块化拆分：`src/config.py`、`src/monitor.py`、`src/gui.py`
- pytest 测试框架 + 27 个单元测试（config / monitor / gui）
- pyproject.toml 统一管理项目元数据和工具配置（ruff, mypy, pytest, coverage）
- GitHub Actions CI 流水线
- README.md 和 CHANGELOG.md

### Changed
- `deepseek_api_monitor.py` 改为入口脚本，从 `src/` 导入模块
- 配置管理统一为 `AppConfig` 类
- API 调用和格式化逻辑抽取为纯函数，方便测试

## [2.0.0] — 2026-06-03

### Added
- DeepSeek API 余额监控 GUI（tkinter）
- .env 文件支持（python-dotenv）
- config.ini 配置持久化
- 开机自启动快捷方式（Windows）
- PyInstaller 打包支持
