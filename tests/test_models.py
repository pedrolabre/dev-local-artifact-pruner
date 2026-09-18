from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from pathlib import Path
import pytest

from dev_local_artifact_pruner.core import (
    ActionState,
    Artifact,
    EcosystemType,
    GitInfo,
    Project,
    PruneSummary,
)


def test_ecosystem_type_values():
    assert EcosystemType.NODE.value == "node"
    assert EcosystemType.PYTHON.value == "python"
    assert EcosystemType.UNKNOWN.value == "unknown"


def test_action_state_values():
    assert ActionState.INITIAL.value == "initial"
    assert ActionState.ANALYZING.value == "analyzing"
    assert ActionState.ANALYZED.value == "analyzed"
    assert ActionState.PRUNING_REQUESTED.value == "pruning_requested"
    assert ActionState.PRUNING.value == "pruning"
    assert ActionState.COMPLETED.value == "completed"


def test_artifact_instantiation_and_immutability():
    artifact = Artifact(
        name="node_modules",
        path=Path("/tmp/proj/node_modules"),
        size_bytes=1048576,
        rebuild_command="npm install",
        is_untracked=False,
    )
    assert artifact.name == "node_modules"
    assert artifact.path == Path("/tmp/proj/node_modules")
    assert artifact.size_bytes == 1048576
    assert artifact.rebuild_command == "npm install"
    assert artifact.is_untracked is False

    with pytest.raises(FrozenInstanceError):
        artifact.size_bytes = 2048


def test_artifact_converts_str_to_path():
    artifact = Artifact(
        name=".venv",
        path="/tmp/proj/.venv",
        size_bytes=524288,
    )
    assert isinstance(artifact.path, Path)
    assert artifact.path == Path("/tmp/proj/.venv")


def test_artifact_negative_size_rejected():
    with pytest.raises(ValueError, match="cannot be negative"):
        Artifact(name="dist", path=Path("/tmp/proj/dist"), size_bytes=-1)


@pytest.mark.parametrize(
    "protected_path",
    [
        Path("/tmp/proj/README.md"),
        Path("/tmp/proj/docs/architecture.MD"),
        Path("/tmp/proj/notes.txt"),
        Path("/tmp/proj/index.html"),
        Path("/tmp/proj/.env"),
        Path("/tmp/proj/.env.local"),
        Path("/tmp/proj/.env.production"),
        Path("/tmp/proj/data.sqlite"),
        Path("/tmp/proj/dev.db"),
        Path("/tmp/proj/prod.sqlite3"),
        Path("/tmp/proj/.git"),
        Path("/tmp/proj/.git/config"),
        Path("/tmp/proj/.git/HEAD"),
    ],
)
def test_artifact_rejects_protected_paths(protected_path):
    with pytest.raises(ValueError, match="Protected path cannot be instantiated as Artifact"):
        Artifact(name=protected_path.name, path=protected_path, size_bytes=100)


def test_git_info_defaults_and_immutability():
    git_info = GitInfo()
    assert git_info.is_git_repo is False
    assert git_info.last_commit_date is None
    assert git_info.last_commit_message is None
    assert git_info.is_dirty is False
    assert git_info.days_inactive is None

    with pytest.raises(FrozenInstanceError):
        git_info.is_dirty = True


def test_git_info_with_values():
    now = datetime.now(timezone.utc)
    git_info = GitInfo(
        is_git_repo=True,
        last_commit_date=now,
        last_commit_message="feat: initial commit",
        is_dirty=False,
        days_inactive=42,
    )
    assert git_info.is_git_repo is True
    assert git_info.last_commit_date == now
    assert git_info.last_commit_message == "feat: initial commit"
    assert git_info.is_dirty is False
    assert git_info.days_inactive == 42


def test_git_info_rejects_negative_days():
    with pytest.raises(ValueError, match="cannot be negative"):
        GitInfo(is_git_repo=True, days_inactive=-5)


def test_project_instantiation_and_immutability():
    project = Project(
        name="my-app",
        root_path=Path("/tmp/my-app"),
        ecosystem=EcosystemType.NODE,
    )
    assert project.name == "my-app"
    assert project.root_path == Path("/tmp/my-app")
    assert project.ecosystem == EcosystemType.NODE
    assert project.git_info is None
    assert project.artifacts == ()
    assert project.total_size_bytes == 0

    with pytest.raises(FrozenInstanceError):
        project.name = "renamed"


