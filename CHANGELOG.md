# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.2.0] — 2026-06-06

### Added
- **偏好设置对话框** (`src/settings_dialog.py`) — 独立的设置窗口，支持标签页切换
- **API Key 测试连接** — 在设置中可直接验证 API Key 是否有效
- **开机自启动开关** — GUI 内可手动启用/禁用开机自启动
- **智能启动提示** — 首次运行仅询问一次，选择后不再打扰
- **启动自动监控选项** — 启动时是否自动开始监控
- **菜单栏** — 设置 > 偏好设置，帮助 > 使用指南/关于
- **Inno Setup 安装脚本** (`installer/setup.iss`) — 生成 Windows 安装包
- **中文用户指南** (`docs/USER_GUIDE_CN.md`) — 面向普通用户的图文教程

### Changed
- `AppConfig` 扩展支持 `startup_enabled`、`startup_asked`、`auto_monitor` 字段
- `save()` 方法支持部分更新（None 参数保留现有值）
- 入口脚本 `deepseek_api_monitor.py` 简化为薄启动器
- 构建脚本 `scripts/build.py` 增强：复制配置模板 + Inno Setup 集成
- README 重构为双轨体验（普通用户 vs 开发者）
- 测试数量：27 → 44

### Fixed
- 修复开机自启动弹窗每次都弹出的问题
- 修复 mypy 类型检查问题 (call-overload, lambda inference)

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
