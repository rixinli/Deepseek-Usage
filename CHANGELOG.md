# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.4.6] — 2026-06-07

### Fixed
- 修复 Gitee credential store 认证方式，统一使用 API 获取登录名
- 移除 `continue-on-error` 让 Gitee 同步错误可被看到
- 修复下载链接使用硬编码用户名的问题

## [2.4.5] — 2026-06-07

### Fixed
- 修复 Gitee 同步脚本 Unicode 语法错误
- `create-release` job 添加 `setup-python` 确保 Python 可用

## [2.4.4] — 2026-06-07

### Added
- **完整 Gitee-GitHub 同步链路** — CI 测试通过后自动镜像源码到 Gitee，发布时同步 Release 内容一致
- Gitee 大文件通过 git push 传输到 dist 分支，绕过 API 上传限制

### Fixed
- 修复 Gitee 认证方式，使用 credential store 替代 URL 内嵌 token
- Gitee Release 下载列表过滤掉多余的 `deepseek_config.ini.example`

## [2.3.1] — 2026-06-06

### Added
- **Gitee Release 镜像同步** — GitHub Actions 构建完成自动推送到 Gitee，国内满速下载

### Fixed
- 修复 ruff I001 import 排序问题

## [2.3.0] — 2026-06-06

### Added
- **全新设置向导 UI** — 顶部步骤条 + 底部按钮栏，页面切换更直观
- **偏好设置页滚动支持** — 小窗口下可鼠标滚轮滚动设置项
- **API Key 获取链接可点击打开浏览器**
- `--wizard` 命令行标志，强制弹出设置向导

### Changed
- 统一字体常量管理，tk 与 ttk 控件字体一致
- 完成按钮文案简化为「保存」

### Fixed
- **修复 API Key 保存后重启被 `.env` 覆盖的问题** — config.ini 优先级调整为高于 .env
- 修复 CI 缺少 ChineseSimplified.isl 导致构建失败
- 修复 release workflow 中版本提取脚本的 Python 内联转义问题

## [2.2.1] — 2026-06-06

### Fixed
- 修复 CI 流水线 Python 3.9 兼容性问题（`X | None` 语法需要 `from __future__ import annotations`）
- 修复 `*.spec` 文件被 `.gitignore` 忽略导致无法构建的问题
- 修复 `ruff` UP035/UP045 规则（`Callable` 从 `collections.abc` 导入，`Optional[str]` 替换为 `str | None`）
- 更新 CI 矩阵：Python 3.9 → 3.10/3.11/3.12/3.13

### Added
- **GitHub Release 工作流** (`.github/workflows/release.yml`) — 标签推送时自动构建 EXE + 安装包并发布 Release
- `DeepSeek_API_Monitor.spec` 追加入库（构建必需）

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
