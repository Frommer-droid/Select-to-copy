from __future__ import annotations

import logging
import os

try:
    import win32api
    import win32con
    import win32gui
    import win32process

    PYWIN32_AVAILABLE = True
except ImportError:
    PYWIN32_AVAILABLE = False
    win32api = None
    win32con = None
    win32gui = None
    win32process = None


class ForegroundWindowService:
    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger
        if not PYWIN32_AVAILABLE:
            self._logger.warning(
                "pywin32 не установлена, авто-пауза по активному процессу недоступна."
            )

    def get_foreground_window(self) -> int | None:
        if not PYWIN32_AVAILABLE:
            return None
        try:
            return win32gui.GetForegroundWindow()
        except Exception as error:
            self._logger.debug("Не удалось получить foreground window: %s", error)
            return None

    def get_foreground_process_name(self) -> str | None:
        hwnd = self.get_foreground_window()
        return self.get_process_name_from_hwnd(hwnd)

    def get_capture_target_process_name(self) -> str | None:
        if not PYWIN32_AVAILABLE:
            return None
        try:
            cursor_x, cursor_y = win32api.GetCursorPos()
        except Exception:
            cursor_x, cursor_y = (None, None)

        if cursor_x is not None and cursor_y is not None:
            process_name = self.get_process_name_at_point(cursor_x, cursor_y)
            if process_name:
                return process_name

        return self.get_foreground_process_name()

    def get_process_name_at_point(self, x: int, y: int) -> str | None:
        if not PYWIN32_AVAILABLE:
            return None
        try:
            hwnd = win32gui.WindowFromPoint((int(x), int(y)))
            if not hwnd:
                return None

            ga_root = getattr(win32con, "GA_ROOT", 2)
            try:
                root_hwnd = win32gui.GetAncestor(hwnd, ga_root)
                hwnd = root_hwnd or hwnd
            except Exception:
                pass

            return self.get_process_name_from_hwnd(hwnd)
        except Exception as error:
            self._logger.debug(
                "Не удалось определить процесс по координатам (%s, %s): %s",
                x,
                y,
                error,
            )
            return None

    def get_process_name_from_hwnd(self, hwnd: int | None) -> str | None:
        if not PYWIN32_AVAILABLE or not hwnd:
            return None
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            process_handle = win32api.OpenProcess(
                win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ,
                False,
                pid,
            )
            try:
                process_path = win32process.GetModuleFileNameEx(process_handle, 0)
            finally:
                win32api.CloseHandle(process_handle)
            return os.path.basename(process_path).lower()
        except Exception as error:
            self._logger.debug("Не удалось определить имя процесса для hwnd=%s: %s", hwnd, error)
            return None
