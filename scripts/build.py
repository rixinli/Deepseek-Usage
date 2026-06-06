#!/usr/bin/env python3
"""构建脚本 — 使用 PyInstaller 打包为 Windows EXE，并可生成安装包。"""

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC_FILE = ROOT / "DeepSeek_API_Monitor.spec"
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build"
INSTALLER_SCRIPT = ROOT / "installer" / "setup.iss"
EXE_NAME = "DeepSeek_API_Monitor.exe"
CONFIG_EXAMPLE = ROOT / "deepseek_config.ini.example"


def clean_old_builds() -> None:
    """清理旧的构建产物。"""
    for d in [BUILD_DIR, DIST_DIR]:
        if d.exists():
            shutil.rmtree(d)
            print(f"  ✓ 已清理 {d.name}/")


def build_exe() -> bool:
    """使用 PyInstaller 打包为独立 EXE。

    Returns:
        True 表示成功。
    """
    print("\n[1/3] 运行 PyInstaller 打包...")
    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller", str(SPEC_FILE)],
        cwd=str(ROOT),
        capture_output=False,
    )

    if result.returncode != 0:
        print(f"\n  ✗ PyInstaller 失败 (exit code {result.returncode})")
        return False

    exe_path = DIST_DIR / EXE_NAME
    if not exe_path.exists():
        print("\n  ✗ PyInstaller 完成但未找到 EXE")
        return False

    print(f"  ✓ EXE 已生成: {exe_path}")
    return True


def copy_config_template() -> bool:
    """复制配置文件模板到 dist/ 目录。

    Returns:
        True 表示成功。
    """
    print("\n[2/3] 复制配置文件模板...")
    if not CONFIG_EXAMPLE.exists():
        print(f"  ✗ 未找到 {CONFIG_EXAMPLE}")
        return False

    dest = DIST_DIR / CONFIG_EXAMPLE.name
    shutil.copy2(CONFIG_EXAMPLE, dest)
    print(f"  ✓ 已复制到 {dest}")
    return True


def build_installer() -> bool:
    """使用 Inno Setup 生成 Windows 安装包。

    Returns:
        True 表示成功（或 Inno Setup 未安装时返回 False 但非致命）。
    """
    print("\n[3/3] 生成安装包...")

    if not INSTALLER_SCRIPT.exists():
        print(f"  ⚠ 未找到安装脚本: {INSTALLER_SCRIPT}")
        print("    请先创建 installer/setup.iss")
        return False

    # 尝试查找 Inno Setup 编译器
    iscc_paths = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
    ]

    iscc_exe = None
    for path in iscc_paths:
        if Path(path).exists():
            iscc_exe = path
            break

    if iscc_exe is None:
        print("  ⚠ 未找到 Inno Setup Compiler (ISCC.exe)")
        print("    安装包未生成。如需安装包，请安装 Inno Setup:")
        print("    https://jrsoftware.org/isinfo.php")
        print(f"\n    手动编译: 用 Inno Setup 打开 {INSTALLER_SCRIPT}")
        return False  # 非致命 — EXE 已可用

    result = subprocess.run(
        [iscc_exe, str(INSTALLER_SCRIPT)],
        cwd=str(ROOT),
        capture_output=False,
    )

    if result.returncode == 0:
        installer_dir = DIST_DIR / "installer"
        print(f"  ✓ 安装包已生成到 {installer_dir}/")
        return True
    else:
        print(f"\n  ✗ Inno Setup 编译失败 (exit code {result.returncode})")
        return False


def main() -> int:
    """主构建流程。"""
    print("=" * 55)
    print(" DeepSeek API Monitor — Build Script")
    print("=" * 55)

    # 清理旧构建
    print("\n清理旧构建产物...")
    clean_old_builds()

    # 打包 EXE
    if not build_exe():
        return 1

    # 复制配置模板
    copy_config_template()

    # 生成安装包（可选）
    build_installer()

    # 总结
    print("\n" + "=" * 55)
    print(" ✅ 构建完成!")
    print(f"    EXE:       {DIST_DIR / EXE_NAME}")
    installer = DIST_DIR / "installer"
    if installer.exists():
        setups = list(installer.glob("*_Setup.exe"))
        if setups:
            print(f"    安装包:    {setups[0]}")
    print("=" * 55)
    return 0


if __name__ == "__main__":
    sys.exit(main())
