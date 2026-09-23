from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Generator
import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QWidget

from dev_local_artifact_pruner.core.models import (
    Artifact,
    EcosystemType,
    GitInfo,
    Project,
)
from dev_local_artifact_pruner.ui import ProjectListWidget
from dev_local_artifact_pruner.utils.formatters import format_bytes

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
        last_commit_message="feat: old work",
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
        last_commit_message="fix: recent fix",
        is_dirty=False,
        days_inactive=10,
    )
    proj2 = Project(
        name="python_active",
        root_path=p2_dir,
        ecosystem=EcosystemType.PYTHON,
        git_info=git2,
        artifacts=(art2,),
        total_size_bytes=art2.size_bytes,
    )

    p3_dir = tmp_path / "unknown_project"
    p3_dir.mkdir(parents=True, exist_ok=True)
    proj3 = Project(
        name="unknown_project",
        root_path=p3_dir,
        ecosystem=EcosystemType.UNKNOWN,
        git_info=None,
        artifacts=(),
        total_size_bytes=1024 * 1024 * 20,
    )

    return [proj1, proj2, proj3]


@pytest.fixture
def project_list_widget(qapp: QApplication) -> ProjectListWidget:
    widget = ProjectListWidget()
    widget.resize(400, 600)
    widget.show()
    return widget


def test_project_list_widget_initial_state(project_list_widget: ProjectListWidget) -> None:
    assert isinstance(project_list_widget, QWidget)
    assert project_list_widget.btn_select_inactive.text() == "[ Marcar Inativos ]"
    assert project_list_widget.btn_deselect_all.text() == "[ Desmarcar Todos ]"
    assert project_list_widget.btn_select_inactive.cursor().shape() == Qt.CursorShape.PointingHandCursor
    assert project_list_widget.btn_deselect_all.cursor().shape() == Qt.CursorShape.PointingHandCursor

    assert project_list_widget.count() == 0
    assert project_list_widget.get_selected_projects() == []
    assert project_list_widget.get_selected_bytes() == 0
    assert project_list_widget.get_all_projects() == []

    assert project_list_widget.btn_mark_inactive is project_list_widget.btn_select_inactive
    assert project_list_widget.btn_uncheck_all is project_list_widget.btn_deselect_all
    assert project_list_widget.items_list is project_list_widget.list_widget
    assert project_list_widget.project_list is project_list_widget.list_widget


def test_populate_projects_and_preselection(
    project_list_widget: ProjectListWidget, sample_projects: list[Project]
) -> None:
    project_list_widget.populate_projects(sample_projects)

    assert project_list_widget.count() == 3
    all_projs = project_list_widget.get_all_projects()
    assert len(all_projs) == 3
    assert all_projs[0].name == "node_inactive"
    assert all_projs[1].name == "python_active"
    assert all_projs[2].name == "unknown_project"

    item0 = project_list_widget.list_widget.item(0)
    item1 = project_list_widget.list_widget.item(1)
    item2 = project_list_widget.list_widget.item(2)

    assert item0.checkState() == Qt.CheckState.Checked
    assert item1.checkState() == Qt.CheckState.Unchecked
    assert item2.checkState() == Qt.CheckState.Unchecked

    assert bool(item0.flags() & Qt.ItemFlag.ItemIsUserCheckable) is True
    assert bool(item1.flags() & Qt.ItemFlag.ItemIsUserCheckable) is True
    assert bool(item2.flags() & Qt.ItemFlag.ItemIsUserCheckable) is True

    selected = project_list_widget.get_selected_projects()
    assert len(selected) == 1
    assert selected[0].name == "node_inactive"

    expected_bytes = sample_projects[0].reclaimable_bytes
    assert project_list_widget.get_selected_bytes() == expected_bytes


def test_item_formatting(
    project_list_widget: ProjectListWidget, sample_projects: list[Project]
) -> None:
    project_list_widget.populate_projects(sample_projects)

    item0_text = project_list_widget.list_widget.item(0).text()
    assert "node_inactive" in item0_text
    assert "Node.js" in item0_text
    assert format_bytes(sample_projects[0].reclaimable_bytes) in item0_text
    assert "[Inativo]" in item0_text

    item1_text = project_list_widget.list_widget.item(1).text()
    assert "python_active" in item1_text
    assert "Python" in item1_text
    assert format_bytes(sample_projects[1].reclaimable_bytes) in item1_text
    assert "[Ativo]" in item1_text

    item2_text = project_list_widget.list_widget.item(2).text()
    assert "unknown_project" in item2_text
    assert "Desconhecido" in item2_text
    assert format_bytes(sample_projects[2].total_size_bytes) in item2_text
    assert "[Ativo]" in item2_text


