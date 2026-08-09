from __future__ import annotations

import threading

from PySide6.QtCore import QObject, QTimer, Signal, Slot
from PySide6.QtWidgets import QApplication

from app.config.app_config import AUTO_PAUSE_POLL_INTERVAL_MS, COPY_TOOLTIP_TEXT, LOG_FILE_NAME
from app.models.exclusion_settings import ExclusionSettings
from app.services.foreground_window_service import ForegroundWindowService
from app.services.logging_service import flush_and_close_logger, setup_session_logger
from app.services.mouse_selection_service import MouseSelectionService
from app.services.pause_state_service import PauseStateService
from app.services.process_exclusion_service import ProcessExclusionService
from app.services.selection_copy_service import SelectionCopyService
from app.services.settings_service import SettingsService
from app.ui.exclusions_dialog import ExclusionsDialog
from app.ui.tray_controller import TrayController


class ApplicationController(QObject):
    copy_feedback_requested = Signal(str)

    def __init__(self, project_root, icon_path, pause_icon_path, version: str) -> None:
        super().__init__()
        self._project_root = project_root
        self._version = version

        self._is_stopped = False

        self._logger = setup_session_logger(self._project_root / LOG_FILE_NAME)

        self._settings_service = SettingsService(project_root=self._project_root, logger=self._logger)
        initial_exclusions = self._settings_service.get_exclusion_settings()
        self._exclusion_service = ProcessExclusionService(
            enabled=initial_exclusions.enabled,
            process_names=initial_exclusions.process_names,
        )
        self._pause_state_service = PauseStateService()
        self._foreground_window_service = ForegroundWindowService(self._logger)

        self._selection_service = SelectionCopyService(self._logger)
        self._mouse_service = MouseSelectionService(
            selection_service=self._selection_service,
            should_process_drag=lambda: not self._pause_state_service.is_effectively_paused(),
            on_copy_requested=self._schedule_copy_worker,
            logger=self._logger,
        )
        self._tray_controller = TrayController(
            icon_path=icon_path,
            pause_icon_path=pause_icon_path,
            version=version,
            is_paused_provider=lambda: self._pause_state_service.is_effectively_paused(),
            is_manual_paused_provider=lambda: self._pause_state_service.manual_paused,
            auto_pause_process_provider=lambda: self._pause_state_service.auto_pause_process_name,
            logger=self._logger,
        )

        self._foreground_poll_timer = QTimer(self)
        self._foreground_poll_timer.setInterval(AUTO_PAUSE_POLL_INTERVAL_MS)
        self._foreground_poll_timer.timeout.connect(self._refresh_auto_pause_state)

        self._tray_controller.pause_requested.connect(self.toggle_manual_pause)
        self._tray_controller.exclusions_requested.connect(self.open_exclusions_dialog)
        self._tray_controller.exit_requested.connect(self.shutdown)
        self.copy_feedback_requested.connect(self._tray_controller.show_copy_tooltip)

        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self.shutdown)

    def start(self) -> None:
        self._tray_controller.show()
        self._mouse_service.start()
        self._refresh_auto_pause_state(force_log=False)
        self._foreground_poll_timer.start()
        self._update_tray_state()
        self._logger.info("Приложение запущено. Версия: %s", self._version)

    @Slot()
    def toggle_manual_pause(self) -> None:
        self._pause_state_service.toggle_manual_pause()
        self._update_tray_state()
        self._logger.info(
            "Ручная пауза: %s",
            "включена" if self._pause_state_service.manual_paused else "выключена",
        )

    @Slot()
    def open_exclusions_dialog(self) -> None:
        current_exclusions = ExclusionSettings(
            enabled=self._exclusion_service.enabled,
            process_names=self._exclusion_service.process_names,
        )

        dialog = ExclusionsDialog(
            exclusions=current_exclusions,
            window_settings=self._settings_service.get_window_settings(),
            captured_process_provider=self._foreground_window_service.get_capture_target_process_name,
            save_callback=self._save_exclusions,
            import_callback=self._settings_service.load_exclusions_from_file,
            export_callback=self._settings_service.save_exclusions_to_file,
        )

        dialog.exec()
        self._settings_service.update_window_settings(dialog.get_window_settings())

    def _save_exclusions(self, updated_exclusions: ExclusionSettings) -> None:
        self._exclusion_service.set_enabled(updated_exclusions.enabled)
        self._exclusion_service.set_process_names(updated_exclusions.process_names)
        self._settings_service.update_exclusion_settings(updated_exclusions)
        self._logger.info(
            "Исключения обновлены: enabled=%s, count=%s",
            updated_exclusions.enabled,
            len(updated_exclusions.process_names),
        )
        self._refresh_auto_pause_state(force_log=True)

    def _schedule_copy_worker(self, cursor_x: int, cursor_y: int) -> None:
        _ = (cursor_x, cursor_y)
        threading.Thread(target=self._copy_worker, daemon=True).start()

    def _copy_worker(self) -> None:
        try:
            copy_successful = self._selection_service.copy_current_selection()
            if copy_successful:
                self.copy_feedback_requested.emit(COPY_TOOLTIP_TEXT)
        except Exception as error:
            self._logger.exception("Ошибка в фоне копирования: %s", error)

    def _refresh_auto_pause_state(self, force_log: bool = False) -> None:
        active_process_name = self._foreground_window_service.get_foreground_process_name()
        should_auto_pause = self._exclusion_service.is_process_excluded(active_process_name)

        changed = self._pause_state_service.apply_auto_pause(
            process_name=active_process_name,
            should_pause=should_auto_pause,
        )

        if not changed and not force_log:
            return

        self._update_tray_state()
        if self._pause_state_service.auto_paused:
            self._logger.info(
                "Авто-пауза включена для процесса: %s",
                self._pause_state_service.auto_pause_process_name,
            )
        else:
            self._logger.info("Авто-пауза снята.")

    def _update_tray_state(self) -> None:
        self._tray_controller.update_state(
            is_paused=self._pause_state_service.is_effectively_paused(),
            is_manual_paused=self._pause_state_service.manual_paused,
            auto_pause_process_name=self._pause_state_service.auto_pause_process_name,
        )

    @Slot()
    def shutdown(self) -> None:
        if self._is_stopped:
            return
        self._is_stopped = True

        self._logger.info("Запрошено завершение приложения.")
        if self._foreground_poll_timer.isActive():
            self._foreground_poll_timer.stop()
        self._mouse_service.stop()
        self._tray_controller.hide()
        flush_and_close_logger(self._logger)

        app = QApplication.instance()
        if app is not None:
            app.quit()
