# -*- coding: utf-8 -*-
"""Формирование итоговой onedir-папки после сборки PyInstaller."""

import importlib.metadata
import json
import platform
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

# Force UTF-8 for stdout
if sys.stdout:
    sys.stdout.reconfigure(encoding='utf-8')

# ========================================================
# 🔧 CONFIGURATION SECTION
# ========================================================
# Имя папки в dist (должно совпадать с именем в .spec файле)
APP_NAME = "Select-to-Copy"

FILES_TO_COPY = ("VERSION", "logo.ico", "LICENSE")
RUNTIME_PACKAGES = ("PySide6", "shiboken6", "PyInstaller")

# ========================================================
def installed_version(package_name: str) -> str | None:
    try:
        return importlib.metadata.version(package_name)
    except importlib.metadata.PackageNotFoundError:
        return None


def copy_required_file(project_root: Path, target_dir: Path, filename: str) -> None:
    source = project_root / filename
    if not source.is_file():
        raise FileNotFoundError(f"Не найден обязательный файл: {source}")
    shutil.copy2(source, target_dir / filename)
    print(f"[OK] Скопирован {filename}")


def write_runtime_manifest(project_root: Path, target_dir: Path) -> None:
    packages = {name: installed_version(name) for name in RUNTIME_PACKAGES}
    qt_root = target_dir / "_internal" / "PySide6"
    qt_dlls = (
        sorted(
            path.relative_to(target_dir).as_posix()
            for path in qt_root.rglob("Qt*.dll")
        )
        if qt_root.is_dir()
        else []
    )
    manifest = {
        "manifest_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "application": {
            "name": APP_NAME,
            "release_version": (project_root / "VERSION")
            .read_text(encoding="utf-8")
            .strip(),
        },
        "build_environment": {
            "python_version": sys.version.split()[0],
            "platform": platform.platform(),
            "pyinstaller_version": packages["PyInstaller"],
        },
        "bundled_python_packages": packages,
        "qt_runtime": {"qt_dlls": qt_dlls},
    }
    (target_dir / "RUNTIME_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("[OK] Создан RUNTIME_MANIFEST.json")


def main() -> int:
    print("\n" + "=" * 60)
    print(f"POST-BUILD CLEANUP: {APP_NAME}")
    print("=" * 60)

    if "REPLACE_WITH" in APP_NAME:
        print("ERROR: Please configure APP_NAME in post_build.py first!")
        return 1

    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent
    dist_app_dir = script_dir / "dist" / APP_NAME
    final_app_dir = project_root / APP_NAME

    # 1. Переносим собранное приложение
    if dist_app_dir.is_dir():
        try:
            if final_app_dir.exists():
                shutil.rmtree(final_app_dir)
                print(f"[OK] Removed old {APP_NAME}/")
            shutil.move(str(dist_app_dir), str(final_app_dir))
            print(f"[OK] Moved to: {final_app_dir}")
        except Exception as exc:
            print(f"[ERROR] Failed to move: {exc}")
            return 1
    else:
        print(f"[ERROR] dist/{APP_NAME} not found! Build might have failed.")
        return 1

    # 2. Удаляем временные директории
    print("\n[CLEANUP] Removing temporary directories...")
    temp_folders = [
        script_dir / "build",
        script_dir / "dist",
        script_dir / "__pycache__",
        project_root / "dist",
        project_root / "build",
        project_root / "__pycache__",
        final_app_dir / "__pycache__",
    ]

    for folder_path in temp_folders:
        if folder_path.exists():
            try:
                shutil.rmtree(folder_path)
                print(f"[OK] Removed {folder_path}")
            except Exception as exc:
                print(f"[ERROR] Failed to remove {folder_path}: {exc}")

    # 3. Копируем дополнительные файлы
    print("\n[COPY] Copying additional files...")
    try:
        for filename in FILES_TO_COPY:
            copy_required_file(project_root, final_app_dir, filename)
        write_runtime_manifest(project_root, final_app_dir)
    except Exception as exc:
        print(f"[ERROR] Post-build validation failed: {exc}")
        return 1

    print("\n" + "=" * 60)
    print(f"DONE! App location: {final_app_dir}")
    print("=" * 60)

    # Собранное приложение не запускается автоматически: запуск выполняется
    # отдельно после проверки или развертывания portable-копии.
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
