# DeepSeek API 额度监控 — 用户指南

## 简介

DeepSeek API 额度监控是一款 Windows 桌面工具，可以**实时监控**你的 DeepSeek API 账户余额。

- 🔄 定时自动刷新余额
- 💰 显示总余额、赠送余额、充值余额
- 🚀 支持开机自启动
- 💾 配置自动保存
- 🖥 独立 EXE 运行，无需安装 Python

---

## 获取 API Key

在使用本软件前，你需要有一个 DeepSeek API Key：

1. 打开 [DeepSeek 开放平台](https://platform.deepseek.com/)
2. 注册/登录你的账号
3. 点击左侧菜单「API Keys」
4. 点击「创建 API Key」，复制生成的 Key

> ⚠️ **API Key 相当于你的账户密码，请勿泄露给他人！**

---

## 安装

### 方式一：安装包（推荐）

1. 下载 `DeepSeek_API_Monitor_vX.X.X_Setup.exe`
2. 双击运行，按提示完成安装
3. 安装过程中可选择：
   - 是否创建桌面快捷方式
   - 是否启用开机自启动
4. 安装完成后自动运行

### 方式二：绿色版（免安装）

直接运行 `DeepSeek_API_Monitor.exe` 即可使用，无需安装。

> 首次运行会提示是否设置开机自启动，选择后不会再次询问。

---

## 使用说明

### 1. 输入 API Key

启动后，在「API Key」输入框中粘贴你的 Key（点 👁 可切换显示/隐藏）。

### 2. 调整刷新间隔

在「刷新间隔」处设置查询频率（秒），推荐 **120-300 秒**：
- 太频繁可能触发 API 限流
- 太久则余额变化不能及时反映

> 范围限制：30 ～ 600 秒

### 3. 开始监控

点击 **▶ 开始监控** 按钮，软件将：
- 立即获取一次当前余额
- 按设定间隔自动刷新
- 显示下次刷新倒计时

### 4. 偏好设置（⚙）

点击工具栏的 ⚙ 按钮，或菜单「设置 > 偏好设置」，可以：

| 设置项 | 说明 |
|--------|------|
| API Key | 修改密钥，支持「测试连接」验证有效性 |
| 刷新间隔 | 30-600 秒 |
| 开机自动启动 | 登录 Windows 时自动运行本软件 |
| 启动时自动监控 | 打开软件后自动开始监控 |

### 5. 停止监控

点击 **⏹ 停止监控** 按钮停止自动刷新。

---

## 配置文件

软件配置保存在 `deepseek_config.ini` 文件中（与 EXE 同目录）：

```ini
[API]
api_key = sk-xxxxxxxx
refresh_interval = 120

[Settings]
startup_enabled = true
startup_asked = true
auto_monitor = true
```

你可以直接编辑此文件修改设置，也可以删除它重置所有配置。

---

## 常见问题

### Q: 显示「API Key 无效或已过期」？

检查 API Key 是否正确复制，或在 [DeepSeek 平台](https://platform.deepseek.com/api_keys) 确认 Key 是否已被删除/重新生成。

### Q: 显示「网络错误」？

- 检查网络连接是否正常
- 检查防火墙/代理设置
- 确认能访问 `https://api.deepseek.com`

### Q: 开机自启动不生效？

打开软件，进入「设置 > 偏好设置」，取消「开机自动启动」后重新勾选保存。也可以手动将 `DeepSeek_API_Monitor.exe` 的快捷方式放到以下文件夹：

```
C:\Users\<用户名>\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup
```

### Q: 如何完全卸载？

- **安装包版本**：通过 Windows「设置 > 应用」卸载，卸载时可选择是否保留配置文件
- **绿色版**：直接删除 EXE 文件及 `deepseek_config.ini` 即可

### Q: API 余额显示不正确？

尝试点击 **🔄 立即刷新** 手动更新一次。如仍不正确，可能是 API 返回数据格式变化，请联系开发者。

---

## 版本信息

- 当前版本：v2.2
- 开源地址：[GitHub](https://github.com/DavidLeeeee/DeepSeek-Usage)

---

## 联系与反馈

如有问题或建议，请在 [GitHub Issues](https://github.com/DavidLeeeee/DeepSeek-Usage/issues) 提交反馈。
