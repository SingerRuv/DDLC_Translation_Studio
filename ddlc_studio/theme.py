"""Qt stylesheets inspired by Visual Studio Code."""

DARK = """
QWidget {
    background: #1e1e1e;
    color: #cccccc;
    font-family: "Segoe UI";
    font-size: 9.5pt;
}
QFrame#card {
    background: #252526;
    border: 1px solid #3c3c3c;
    border-radius: 10px;
}
QFrame#activityBar {
    background: #333333;
    border-right: 1px solid #252526;
}
QFrame#sidebar {
    background: #252526;
    border-right: 1px solid #1e1e1e;
}
QFrame#editorToolbar {
    background: #2d2d30;
    border-bottom: 1px solid #252526;
}
QLabel#title {
    font-size: 22pt;
    font-weight: 600;
    color: #ffffff;
}
QLabel#subtitle {
    font-size: 10.5pt;
    color: #9d9d9d;
}
QLabel#section {
    font-size: 10pt;
    font-weight: 700;
    color: #cccccc;
    letter-spacing: 0.4px;
}
QLabel#muted {
    color: #858585;
}
QLabel#status {
    color: #cccccc;
    padding: 0 8px;
}
QPushButton {
    background: #0e639c;
    border: 1px solid #0e639c;
    border-radius: 3px;
    color: #ffffff;
    padding: 5px 12px;
}
QPushButton:hover {
    background: #1177bb;
}
QPushButton:pressed {
    background: #0d5a8f;
}
QPushButton#primary {
    background: #0e639c;
    border: 1px solid #0e639c;
    color: #ffffff;
    font-weight: 600;
}
QPushButton#secondary {
    background: #3a3d41;
    border: 1px solid #3a3d41;
    color: #cccccc;
}
QPushButton#secondary:hover {
    background: #45494e;
}
QToolButton {
    background: transparent;
    border: none;
    border-radius: 4px;
    padding: 6px;
}
QToolButton:hover {
    background: #3a3d41;
}
QToolButton:checked {
    background: #37373d;
}
QLineEdit, QComboBox {
    background: #3c3c3c;
    border: 1px solid #3c3c3c;
    border-radius: 2px;
    color: #cccccc;
    padding: 4px 6px;
    selection-background-color: #264f78;
}
QLineEdit:focus, QComboBox:focus {
    border: 1px solid #007acc;
}
QListWidget, QTreeView {
    background: #252526;
    border: none;
    outline: none;
    padding: 2px;
}
QListWidget::item {
    padding: 6px;
    border-radius: 3px;
}
QListWidget::item:selected, QTreeView::item:selected {
    background: #094771;
    color: #ffffff;
}
QTreeView::item {
    padding: 3px;
}
QDialog {
    background: #1e1e1e;
}
QTabWidget::pane {
    border: none;
    background: #1e1e1e;
}
QTabBar::tab {
    background: #2d2d30;
    color: #969696;
    border: none;
    border-right: 1px solid #252526;
    padding: 7px 14px;
}
QTabBar::tab:selected {
    background: #1e1e1e;
    color: #ffffff;
    border-top: 1px solid #007acc;
}
QTabBar::tab:hover {
    background: #37373d;
}
QPlainTextEdit#codeEditor {
    background: #1e1e1e;
    color: #d4d4d4;
    border: none;
    selection-background-color: #264f78;
    selection-color: #ffffff;
}
QTableView {
    background: #1e1e1e;
    alternate-background-color: #232323;
    gridline-color: #2d2d30;
    border: none;
    selection-background-color: #094771;
    selection-color: #ffffff;
    font-family: "Consolas";
    font-size: 9pt;
}
QHeaderView::section {
    background: #252526;
    color: #cccccc;
    border: none;
    border-right: 1px solid #2d2d30;
    border-bottom: 1px solid #2d2d30;
    padding: 5px 7px;
    font-weight: 600;
}
QStatusBar {
    background: #007acc;
    color: #ffffff;
    border: none;
}
QStatusBar QLabel {
    color: #ffffff;
    padding: 0 8px;
}
QScrollBar:vertical {
    background: #1e1e1e;
    width: 12px;
}
QScrollBar::handle:vertical {
    background: #424242;
    min-height: 24px;
}
QScrollBar:horizontal {
    background: #1e1e1e;
    height: 12px;
}
QScrollBar::handle:horizontal {
    background: #424242;
    min-width: 24px;
}
QScrollBar::add-line, QScrollBar::sub-line {
    width: 0;
    height: 0;
}
QSplitter::handle {
    background: #2d2d30;
}
QSplitter::handle:horizontal {
    width: 1px;
}
QSplitter::handle:vertical {
    height: 1px;
}
QToolTip {
    background: #252526;
    color: #cccccc;
    border: 1px solid #454545;
}
"""

