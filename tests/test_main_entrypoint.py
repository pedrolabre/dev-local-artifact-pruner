import os
import sys
import tomllib
from pathlib import Path
from typing import Generator
import pytest
from PySide6.QtWidgets import QApplication

from dev_local_artifact_pruner.main import main
from dev_local_artifact_pruner.ui.main_window import MainWindow
from dev_local_artifact_pruner.ui.styles import COLOR_BG_APP

os.environ["QT_QPA_PLATFORM"] = "offscreen"


@pytest.fixture(scope="session")
def qapp() -> Generator[QApplication, None, None]:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_main_execution_mocked_exec(monkeypatch: pytest.MonkeyPatch, qapp: QApplication) -> None:
    monkeypatch.setattr(QApplication, "exec", lambda self: 0)

    exit_code = main(["dev-pruner"])
    assert exit_code == 0
    assert QApplication.applicationName() == "dev-local-artifact-pruner"
    assert COLOR_BG_APP in qapp.styleSheet()


def test_main_with_default_sys_argv(monkeypatch: pytest.MonkeyPatch, qapp: QApplication) -> None:
    monkeypatch.setattr(sys, "argv", ["dev-pruner", "--test"])
    monkeypatch.setattr(QApplication, "exec", lambda self: 42)

    exit_code = main()
    assert exit_code == 42


def test_main_instantiates_and_shows_main_window(
    monkeypatch: pytest.MonkeyPatch, qapp: QApplication
) -> None:
    shown = False

    def mock_show(self: MainWindow) -> None:
        nonlocal shown
        shown = True

    monkeypatch.setattr(MainWindow, "show", mock_show)
    monkeypatch.setattr(QApplication, "exec", lambda self: 0)

    main([])
    assert shown is True


def test_pyproject_toml_scripts_entrypoint(project_root: Path) -> None:
    pyproject_path = project_root / "pyproject.toml"
    assert pyproject_path.exists()

    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)

    assert "project" in data
    assert "scripts" in data["project"]
    assert data["project"]["scripts"].get("dev-pruner") == "dev_local_artifact_pruner.main:main"


def test_main_run_module(monkeypatch: pytest.MonkeyPatch, qapp: QApplication, project_root: Path) -> None:
    import runpy

    main_script = project_root / "src" / "dev_local_artifact_pruner" / "main.py"
    monkeypatch.setattr(QApplication, "exec", lambda self: 0)
    monkeypatch.setattr(sys, "argv", ["dev-pruner"])
    with pytest.raises(SystemExit) as excinfo:
        runpy.run_path(str(main_script), run_name="__main__")
    assert excinfo.value.code == 0


def test_run_desktop_script(monkeypatch: pytest.MonkeyPatch, qapp: QApplication, project_root: Path) -> None:
    import runpy

    desktop_script = project_root / "run_desktop.py"
    assert desktop_script.is_file()

    monkeypatch.setattr(QApplication, "exec", lambda self: 0)
    monkeypatch.setattr(sys, "argv", ["run_desktop.py"])
    with pytest.raises(SystemExit) as excinfo:
        runpy.run_path(str(desktop_script), run_name="__main__")
    assert excinfo.value.code == 0


def test_run_desktop_import_error(monkeypatch: pytest.MonkeyPatch, project_root: Path) -> None:
    import builtins
    import runpy

    desktop_script = project_root / "run_desktop.py"
    real_import = builtins.__import__

    def mock_import(name: str, *args, **kwargs):  # type: ignore[no-untyped-def]
        if "dev_local_artifact_pruner.main" in name or name == "dev_local_artifact_pruner.main":
            raise ImportError("Mocked import error")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)
    monkeypatch.setattr(sys, "argv", ["run_desktop.py"])

    with pytest.raises(SystemExit) as excinfo:
        runpy.run_path(str(desktop_script), run_name="__main__")
    assert excinfo.value.code == 1

