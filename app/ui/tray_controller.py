from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QObject, QRect, Qt, Signal, Slot
from PySide6.QtGui import QAction, QColor, QCursor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QStyle, QSystemTrayIcon, QToolTip

from app.config.app_config import APP_NAME, COPY_TOOLTIP_DURATION_MS
from app.config.theme import TRAY_MENU_STYLESHEET


class TrayController(QObject):
    pause_requested = Signal()
    exclusions_requested = Signal()
    exit_requested = Signal()

    def __init__(
        self,
        icon_path: Path,
        pause_icon_path: Path,
        version: str,
        is_paused_provider,
        is_manual_paused_provider,
        auto_pause_process_provider,
        logger: logging.Logger,
    ) -> None:
        super().__init__()
        self._is_paused_provider = is_paused_provider
        self._is_manual_paused_provider = is_manual_paused_provider
        self._auto_pause_process_provider = auto_pause_process_provider
        self._logger = logger

        self._active_icon = self._resolve_icon(icon_path)
        self._paused_icon = self._resolve_pause_icon(pause_icon_path, self._active_icon)

        self._tray_icon = QSystemTrayIcon(self)
        self._tray_icon.setIcon(self._active_icon)
        self._tray_icon.activated.connect(self._on_tray_activated)

        self._menu = QMenu()
        self._menu.setStyleSheet(TRAY_MENU_STYLESHEET)

        self._pause_action = QAction(self)
        self._pause_action.triggered.connect(self._on_pause_triggered)

        self._exclusions_action = QAction("Исключения...", self)
        self._exclusions_action.triggered.connect(self.exclusions_requested.emit)

        self._exit_action = QAction("Выход", self)
        self._exit_action.triggered.connect(self.exit_requested.emit)

        self._menu.addAction(self._pause_action)
        self._menu.addAction(self._exclusions_action)
        self._menu.addSeparator()
        self._menu.addAction(self._exit_action)

        self._tray_icon.setContextMenu(self._menu)
        self._version = version
        self.update_state(
            is_paused=self._is_paused_provider(),
            is_manual_paused=self._is_manual_paused_provider(),
            auto_pause_process_name=self._auto_pause_process_provider(),
        )

    def _resolve_icon(self, icon_path: Path) -> QIcon:
        if icon_path.exists():
            return QIcon(str(icon_path))
        fallback = QApplication.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
        self._logger.warning("Файл иконки не найден: %s. Используется fallback.", icon_path)
        return fallback

    def _resolve_pause_icon(self, pause_icon_path: Path, active_icon: QIcon) -> QIcon:
        if pause_icon_path.exists():
            return QIcon(str(pause_icon_path))
        self._logger.warning(
            "Пауза-иконка не найдена: %s. Используется fallback с красной точкой.",
            pause_icon_path,
        )
        return self._build_paused_icon(active_icon)

    def _build_paused_icon(self, base_icon: QIcon) -> QIcon:
        size = 64
        pixmap = base_icon.pixmap(size, size)
        if pixmap.isNull():
            pixmap = QPixmap(size, size)
            pixmap.fill(QColor("#17212B"))

        paused_pixmap = QPixmap(pixmap)
        painter = QPainter(paused_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        dot_size = max(14, size // 4)
        dot_x = (size - dot_size) // 2
        dot_y = 2
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#FF3B30"))
        painter.drawEllipse(dot_x, dot_y, dot_size, dot_size)
        painter.end()
        return QIcon(paused_pixmap)

    def show(self) -> None:
        self._tray_icon.show()

    def hide(self) -> None:
        self._tray_icon.hide()

    @Slot()
    def _on_pause_triggered(self) -> None:
        self.pause_requested.emit()

    @Slot(QSystemTrayIcon.ActivationReason)
    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.exclusions_requested.emit()

    def update_state(
        self,
        is_paused: bool,
        is_manual_paused: bool,
        auto_pause_process_name: str | None,
    ) -> None:
        self._pause_action.setText("Возобновить" if is_manual_paused else "Пауза")
        self._tray_icon.setIcon(self._paused_icon if is_paused else self._active_icon)
        state_text = self._build_state_text(
            is_paused=is_paused,
            is_manual_paused=is_manual_paused,
            auto_pause_process_name=auto_pause_process_name,
        )
        self._tray_icon.setToolTip(f"{APP_NAME} v{self._version} ({state_text})")

    @staticmethod
    def _build_state_text(
        is_paused: bool,
        is_manual_paused: bool,
        auto_pause_process_name: str | None,
    ) -> str:
        if not is_paused:
            return "Активно"
        if is_manual_paused and auto_pause_process_name:
            return f"Ручная + авто-пауза ({auto_pause_process_name})"
        if is_manual_paused:
            return "Ручная пауза"
        if auto_pause_process_name:
            return f"Авто-пауза ({auto_pause_process_name})"
        return "Пауза"

    @Slot(str)
    def show_copy_tooltip(self, text: str) -> None:
        QToolTip.showText(QCursor.pos(), text, None, QRect(), COPY_TOOLTIP_DURATION_MS)