LIGHT = """
QWidget {
    background: #ffffff;
    color: #3b3b3b;
    font-family: "Segoe UI";
    font-size: 9.5pt;
}
QFrame#card {
    background: #f3f3f3;
    border: 1px solid #e5e5e5;
    border-radius: 10px;
}
QFrame#activityBar {
    background: #2c2c2c;
    border-right: 1px solid #252526;
}
QFrame#sidebar {
    background: #f3f3f3;
    border-right: 1px solid #e5e5e5;
}
QFrame#editorToolbar {
    background: #f3f3f3;
    border-bottom: 1px solid #e5e5e5;
}
QLabel#title {
    font-size: 22pt;
    font-weight: 600;
    color: #1f1f1f;
}
QLabel#subtitle {
    font-size: 10.5pt;
    color: #616161;
}
QLabel#section {
    font-size: 10pt;
    font-weight: 700;
    color: #3b3b3b;
    letter-spacing: 0.4px;
}
QLabel#muted {
    color: #767676;
}
QPushButton {
    background: #007acc;
    border: 1px solid #007acc;
    border-radius: 3px;
    color: #ffffff;
    padding: 5px 12px;
}
QPushButton:hover {
    background: #0062a3;
}
QPushButton#primary {
    background: #007acc;
    border: 1px solid #007acc;
    color: #ffffff;
    font-weight: 600;
}
QPushButton#secondary {
    background: #e7e7e7;
    border: 1px solid #d1d1d1;
    color: #3b3b3b;
}
QToolButton {
    background: transparent;
    border: none;
    border-radius: 4px;
    padding: 6px;
}
QToolButton:hover {
    background: #e0e0e0;
}
QLineEdit, QComboBox {
    background: #ffffff;
    border: 1px solid #cecece;
    border-radius: 2px;
    color: #3b3b3b;
    padding: 4px 6px;
}
QLineEdit:focus, QComboBox:focus {
    border: 1px solid #007acc;
}
QListWidget, QTreeView {
    background: #f3f3f3;
    border: none;
    outline: none;
    padding: 2px;
}
QListWidget::item {
    padding: 6px;
    border-radius: 3px;
}
QListWidget::item:selected, QTreeView::item:selected {
    background: #cce4f7;
    color: #1f1f1f;
}
QTreeView::item {
    padding: 3px;
}
QDialog {
    background: #ffffff;
}
QTabWidget::pane {
    border: none;
    background: #ffffff;
}
QTabBar::tab {
    background: #ececec;
    color: #6f6f6f;
    border: none;
    border-right: 1px solid #e0e0e0;
    padding: 7px 14px;
}
QTabBar::tab:selected {
    background: #ffffff;
    color: #1f1f1f;
    border-top: 1px solid #007acc;
}
QTabBar::tab:hover {
    background: #e0e0e0;
}
QPlainTextEdit#codeEditor {
    background: #ffffff;
    color: #1f1f1f;
    border: none;
    selection-background-color: #add6ff;
}
QTableView {
    background: #ffffff;
    alternate-background-color: #f7f7f7;
    gridline-color: #ececec;
    border: none;
    selection-background-color: #cce4f7;
    selection-color: #1f1f1f;
    font-family: "Consolas";
    font-size: 9pt;
}
QHeaderView::section {
    background: #f3f3f3;
    color: #3b3b3b;
    border: none;
    border-right: 1px solid #e0e0e0;
    border-bottom: 1px solid #e0e0e0;
    padding: 5px 7px;
    font-weight: 600;
}
QStatusBar {
    background: #007acc;
    color: #ffffff;
    border: none;
}
QStatusBar QLabel {
    color: #ffffff;
}
QScrollBar:vertical {
    background: #ffffff;
    width: 12px;
}
QScrollBar::handle:vertical {
    background: #c1c1c1;
    min-height: 24px;
}
QScrollBar:horizontal {
    background: #ffffff;
    height: 12px;
}
QScrollBar::handle:horizontal {
    background: #c1c1c1;
    min-width: 24px;
}
QScrollBar::add-line, QScrollBar::sub-line {
    width: 0;
    height: 0;
}
QSplitter::handle {
    background: #e5e5e5;
}
QToolTip {
    background: #f3f3f3;
    color: #3b3b3b;
    border: 1px solid #cecece;
}
"""


def stylesheet(name):
    return LIGHT if name == "light" else DARK


def apply_theme(app, name):
    app.setStyleSheet(stylesheet(name))

