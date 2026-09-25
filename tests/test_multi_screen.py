from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock

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
from dev_local_artifact_pruner.ui import (
    MultiProjectScreen,
    ProjectListWidget,
    ScanWorker,
    TerminalWidget,
)

os.environ["QT_QPA_PLATFORM"] = "offscreen"


@pytest.fixture(scope="session")
def qapp() -> Generator[QApplication, None, None]:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def sample_projects(tmp_path: Path) -> list[Project]:
    p1_dir = tmp_path / "node_inactive"
    p1_dir.mkdir(parents=True, exist_ok=True)
    art1 = Artifact(name="node_modules", path=p1_dir / "node_modules", size_bytes=1024 * 1024 * 150)
    git1 = GitInfo(
        is_git_repo=True,
        last_commit_date=datetime.now(timezone.utc),
        last_commit_message="feat: initial work",
        is_dirty=False,
        days_inactive=120,
    )
    proj1 = Project(
        name="node_inactive",
        root_path=p1_dir,
        ecosystem=EcosystemType.NODE,
        git_info=git1,
        artifacts=(art1,),
        total_size_bytes=art1.size_bytes,
    )

    p2_dir = tmp_path / "python_active"
    p2_dir.mkdir(parents=True, exist_ok=True)
    art2 = Artifact(name=".venv", path=p2_dir / ".venv", size_bytes=1024 * 1024 * 80)
    git2 = GitInfo(
        is_git_repo=True,
        last_commit_date=datetime.now(timezone.utc),
        last_commit_message="fix: latest change",
        is_dirty=True,
        days_inactive=5,
    )
    proj2 = Project(
        name="python_active",
        root_path=p2_dir,
        ecosystem=EcosystemType.PYTHON,
        git_info=git2,
        artifacts=(art2,),
        total_size_bytes=art2.size_bytes,
    )
    return [proj1, proj2]


@pytest.fixture
def multi_screen(qapp: QApplication) -> Generator[MultiProjectScreen, None, None]:
    screen = MultiProjectScreen()
    screen.resize(1000, 700)
    screen.show()
    yield screen
    if screen.scan_worker is not None and screen.scan_worker.isRunning():
        screen.scan_worker.cancel()
        screen.scan_worker.wait(2000)
        QApplication.processEvents()
    screen.close()


def _wait_for_scan(screen: MultiProjectScreen) -> None:
    if screen.scan_worker is not None:
        screen.scan_worker.wait(5000)
        QApplication.processEvents()


def test_multi_screen_initial_state(multi_screen: MultiProjectScreen) -> None:
    assert isinstance(multi_screen, QWidget)
    assert multi_screen.btn_back.text() == "[ ← Voltar ao Início ]"
    assert "Procurar" in multi_screen.btn_browse.text()
    assert not multi_screen.btn_browse.icon().isNull()
    assert isinstance(multi_screen.project_list, ProjectListWidget)
    assert isinstance(multi_screen.terminal, TerminalWidget)

    assert multi_screen.current_state == ActionState.INITIAL
    assert multi_screen.btn_analyze.isEnabled() is True
    assert multi_screen.btn_prune.isEnabled() is False
    assert multi_screen.btn_confirm.isEnabled() is False
    assert multi_screen.btn_cancel.isEnabled() is False

    assert "Modo Múltiplos Projetos" in multi_screen.terminal.toPlainText()
    assert multi_screen.discovered_projects == []


def test_multi_screen_back_button_emits_signal(multi_screen: MultiProjectScreen) -> None:
    clicked_count = 0

    def on_back() -> None:
        nonlocal clicked_count
        clicked_count += 1

    multi_screen.back_requested.connect(on_back)
    QTest.mouseClick(multi_screen.btn_back, Qt.MouseButton.LeftButton)
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
def test_multi_screen_action_button_states(
    multi_screen: MultiProjectScreen,
    state: ActionState,
    expected_analyze: bool,
    expected_prune: bool,
    expected_confirm: bool,
    expected_cancel: bool,
) -> None:
    multi_screen.set_action_state(state)
    assert multi_screen.current_state == state
    assert multi_screen.btn_analyze.isEnabled() is expected_analyze
    assert multi_screen.btn_prune.isEnabled() is expected_prune
    assert multi_screen.btn_confirm.isEnabled() is expected_confirm
    assert multi_screen.btn_cancel.isEnabled() is expected_cancel


def test_multi_screen_browse_folder_selected(
    multi_screen: MultiProjectScreen, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    target_dir = str(tmp_path / "mock_root")
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *args, **kwargs: target_dir)

    multi_screen.browse_folder()
    assert multi_screen.path_edit.text() == target_dir
    assert multi_screen.current_state == ActionState.INITIAL
    assert multi_screen.project_list.count() == 0