def test_project_converts_str_to_path_and_list_to_tuple():
    art = Artifact(name="node_modules", path=Path("/tmp/node_modules"), size_bytes=1000)
    project = Project(
        name="my-app",
        root_path="/tmp/my-app",
        artifacts=[art],
    )
    assert isinstance(project.root_path, Path)
    assert isinstance(project.artifacts, tuple)
    assert project.artifacts == (art,)


def test_project_rejects_negative_total_size():
    with pytest.raises(ValueError, match="cannot be negative"):
        Project(name="bad", root_path=Path("/tmp/bad"), total_size_bytes=-1)


def test_project_reclaimable_bytes():
    art1 = Artifact(name="node_modules", path=Path("/tmp/node_modules"), size_bytes=1000)
    art2 = Artifact(name=".cache", path=Path("/tmp/.cache"), size_bytes=500)
    project = Project(
        name="my-app",
        root_path=Path("/tmp/my-app"),
        artifacts=(art1, art2),
    )
    assert project.reclaimable_bytes == 1500


def test_project_reclaimable_bytes_empty():
    project = Project(name="empty", root_path=Path("/tmp/empty"))
    assert project.reclaimable_bytes == 0


def test_project_is_inactive_without_git_info():
    project = Project(name="no-git", root_path=Path("/tmp/no-git"))
    assert project.is_inactive is False


def test_project_is_inactive_not_git_repo():
    git_info = GitInfo(is_git_repo=False, days_inactive=90, is_dirty=False)
    project = Project(name="not-git", root_path=Path("/tmp/not-git"), git_info=git_info)
    assert project.is_inactive is False


def test_project_is_inactive_none_days():
    git_info = GitInfo(is_git_repo=True, days_inactive=None, is_dirty=False)
    project = Project(name="no-days", root_path=Path("/tmp/no-days"), git_info=git_info)
    assert project.is_inactive is False


def test_project_is_inactive_less_than_threshold():
    git_info = GitInfo(is_git_repo=True, days_inactive=59, is_dirty=False)
    project = Project(name="active", root_path=Path("/tmp/active"), git_info=git_info)
    assert project.is_inactive is False


def test_project_is_inactive_threshold_dirty():
    git_info = GitInfo(is_git_repo=True, days_inactive=60, is_dirty=True)
    project = Project(name="dirty", root_path=Path("/tmp/dirty"), git_info=git_info)
    assert project.is_inactive is False


def test_project_is_inactive_threshold_clean():
    git_info = GitInfo(is_git_repo=True, days_inactive=60, is_dirty=False)
    project = Project(name="inactive", root_path=Path("/tmp/inactive"), git_info=git_info)
    assert project.is_inactive is True


def test_project_is_inactive_long_dormant_clean():
    git_info = GitInfo(is_git_repo=True, days_inactive=365, is_dirty=False)
    project = Project(name="dormant", root_path=Path("/tmp/dormant"), git_info=git_info)
    assert project.is_inactive is True


def test_prune_summary_defaults_and_immutability():
    summary = PruneSummary()
    assert summary.projects_pruned == 0
    assert summary.bytes_reclaimed == 0
    assert summary.rebuild_scripts_created == 0
    assert summary.errors == ()
    assert summary.is_successful is True

    with pytest.raises(FrozenInstanceError):
        summary.projects_pruned = 1


def test_prune_summary_with_errors():
    summary = PruneSummary(
        projects_pruned=2,
        bytes_reclaimed=1024,
        rebuild_scripts_created=2,
        errors=["Permission denied on file X"],
    )
    assert isinstance(summary.errors, tuple)
    assert summary.errors == ("Permission denied on file X",)
    assert summary.is_successful is False


@pytest.mark.parametrize(
    "field,value",
    [
        ("projects_pruned", -1),
        ("bytes_reclaimed", -1),
        ("rebuild_scripts_created", -1),
    ],
)
def test_prune_summary_negative_values_rejected(field, value):
    with pytest.raises(ValueError, match="cannot be negative"):
        PruneSummary(**{field: value})
