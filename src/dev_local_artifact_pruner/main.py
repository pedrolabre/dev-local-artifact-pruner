import sys
from typing import Optional, Sequence

from PySide6.QtWidgets import QApplication

from dev_local_artifact_pruner.ui.main_window import MainWindow
from dev_local_artifact_pruner.ui.styles import get_global_stylesheet


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = list(argv) if argv is not None else sys.argv
    app = QApplication.instance()
    if app is None:
        app = QApplication(args)
    app.setApplicationName("dev-local-artifact-pruner")
    app.setStyleSheet(get_global_stylesheet())

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
