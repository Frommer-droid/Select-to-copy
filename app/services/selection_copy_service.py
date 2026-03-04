from __future__ import annotations

import logging
import os
import time

import pyperclip

from app.config.app_config import CLIPBOARD_SETTLE_DELAY_SEC, COPY_SETTLE_DELAY_SEC
from app.services.windows_scancode_input_service import send_left_ctrl_c

try:
    from pywinauto import Desktop, uia_defines

    PYWINAUTO_AVAILABLE = True
except ImportError:
    PYWINAUTO_AVAILABLE = False
    Desktop = None
    uia_defines = None

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


class SelectionCopyService:
    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

        if not PYWINAUTO_AVAILABLE:
            self._logger.warning(
                "pywinauto не установлена, UIA-метод получения выделенного текста недоступен."
            )
        if not PYWIN32_AVAILABLE:
            self._logger.warning(
                "pywin32 не установлена, fallback-копирование и проверка модификаторов недоступны."
            )

    @staticmethod
    def is_left_ctrl_pressed() -> bool:
        if not PYWIN32_AVAILABLE:
            return False
        try:
            return (win32api.GetAsyncKeyState(win32con.VK_LCONTROL) & 0x8000) != 0
        except Exception:
            return False

    def copy_current_selection(self) -> bool:
        time.sleep(COPY_SETTLE_DELAY_SEC)
        hwnd = self._get_foreground_window()
        if not hwnd:
            self._logger.debug("Не удалось получить foreground window.")
            return False

        selected_text = self._get_selected_text_uia(hwnd)
        if selected_text:
            pyperclip.copy(selected_text)
            preview = selected_text[:50].replace("\n", " ")
            self._logger.info("Скопировано через UIA: %s...", preview)
            return True

        return self._copy_with_ctrl_c_fallback(hwnd)

    def _get_foreground_window(self) -> int | None:
        if not PYWIN32_AVAILABLE:
            return None
        try:
            return win32gui.GetForegroundWindow()
        except Exception as error:
            self._logger.exception("Ошибка получения foreground window: %s", error)
            return None

    def _copy_with_ctrl_c_fallback(self, hwnd: int) -> bool:
        if not PYWIN32_AVAILABLE:
            return False

        try:
            win32gui.SetForegroundWindow(hwnd)
            time.sleep(0.05)
        except Exception as error:
            self._logger.debug("Не удалось установить фокус на окно: %s", error)

        original_clipboard = ""
        try:
            original_clipboard = pyperclip.paste()
        except Exception:
            pass

        try:
            pyperclip.copy("")
            if not send_left_ctrl_c():
                self._logger.warning("SendInput не смог полностью отправить Ctrl+C.")
            time.sleep(CLIPBOARD_SETTLE_DELAY_SEC)
            new_clipboard = pyperclip.paste()
            if new_clipboard:
                self._logger.info("Скопировано через fallback Ctrl+C.")
                return True
            pyperclip.copy(original_clipboard)
            return False
        except Exception as error:
            self._logger.exception("Ошибка fallback-копирования: %s", error)
            try:
                pyperclip.copy(original_clipboard)
            except Exception:
                pass
            return False

    def _get_selected_text_uia(self, hwnd: int) -> str:
        if not PYWINAUTO_AVAILABLE or not hwnd:
            return ""

        try:
            app_element = Desktop(backend="uia").window(handle=hwnd)
            element = None
            for _ in range(5):
                try:
                    element = app_element.element_info.element.GetFocusedElement()
                    if element:
                        break
                except Exception:
                    time.sleep(0.03)

            if not element:
                return ""

            if "TextPattern" in element.GetSupportedPatterns():
                text_pattern = element.QueryInterface(uia_defines.IUIA_TextPattern)
                selection = text_pattern.GetSelection()
                if selection:
                    return " ".join(s.GetText(-1) for s in selection)
        except Exception as error:
            self._logger.debug("Ошибка UIA: %s", error)

        return ""

    def get_process_name_from_hwnd(self, hwnd: int) -> str | None:
        if not PYWIN32_AVAILABLE or not hwnd:
            return None
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            handle = win32api.OpenProcess(
                win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ,
                False,
                pid,
            )
            try:
                process_path = win32process.GetModuleFileNameEx(handle, 0)
            finally:
                win32api.CloseHandle(handle)
            return os.path.basename(process_path).lower()
        except Exception:
            return None