def test_multi_screen_browse_folder_cancelled(
    multi_screen: MultiProjectScreen, monkeypatch: pytest.MonkeyPatch
) -> None:
    multi_screen.path_edit.setText("original_path")
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *args, **kwargs: "")

    multi_screen.browse_folder()
    assert multi_screen.path_edit.text() == "original_path"


def test_multi_screen_analyze_empty_path(multi_screen: MultiProjectScreen) -> None:
    multi_screen.path_edit.setText("")
    multi_screen.analyze_projects()
    assert "Aviso: Informe ou selecione a pasta raiz" in multi_screen.terminal.toPlainText()
    assert multi_screen.current_state == ActionState.INITIAL


def test_multi_screen_analyze_nonexistent_path(multi_screen: MultiProjectScreen, tmp_path: Path) -> None:
    fake_dir = tmp_path / "does_not_exist"
    multi_screen.path_edit.setText(str(fake_dir))
    multi_screen.analyze_projects()
    assert "Erro: O caminho especificado não existe" in multi_screen.terminal.toPlainText()
    assert multi_screen.current_state == ActionState.INITIAL


def test_scan_worker_execution(tmp_path: Path, sample_projects: list[Project]) -> None:
    mock_scanner = MagicMock(spec=ProjectScanner)
    mock_scanner.scan_multiple_projects.return_value = sample_projects

    worker = ScanWorker(root_path=tmp_path, scanner=mock_scanner)
    received_projects: list[Project] = []
    received_finished: list[list[Project]] = []
    progress_messages: list[str] = []

    worker.project_found.connect(lambda p: received_projects.append(p))
    worker.scan_finished.connect(lambda lst: received_finished.append(lst))
    worker.progress_message.connect(lambda msg: progress_messages.append(msg))

    worker.start()
    assert worker.wait(5000) is True
    QApplication.processEvents()

    assert len(progress_messages) >= 1
    assert len(received_projects) == 2
    assert len(received_finished) == 1
    assert received_finished[0] == sample_projects


def test_scan_worker_cancellation(tmp_path: Path, sample_projects: list[Project]) -> None:
    mock_scanner = MagicMock(spec=ProjectScanner)
    mock_scanner.scan_multiple_projects.return_value = sample_projects

    worker = ScanWorker(root_path=tmp_path, scanner=mock_scanner)
    worker.cancel()
    finished_called = False
    worker.scan_finished.connect(lambda _: setattr(worker, "_finished_called", True))

    worker.run()
    QApplication.processEvents()
    assert not getattr(worker, "_finished_called", False)


def test_scan_worker_exception(tmp_path: Path) -> None:
    mock_scanner = MagicMock(spec=ProjectScanner)
    mock_scanner.scan_multiple_projects.side_effect = RuntimeError("Disk failure")

    worker = ScanWorker(root_path=tmp_path, scanner=mock_scanner)
    errors: list[str] = []
    finished: list[list] = []

    worker.error_occurred.connect(lambda err: errors.append(err))
    worker.scan_finished.connect(lambda lst: finished.append(lst))

    worker.start()
    assert worker.wait(5000) is True
    QApplication.processEvents()

    assert len(errors) == 1
    assert "Disk failure" in errors[0]
    assert finished == [[]]


def test_multi_screen_analyze_successful_flow(
    multi_screen: MultiProjectScreen, sample_projects: list[Project], tmp_path: Path
) -> None:
    mock_scanner = MagicMock(spec=ProjectScanner)
    mock_scanner.scan_multiple_projects.return_value = sample_projects
    multi_screen.scanner = mock_scanner

    multi_screen.path_edit.setText(str(tmp_path))
    multi_screen.analyze_projects()

    _wait_for_scan(multi_screen)

    assert multi_screen.current_state == ActionState.ANALYZED
    assert multi_screen.project_list.count() == 2

    selected = multi_screen.project_list.get_selected_projects()
    assert len(selected) == 1
    assert selected[0].name == "node_inactive"

    terminal_text = multi_screen.terminal.toPlainText()
    assert "💡 SUGESTÕES IDENTIFICADAS:" in terminal_text
    assert "• node_inactive:" in terminal_text
    assert "• python_active:" in terminal_text
    assert "Total selecionado:" in terminal_text