def test_shortcut_buttons_and_methods(
    project_list_widget: ProjectListWidget, sample_projects: list[Project]
) -> None:
    project_list_widget.populate_projects(sample_projects)

    QTest.mouseClick(project_list_widget.btn_deselect_all, Qt.MouseButton.LeftButton)
    assert project_list_widget.get_selected_projects() == []
    assert project_list_widget.get_selected_bytes() == 0

    QTest.mouseClick(project_list_widget.btn_select_inactive, Qt.MouseButton.LeftButton)
    selected = project_list_widget.get_selected_projects()
    assert len(selected) == 1
    assert selected[0].name == "node_inactive"
    assert project_list_widget.get_selected_bytes() == sample_projects[0].reclaimable_bytes

    project_list_widget.select_all()
    assert len(project_list_widget.get_selected_projects()) == 3
    expected_total = (
        sample_projects[0].reclaimable_bytes
        + sample_projects[1].reclaimable_bytes
        + sample_projects[2].total_size_bytes
    )
    assert project_list_widget.get_selected_bytes() == expected_total

    project_list_widget.deselect_all()
    assert len(project_list_widget.get_selected_projects()) == 0

    project_list_widget.select_inactive()
    assert len(project_list_widget.get_selected_projects()) == 1

    project_list_widget.mark_inactive()
    assert len(project_list_widget.get_selected_projects()) == 1

    project_list_widget.uncheck_all()
    assert len(project_list_widget.get_selected_projects()) == 0


def test_selection_changed_signal(
    project_list_widget: ProjectListWidget, sample_projects: list[Project]
) -> None:
    signal_count = 0

    def on_selection_changed() -> None:
        nonlocal signal_count
        signal_count += 1

    project_list_widget.selection_changed.connect(on_selection_changed)

    project_list_widget.populate_projects(sample_projects)
    assert signal_count >= 1

    count_before = signal_count
    item1 = project_list_widget.list_widget.item(1)
    item1.setCheckState(Qt.CheckState.Checked)
    assert signal_count == count_before + 1

    count_before = signal_count
    project_list_widget.deselect_all()
    assert signal_count == count_before + 1

    count_before = signal_count
    project_list_widget.select_inactive()
    assert signal_count == count_before + 1


def test_project_clicked_signal(
    project_list_widget: ProjectListWidget, sample_projects: list[Project]
) -> None:
    clicked_projects: list[Project] = []

    def on_project_clicked(p: Project) -> None:
        clicked_projects.append(p)

    project_list_widget.project_clicked.connect(on_project_clicked)
    project_list_widget.populate_projects(sample_projects)

    item1 = project_list_widget.list_widget.item(1)
    project_list_widget.list_widget.itemClicked.emit(item1)

    assert len(clicked_projects) == 1
    assert clicked_projects[0].name == "python_active"

    item0 = project_list_widget.list_widget.item(0)
    project_list_widget.list_widget.itemClicked.emit(item0)
    assert len(clicked_projects) == 2
    assert clicked_projects[1].name == "node_inactive"


def test_clear_method(
    project_list_widget: ProjectListWidget, sample_projects: list[Project]
) -> None:
    project_list_widget.populate_projects(sample_projects)
    assert project_list_widget.count() == 3

    cleared_signal = 0

    def on_change() -> None:
        nonlocal cleared_signal
        cleared_signal += 1

    project_list_widget.selection_changed.connect(on_change)
    project_list_widget.clear()

    assert project_list_widget.count() == 0
    assert project_list_widget.get_selected_projects() == []
    assert project_list_widget.get_selected_bytes() == 0
    assert project_list_widget.get_all_projects() == []
    assert cleared_signal >= 1


def test_populate_empty_list(project_list_widget: ProjectListWidget) -> None:
    project_list_widget.populate_projects([])
    assert project_list_widget.count() == 0
    assert project_list_widget.get_selected_projects() == []
    assert project_list_widget.get_selected_bytes() == 0
    assert project_list_widget.get_all_projects() == []


def test_dirty_project_treated_as_active(
    project_list_widget: ProjectListWidget, tmp_path: Path
) -> None:
    p_dir = tmp_path / "dirty_project"
    p_dir.mkdir(parents=True, exist_ok=True)
    git_dirty = GitInfo(
        is_git_repo=True,
        last_commit_date=datetime.now(timezone.utc),
        last_commit_message="WIP: unfinished changes",
        is_dirty=True,
        days_inactive=150,
    )
    proj_dirty = Project(
        name="dirty_project",
        root_path=p_dir,
        ecosystem=EcosystemType.NODE,
        git_info=git_dirty,
        artifacts=(),
        total_size_bytes=5000,
    )

    project_list_widget.populate_projects([proj_dirty])
    assert proj_dirty.is_inactive is False
    assert project_list_widget.list_widget.item(0).checkState() == Qt.CheckState.Unchecked
    assert "[Ativo]" in project_list_widget.list_widget.item(0).text()
    assert project_list_widget.get_selected_projects() == []


def test_item_clicked_with_non_project_data(
    project_list_widget: ProjectListWidget,
) -> None:
    clicked_projects: list[Project] = []
    project_list_widget.project_clicked.connect(lambda p: clicked_projects.append(p))

    from PySide6.QtWidgets import QListWidgetItem
    generic_item = QListWidgetItem("generic text")
    generic_item.setData(Qt.ItemDataRole.UserRole, "not a project")
    project_list_widget.list_widget.addItem(generic_item)

    project_list_widget.list_widget.itemClicked.emit(generic_item)
    assert len(clicked_projects) == 0


def test_ui_exports() -> None:
    from dev_local_artifact_pruner.ui import (
        ProjectListWidget as ExportedProjectListWidget,
        __all__,
    )

    assert ExportedProjectListWidget is ProjectListWidget
    assert "ProjectListWidget" in __all__

