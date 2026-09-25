import html
from typing import Optional

from PySide6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QPlainTextEdit, QWidget

from dev_local_artifact_pruner.ui.styles import (
    COLOR_STATUS_ERROR,
    COLOR_STATUS_SUCCESS,
    COLOR_STATUS_WARNING,
    COLOR_TEXT_PRIMARY,
    TERMINAL_QSS,
)


class TerminalWidget(QPlainTextEdit):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)

        font = QFont("Consolas", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setFamilies(["Consolas", "Courier New", "monospace"])
        self.setFont(font)

        self.setStyleSheet(TERMINAL_QSS)
        v_bar = self.verticalScrollBar()
        if v_bar is not None:
            v_bar.setSingleStep(15)

    def _scroll_to_bottom(self) -> None:
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()
        scroll_bar = self.verticalScrollBar()
        if scroll_bar is not None:
            scroll_bar.setValue(scroll_bar.maximum())

    def _reset_char_format(self) -> None:
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(COLOR_TEXT_PRIMARY))
        cursor.setCharFormat(fmt)
        self.setCurrentCharFormat(fmt)
        self.setTextCursor(cursor)

    def append_line(self, text: str = "") -> None:
        self._reset_char_format()
        self.appendPlainText(text)
        self._scroll_to_bottom()

    def log(self, text: str = "") -> None:
        self.append_line(text)

    def log_success(self, text: str) -> None:
        escaped = html.escape(text).replace("\n", "<br/>")
        self.appendHtml(
            f"<span style='color: {COLOR_STATUS_SUCCESS}; font-family: Consolas, monospace;'>{escaped}</span>"
        )
        self._reset_char_format()
        self._scroll_to_bottom()

    def log_warning(self, text: str) -> None:
        escaped = html.escape(text).replace("\n", "<br/>")
        self.appendHtml(
            f"<span style='color: {COLOR_STATUS_WARNING}; font-family: Consolas, monospace;'>{escaped}</span>"
        )
        self._reset_char_format()
        self._scroll_to_bottom()

    def log_error(self, text: str) -> None:
        escaped = html.escape(text).replace("\n", "<br/>")
        self.appendHtml(
            f"<span style='color: {COLOR_STATUS_ERROR}; font-family: Consolas, monospace;'>{escaped}</span>"
        )
        self._reset_char_format()
        self._scroll_to_bottom()

    def clear_terminal(self) -> None:
        self.clear()
        self._reset_char_format()
