"""
cx_Freeze setup script for building a Windows MSI installer.

Usage (on Windows):
    python setup_msi.py bdist_msi

This will create an MSI installer in the dist/ folder.
"""

import sys
from cx_Freeze import setup, Executable

build_exe_options = {
    "packages": [
        "customtkinter",
        "pystray",
        "keyboard",
        "pyautogui",
        "PIL",
        "requests",
        "psutil",
        "tkinter",
        "io",
        "threading",
        "socket",
        "platform",
        "ctypes",
        "json",
    ],
    "includes": [
        "src.it_agent",
        "src.it_agent.sysinfo",
        "src.it_agent.screenshot",
        "src.it_agent.gui",
        "src.it_agent.tray",
        "src.it_agent.api",
    ],
    "include_files": [],
    "excludes": ["test", "unittest"],
}

bdist_msi_options = {
    "upgrade_code": "{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}",
    "add_to_path": False,
    "initial_target_dir": r"[ProgramFilesFolder]\OCP_IT_Help_Center",
}

base = None
if sys.platform == "win32":
    base = "Win32GUI"

executables = [
    Executable(
        "main.py",
        base=base,
        target_name="OCP_IT_Help_Center.exe",
        shortcut_name="OCP IT Help Center",
        shortcut_dir="DesktopFolder",
        icon=None,
    )
]

setup(
    name="OCP IT Help Center",
    version="1.0.0",
    description="OCP IT Help Center - Background desktop tool for capturing screenshots and IT tickets",
    author="OCP IT",
    options={
        "build_exe": build_exe_options,
        "bdist_msi": bdist_msi_options,
    },
    executables=executables,
)
