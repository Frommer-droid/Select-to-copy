from __future__ import annotations

from typing import Iterable


class ProcessExclusionService:
    def __init__(self, enabled: bool = True, process_names: Iterable[str] | None = None) -> None:
        self._enabled = bool(enabled)
        self._process_names: list[str] = []
        self._normalized_process_names: set[str] = set()
        self.set_process_names(list(process_names or []))

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, value: bool) -> None:
        self._enabled = bool(value)

    @property
    def process_names(self) -> list[str]:
        return list(self._process_names)

    def set_process_names(self, process_names: Iterable[str]) -> None:
        cleaned_process_names: list[str] = []
        normalized: set[str] = set()

        for raw_process_name in process_names:
            process_name = str(raw_process_name).strip()
            if not process_name:
                continue
            process_name_key = process_name.lower()
            if process_name_key in normalized:
                continue
            cleaned_process_names.append(process_name)
            normalized.add(process_name_key)

        self._process_names = cleaned_process_names
        self._normalized_process_names = normalized

    def is_process_excluded(self, process_name: str | None) -> bool:
        if not self._enabled or not process_name:
            return False
        return process_name.strip().lower() in self._normalized_process_names