def test_multi_screen_analyze_no_artifacts_found(
    multi_screen: MultiProjectScreen, tmp_path: Path
) -> None:
    proj_clean = Project(
        name="clean_project",
        root_path=tmp_path / "clean",
        ecosystem=EcosystemType.PYTHON,
        git_info=None,
        artifacts=(),
        total_size_bytes=1000,
    )
    mock_scanner = MagicMock(spec=ProjectScanner)
    mock_scanner.scan_multiple_projects.return_value = [proj_clean]
    multi_screen.scanner = mock_scanner

    multi_screen.path_edit.setText(str(tmp_path))
    multi_screen.analyze_projects()

    _wait_for_scan(multi_screen)

    assert multi_screen.current_state == ActionState.COMPLETED
    assert multi_screen.project_list.count() == 0
    assert "Nenhum projeto com artefatos descartáveis encontrado." in multi_screen.terminal.toPlainText()


def test_multi_screen_selection_changed_synchronization(
    multi_screen: MultiProjectScreen, sample_projects: list[Project], tmp_path: Path
) -> None:
    mock_scanner = MagicMock(spec=ProjectScanner)
    mock_scanner.scan_multiple_projects.return_value = sample_projects
    multi_screen.scanner = mock_scanner

    multi_screen.path_edit.setText(str(tmp_path))
    multi_screen.analyze_projects()
    _wait_for_scan(multi_screen)

    multi_screen.project_list.deselect_all()
    assert "Total selecionado atualizado:" in multi_screen.terminal.toPlainText()
    assert "0 projeto(s) marcados" in multi_screen.terminal.toPlainText()

    multi_screen.project_list.select_inactive()
    assert "1 projeto(s) marcados" in multi_screen.terminal.toPlainText()


def test_multi_screen_project_clicked_details(
    multi_screen: MultiProjectScreen, sample_projects: list[Project], tmp_path: Path
) -> None:
    mock_scanner = MagicMock(spec=ProjectScanner)
    mock_scanner.scan_multiple_projects.return_value = sample_projects
    multi_screen.scanner = mock_scanner

    multi_screen.path_edit.setText(str(tmp_path))
    multi_screen.analyze_projects()
    _wait_for_scan(multi_screen)

    multi_screen._on_project_clicked(sample_projects[0])
    text = multi_screen.terminal.toPlainText()
    assert "--- Detalhes: node_inactive ---" in text
    assert "Node.js" in text
    assert "node_modules" in text

    multi_screen._on_project_clicked(sample_projects[1])
    text2 = multi_screen.terminal.toPlainText()
    assert "--- Detalhes: python_active ---" in text2
    assert "Python" in text2
    assert ".venv" in text2


def test_multi_screen_request_prune_no_selection(
    multi_screen: MultiProjectScreen, sample_projects: list[Project], tmp_path: Path
) -> None:
    mock_scanner = MagicMock(spec=ProjectScanner)
    mock_scanner.scan_multiple_projects.return_value = sample_projects
    multi_screen.scanner = mock_scanner

    multi_screen.path_edit.setText(str(tmp_path))
    multi_screen.analyze_projects()
    _wait_for_scan(multi_screen)

    multi_screen.project_list.deselect_all()
    multi_screen.request_prune()

    assert "Aviso: Nenhum projeto selecionado para poda" in multi_screen.terminal.toPlainText()
    assert multi_screen.current_state == ActionState.ANALYZED


def test_multi_screen_request_prune_and_cancel(
    multi_screen: MultiProjectScreen, sample_projects: list[Project], tmp_path: Path
) -> None:
    mock_scanner = MagicMock(spec=ProjectScanner)
    mock_scanner.scan_multiple_projects.return_value = sample_projects
    multi_screen.scanner = mock_scanner

    multi_screen.path_edit.setText(str(tmp_path))
    multi_screen.analyze_projects()
    _wait_for_scan(multi_screen)

    multi_screen.request_prune()
    assert multi_screen.current_state == ActionState.PRUNING_REQUESTED
    assert "Confirmação necessária: Deseja realmente podar" in multi_screen.terminal.toPlainText()

    multi_screen.cancel_prune()
    assert multi_screen.current_state == ActionState.ANALYZED
    assert multi_screen.btn_prune.isEnabled() is True
    assert "Operação de poda cancelada pelo usuário." in multi_screen.terminal.toPlainText()


