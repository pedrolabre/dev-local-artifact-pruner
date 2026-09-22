COLOR_BG_APP = "#121212"
COLOR_BG_PANEL = "#1e1e1e"
COLOR_BG_SURFACE = "#252525"
COLOR_BG_TERMINAL = "#0d1117"
COLOR_BORDER = "#2d2d2d"
COLOR_BORDER_LIGHT = "#3a3a3a"
COLOR_BORDER_FOCUS = "#58a6ff"

COLOR_TEXT_PRIMARY = "#e6edf3"
COLOR_TEXT_SECONDARY = "#8b949e"
COLOR_TEXT_MUTED = "#6e7681"

COLOR_ACCENT_BLUE = "#58a6ff"
COLOR_ACCENT_GREEN = "#3fb950"

COLOR_STATUS_SUCCESS = "#3fb950"
COLOR_STATUS_WARNING = "#d29922"
COLOR_STATUS_ERROR = "#f85149"

COLOR_BTN_PRIMARY_BG = "#238636"
COLOR_BTN_PRIMARY_HOVER = "#2ea043"
COLOR_BTN_PRIMARY_PRESSED = "#1f752e"

COLOR_BTN_DEFAULT_BG = "#21262d"
COLOR_BTN_DEFAULT_HOVER = "#30363d"
COLOR_BTN_DEFAULT_PRESSED = "#282e33"

COLOR_BTN_DANGER_BG = "#da3633"
COLOR_BTN_DANGER_HOVER = "#b62324"
COLOR_BTN_DANGER_PRESSED = "#8e1a1b"

COLOR_BTN_DISABLED_BG = "#161b22"
COLOR_BTN_DISABLED_TEXT = "#484f58"

TERMINAL_QSS = f"""
QPlainTextEdit {{
    background-color: {COLOR_BG_TERMINAL};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    padding: 8px;
    font-family: Consolas, 'Courier New', monospace;
    font-size: 10pt;
    selection-background-color: #1f6feb;
    selection-color: #ffffff;
}}
"""

GLOBAL_QSS = f"""
QWidget {{
    background-color: {COLOR_BG_APP};
    color: {COLOR_TEXT_PRIMARY};
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
    font-size: 13px;
}}

QMainWindow, QDialog {{
    background-color: {COLOR_BG_APP};
}}

QFrame {{
    border: none;
}}

QPlainTextEdit, QTextEdit {{
    background-color: {COLOR_BG_TERMINAL};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    padding: 8px;
    font-family: Consolas, 'Courier New', monospace;
    font-size: 10pt;
    selection-background-color: #1f6feb;
    selection-color: #ffffff;
}}

QLineEdit {{
    background-color: {COLOR_BG_PANEL};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 13px;
}}

QLineEdit:focus {{
    border: 1px solid {COLOR_BORDER_FOCUS};
}}

QPushButton {{
    background-color: {COLOR_BTN_DEFAULT_BG};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    padding: 6px 14px;
    font-size: 13px;
    font-weight: 500;
}}

QPushButton:hover {{
    background-color: {COLOR_BTN_DEFAULT_HOVER};
    border-color: {COLOR_BORDER_LIGHT};
}}

QPushButton:pressed {{
    background-color: {COLOR_BTN_DEFAULT_PRESSED};
}}

QPushButton:disabled {{
    background-color: {COLOR_BTN_DISABLED_BG};
    color: {COLOR_BTN_DISABLED_TEXT};
    border-color: {COLOR_BORDER};
}}

QListWidget {{
    background-color: {COLOR_BG_PANEL};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    padding: 4px;
}}

QListWidget::item {{
    padding: 6px 8px;
    border-radius: 4px;
}}

QListWidget::item:hover {{
    background-color: {COLOR_BG_SURFACE};
}}

QListWidget::item:selected {{
    background-color: #1f6feb;
    color: #ffffff;
}}

QScrollBar:vertical {{
    background-color: {COLOR_BG_TERMINAL};
    width: 10px;
    margin: 0px;
}}

QScrollBar::handle:vertical {{
    background-color: {COLOR_BORDER_LIGHT};
    min-height: 20px;
    border-radius: 5px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: #484f58;
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    background-color: {COLOR_BG_TERMINAL};
    height: 10px;
    margin: 0px;
}}

QScrollBar::handle:horizontal {{
    background-color: {COLOR_BORDER_LIGHT};
    min-width: 20px;
    border-radius: 5px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: #484f58;
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}
"""


def get_global_stylesheet() -> str:
    return GLOBAL_QSS


def get_terminal_stylesheet() -> str:
    return TERMINAL_QSS
