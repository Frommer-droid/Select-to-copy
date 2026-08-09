TRAY_MENU_STYLESHEET = """
QMenu {
    background-color: #17212B;
    color: #EAF2F8;
    border: 1px solid #2A3A4A;
}
QMenu::item {
    padding: 7px 24px 7px 16px;
}
QMenu::item:selected {
    background-color: #3AE2CE;
    color: #17212B;
}
QMenu::separator {
    height: 1px;
    background: #2A3A4A;
    margin: 4px 10px;
}
"""

EXCLUSIONS_DIALOG_STYLESHEET = """
QDialog {
    background-color: #17212B;
    color: #FFFFFF;
}
QLabel {
    color: #3AE2CE;
}
QCheckBox {
    color: #FFFFFF;
    spacing: 8px;
}
QListWidget, QLineEdit {
    background-color: #0E1621;
    color: #FFFFFF;
    border: 1px solid #3AE2CE;
    border-radius: 4px;
    padding: 4px;
}
QListWidget::item:selected {
    background-color: #3AE2CE;
    color: #17212B;
}
QStatusBar {
    background-color: #0E1621;
    color: #EAF2F8;
    border-top: 1px solid #2A3A4A;
    min-height: 20px;
    padding-left: 8px;
}
QPushButton {
    background-color: #4B82E5;
    color: #FFFFFF;
    border: 1px solid #4B82E5;
    border-radius: 4px;
    padding: 5px 10px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #5E90E9;
    border-color: #5E90E9;
}
QPushButton:pressed {
    background-color: #3F72CF;
    border-color: #3F72CF;
}
QPushButton#warningButton {
    background-color: #BF8255;
    border-color: #BF8255;
    color: #FFFFFF;
}
QPushButton#warningButton:hover {
    background-color: #CA9268;
    border-color: #CA9268;
}
QPushButton#primaryButton {
    background-color: #6AF1E2;
    color: #000000;
    border-color: #6AF1E2;
}
QPushButton#primaryButton:hover {
    background-color: #80F4E8;
    border-color: #80F4E8;
}
QPushButton#primaryButton:pressed {
    background-color: #56DACB;
    border-color: #56DACB;
}
"""

TOOLTIP_STYLESHEET = """
QToolTip {
    background-color: #3AE2CE;
    color: #17212B;
    border: 1px solid #17212B;
    padding: 2px 4px;
    font-size: 8px;
    font-weight: 500;
    border-radius: 2px;
}
"""
