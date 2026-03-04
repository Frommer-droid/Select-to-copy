from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _deduplicate_process_names(process_names: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for process_name in process_names:
        normalized = process_name.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        result.append(process_name)
    return result


@dataclass(slots=True)
class ExclusionSettings:
    enabled: bool = True
    process_names: list[str] = field(default_factory=list)

    @staticmethod
    def from_dict(data: dict[str, Any] | None) -> "ExclusionSettings":
        if not isinstance(data, dict):
            return ExclusionSettings()

        enabled = bool(data.get("enabled", True))
        raw_process_names = data.get("process_names", [])

        process_names: list[str] = []
        if isinstance(raw_process_names, list):
            for raw_process_name in raw_process_names:
                if not isinstance(raw_process_name, str):
                    continue
                process_name = raw_process_name.strip()
                if process_name:
                    process_names.append(process_name)

        return ExclusionSettings(
            enabled=enabled,
            process_names=_deduplicate_process_names(process_names),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "process_names": list(self.process_names),
        }
