# DeepSeek API 额度监控

DeepSeek API 余额实时监控工具 — 基于 Python tkinter 的 Windows 桌面应用。

## 🚀 普通用户（无需 Python）

### 下载安装

1. 从 [Releases](../../releases) 下载最新安装包 `DeepSeek_API_Monitor_vX.X.X_Setup.exe`
2. 双击运行，按提示完成安装
3. 输入你的 DeepSeek API Key，开始使用

> 📖 详细使用说明请查看 [用户指南](docs/USER_GUIDE_CN.md)

### 功能

- 🔄 定时自动刷新 DeepSeek API 余额
- 📊 显示 CNY/USD 总余额、赠送余额、充值余额
- ⚙ 偏好设置：修改 API Key、测试连接、开关自启动
- 🚀 可选手动/自动开机自启动
- 💾 配置持久化（config.ini）
- 🖥 独立 EXE，无需安装 Python

---

## 👨‍💻 开发者

### 环境准备

```bash
# 克隆仓库
git clone <repo-url>
cd Deepseek-Usage

# 创建虚拟环境
python -m venv .venv
.venv\Scripts\Activate.ps1   # Windows PowerShell

# 安装依赖
pip install -r requirements.txt

# (可选) 安装开发依赖
pip install -r requirements-dev.txt
```

### 配置

**优先级**: 环境变量 (`.env`) > `config.ini` > 默认值

#### .env 文件（开发模式推荐）

```bash
cp .env.example .env
# 编辑 .env 填入真实 API Key
```

#### config.ini（运行时生成）

通过 GUI 界面「保存设置」或「偏好设置」生成。

### 运行

```bash
python deepseek_api_monitor.py
```

### 打包

```bash
# 仅打包 EXE
pip install pyinstaller
pyinstaller DeepSeek_API_Monitor.spec

# 打包 EXE + 安装包（需要安装 Inno Setup）
python scripts/build.py
```

> 安装包需要 [Inno Setup](https://jrsoftware.org/isinfo.php)，无 Inno Setup 时仅生成独立 EXE。

### 测试 & 质量

```bash
# 单元测试
pytest --cov=src --cov-report=term-missing

# 代码检查
ruff check src/

# 类型检查
mypy src/
```

---

## 项目结构

```
Deepseek-Usage/
├── src/                         # 源代码
│   ├── __init__.py              # 版本号
│   ├── config.py                # 配置管理 (env + ini)
│   ├── monitor.py               # API 调用 & 数据解析
│   ├── gui.py                   # tkinter 主界面 + 菜单 + 启动管理
│   └── settings_dialog.py       # 偏好设置对话框
├── scripts/
│   └── build.py                 # 构建脚本 (EXE + 安装包)
├── installer/
│   └── setup.iss                # Inno Setup 安装脚本
├── docs/
│   └── USER_GUIDE_CN.md         # 中文用户指南
├── tests/                       # 单元测试
├── deepseek_api_monitor.py      # 应用入口
├── pyproject.toml               # 项目元数据 & 工具配置
└── requirements.txt             # 运行时依赖
```

## 技术栈

- Python 3.9+
- tkinter (GUI)
- requests (HTTP)
- PyInstaller (打包)
- Inno Setup (安装包)
- pytest + ruff + mypy (开发)

## License

MIT
