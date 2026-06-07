; ═══════════════════════════════════════════════════════════════
; DeepSeek API 额度监控 — Inno Setup 安装脚本
; ═══════════════════════════════════════════════════════════════
;
; 使用方法:
;   1. 先运行 PyInstaller 生成 EXE → dist/DeepSeek_API_Monitor.exe
;   2. 用 Inno Setup Compiler 打开此 .iss 文件并编译
;   3. 安装包输出到 dist/installer/
;
; 安装后:
;   - EXE 安装到 {app} (默认 Program Files)
;   - 配置文件存储在 %APPDATA%\DeepSeek API Monitor\
;   - 卸载时默认保留配置文件（用户可选删除）
;
; ═══════════════════════════════════════════════════════════════

#define MyAppName "DeepSeek API 额度监控"
#define MyAppNameEn "DeepSeek API Monitor"
#define MyAppVersion "2.4.4"
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

; 安装路径（用户可在向导中自定义）
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
AllowNoIcons=yes

; 允许用户选择安装目录（默认启用，无需显式设置）
; DisableDirPage=no  是默认值

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

[Languages]
; 中文语言文件已随仓库打包，不依赖系统 Inno Setup 安装目录
Name: "chinese"; MessagesFile: "ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
; 桌面快捷方式
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "快捷方式:"; Flags: checkedonce
; 开机自启动
Name: "startup"; Description: "开机自动启动（登录 Windows 时自动运行）"; GroupDescription: "其他选项:"
; 安装后立即运行
Name: "launch"; Description: "安装完成后立即运行"; GroupDescription: "其他选项:"; Flags: checkedonce unchecked

[Dirs]
; 提前创建 %APPDATA% 配置目录，确保应用启动时目录已存在
Name: "{userappdata}\{#MyAppName}"; Flags: uninsneveruninstall

[Files]
; 主程序 EXE — 仅安装到 {app}，配置文件由应用自动管理
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; 开始菜单快捷方式
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\卸载 {#MyAppName}"; Filename: "{uninstallexe}"
; 桌面快捷方式
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
; 开机自启动 — 从 Program Files 启动，WorkingDirectory 对应用无影响
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startup

[Run]
; 安装完成后运行
Filename: "{app}\{#MyAppExeName}"; Description: "运行 {#MyAppName}"; Flags: nowait postinstall skipifsilent; Tasks: launch

[UninstallRun]
; 卸载前关闭正在运行的程序
Filename: "taskkill"; Parameters: "/f /im {#MyAppExeName}"; Flags: runhidden skipifdoesntexist

[Code]
// ═══════════════════════════════════════════════════════════════
// 自定义卸载逻辑 — 保护配置文件
// ═══════════════════════════════════════════════════════════════

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ConfigDir: String;
begin
  // 卸载进行中 — 清理开机自启动快捷方式
  if CurUninstallStep = usUninstall then
  begin
    if DeleteFile(ExpandConstant('{userstartup}\{#MyAppName}.lnk')) then
      Log('Removed startup shortcut');
  end;

  // 卸载完成后 — 询问是否保留配置
  if CurUninstallStep = usPostUninstall then
  begin
    ConfigDir := ExpandConstant('{userappdata}\{#MyAppName}');
    if DirExists(ConfigDir) then
    begin
      if MsgBox(
        '是否保留配置文件（API Key 和偏好设置）？' + #13#10 + #13#10 +
        '是 — 保留配置。重新安装后将自动恢复您的设置。' + #13#10 +
        '否 — 永久删除所有配置数据。',
        mbConfirmation, MB_YESNO or MB_DEFBUTTON1
      ) = IDNO then
      begin
        if DelTree(ConfigDir, True, True, True) then
          Log('Config directory deleted: ' + ConfigDir)
        else
          Log('Failed to delete config directory: ' + ConfigDir);
      end
      else
        Log('Config directory preserved: ' + ConfigDir);
    end;
  end;
end;
