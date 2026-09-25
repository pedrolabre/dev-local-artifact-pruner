from pathlib import Path

ASSETS_DIR = Path(__file__).parent / "assets"
UP_ARROW_PATH = (ASSETS_DIR / "up_arrow.svg").as_posix()
DOWN_ARROW_PATH = (ASSETS_DIR / "down_arrow.svg").as_posix()
LEFT_ARROW_PATH = (ASSETS_DIR / "left_arrow.svg").as_posix()
RIGHT_ARROW_PATH = (ASSETS_DIR / "right_arrow.svg").as_posix()

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

SCROLLBAR_QSS = f"""
QScrollBar:vertical {{
    background-color: {COLOR_BG_TERMINAL};
    width: 14px;
    margin: 14px 0 14px 0;
}}

QScrollBar::handle:vertical {{
    background-color: {COLOR_BORDER_LIGHT};
    min-height: 20px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: #484f58;
}}

QScrollBar::sub-line:vertical {{
    background-color: {COLOR_BG_PANEL};
    height: 14px;
    subcontrol-position: top;
    subcontrol-origin: margin;
    border: 1px solid {COLOR_BORDER};
    border-top-left-radius: 3px;
    border-top-right-radius: 3px;
}}

QScrollBar::sub-line:vertical:hover {{
    background-color: {COLOR_BG_SURFACE};
}}

QScrollBar::add-line:vertical {{
    background-color: {COLOR_BG_PANEL};
    height: 14px;
    subcontrol-position: bottom;
    subcontrol-origin: margin;
    border: 1px solid {COLOR_BORDER};
    border-bottom-left-radius: 3px;
    border-bottom-right-radius: 3px;
}}

QScrollBar::add-line:vertical:hover {{
    background-color: {COLOR_BG_SURFACE};
}}

QScrollBar::up-arrow:vertical {{
    image: url({UP_ARROW_PATH});
    width: 8px;
    height: 8px;
}}

QScrollBar::down-arrow:vertical {{
    image: url({DOWN_ARROW_PATH});
    width: 8px;
    height: 8px;
}}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}

QScrollBar:horizontal {{
    background-color: {COLOR_BG_TERMINAL};
    height: 14px;
    margin: 0 14px 0 14px;
}}

QScrollBar::handle:horizontal {{
    background-color: {COLOR_BORDER_LIGHT};
    min-width: 20px;
    border-radius: 4px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: #484f58;
}}

QScrollBar::sub-line:horizontal {{
    background-color: {COLOR_BG_PANEL};
    width: 14px;
    subcontrol-position: left;
    subcontrol-origin: margin;
    border: 1px solid {COLOR_BORDER};
    border-top-left-radius: 3px;
    border-bottom-left-radius: 3px;
}}

QScrollBar::sub-line:horizontal:hover {{
    background-color: {COLOR_BG_SURFACE};
}}

QScrollBar::add-line:horizontal {{
    background-color: {COLOR_BG_PANEL};
    width: 14px;
    subcontrol-position: right;
    subcontrol-origin: margin;
    border: 1px solid {COLOR_BORDER};
    border-top-right-radius: 3px;
    border-bottom-right-radius: 3px;
}}

QScrollBar::add-line:horizontal:hover {{
    background-color: {COLOR_BG_SURFACE};
}}

QScrollBar::left-arrow:horizontal {{
    image: url({LEFT_ARROW_PATH});
    width: 8px;
    height: 8px;
}}

QScrollBar::right-arrow:horizontal {{
    image: url({RIGHT_ARROW_PATH});
    width: 8px;
    height: 8px;
}}

QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: none;
}}
"""

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
{SCROLLBAR_QSS}
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

{SCROLLBAR_QSS}
"""


def get_global_stylesheet() -> str:
    return GLOBAL_QSS


def get_terminal_stylesheet() -> str:
    return TERMINAL_QSS
