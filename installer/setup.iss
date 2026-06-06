; ═══════════════════════════════════════════════════════════════
; DeepSeek API 额度监控 — Inno Setup 安装脚本
; ═══════════════════════════════════════════════════════════════
;
; 使用方法:
;   1. 先运行 scripts/build.py 生成 EXE → dist/DeepSeek_API_Monitor.exe
;   2. 安装 Inno Setup: https://jrsoftware.org/isinfo.php
;   3. 用 Inno Setup Compiler 打开此 .iss 文件并编译
;   4. 安装包输出到 dist/installer/
;
; ═══════════════════════════════════════════════════════════════

#define MyAppName "DeepSeek API 额度监控"
#define MyAppNameEn "DeepSeek API Monitor"
#define MyAppVersion "2.2.0"
#define MyAppPublisher "DeepSeek-Usage"
#define MyAppURL "https://github.com/DavidLeeeee/DeepSeek-Usage"
#define MyAppExeName "DeepSeek_API_Monitor.exe"

[Setup]
; 安装程序基本信息
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; 安装路径
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
AllowNoIcons=yes

; 安装程序输出
OutputDir=..\dist\installer
OutputBaseFilename=DeepSeek_API_Monitor_v{#MyAppVersion}_Setup

; 压缩
Compression=lzma2/ultra64
SolidCompression=yes

; 界面设置
WizardStyle=modern
WizardSizePercent=100,100

; 语言
ShowLanguageDialog=auto
UsePreviousLanguage=no

; 权限 — 当前用户即可安装，无需管理员
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; 卸载时可选保留配置
; (通过自定义卸载页面实现)

[Languages]
Name: "chinese"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
; 桌面快捷方式
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "快捷方式:"; Flags: checkedonce
; 开机自启动
Name: "startup"; Description: "开机自动启动（登录 Windows 时自动运行）"; GroupDescription: "其他选项:";
; 安装后立即运行
Name: "launch"; Description: "安装完成后立即运行"; GroupDescription: "其他选项:"; Flags: checkedonce unchecked

[Files]
; 主程序 EXE
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
; 配置文件模板
Source: "..\deepseek_config.ini.example"; DestDir: "{app}"; DestName: "deepseek_config.ini.example"; Flags: ignoreversion
; 如果用户已有 config.ini，不要覆盖
; (首次安装不存在 config.ini，所以不会覆盖)

[Icons]
; 开始菜单快捷方式
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\卸载 {#MyAppName}"; Filename: "{uninstallexe}"
; 桌面快捷方式
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
; 开机自启动
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startup

[Run]
; 安装完成后运行
Filename: "{app}\{#MyAppExeName}"; Description: "运行 {#MyAppName}"; Flags: nowait postinstall skipifsilent; Tasks: launch

[UninstallRun]
; 卸载前关闭正在运行的程序（如果是监控应用）
Filename: "taskkill"; Parameters: "/f /im {#MyAppExeName}"; Flags: runhidden skipifdoesntexist

[Code]
// ═══════════════════════════════════════════════════════════════
// 自定义卸载页面 — 询问是否保留配置文件
// ═══════════════════════════════════════════════════════════════

var
  KeepConfigPage: TInputOptionWizardPage;

procedure InitializeWizard;
begin
  // 安装界面 — 无额外自定义
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ConfigPath: String;
begin
  if CurUninstallStep = usUninstall then
  begin
    // 卸载时清理开机自启动快捷方式
    if DeleteFile(ExpandConstant('{userstartup}\{#MyAppName}.lnk')) then
      Log('Removed startup shortcut');
  end;

  if CurUninstallStep = usPostUninstall then
  begin
    // 彻底清理 — 删除数据目录（如果用户选择不保留）
    ConfigPath := ExpandConstant('{app}');
    if DirExists(ConfigPath) then
    begin
      if MsgBox('是否保留配置文件 (deepseek_config.ini)？' + #13#10 +
                '保留后重新安装将无需重新配置 API Key。',
                mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDNO then
      begin
        DelTree(ConfigPath, True, True, True);
      end;
    end;
  end;
end;