def test_multi_screen_confirm_prune_success(
    multi_screen: MultiProjectScreen, sample_projects: list[Project], tmp_path: Path
) -> None:
    mock_scanner = MagicMock(spec=ProjectScanner)
    mock_scanner.scan_multiple_projects.return_value = sample_projects
    multi_screen.scanner = mock_scanner

    mock_pruner = MagicMock(spec=ProjectPruner)
    mock_pruner.prune_multiple_projects.return_value = PruneSummary(
        projects_pruned=1,
        bytes_reclaimed=1024 * 1024 * 150,
        rebuild_scripts_created=1,
        errors=(),
    )
    multi_screen.pruner = mock_pruner

    multi_screen.path_edit.setText(str(tmp_path))
    multi_screen.analyze_projects()
    _wait_for_scan(multi_screen)

    multi_screen.request_prune()
    multi_screen.confirm_prune()

    assert multi_screen.current_state == ActionState.COMPLETED
    text = multi_screen.terminal.toPlainText()
    assert "Poda concluída com sucesso!" in text
    assert "Projetos podados: 1" in text
    assert "rebuild_dependencies.py" in text


def test_multi_screen_confirm_prune_with_errors(
    multi_screen: MultiProjectScreen, sample_projects: list[Project], tmp_path: Path
) -> None:
    mock_scanner = MagicMock(spec=ProjectScanner)
    mock_scanner.scan_multiple_projects.return_value = sample_projects
    multi_screen.scanner = mock_scanner

    mock_pruner = MagicMock(spec=ProjectPruner)
    mock_pruner.prune_multiple_projects.return_value = PruneSummary(
        projects_pruned=0,
        bytes_reclaimed=0,
        rebuild_scripts_created=0,
        errors=("Permission error on node_modules",),
    )
    multi_screen.pruner = mock_pruner

    multi_screen.path_edit.setText(str(tmp_path))
    multi_screen.analyze_projects()
    _wait_for_scan(multi_screen)

    multi_screen.request_prune()
    multi_screen.confirm_prune()

    assert multi_screen.current_state == ActionState.COMPLETED
    assert "Permission error on node_modules" in multi_screen.terminal.toPlainText()


def test_multi_screen_confirm_prune_exception(
    multi_screen: MultiProjectScreen, sample_projects: list[Project], tmp_path: Path
) -> None:
    mock_scanner = MagicMock(spec=ProjectScanner)
    mock_scanner.scan_multiple_projects.return_value = sample_projects
    multi_screen.scanner = mock_scanner

    mock_pruner = MagicMock(spec=ProjectPruner)
    mock_pruner.prune_multiple_projects.side_effect = RuntimeError("Fatal crash")
    multi_screen.pruner = mock_pruner

    multi_screen.path_edit.setText(str(tmp_path))
    multi_screen.analyze_projects()
    _wait_for_scan(multi_screen)

    multi_screen.request_prune()
    multi_screen.confirm_prune()

    assert multi_screen.current_state == ActionState.COMPLETED
    assert "Erro inesperado durante a poda: Fatal crash" in multi_screen.terminal.toPlainText()


def test_multi_screen_stop_worker_on_back(multi_screen: MultiProjectScreen, tmp_path: Path) -> None:
    mock_scanner = MagicMock(spec=ProjectScanner)
    mock_scanner.scan_multiple_projects.return_value = []
    multi_screen.scanner = mock_scanner

    multi_screen.path_edit.setText(str(tmp_path))
    multi_screen.analyze_projects()

    worker = multi_screen.scan_worker
    assert worker is not None
    multi_screen._on_back_clicked()
    assert worker.isFinished() or not worker.isRunning()


def test_ui_exports_multi_screen() -> None:
    from dev_local_artifact_pruner.ui import (
        MultiProjectScreen as ExportedMultiProjectScreen,
        ScanWorker as ExportedScanWorker,
        __all__,
    )

    assert ExportedMultiProjectScreen is MultiProjectScreen
    assert ExportedScanWorker is ScanWorker
    assert "MultiProjectScreen" in __all__
    assert "ScanWorker" in __all__


def test_multi_screen_selection_change_during_prune_requested(
    multi_screen: MultiProjectScreen, sample_projects: list[Project], tmp_path: Path
) -> None:
    mock_scanner = MagicMock(spec=ProjectScanner)
    mock_scanner.scan_multiple_projects.return_value = sample_projects
    multi_screen.scanner = mock_scanner

    multi_screen.path_edit.setText(str(tmp_path))
    multi_screen.analyze_projects()
    _wait_for_scan(multi_screen)

    multi_screen.request_prune()
    assert multi_screen.current_state == ActionState.PRUNING_REQUESTED

    # Modificar seleção deve retornar para ANALYZED e reabilitar botão Apagar
    multi_screen._on_selection_changed()
    assert multi_screen.current_state == ActionState.ANALYZED
    assert multi_screen.btn_prune.isEnabled() is True
    assert "Confirmação anterior cancelada" in multi_screen.terminal.toPlainText()

