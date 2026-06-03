# DeepSeek API 额度监控

DeepSeek API 余额实时监控工具 — 基于 Python tkinter 的 Windows 桌面应用。

## 功能

- 🔄 定时自动刷新 DeepSeek API 余额
- 📊 显示 CNY/USD 总余额、赠送余额、充值余额
- 👁 密码显示/隐藏切换
- 💾 设置持久化（config.ini）
- 🚀 可选开机自启动
- 🖥 支持 PyInstaller 打包为独立 EXE

## 安装

```bash
# 克隆仓库
git clone <repo-url>
cd Deepseek-Usage

# 创建虚拟环境
python -m venv .venv
.venv\Scripts\Activate.ps1   # Windows PowerShell

# 安装依赖
pip install -r requirements.txt
```

## 配置

**优先级**: 环境变量 (`.env`) > `config.ini` > 默认值

### 方式一：.env 文件（开发模式推荐）

```bash
cp .env.example .env
# 编辑 .env 填入真实 API Key
```

### 方式二：config.ini（打包后自动生成）

通过 GUI 界面「保存设置」按钮生成。

## 使用

```bash
python deepseek_api_monitor.py
```

### 打包为 EXE

```bash
pip install pyinstaller
pyinstaller DeepSeek_API_Monitor.spec
# EXE 输出在 dist/ 目录
```

## 开发

```bash
# 安装开发依赖
pip install -r requirements-dev.txt

# 运行测试
pytest --cov=src --cov-report=term-missing

# 代码检查
ruff check src/
ruff format --check src/

# 类型检查
mypy src/
```

## 项目结构

```
Deepseek-Usage/
├── src/                    # 源代码
│   ├── __init__.py         # 版本号
│   ├── config.py           # 配置管理
│   ├── monitor.py          # API 调用 & 数据解析
│   └── gui.py              # tkinter GUI
├── tests/                  # 测试
│   ├── test_config.py
│   ├── test_monitor.py
│   └── test_gui.py
├── deepseek_api_monitor.py # 应用入口
├── pyproject.toml          # 项目元数据 & 工具配置
└── requirements.txt        # 运行时依赖
```

## 技术栈

- Python 3.9+
- tkinter (GUI)
- requests (HTTP)
- PyInstaller (打包)
- pytest + ruff + mypy (开发)
