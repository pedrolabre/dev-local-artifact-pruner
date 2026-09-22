import os
from typing import Generator
import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QFrame, QWidget

from dev_local_artifact_pruner.ui import HomeScreen, ModeCard

os.environ["QT_QPA_PLATFORM"] = "offscreen"


@pytest.fixture(scope="session")
def qapp() -> Generator[QApplication, None, None]:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def mode_card(qapp: QApplication) -> ModeCard:
    card = ModeCard("📁", "Projeto", "Analisar uma pasta")
    card.show()
    return card


@pytest.fixture
def home_screen(qapp: QApplication) -> HomeScreen:
    screen = HomeScreen()
    screen.resize(800, 600)
    screen.show()
    return screen


def test_mode_card_initial_state(mode_card: ModeCard) -> None:
    assert isinstance(mode_card, QFrame)
    assert mode_card.objectName() == "modeCard"
    assert mode_card.cursor().shape() == Qt.CursorShape.PointingHandCursor
    assert mode_card.width() == 220
    assert mode_card.height() == 190

    assert mode_card.icon_label.text() == "📁"
    assert mode_card.icon_label.alignment() == Qt.AlignmentFlag.AlignCenter
    assert mode_card.icon_label.font().pointSize() == 36

    assert mode_card.title_label.text() == "Projeto"
    assert mode_card.title_label.alignment() == Qt.AlignmentFlag.AlignCenter
    assert mode_card.title_label.font().pointSize() == 14
    assert mode_card.title_label.font().bold() is True

    assert mode_card.subtitle_label.text() == "Analisar uma pasta"
    assert mode_card.subtitle_label.alignment() == Qt.AlignmentFlag.AlignCenter
    assert mode_card.subtitle_label.font().pointSize() == 10


def test_mode_card_stylesheet_content(mode_card: ModeCard) -> None:
    style = mode_card.styleSheet()
    assert "QFrame#modeCard" in style
    assert "border-radius: 12px" in style
    assert "QFrame#modeCard:hover" in style
    assert "QFrame#modeCard QLabel" in style


def test_mode_card_left_click_emits_signal(mode_card: ModeCard) -> None:
    click_count = 0

    def on_clicked() -> None:
        nonlocal click_count
        click_count += 1

    mode_card.clicked.connect(on_clicked)
    QTest.mouseClick(mode_card, Qt.MouseButton.LeftButton)

    assert click_count == 1


def test_mode_card_right_click_does_not_emit_signal(mode_card: ModeCard) -> None:
    click_count = 0

    def on_clicked() -> None:
        nonlocal click_count
        click_count += 1

    mode_card.clicked.connect(on_clicked)
    QTest.mouseClick(mode_card, Qt.MouseButton.RightButton)

    assert click_count == 0


def test_home_screen_initial_state(home_screen: HomeScreen) -> None:
    assert isinstance(home_screen, QWidget)

    assert home_screen.title_label.text() == "dev-local-artifact-pruner"
    assert home_screen.title_label.alignment() == Qt.AlignmentFlag.AlignCenter
    assert home_screen.title_label.font().pointSize() == 22
    assert home_screen.title_label.font().bold() is True

    assert home_screen.subtitle_label.text() == "Selecione o tipo de análise"
    assert home_screen.subtitle_label.alignment() == Qt.AlignmentFlag.AlignCenter
    assert home_screen.subtitle_label.font().pointSize() == 12

    assert isinstance(home_screen.card_single, ModeCard)
    assert home_screen.card_single.icon_label.text() == "📁"
    assert home_screen.card_single.title_label.text() == "Projeto"
    assert home_screen.card_single.subtitle_label.text() == "Analisar uma pasta"

    assert isinstance(home_screen.card_multi, ModeCard)
    assert home_screen.card_multi.icon_label.text() == "🗂️"
    assert home_screen.card_multi.title_label.text() == "Múltiplos"
    assert home_screen.card_multi.subtitle_label.text() == "Analisar vários projetos"


def test_home_screen_single_mode_signal_emitted(home_screen: HomeScreen) -> None:
    single_selected = 0
    multi_selected = 0

    def on_single() -> None:
        nonlocal single_selected
        single_selected += 1

    def on_multi() -> None:
        nonlocal multi_selected
        multi_selected += 1

    home_screen.single_mode_selected.connect(on_single)
    home_screen.multi_mode_selected.connect(on_multi)

    QTest.mouseClick(home_screen.card_single, Qt.MouseButton.LeftButton)

    assert single_selected == 1
    assert multi_selected == 0


def test_home_screen_multi_mode_signal_emitted(home_screen: HomeScreen) -> None:
    single_selected = 0
    multi_selected = 0

    def on_single() -> None:
        nonlocal single_selected
        single_selected += 1

    def on_multi() -> None:
        nonlocal multi_selected
        multi_selected += 1

    home_screen.single_mode_selected.connect(on_single)
    home_screen.multi_mode_selected.connect(on_multi)

    QTest.mouseClick(home_screen.card_multi, Qt.MouseButton.LeftButton)

    assert single_selected == 0
    assert multi_selected == 1


def test_ui_exports_mode_card_and_home_screen() -> None:
    import dev_local_artifact_pruner.ui as ui_module

    assert hasattr(ui_module, "ModeCard")
    assert hasattr(ui_module, "HomeScreen")
    assert "ModeCard" in ui_module.__all__
    assert "HomeScreen" in ui_module.__all__
    assert ui_module.ModeCard is ModeCard
    assert ui_module.HomeScreen is HomeScreen
