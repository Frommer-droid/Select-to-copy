# -*- coding: utf-8 -*-
"""Обновление локальной portable-копии Select-to-Copy."""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
import time
from pathlib import Path


APP_NAME = "Select-to-Copy"
DESTINATION_PARENT = Path(r"D:\Portable_soft")


def remove_readonly(func, path, _exc_info) -> None:
    os.chmod(path, stat.S_IWRITE)
    func(path)


def ensure_safe_target(target: Path, parent: Path) -> None:
    resolved_parent = parent.resolve()
    resolved_target = target.resolve(strict=False)
    if resolved_target == resolved_parent:
        raise RuntimeError("Целевая папка совпадает с родительской.")
    try:
        resolved_target.relative_to(resolved_parent)
    except ValueError as exc:
        raise RuntimeError(f"Небезопасный целевой путь: {resolved_target}") from exc


def stop_target_process(target_folder: Path) -> None:
    escaped_path = str(target_folder.resolve(strict=False)).replace("'", "''")
    script = (
        f"$target = [System.IO.Path]::GetFullPath('{escaped_path}'); "
        "if (-not $target.EndsWith([System.IO.Path]::DirectorySeparatorChar)) "
        "{ $target += [System.IO.Path]::DirectorySeparatorChar }; "
        f"Get-Process -Name '{APP_NAME}' -ErrorAction SilentlyContinue | "
        "Where-Object { $_.Path -and "
        "([System.IO.Path]::GetFullPath($_.Path)).StartsWith("
        "$target, [System.StringComparison]::OrdinalIgnoreCase) } | "
        "Stop-Process -Force"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        check=True,
    )
    time.sleep(1)


def main() -> int:
    project_root = Path(__file__).resolve().parent
    source_folder = project_root / APP_NAME
    target_folder = DESTINATION_PARENT / APP_NAME

    if not source_folder.is_dir():
        raise RuntimeError(f"Исходная папка не найдена: {source_folder}")
    required_items = (
        f"{APP_NAME}.exe",
        "_internal",
        "VERSION",
        "RUNTIME_MANIFEST.json",
    )
    for required in required_items:
        if not (source_folder / required).exists():
            raise RuntimeError(f"В сборке отсутствует: {required}")

    DESTINATION_PARENT.mkdir(parents=True, exist_ok=True)
    ensure_safe_target(target_folder, DESTINATION_PARENT)
    stop_target_process(target_folder)

    settings_path = target_folder / "settings.json"
    preserved_settings = settings_path.read_bytes() if settings_path.is_file() else None

    if target_folder.exists():
        shutil.rmtree(target_folder, onerror=remove_readonly)
        print(f"[OK] Удалена старая portable-папка: {target_folder}")
    shutil.copytree(source_folder, target_folder)
    if preserved_settings is not None:
        (target_folder / "settings.json").write_bytes(preserved_settings)
        print("[OK] Сохранен существующий settings.json")
    print(f"[OK] Portable-папка обновлена: {target_folder}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
