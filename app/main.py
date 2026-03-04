from __future__ import annotations

import ctypes
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from app.config.app_config import (
    APP_ID,
    APP_NAME,
    ICON_FILE_NAME,
    PAUSE_ICON_RELATIVE_PATH,
    project_root,
)
from app.config.theme import TOOLTIP_STYLESHEET
from app.version import __version__


def _set_windows_app_user_model_id() -> None:
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    except Exception:
        pass


def run() -> int:
    _set_windows_app_user_model_id()

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setQuitOnLastWindowClosed(False)
    app.setStyleSheet(TOOLTIP_STYLESHEET)

    root = project_root()
    icon_path = root / ICON_FILE_NAME
    pause_icon_path = root / PAUSE_ICON_RELATIVE_PATH
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    if not QSystemTrayIcon.isSystemTrayAvailable():
        print("Системный трей недоступен. Завершение приложения.")
        return 1

    # Локальный импорт уменьшает риск конфликтов COM/DPI до инициализации Qt.
    from app.core.application_controller import ApplicationController

    controller = ApplicationController(
        project_root=root,
        icon_path=icon_path,
        pause_icon_path=pause_icon_path,
        version=__version__,
    )
    controller.start()
    return app.exec()
