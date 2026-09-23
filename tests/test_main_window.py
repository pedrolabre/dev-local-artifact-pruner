import os
from typing import Generator
import pytest
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication, QStackedWidget

from dev_local_artifact_pruner.ui import (
    PAGE_INDEX_HOME,
    PAGE_INDEX_MULTI,
    PAGE_INDEX_SINGLE,
    PAGE_TITLES,
    WINDOW_TITLE_HOME,
    WINDOW_TITLE_MULTI,
    WINDOW_TITLE_SINGLE,
    HomeScreen,
    MainWindow,
    MultiProjectScreen,
    SingleProjectScreen,
)

os.environ["QT_QPA_PLATFORM"] = "offscreen"


@pytest.fixture(scope="session")
def qapp() -> Generator[QApplication, None, None]:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def main_window(qapp: QApplication) -> Generator[MainWindow, None, None]:
    window = MainWindow()
    window.show()
    yield window
    window.close()


def test_main_window_initialization(main_window: MainWindow) -> None:
    assert main_window.objectName() == "mainWindow"
    assert main_window.width() == 1000
    assert main_window.height() == 700
    assert main_window.minimumSize().width() == 800
    assert main_window.minimumSize().height() == 600

    assert isinstance(main_window.centralWidget(), QStackedWidget)
    assert main_window.stacked_widget.count() == 3
    assert main_window.stacked_widget.currentIndex() == PAGE_INDEX_HOME
    assert main_window.windowTitle() == WINDOW_TITLE_HOME


def test_main_window_screens_membership(main_window: MainWindow) -> None:
    assert isinstance(main_window.home_screen, HomeScreen)
    assert isinstance(main_window.single_screen, SingleProjectScreen)
    assert isinstance(main_window.multi_screen, MultiProjectScreen)

    assert main_window.stacked_widget.widget(PAGE_INDEX_HOME) is main_window.home_screen
    assert main_window.stacked_widget.widget(PAGE_INDEX_SINGLE) is main_window.single_screen
    assert main_window.stacked_widget.widget(PAGE_INDEX_MULTI) is main_window.multi_screen


def test_navigation_to_single_and_back(main_window: MainWindow) -> None:
    assert main_window.stacked_widget.currentIndex() == PAGE_INDEX_HOME

    main_window.home_screen.single_mode_selected.emit()
    assert main_window.stacked_widget.currentIndex() == PAGE_INDEX_SINGLE
    assert main_window.windowTitle() == WINDOW_TITLE_SINGLE

    main_window.single_screen.back_requested.emit()
    assert main_window.stacked_widget.currentIndex() == PAGE_INDEX_HOME
    assert main_window.windowTitle() == WINDOW_TITLE_HOME


def test_navigation_to_multi_and_back(main_window: MainWindow) -> None:
    assert main_window.stacked_widget.currentIndex() == PAGE_INDEX_HOME

    main_window.home_screen.multi_mode_selected.emit()
    assert main_window.stacked_widget.currentIndex() == PAGE_INDEX_MULTI
    assert main_window.windowTitle() == WINDOW_TITLE_MULTI

    main_window.multi_screen.back_requested.emit()
    assert main_window.stacked_widget.currentIndex() == PAGE_INDEX_HOME
    assert main_window.windowTitle() == WINDOW_TITLE_HOME


def test_navigation_via_direct_methods(main_window: MainWindow) -> None:
    main_window.go_to_single()
    assert main_window.stacked_widget.currentIndex() == PAGE_INDEX_SINGLE
    assert main_window.windowTitle() == WINDOW_TITLE_SINGLE

    main_window.go_to_multi()
    assert main_window.stacked_widget.currentIndex() == PAGE_INDEX_MULTI
    assert main_window.windowTitle() == WINDOW_TITLE_MULTI

    main_window.go_to_home()
    assert main_window.stacked_widget.currentIndex() == PAGE_INDEX_HOME
    assert main_window.windowTitle() == WINDOW_TITLE_HOME


def test_set_page_unknown_index(main_window: MainWindow) -> None:
    main_window.set_page(99)
    assert main_window.stacked_widget.currentIndex() == PAGE_INDEX_HOME
    assert main_window.windowTitle() == WINDOW_TITLE_HOME


def test_main_window_custom_screens_injection(qapp: QApplication) -> None:
    custom_home = HomeScreen()
    custom_single = SingleProjectScreen()
    custom_multi = MultiProjectScreen()

    window = MainWindow(
        home_screen=custom_home,
        single_screen=custom_single,
        multi_screen=custom_multi,
    )
    window.show()

    assert window.home_screen is custom_home
    assert window.single_screen is custom_single
    assert window.multi_screen is custom_multi
    assert window.stacked_widget.widget(0) is custom_home
    assert window.stacked_widget.widget(1) is custom_single
    assert window.stacked_widget.widget(2) is custom_multi

    window.close()


def test_navigation_via_mouse_clicks(main_window: MainWindow) -> None:
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    assert main_window.stacked_widget.currentIndex() == PAGE_INDEX_HOME

    QTest.mouseClick(main_window.home_screen.card_single, Qt.MouseButton.LeftButton)
    assert main_window.stacked_widget.currentIndex() == PAGE_INDEX_SINGLE
    assert main_window.windowTitle() == WINDOW_TITLE_SINGLE

    QTest.mouseClick(main_window.single_screen.btn_back, Qt.MouseButton.LeftButton)
    assert main_window.stacked_widget.currentIndex() == PAGE_INDEX_HOME
    assert main_window.windowTitle() == WINDOW_TITLE_HOME

    QTest.mouseClick(main_window.home_screen.card_multi, Qt.MouseButton.LeftButton)
    assert main_window.stacked_widget.currentIndex() == PAGE_INDEX_MULTI
    assert main_window.windowTitle() == WINDOW_TITLE_MULTI

    QTest.mouseClick(main_window.multi_screen.btn_back, Qt.MouseButton.LeftButton)
    assert main_window.stacked_widget.currentIndex() == PAGE_INDEX_HOME
    assert main_window.windowTitle() == WINDOW_TITLE_HOME


def test_close_event_with_running_multi_worker(qapp: QApplication) -> None:
    from pathlib import Path
    from dev_local_artifact_pruner.ui.multi_screen import ScanWorker

    window = MainWindow()
    worker = ScanWorker(root_path=Path("."))
    window.multi_screen.scan_worker = worker

    event = QCloseEvent()
    window.closeEvent(event)
    assert event.isAccepted()
    window.close()


def test_close_event_handling(main_window: MainWindow) -> None:
    event = QCloseEvent()
    main_window.closeEvent(event)
    assert event.isAccepted()


def test_page_titles_and_indexes_mapping() -> None:
    assert PAGE_INDEX_HOME == 0
    assert PAGE_INDEX_SINGLE == 1
    assert PAGE_INDEX_MULTI == 2
    assert PAGE_TITLES[PAGE_INDEX_HOME] == "dev-local-artifact-pruner"
    assert PAGE_TITLES[PAGE_INDEX_SINGLE] == "dev-local-artifact-pruner - Projeto Individual"
    assert PAGE_TITLES[PAGE_INDEX_MULTI] == "dev-local-artifact-pruner - Múltiplos Projetos"
