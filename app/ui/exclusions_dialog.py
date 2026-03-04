from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from app.config.theme import EXCLUSIONS_DIALOG_STYLESHEET
from app.models.exclusion_settings import ExclusionSettings
from app.ui.process_capture_overlay import ProcessCaptureOverlay


class ExclusionsDialog(QDialog):
    _CAPTURE_START_DELAY_MS = 3000

    def __init__(
        self,
        exclusions: ExclusionSettings,
        window_settings: dict[str, int | bool],
        captured_process_provider: Callable[[], str | None],
        save_callback: Callable[[ExclusionSettings], None],
        import_callback: Callable[[Path], ExclusionSettings],
        export_callback: Callable[[Path, ExclusionSettings], None],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Исключения автокопирования")
        self.setModal(True)
        self.setStyleSheet(EXCLUSIONS_DIALOG_STYLESHEET)

        self._captured_process_provider = captured_process_provider
        self._save_callback = save_callback
        self._import_callback = import_callback
        self._export_callback = export_callback
        self._capture_overlay: ProcessCaptureOverlay | None = None
        self._capture_start_timer = QTimer(self)
        self._capture_start_timer.setSingleShot(True)
        self._capture_start_timer.timeout.connect(self._show_capture_overlay)

        self._enabled_checkbox = QCheckBox("Включить исключения по процессам", self)
        self._enabled_checkbox.setChecked(exclusions.enabled)

        self._process_list = QListWidget(self)
        self._process_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._populate_process_list(exclusions.process_names)

        self._process_input = QLineEdit(self)
        self._process_input.setPlaceholderText("process.exe")
        self._process_input.returnPressed.connect(self._add_process_from_input)

        self._add_process_button = QPushButton("Добавить", self)
        self._add_process_button.clicked.connect(self._add_process_from_input)

        self._remove_selected_button = QPushButton("Удалить выбранное", self)
        self._remove_selected_button.setObjectName("warningButton")
        self._remove_selected_button.clicked.connect(self._remove_selected_processes)

        self._capture_process_button = QPushButton("Захватить процесс...", self)
        self._capture_process_button.setObjectName("primaryButton")
        self._capture_process_button.clicked.connect(self._start_overlay_capture)

        self._import_button = QPushButton("Импорт", self)
        self._import_button.clicked.connect(self._import_from_file)

        self._export_button = QPushButton("Экспорт", self)
        self._export_button.clicked.connect(self._export_to_file)

        self._save_button = QPushButton("Сохранить", self)
        self._save_button.setObjectName("primaryButton")
        self._save_button.clicked.connect(self._save_without_close)

        self._status_bar = QStatusBar(self)
        self._status_bar.setSizeGripEnabled(False)
        self._status_bar.setFixedHeight(22)
        self._status_bar.showMessage("Готово", 1200)

        for compact_button in (
            self._import_button,
            self._export_button,
            self._save_button,
        ):
            compact_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        controls_layout = QHBoxLayout()
        controls_layout.addWidget(self._process_input, stretch=1)
        controls_layout.addWidget(self._add_process_button)

        actions_layout = QHBoxLayout()
        actions_layout.addWidget(self._remove_selected_button, 1)
        actions_layout.addWidget(self._capture_process_button, 1)

        import_export_left_container = QWidget(self)
        import_export_left_layout = QHBoxLayout(import_export_left_container)
        import_export_left_layout.setContentsMargins(0, 0, 0, 0)
        import_export_left_layout.setSpacing(actions_layout.spacing())
        import_export_left_layout.addWidget(self._import_button, 1)
        import_export_left_layout.addWidget(self._export_button, 1)

        import_export_layout = QHBoxLayout()
        import_export_layout.addWidget(import_export_left_container, 1)
        import_export_layout.addWidget(self._save_button, 1)

        root_layout = QVBoxLayout(self)
        root_layout.addWidget(self._enabled_checkbox)
        root_layout.addWidget(
            QLabel("Процессы, в которых автокопирование должно выключаться:", self)
        )
        root_layout.addWidget(self._process_list, stretch=1)
        root_layout.addLayout(controls_layout)
        root_layout.addLayout(actions_layout)
        root_layout.addLayout(import_export_layout)
        root_layout.addWidget(self._status_bar)

        self._apply_window_settings(window_settings)

    def get_exclusion_settings(self) -> ExclusionSettings:
        return ExclusionSettings(
            enabled=self._enabled_checkbox.isChecked(),
            process_names=self._collect_process_names(),
        )

    def get_window_settings(self) -> dict[str, int | bool]:
        if self.isMaximized():
            geometry = self.normalGeometry()
        else:
            geometry = self.geometry()
        return {
            "x": geometry.x(),
            "y": geometry.y(),
            "width": geometry.width(),
            "height": geometry.height(),
            "maximized": self.isMaximized(),
        }

    def _add_process_from_input(self) -> None:
        process_name = self._process_input.text().strip()
        if self._add_process_name(process_name):
            self._process_input.clear()
            self._set_status(f"Добавлено: {process_name}")
            return

        if process_name:
            self._set_status(f"Уже в списке: {process_name}")

    def _remove_selected_processes(self) -> None:
        selected_items = self._process_list.selectedItems()
        if not selected_items:
            self._set_status("Ничего не выбрано")
            return

        for item in selected_items:
            row = self._process_list.row(item)
            self._process_list.takeItem(row)
        self._set_status(f"Удалено записей: {len(selected_items)}")

    def _start_overlay_capture(self) -> None:
        self._stop_capture_timer()
        self._cleanup_capture_overlay()

        user_choice = QMessageBox.information(
            self,
            "Захват процесса",
            (
                "Через 3 секунды появится полупрозрачный оверлей захвата.\n"
                "Сейчас активируйте нужное окно через панель задач.\n"
                "После появления оверлея кликните по нужному окну."
            ),
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Ok,
        )
        if user_choice != QMessageBox.StandardButton.Ok:
            return

        self._capture_start_timer.start(self._CAPTURE_START_DELAY_MS)
        self._set_status("Захват активируется через 3 секунды...", 3000)

    def _show_capture_overlay(self) -> None:
        self._cleanup_capture_overlay()
        self._capture_overlay = ProcessCaptureOverlay(self)
        self._capture_overlay.capture_triggered.connect(self._schedule_finish_overlay_capture)
        self._capture_overlay.capture_canceled.connect(self._cancel_overlay_capture)
        self._capture_overlay.show_overlay()

    def _schedule_finish_overlay_capture(self) -> None:
        QTimer.singleShot(120, self._finish_overlay_capture)

    def _finish_overlay_capture(self) -> None:
        process_name = self._captured_process_provider()
        self._cleanup_capture_overlay()
        self._restore_dialog_after_capture()

        if not process_name:
            self._set_status(
                "Не удалось определить процесс выбранного окна. Повторите захват.",
                4500,
            )
            return

        added = self._add_process_name(process_name)
        if added:
            self._set_status(f"Процесс добавлен: {process_name}")
            return

        self._set_status(f"Уже в списке: {process_name}")

    def _cancel_overlay_capture(self) -> None:
        self._cleanup_capture_overlay()
        self._restore_dialog_after_capture()
        self._set_status("Захват отменен")

    def _restore_dialog_after_capture(self) -> None:
        self.raise_()
        self.activateWindow()

    def _cleanup_capture_overlay(self) -> None:
        if self._capture_overlay is None:
            return
        try:
            self._capture_overlay.capture_triggered.disconnect(self._schedule_finish_overlay_capture)
        except Exception:
            pass
        try:
            self._capture_overlay.capture_canceled.disconnect(self._cancel_overlay_capture)
        except Exception:
            pass
        self._capture_overlay.deleteLater()
        self._capture_overlay = None

    def _stop_capture_timer(self) -> None:
        if self._capture_start_timer.isActive():
            self._capture_start_timer.stop()

    def _import_from_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Импорт исключений",
            str(Path.home()),
            "JSON files (*.json);;All files (*.*)",
        )
        if not file_path:
            return

        try:
            exclusions = self._import_callback(Path(file_path))
        except Exception as error:
            self._set_status(f"Ошибка импорта: {error}", 5000)
            return

        self._enabled_checkbox.setChecked(exclusions.enabled)
        self._populate_process_list(exclusions.process_names)
        self._set_status("Исключения импортированы")

    def _export_to_file(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Экспорт исключений",
            str(Path.home() / "select_to_copy_exclusions.json"),
            "JSON files (*.json);;All files (*.*)",
        )
        if not file_path:
            return

        exclusions = self.get_exclusion_settings()
        try:
            self._export_callback(Path(file_path), exclusions)
        except Exception as error:
            self._set_status(f"Ошибка экспорта: {error}", 5000)
            return

        self._set_status("Исключения экспортированы")

    def _save_without_close(self) -> None:
        exclusions = self.get_exclusion_settings()
        try:
            self._save_callback(exclusions)
        except Exception as error:
            self._set_status(f"Ошибка сохранения: {error}", 5000)
            return

        self._set_status("Сохранено")

    def _add_process_name(self, process_name: str) -> bool:
        process_name = process_name.strip()
        if not process_name:
            return False

        normalized_process_name = process_name.lower()
        existing_process_names = {name.lower() for name in self._collect_process_names()}
        if normalized_process_name in existing_process_names:
            return False

        self._process_list.addItem(QListWidgetItem(process_name))
        return True

    def _collect_process_names(self) -> list[str]:
        process_names: list[str] = []
        for index in range(self._process_list.count()):
            item = self._process_list.item(index)
            process_name = item.text().strip()
            if process_name:
                process_names.append(process_name)
        return process_names

    def _populate_process_list(self, process_names: list[str]) -> None:
        self._process_list.clear()
        for process_name in process_names:
            self._add_process_name(process_name)

    def _set_status(self, message: str, timeout_ms: int = 2200) -> None:
        self._status_bar.showMessage(message, timeout_ms)

    def _apply_window_settings(self, window_settings: dict[str, int | bool]) -> None:
        width = int(window_settings.get("width", 540))
        height = int(window_settings.get("height", 420))
        x = int(window_settings.get("x", 120))
        y = int(window_settings.get("y", 120))
        maximized = bool(window_settings.get("maximized", False))

        self.resize(width, height)
        self.move(x, y)

        if maximized:
            self.setWindowState(self.windowState() | Qt.WindowState.WindowMaximized)

    def closeEvent(self, event) -> None:  # noqa: N802
        self._stop_capture_timer()
        self._cleanup_capture_overlay()
        super().closeEvent(event)

    def reject(self) -> None:
        self._stop_capture_timer()
        self._cleanup_capture_overlay()
        super().reject()
