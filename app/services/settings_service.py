from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.config.app_config import SETTINGS_FILE_NAME
from app.models.exclusion_settings import ExclusionSettings

DEFAULT_WINDOW_SETTINGS: dict[str, Any] = {
    "x": 120,
    "y": 120,
    "width": 540,
    "height": 420,
    "maximized": False,
}


class SettingsService:
    def __init__(self, project_root: Path, logger: logging.Logger) -> None:
        self._logger = logger
        self._settings_path = project_root / SETTINGS_FILE_NAME

    @property
    def settings_path(self) -> Path:
        return self._settings_path

    def load_settings(self) -> dict[str, Any]:
        if not self._settings_path.exists():
            settings = self._build_default_settings()
            self.save_settings(settings)
            return settings

        try:
            with self._settings_path.open("r", encoding="utf-8") as settings_file:
                loaded = json.load(settings_file)
        except Exception as error:
            self._logger.warning(
                "Не удалось прочитать settings.json, используется конфигурация по умолчанию: %s",
                error,
            )
            settings = self._build_default_settings()
            self.save_settings(settings)
            return settings

        settings = self._normalize_settings(loaded)
        if settings != loaded:
            self.save_settings(settings)
        return settings

    def save_settings(self, settings: dict[str, Any]) -> None:
        self._settings_path.parent.mkdir(parents=True, exist_ok=True)
        with self._settings_path.open("w", encoding="utf-8") as settings_file:
            json.dump(settings, settings_file, ensure_ascii=False, indent=2)
            settings_file.write("\n")

    def get_exclusion_settings(self) -> ExclusionSettings:
        settings = self.load_settings()
        return ExclusionSettings.from_dict(settings.get("exclusions"))

    def update_exclusion_settings(self, exclusions: ExclusionSettings) -> None:
        settings = self.load_settings()
        settings["exclusions"] = exclusions.to_dict()
        self.save_settings(settings)

    def get_window_settings(self) -> dict[str, Any]:
        settings = self.load_settings()
        window_settings = settings.get("window", {})
        return {
            "x": self._safe_int(window_settings.get("x"), DEFAULT_WINDOW_SETTINGS["x"]),
            "y": self._safe_int(window_settings.get("y"), DEFAULT_WINDOW_SETTINGS["y"]),
            "width": self._safe_int(
                window_settings.get("width"), DEFAULT_WINDOW_SETTINGS["width"]
            ),
            "height": self._safe_int(
                window_settings.get("height"), DEFAULT_WINDOW_SETTINGS["height"]
            ),
            "maximized": bool(window_settings.get("maximized", False)),
        }

    def update_window_settings(self, window_settings: dict[str, Any]) -> None:
        settings = self.load_settings()
        current = self.get_window_settings()
        current.update(
            {
                "x": self._safe_int(window_settings.get("x"), current["x"]),
                "y": self._safe_int(window_settings.get("y"), current["y"]),
                "width": self._safe_int(window_settings.get("width"), current["width"]),
                "height": self._safe_int(window_settings.get("height"), current["height"]),
                "maximized": bool(window_settings.get("maximized", current["maximized"])),
            }
        )
        settings["window"] = current
        self.save_settings(settings)

    def export_exclusions(self, export_path: Path) -> None:
        exclusions = self.get_exclusion_settings()
        self.save_exclusions_to_file(export_path, exclusions)

    def import_exclusions(self, import_path: Path) -> ExclusionSettings:
        exclusions = self.load_exclusions_from_file(import_path)
        self.update_exclusion_settings(exclusions)
        return exclusions

    def save_exclusions_to_file(self, export_path: Path, exclusions: ExclusionSettings) -> None:
        export_path.parent.mkdir(parents=True, exist_ok=True)
        with export_path.open("w", encoding="utf-8") as export_file:
            json.dump(exclusions.to_dict(), export_file, ensure_ascii=False, indent=2)
            export_file.write("\n")

    def load_exclusions_from_file(self, import_path: Path) -> ExclusionSettings:
        with import_path.open("r", encoding="utf-8") as import_file:
            raw_data = json.load(import_file)

        if isinstance(raw_data, dict) and "exclusions" in raw_data:
            raw_data = raw_data["exclusions"]

        return ExclusionSettings.from_dict(raw_data)

    @staticmethod
    def _build_default_settings() -> dict[str, Any]:
        return {
            "window": dict(DEFAULT_WINDOW_SETTINGS),
            "exclusions": ExclusionSettings().to_dict(),
        }

    def _normalize_settings(self, raw_settings: Any) -> dict[str, Any]:
        if not isinstance(raw_settings, dict):
            return self._build_default_settings()

        normalized = self._build_default_settings()
        normalized["exclusions"] = ExclusionSettings.from_dict(
            raw_settings.get("exclusions")
        ).to_dict()

        raw_window = raw_settings.get("window", {})
        if isinstance(raw_window, dict):
            normalized["window"].update(
                {
                    "x": self._safe_int(raw_window.get("x"), normalized["window"]["x"]),
                    "y": self._safe_int(raw_window.get("y"), normalized["window"]["y"]),
                    "width": self._safe_int(
                        raw_window.get("width"), normalized["window"]["width"]
                    ),
                    "height": self._safe_int(
                        raw_window.get("height"), normalized["window"]["height"]
                    ),
                    "maximized": bool(raw_window.get("maximized", False)),
                }
            )
        return normalized

    @staticmethod
    def _safe_int(value: Any, fallback: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return fallback
