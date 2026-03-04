from __future__ import annotations

from pathlib import Path

APP_ID = "mycompany.selecttocopy.utility.1.10"
APP_NAME = "Select-to-Copy"
LOG_FILE_NAME = "select_to_copy.log"
SETTINGS_FILE_NAME = "settings.json"
ICON_FILE_NAME = "logo.ico"
PAUSE_ICON_RELATIVE_PATH = "assets/icons/logo-pause.ico"

DRAG_THRESHOLD_PX = 10
COPY_SETTLE_DELAY_SEC = 0.05
CLIPBOARD_SETTLE_DELAY_SEC = 0.1
COPY_TOOLTIP_DURATION_MS = 1000
COPY_TOOLTIP_TEXT = "Скопировано!"
AUTO_PAUSE_POLL_INTERVAL_MS = 300


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent
