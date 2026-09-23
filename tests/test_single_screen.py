from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Generator
import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QFileDialog, QWidget

from dev_local_artifact_pruner.core.models import (
    ActionState,
    Artifact,
    EcosystemType,
    GitInfo,
    Project,
    PruneSummary,
)
from dev_local_artifact_pruner.core.pruner import ProjectPruner
from dev_local_artifact_pruner.core.scanner import ProjectScanner
from dev_local_artifact_pruner.ui import SingleProjectScreen, TerminalWidget

os.environ["QT_QPA_PLATFORM"] = "offscreen"


@pytest.fixture(scope="session")
def qapp() -> Generator[QApplication, None, None]:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def dummy_project(tmp_path: Path) -> Project:
    proj_dir = tmp_path / "mock_project"
    proj_dir.mkdir(parents=True, exist_ok=True)
    art_path = proj_dir / "node_modules"
    art_path.mkdir(parents=True, exist_ok=True)

    artifact = Artifact(name="node_modules", path=art_path, size_bytes=1024 * 1024 * 50)
    git_info = GitInfo(
        is_git_repo=True,
        last_commit_date=datetime.now(timezone.utc),
        last_commit_message="feat: initial commit",
        is_dirty=False,
        days_inactive=90,
    )
    return Project(
        name="mock_project",
        root_path=proj_dir,
        ecosystem=EcosystemType.NODE,
        git_info=git_info,
        artifacts=(artifact,),
        total_size_bytes=artifact.size_bytes,
    )


@pytest.fixture
def single_screen(qapp: QApplication) -> SingleProjectScreen:
    screen = SingleProjectScreen()
    screen.resize(900, 650)
    screen.show()
    return screen


def test_single_screen_initial_state(single_screen: SingleProjectScreen) -> None:
    assert isinstance(single_screen, QWidget)
    assert single_screen.btn_back.text() == "[ ← Voltar ao Início ]"
    assert single_screen.path_edit.text() == ""
    assert "📁" in single_screen.btn_browse.text()
    assert isinstance(single_screen.terminal, TerminalWidget)

    assert single_screen.current_state == ActionState.INITIAL
    assert single_screen.btn_analyze.isEnabled() is True
    assert single_screen.btn_prune.isEnabled() is False
    assert single_screen.btn_confirm.isEnabled() is False
    assert single_screen.btn_cancel.isEnabled() is False

    plain_text = single_screen.terminal.toPlainText()
    assert "Modo Projeto Individual" in plain_text


def test_single_screen_back_button_emits_signal(single_screen: SingleProjectScreen) -> None:
    clicked_count = 0

    def on_back() -> None:
        nonlocal clicked_count
        clicked_count += 1

    single_screen.back_requested.connect(on_back)
    QTest.mouseClick(single_screen.btn_back, Qt.MouseButton.LeftButton)

    assert clicked_count == 1


@pytest.mark.parametrize(
    "state,expected_analyze,expected_prune,expected_confirm,expected_cancel",
    [
        (ActionState.INITIAL, True, False, False, False),
        (ActionState.ANALYZING, False, False, False, False),
        (ActionState.ANALYZED, True, True, False, False),
        (ActionState.PRUNING_REQUESTED, False, False, True, True),
        (ActionState.PRUNING, False, False, False, False),
        (ActionState.COMPLETED, True, False, False, False),
    ],
)
def test_state_machine_button_permissions(
    single_screen: SingleProjectScreen,
    state: ActionState,
    expected_analyze: bool,
    expected_prune: bool,
    expected_confirm: bool,
    expected_cancel: bool,
) -> None:
    single_screen.set_action_state(state)

    assert single_screen.current_state == state
    assert single_screen.btn_analyze.isEnabled() == expected_analyze
    assert single_screen.btn_prune.isEnabled() == expected_prune
    assert single_screen.btn_confirm.isEnabled() == expected_confirm
    assert single_screen.btn_cancel.isEnabled() == expected_cancel


def test_browse_folder_updates_path_and_resets_state(
    single_screen: SingleProjectScreen,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target_dir = tmp_path / "selected_project"
    target_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        QFileDialog,
        "getExistingDirectory",
        lambda *args, **kwargs: str(target_dir),
    )

    single_screen.set_action_state(ActionState.ANALYZED)
    single_screen.browse_folder()

    assert single_screen.path_edit.text() == str(target_dir)
    assert single_screen.current_project is None
    assert single_screen.current_state == ActionState.INITIAL


def test_browse_folder_canceled_keeps_current_path(
    single_screen: SingleProjectScreen,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    single_screen.path_edit.setText("C:/existing/path")

    monkeypatch.setattr(
        QFileDialog,
        "getExistingDirectory",
        lambda *args, **kwargs: "",
    )

    single_screen.browse_folder()
    assert single_screen.path_edit.text() == "C:/existing/path"


def test_analyze_empty_path_logs_warning(single_screen: SingleProjectScreen) -> None:
    single_screen.path_edit.setText("")
    single_screen.analyze_project()

    plain_text = single_screen.terminal.toPlainText()
    assert "Aviso" in plain_text
    assert single_screen.current_state == ActionState.INITIAL


def test_analyze_nonexistent_path_logs_error(
    single_screen: SingleProjectScreen,
    tmp_path: Path,
) -> None:
    missing_path = tmp_path / "does_not_exist"
    single_screen.path_edit.setText(str(missing_path))
    single_screen.analyze_project()

    plain_text = single_screen.terminal.toPlainText()
    assert "Erro" in plain_text


def test_analyze_project_success_with_artifacts(
    single_screen: SingleProjectScreen,
    dummy_project: Project,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    single_screen.path_edit.setText(str(dummy_project.root_path))

    monkeypatch.setattr(
        single_screen.scanner,
        "scan_single_project",
        lambda p: dummy_project,
    )

    single_screen.analyze_project()

    assert single_screen.current_project == dummy_project
    assert single_screen.current_state == ActionState.ANALYZED
    assert single_screen.btn_analyze.isEnabled() is True
    assert single_screen.btn_prune.isEnabled() is True

    plain_text = single_screen.terminal.toPlainText()
    assert "Node.js" in plain_text
    assert "node_modules" in plain_text
    assert "Espaço recuperável: 50.00 MB" in plain_text
    assert "Inativo há mais de 60 dias" in plain_text


def test_analyze_project_success_without_artifacts(
    single_screen: SingleProjectScreen,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proj_dir = tmp_path / "clean_project"
    proj_dir.mkdir(parents=True, exist_ok=True)
    clean_project = Project(
        name="clean_project",
        root_path=proj_dir,
        ecosystem=EcosystemType.PYTHON,
        git_info=GitInfo(is_git_repo=True, is_dirty=False, days_inactive=10),
        artifacts=(),
        total_size_bytes=0,
    )

    single_screen.path_edit.setText(str(proj_dir))
    monkeypatch.setattr(
        single_screen.scanner,
        "scan_single_project",
        lambda p: clean_project,
    )

    single_screen.analyze_project()

    assert single_screen.current_project == clean_project
    assert single_screen.current_state == ActionState.ANALYZED
    plain_text = single_screen.terminal.toPlainText()
    assert "Nenhum artefato elegível para poda encontrado" in plain_text


def test_analyze_project_not_found(
    single_screen: SingleProjectScreen,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_dir = tmp_path / "empty_dir"
    test_dir.mkdir(parents=True, exist_ok=True)

    single_screen.path_edit.setText(str(test_dir))
    monkeypatch.setattr(
        single_screen.scanner,
        "scan_single_project",
        lambda p: None,
    )

    single_screen.analyze_project()

    assert single_screen.current_project is None
    assert single_screen.current_state == ActionState.COMPLETED
    plain_text = single_screen.terminal.toPlainText()
    assert "Nenhum manifesto de projeto suportado" in plain_text


def test_analyze_project_handles_scanner_exception(
    single_screen: SingleProjectScreen,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_dir = tmp_path / "error_dir"
    test_dir.mkdir(parents=True, exist_ok=True)

    def raise_scanner_error(p: Path) -> None:
        raise RuntimeError("Disk read error")

    single_screen.path_edit.setText(str(test_dir))
    monkeypatch.setattr(
        single_screen.scanner,
        "scan_single_project",
        raise_scanner_error,
    )

    single_screen.analyze_project()

    assert single_screen.current_state == ActionState.COMPLETED
    plain_text = single_screen.terminal.toPlainText()
    assert "Disk read error" in plain_text


def test_request_prune_without_project_or_artifacts(single_screen: SingleProjectScreen) -> None:
    single_screen.current_project = None
    single_screen.request_prune()

    plain_text = single_screen.terminal.toPlainText()
    assert "Aviso: Nenhum artefato disponível para poda" in plain_text
    assert single_screen.current_state == ActionState.INITIAL


def test_request_prune_transitions_to_pruning_requested(
    single_screen: SingleProjectScreen,
    dummy_project: Project,
) -> None:
    single_screen.current_project = dummy_project
    single_screen.set_action_state(ActionState.ANALYZED)

    single_screen.request_prune()

    assert single_screen.current_state == ActionState.PRUNING_REQUESTED
    assert single_screen.btn_analyze.isEnabled() is False
    assert single_screen.btn_prune.isEnabled() is False
    assert single_screen.btn_confirm.isEnabled() is True
    assert single_screen.btn_cancel.isEnabled() is True

    plain_text = single_screen.terminal.toPlainText()
    assert "Confirmação necessária" in plain_text
    assert "mock_project" in plain_text


def test_cancel_prune_transitions_to_completed(
    single_screen: SingleProjectScreen,
    dummy_project: Project,
) -> None:
    single_screen.current_project = dummy_project
    single_screen.set_action_state(ActionState.PRUNING_REQUESTED)

    single_screen.cancel_prune()

    assert single_screen.current_state == ActionState.COMPLETED
    assert single_screen.btn_analyze.isEnabled() is True
    assert single_screen.btn_prune.isEnabled() is False
    assert single_screen.btn_confirm.isEnabled() is False
    assert single_screen.btn_cancel.isEnabled() is False

    plain_text = single_screen.terminal.toPlainText()
    assert "Operação de poda cancelada pelo usuário" in plain_text


def test_confirm_prune_success(
    single_screen: SingleProjectScreen,
    dummy_project: Project,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    single_screen.current_project = dummy_project
    single_screen.set_action_state(ActionState.PRUNING_REQUESTED)

    mock_summary = PruneSummary(
        projects_pruned=1,
        bytes_reclaimed=1024 * 1024 * 50,
        rebuild_scripts_created=1,
        errors=(),
    )
    monkeypatch.setattr(
        single_screen.pruner,
        "prune_project",
        lambda p: mock_summary,
    )

    single_screen.confirm_prune()

    assert single_screen.current_state == ActionState.COMPLETED
    assert single_screen.current_project is None
    assert single_screen.btn_analyze.isEnabled() is True
    assert single_screen.btn_prune.isEnabled() is False

    plain_text = single_screen.terminal.toPlainText()
    assert "Poda concluída com sucesso!" in plain_text
    assert "rebuild_dependencies.py" in plain_text


def test_confirm_prune_with_errors(
    single_screen: SingleProjectScreen,
    dummy_project: Project,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    single_screen.current_project = dummy_project
    single_screen.set_action_state(ActionState.PRUNING_REQUESTED)

    mock_summary = PruneSummary(
        projects_pruned=0,
        bytes_reclaimed=0,
        rebuild_scripts_created=0,
        errors=("Permissão negada ao excluir node_modules",),
    )
    monkeypatch.setattr(
        single_screen.pruner,
        "prune_project",
        lambda p: mock_summary,
    )

    single_screen.confirm_prune()

    assert single_screen.current_state == ActionState.COMPLETED
    plain_text = single_screen.terminal.toPlainText()
    assert "Permissão negada" in plain_text


def test_confirm_prune_handles_exception(
    single_screen: SingleProjectScreen,
    dummy_project: Project,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    single_screen.current_project = dummy_project
    single_screen.set_action_state(ActionState.PRUNING_REQUESTED)

    def raise_pruner_error(p: Project) -> None:
        raise OSError("I/O failure during deletion")

    monkeypatch.setattr(
        single_screen.pruner,
        "prune_project",
        raise_pruner_error,
    )

    single_screen.confirm_prune()

    assert single_screen.current_state == ActionState.COMPLETED
    plain_text = single_screen.terminal.toPlainText()
    assert "I/O failure during deletion" in plain_text


def test_ui_exports_single_project_screen() -> None:
    import dev_local_artifact_pruner.ui as ui_module

    assert hasattr(ui_module, "SingleProjectScreen")
    assert "SingleProjectScreen" in ui_module.__all__
    assert ui_module.SingleProjectScreen is SingleProjectScreen
