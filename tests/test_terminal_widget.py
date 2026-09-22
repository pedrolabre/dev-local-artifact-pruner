import os
from typing import Generator
import pytest
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import QApplication, QPlainTextEdit

from dev_local_artifact_pruner.ui import (
    COLOR_ACCENT_BLUE,
    COLOR_ACCENT_GREEN,
    COLOR_BG_APP,
    COLOR_BG_PANEL,
    COLOR_BG_SURFACE,
    COLOR_BG_TERMINAL,
    COLOR_BORDER,
    COLOR_STATUS_ERROR,
    COLOR_STATUS_SUCCESS,
    COLOR_STATUS_WARNING,
    GLOBAL_QSS,
    TERMINAL_QSS,
    TerminalWidget,
    get_global_stylesheet,
    get_terminal_stylesheet,
)

os.environ["QT_QPA_PLATFORM"] = "offscreen"


@pytest.fixture(scope="session")
def qapp() -> Generator[QApplication, None, None]:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def terminal(qapp: QApplication) -> TerminalWidget:
    widget = TerminalWidget()
    widget.resize(400, 200)
    widget.show()
    return widget


def test_terminal_widget_initial_state(terminal: TerminalWidget) -> None:
    assert isinstance(terminal, QPlainTextEdit)
    assert terminal.isReadOnly() is True
    assert terminal.toPlainText() == ""
    assert terminal.lineWrapMode() == QPlainTextEdit.LineWrapMode.WidgetWidth
    font = terminal.font()
    assert font.styleHint() == QFont.StyleHint.Monospace
    assert font.pointSize() == 10
    families = font.families()
    assert "Consolas" in families or "Courier New" in families or "monospace" in families


def test_terminal_widget_append_line(terminal: TerminalWidget) -> None:
    terminal.append_line("Primeira linha de teste")
    assert terminal.toPlainText() == "Primeira linha de teste"

    terminal.append_line("Segunda linha de teste")
    assert terminal.toPlainText() == "Primeira linha de teste\nSegunda linha de teste"

    terminal.append_line("")
    assert terminal.toPlainText() == "Primeira linha de teste\nSegunda linha de teste\n"


def test_terminal_widget_log(terminal: TerminalWidget) -> None:
    terminal.log("Mensagem de log regular")
    terminal.log("Outra mensagem")
    assert terminal.toPlainText() == "Mensagem de log regular\nOutra mensagem"


def test_terminal_widget_log_success(terminal: TerminalWidget) -> None:
    terminal.log_success("Operacao realizada com sucesso")
    assert "Operacao realizada com sucesso" in terminal.toPlainText()
    assert COLOR_STATUS_SUCCESS.lower() in terminal.document().toHtml().lower()


def test_terminal_widget_log_warning(terminal: TerminalWidget) -> None:
    terminal.log_warning("Atencao: verificacao recomendada")
    assert "Atencao: verificacao recomendada" in terminal.toPlainText()
    assert COLOR_STATUS_WARNING.lower() in terminal.document().toHtml().lower()


def test_terminal_widget_log_error(terminal: TerminalWidget) -> None:
    terminal.log_error("Falha critica na execucao")
    assert "Falha critica na execucao" in terminal.toPlainText()
    assert COLOR_STATUS_ERROR.lower() in terminal.document().toHtml().lower()


def test_terminal_widget_html_escaping(terminal: TerminalWidget) -> None:
    dangerous_input = "<script>alert('xss')</script> & 'single' & \"double\" <tag>"
    terminal.log_success(dangerous_input)
    assert dangerous_input in terminal.toPlainText()
    html_content = terminal.document().toHtml()
    assert "<script>" not in html_content
    assert "&lt;script&gt;" in html_content


def test_terminal_widget_multiline_formatted_logs(terminal: TerminalWidget) -> None:
    multiline_text = "Linha 1\nLinha 2\nLinha 3"
    terminal.log_success(multiline_text)
    plain = terminal.toPlainText()
    assert "Linha 1" in plain
    assert "Linha 2" in plain
    assert "Linha 3" in plain


def test_terminal_widget_clear_terminal(terminal: TerminalWidget) -> None:
    terminal.log("Linha normal")
    terminal.log_success("Sucesso")
    terminal.log_warning("Aviso")
    terminal.log_error("Erro")
    assert terminal.toPlainText() != ""

    terminal.clear_terminal()
    assert terminal.toPlainText() == ""

    terminal.log("Linha apos limpeza")
    assert terminal.toPlainText() == "Linha apos limpeza"


def test_terminal_widget_auto_scroll(terminal: TerminalWidget) -> None:
    for i in range(100):
        terminal.append_line(f"Linha de log com indice {i}")

    cursor = terminal.textCursor()
    assert cursor.position() == len(terminal.toPlainText())

    scroll_bar = terminal.verticalScrollBar()
    assert scroll_bar is not None
    assert scroll_bar.maximum() > 0
    assert scroll_bar.value() == scroll_bar.maximum()


def test_styles_palette_constants() -> None:
    assert COLOR_BG_APP == "#121212"
    assert COLOR_BG_PANEL == "#1e1e1e"
    assert COLOR_BG_SURFACE == "#252525"
    assert COLOR_BG_TERMINAL == "#0d1117"
    assert COLOR_BORDER == "#2d2d2d"
    assert COLOR_ACCENT_BLUE == "#58a6ff"
    assert COLOR_ACCENT_GREEN == "#3fb950"
    assert COLOR_STATUS_SUCCESS == "#3fb950"
    assert COLOR_STATUS_WARNING == "#d29922"
    assert COLOR_STATUS_ERROR == "#f85149"


def test_styles_stylesheets_content() -> None:
    assert "QPlainTextEdit" in TERMINAL_QSS
    assert "#0d1117" in TERMINAL_QSS

    assert "QWidget" in GLOBAL_QSS
    assert "QMainWindow" in GLOBAL_QSS
    assert "QPushButton" in GLOBAL_QSS
    assert "QLineEdit" in GLOBAL_QSS
    assert "QListWidget" in GLOBAL_QSS
    assert "QScrollBar:vertical" in GLOBAL_QSS

    assert get_global_stylesheet() == GLOBAL_QSS
    assert get_terminal_stylesheet() == TERMINAL_QSS


def test_ui_module_exports() -> None:
    import dev_local_artifact_pruner.ui as ui_module

    assert hasattr(ui_module, "TerminalWidget")
    assert hasattr(ui_module, "GLOBAL_QSS")
    assert hasattr(ui_module, "TERMINAL_QSS")
    assert hasattr(ui_module, "get_global_stylesheet")
    assert hasattr(ui_module, "get_terminal_stylesheet")
    for name in ui_module.__all__:
        assert hasattr(ui_module, name)
