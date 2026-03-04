from __future__ import annotations

from PySide6.QtCore import QRect, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QGuiApplication, QKeyEvent, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import QWidget


class ProcessCaptureOverlay(QWidget):
    capture_triggered = Signal()
    capture_canceled = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Window
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)

    def show_overlay(self) -> None:
        self.setGeometry(self._resolve_virtual_geometry())
        self.show()
        self.raise_()
        self.activateWindow()

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.RightButton:
            self.hide()
            self.capture_canceled.emit()
            return

        if event.button() != Qt.MouseButton.LeftButton:
            return

        self.hide()
        QTimer.singleShot(60, self.capture_triggered.emit)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
            self.capture_canceled.emit()
            return
        super().keyPressEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802
        _ = event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), QColor(10, 18, 28, 135))

        panel_width = min(620, self.width() - 40)
        panel_height = 124
        panel_rect = QRect(0, 0, panel_width, panel_height)
        panel_rect.moveCenter(self.rect().center())

        painter.setBrush(QColor(23, 33, 43, 232))
        painter.setPen(QPen(QColor("#3AE2CE"), 2))
        painter.drawRoundedRect(panel_rect, 12, 12)

        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(
            panel_rect.adjusted(20, 16, -20, -16),
            Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
            "Кликните по нужному окну для добавления процесса в исключения.\nEsc или правая кнопка мыши - отмена.",
        )
        painter.end()

    @staticmethod
    def _resolve_virtual_geometry() -> QRect:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return QRect(0, 0, 1920, 1080)
        return screen.virtualGeometry()
