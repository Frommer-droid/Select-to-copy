from __future__ import annotations

import logging
import math
import threading
from typing import Callable

from pynput import mouse

from app.config.app_config import DRAG_THRESHOLD_PX
from app.services.selection_copy_service import SelectionCopyService


class MouseSelectionService:
    def __init__(
        self,
        selection_service: SelectionCopyService,
        should_process_drag: Callable[[], bool],
        on_copy_requested: Callable[[int, int], None],
        logger: logging.Logger,
    ) -> None:
        self._selection_service = selection_service
        self._should_process_drag = should_process_drag
        self._on_copy_requested = on_copy_requested
        self._logger = logger

        self._drag_start_pos = (0, 0)
        self._is_dragging = False
        self._skip_copy_for_current_drag = False

        self._stop_event = threading.Event()
        self._listener: mouse.Listener | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_listener, daemon=True)
        self._thread.start()
        self._logger.info("Глобальный слушатель мыши запущен.")

    def stop(self) -> None:
        self._stop_event.set()
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:
                pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._logger.info("Глобальный слушатель мыши остановлен.")

    def _run_listener(self) -> None:
        with mouse.Listener(on_click=self._on_click) as listener:
            self._listener = listener
            self._stop_event.wait()

    def _on_click(self, x: int, y: int, button: mouse.Button, pressed: bool) -> None:
        if button != mouse.Button.left:
            return

        if pressed:
            self._drag_start_pos = (x, y)
            self._is_dragging = True
            self._skip_copy_for_current_drag = self._selection_service.is_left_ctrl_pressed()
            return

        if not self._is_dragging:
            return

        try:
            if not self._should_process_drag():
                return

            drag_distance = math.sqrt(
                (x - self._drag_start_pos[0]) ** 2 + (y - self._drag_start_pos[1]) ** 2
            )
            if drag_distance < DRAG_THRESHOLD_PX:
                return

            if self._skip_copy_for_current_drag or self._selection_service.is_left_ctrl_pressed():
                self._logger.info("Режим Left Ctrl: только выделение, копирование пропущено.")
                return

            self._on_copy_requested(x, y)
        finally:
            self._is_dragging = False
            self._skip_copy_for_current_drag = False
