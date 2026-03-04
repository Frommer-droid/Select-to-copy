from __future__ import annotations

import logging
from pathlib import Path

LOGGER_NAME = "select_to_copy"


def setup_session_logger(log_path: Path) -> logging.Logger:
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.propagate = False

    file_handler = logging.FileHandler(log_path, mode="w", encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.info("Старт новой сессии приложения.")
    return logger


def flush_and_close_logger(logger: logging.Logger) -> None:
    for handler in list(logger.handlers):
        try:
            handler.flush()
        finally:
            handler.close()
            logger.removeHandler(handler)
