from __future__ import annotations


class PauseStateService:
    def __init__(self) -> None:
        self._manual_paused = False
        self._auto_paused = False
        self._auto_pause_process_name: str | None = None

    @property
    def manual_paused(self) -> bool:
        return self._manual_paused

    @property
    def auto_paused(self) -> bool:
        return self._auto_paused

    @property
    def auto_pause_process_name(self) -> str | None:
        return self._auto_pause_process_name

    def toggle_manual_pause(self) -> bool:
        self._manual_paused = not self._manual_paused
        return self._manual_paused

    def set_manual_paused(self, value: bool) -> None:
        self._manual_paused = bool(value)

    def is_effectively_paused(self) -> bool:
        return self._manual_paused or self._auto_paused

    def apply_auto_pause(self, process_name: str | None, should_pause: bool) -> bool:
        normalized_process_name = process_name.strip().lower() if process_name else None
        target_process_name = normalized_process_name if should_pause else None

        state_changed = (
            self._auto_paused != bool(should_pause)
            or self._auto_pause_process_name != target_process_name
        )

        self._auto_paused = bool(should_pause)
        self._auto_pause_process_name = target_process_name
        return state_changed
