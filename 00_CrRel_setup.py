# -*- coding: utf-8 -*-
"""Создание Windows-установщика Select-to-Copy через Inno Setup 6."""

from __future__ import annotations

import ctypes
import os
import shutil
import string
import subprocess
import tempfile
import winreg
from ctypes import wintypes
from pathlib import Path


APP_NAME = "Select-to-Copy"
APP_PUBLISHER = "Frommer-droid"
APP_ID = "{{3295C616-2F4C-407A-A3F1-9DCB9506A58E}}"
REQUIRED_ITEMS = (
    "Select-to-Copy.exe",
    "_internal",
    "VERSION",
    "logo.ico",
    "LICENSE",
    "RUNTIME_MANIFEST.json",
)


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", ctypes.c_ubyte * 8),
    ]


def resolve_desktop_dir() -> Path:
    override = os.environ.get("SELECT_TO_COPY_DESKTOP_DIR", "").strip()
    if override:
        return Path(override).expanduser().resolve()

    key_path = (
        r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
    )
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            value, _ = winreg.QueryValueEx(key, "Desktop")
        return Path(os.path.expandvars(value)).resolve()
    except OSError:
        pass

    folder_id = GUID(
        0xB4BFCC3A,
        0xDB2C,
        0x424C,
        (ctypes.c_ubyte * 8)(0xB0, 0x29, 0x7F, 0xE9, 0x9A, 0x87, 0xC6, 0x41),
    )
    desktop_pointer = ctypes.c_wchar_p()
    try:
        result = ctypes.windll.shell32.SHGetKnownFolderPath(
            ctypes.byref(folder_id),
            0,
            None,
            ctypes.byref(desktop_pointer),
        )
        if result == 0 and desktop_pointer.value:
            return Path(desktop_pointer.value).resolve()
    finally:
        if desktop_pointer:
            ctypes.windll.ole32.CoTaskMemFree(desktop_pointer)

    buffer = ctypes.create_unicode_buffer(260)
    if ctypes.windll.shell32.SHGetFolderPathW(None, 0x0010, None, 0, buffer) == 0:
        return Path(buffer.value).resolve()
    return (Path.home() / "Desktop").resolve()


def resolve_default_install_dir() -> Path:
    fixed_drives: list[Path] = []
    for letter in string.ascii_uppercase:
        root = f"{letter}:\\"
        if ctypes.windll.kernel32.GetDriveTypeW(root) == 3:
            fixed_drives.append(Path(root))
    for drive in fixed_drives:
        if str(drive).upper().startswith("D:"):
            return drive / "Apps" / APP_NAME
    for drive in fixed_drives:
        if not str(drive).upper().startswith("C:"):
            return drive / "Apps" / APP_NAME
    return Path(r"C:\Apps") / APP_NAME


def find_iscc() -> Path | None:
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    candidates = (
        os.environ.get("INNO_SETUP_ISCC", ""),
        shutil.which("ISCC.exe") or "",
        (
            str(Path(local_app_data) / "Programs" / "Inno Setup 6" / "ISCC.exe")
            if local_app_data
            else ""
        ),
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
    )
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return Path(candidate)
    return None


def read_version(project_root: Path) -> str:
    return (project_root / "VERSION").read_text(encoding="utf-8").strip()


def validate_release(source_dir: Path) -> None:
    missing = [item for item in REQUIRED_ITEMS if not (source_dir / item).exists()]
    if missing:
        raise RuntimeError("Папка релиза неполная: " + ", ".join(missing))


def remove_runtime_noise(work_dir: Path) -> None:
    for path in work_dir.rglob("*"):
        if not path.is_file():
            continue
        name = path.name.lower()
        if name == "settings.json" or name.endswith(".log") or ".log." in name:
            path.unlink()


def build_iss(
    work_dir: Path,
    output_dir: Path,
    install_dir: Path,
    version: str,
) -> str:
    return f"""#define MyAppName "{APP_NAME}"
#define MyAppVersion "{version}"
#define MyAppPublisher "{APP_PUBLISHER}"
#define MyAppExeName "{APP_NAME}.exe"

[Setup]
AppId={APP_ID}
AppName={{#MyAppName}}
AppVersion={{#MyAppVersion}}
AppPublisher={{#MyAppPublisher}}
DefaultDirName="{install_dir}"
UsePreviousAppDir=no
DefaultGroupName={{#MyAppName}}
DisableProgramGroupPage=yes
OutputDir="{output_dir}"
OutputBaseFilename={{#MyAppName}}_v{{#MyAppVersion}}_Setup
SetupIconFile="{work_dir / "logo.ico"}"
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
VersionInfoVersion={{#MyAppVersion}}.0
VersionInfoCompany={{#MyAppPublisher}}
VersionInfoDescription={{#MyAppName}} Setup
VersionInfoProductName={{#MyAppName}}

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "Создать значок на рабочем столе"; GroupDescription: "Дополнительные значки:"; Flags: checkedonce

[Files]
Source: "{work_dir}\\*"; DestDir: "{{app}}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{{group}}\\{{#MyAppName}}"; Filename: "{{app}}\\{{#MyAppExeName}}"; IconFilename: "{{app}}\\logo.ico"
Name: "{{group}}\\Удалить {{#MyAppName}}"; Filename: "{{uninstallexe}}"
Name: "{{autodesktop}}\\{{#MyAppName}}"; Filename: "{{app}}\\{{#MyAppExeName}}"; IconFilename: "{{app}}\\logo.ico"; Tasks: desktopicon

[Run]
Filename: "{{app}}\\{{#MyAppExeName}}"; Description: "Запустить {{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "taskkill"; Parameters: "/F /IM {{#MyAppExeName}}"; Flags: runhidden; RunOnceId: "KillApp"

[UninstallDelete]
Type: filesandordirs; Name: "{{app}}"
"""


def main() -> int:
    project_root = Path(__file__).resolve().parent
    source_dir = project_root / APP_NAME
    validate_release(source_dir)

    iscc = find_iscc()
    if iscc is None:
        raise RuntimeError(
            "Не найден ISCC.exe. Установите Inno Setup 6 "
            "или задайте INNO_SETUP_ISCC."
        )

    output_dir = resolve_desktop_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    version = read_version(project_root)

    with tempfile.TemporaryDirectory(prefix="select-to-copy-installer-") as temp:
        temp_root = Path(temp)
        work_dir = temp_root / APP_NAME
        shutil.copytree(source_dir, work_dir)
        remove_runtime_noise(work_dir)
        iss_path = temp_root / f"{APP_NAME}.iss"
        iss_path.write_text(
            build_iss(
                work_dir,
                output_dir,
                resolve_default_install_dir(),
                version,
            ),
            encoding="utf-8-sig",
        )
        subprocess.run([str(iscc), str(iss_path)], check=True)

    installer = output_dir / f"{APP_NAME}_v{version}_Setup.exe"
    if not installer.is_file():
        raise RuntimeError(f"Установщик не создан: {installer}")
    print(f"[OK] Установщик: {installer}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
