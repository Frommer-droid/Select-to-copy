# -*- coding: utf-8 -*-
"""
POST-BUILD CLEANUP SCRIPT
Копирует ключевые файлы и убирает временные директории.
"""

import os
import shutil
import sys
import time

# Force UTF-8 for stdout
if sys.stdout:
    sys.stdout.reconfigure(encoding='utf-8')

# ========================================================
# 🔧 CONFIGURATION SECTION
# ========================================================
# Имя папки в dist (должно совпадать с именем в .spec файле)
APP_NAME = "Select-to-Copy"

# Список файлов для копирования в финальную папку приложения
# (исходный_путь_от_корня, имя_файла_в_папке_приложения)
FILES_TO_COPY = [
    ("logo.ico", "logo.ico"),
    # ("config.json", "config.json"), # Пример, если появится конфиг
]

# ========================================================
def safe_copy(src: str, dst: str, label: str) -> None:
    if os.path.exists(src):
        try:
            if os.path.isdir(src):
                if os.path.exists(dst):
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
            else:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
            print(f"[OK] Copied {label}")
        except Exception as e:
            print(f"[ERROR] Failed to copy {label}: {e}")
    else:
        print(f"[SKIP] {label} not found at {src}")


def main() -> None:
    print("\n" + "=" * 60)
    print(f"POST-BUILD CLEANUP: {APP_NAME}")
    print("=" * 60)

    if "REPLACE_WITH" in APP_NAME:
        print("ERROR: Please configure APP_NAME in post_build.py first!")
        return

    script_dir = os.path.abspath(os.path.dirname(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, ".."))
    dist_app_dir = os.path.join(script_dir, "dist", APP_NAME)
    final_app_dir = os.path.join(project_root, APP_NAME)

    # 1. Переносим собранное приложение
    if os.path.exists(dist_app_dir):
        try:
            if os.path.exists(final_app_dir):
                shutil.rmtree(final_app_dir)
                print(f"[OK] Removed old {APP_NAME}/")
            shutil.move(dist_app_dir, final_app_dir)
            print(f"[OK] Moved to: {final_app_dir}")
        except Exception as e:
            print(f"[ERROR] Failed to move: {e}")
            return
    else:
        print(f"[ERROR] dist/{APP_NAME} not found! Build might have failed.")
        return

    # 2. Удаляем временные директории
    print("\n[CLEANUP] Removing temporary directories...")
    temp_folders = [
        os.path.join(script_dir, "build"),
        os.path.join(script_dir, "dist"),
        os.path.join(script_dir, "__pycache__"),
        os.path.join(project_root, "dist"),
        os.path.join(project_root, "build"),
        os.path.join(project_root, "__pycache__"),
        os.path.join(final_app_dir, "__pycache__"),
    ]

    for folder_path in temp_folders:
        if folder_path and os.path.exists(folder_path):
            try:
                shutil.rmtree(folder_path)
                print(f"[OK] Removed {folder_path}")
            except Exception as e:
                print(f"[ERROR] Failed to remove {folder_path}: {e}")

    # 3. Копируем дополнительные файлы
    print("\n[COPY] Copying additional files...")
    for src_rel, dst_rel in FILES_TO_COPY:
        src = os.path.join(project_root, src_rel)
        dst = os.path.join(final_app_dir, dst_rel)
        safe_copy(src, dst, src_rel)
    
    # Автоматический поиск и копирование всех .json файлов из корня
    print("\n[COPY] Auto-copying .json files...")
    for file in os.listdir(project_root):
        if file.lower().endswith(".json"):
             src = os.path.join(project_root, file)
             dst = os.path.join(final_app_dir, file)
             safe_copy(src, dst, file)

    print("\n" + "=" * 60)
    print(f"DONE! App location: {final_app_dir}")
    print("=" * 60)

    # 4. Запускаем приложение
    exe_path = os.path.join(final_app_dir, f"{APP_NAME}.exe")
    if os.path.exists(exe_path):
        print(f"\n[EXEC] Launching {exe_path}...")
        try:
            os.startfile(exe_path)
        except Exception as e:
            print(f"[ERROR] Failed to launch exe: {e}")
    else:
        print(f"[ERROR] Executable not found: {exe_path}")

if __name__ == "__main__":
    main()
