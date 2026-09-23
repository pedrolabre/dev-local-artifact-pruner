from typing import Dict, Optional

from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QMainWindow, QStackedWidget, QWidget

from dev_local_artifact_pruner.ui.home_screen import HomeScreen
from dev_local_artifact_pruner.ui.multi_screen import MultiProjectScreen
from dev_local_artifact_pruner.ui.single_screen import SingleProjectScreen

WINDOW_TITLE_HOME = "dev-local-artifact-pruner"
WINDOW_TITLE_SINGLE = "dev-local-artifact-pruner - Projeto Individual"
WINDOW_TITLE_MULTI = "dev-local-artifact-pruner - Múltiplos Projetos"

PAGE_INDEX_HOME = 0
PAGE_INDEX_SINGLE = 1
PAGE_INDEX_MULTI = 2

PAGE_TITLES: Dict[int, str] = {
    PAGE_INDEX_HOME: WINDOW_TITLE_HOME,
    PAGE_INDEX_SINGLE: WINDOW_TITLE_SINGLE,
    PAGE_INDEX_MULTI: WINDOW_TITLE_MULTI,
}


class MainWindow(QMainWindow):
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        home_screen: Optional[HomeScreen] = None,
        single_screen: Optional[SingleProjectScreen] = None,
        multi_screen: Optional[MultiProjectScreen] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("mainWindow")

        self.stacked_widget = QStackedWidget(self)

        self.home_screen = (
            home_screen if home_screen is not None else HomeScreen(self)
        )
        self.single_screen = (
            single_screen
            if single_screen is not None
            else SingleProjectScreen(self)
        )
        self.multi_screen = (
            multi_screen
            if multi_screen is not None
            else MultiProjectScreen(self)
        )

        self.stacked_widget.addWidget(self.home_screen)
        self.stacked_widget.addWidget(self.single_screen)
        self.stacked_widget.addWidget(self.multi_screen)

        self.setCentralWidget(self.stacked_widget)
        self.resize(1000, 700)
        self.setMinimumSize(800, 600)

        self.home_screen.single_mode_selected.connect(self.go_to_single)
        self.home_screen.multi_mode_selected.connect(self.go_to_multi)
        self.single_screen.back_requested.connect(self.go_to_home)
        self.multi_screen.back_requested.connect(self.go_to_home)

        self.go_to_home()

    def set_page(self, index: int) -> None:
        self.stacked_widget.setCurrentIndex(index)
        title = PAGE_TITLES.get(index, WINDOW_TITLE_HOME)
        self.setWindowTitle(title)

    def go_to_home(self) -> None:
        self.set_page(PAGE_INDEX_HOME)

    def go_to_single(self) -> None:
        self.set_page(PAGE_INDEX_SINGLE)

    def go_to_multi(self) -> None:
        self.set_page(PAGE_INDEX_MULTI)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.multi_screen.close()
        super().closeEvent(event)
