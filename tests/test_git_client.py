import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import dev_local_artifact_pruner.core as core_pkg
from dev_local_artifact_pruner.core.git_client import (
    DEFAULT_GIT_TIMEOUT,
    GitClient,
)
from dev_local_artifact_pruner.core.models import GitInfo


@pytest.fixture
def empty_git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "empty_repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=str(repo), check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Pruner Test"],
        cwd=str(repo),
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@pruner.local"],
        cwd=str(repo),
        check=True,
        capture_output=True,
    )
    return repo


@pytest.fixture
def committed_git_repo(empty_git_repo: Path) -> Path:
    file_path = empty_git_repo / "tracked.txt"
    file_path.write_text("initial content", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=str(empty_git_repo), check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "feat: initial commit"],
        cwd=str(empty_git_repo),
        check=True,
        capture_output=True,
    )
    return empty_git_repo


def test_core_reexports():
    assert "GitClient" in core_pkg.__all__
    assert "DEFAULT_GIT_TIMEOUT" in core_pkg.__all__
    assert core_pkg.GitClient is GitClient


def test_git_client_initialization_defaults():
    client = GitClient()
    assert client.timeout == DEFAULT_GIT_TIMEOUT
    assert client.timeout == 5.0


def test_git_client_initialization_custom():
    client = GitClient(timeout=10.5)
    assert client.timeout == 10.5

    client_negative = GitClient(timeout=-1.0)
    assert client_negative.timeout == DEFAULT_GIT_TIMEOUT


def test_is_git_repository_positive(committed_git_repo: Path):
    client = GitClient()
    assert client.is_git_repository(committed_git_repo) is True
    assert client.is_git_repository(str(committed_git_repo)) is True


def test_is_git_repository_class_call(committed_git_repo: Path):
    assert GitClient.is_git_repository(committed_git_repo) is True
    assert GitClient.is_git_repository(str(committed_git_repo)) is True


def test_is_git_repository_empty_repo(empty_git_repo: Path):
    client = GitClient()
    assert client.is_git_repository(empty_git_repo) is True


def test_is_git_repository_non_git_directory(tmp_path: Path):
    plain_dir = tmp_path / "plain_dir"
    plain_dir.mkdir()
    client = GitClient()
    assert client.is_git_repository(plain_dir) is False


def test_is_git_repository_non_existent_directory(tmp_path: Path):
    non_existent = tmp_path / "does_not_exist"
    client = GitClient()
    assert client.is_git_repository(non_existent) is False


def test_is_git_repository_file_path(tmp_path: Path):
    file_path = tmp_path / "sample.txt"
    file_path.write_text("data", encoding="utf-8")
    client = GitClient()
    assert client.is_git_repository(file_path) is False


def test_is_git_repository_subfolder_in_repo(committed_git_repo: Path):
    subfolder = committed_git_repo / "src" / "pkg"
    subfolder.mkdir(parents=True)
    client = GitClient()
    assert client.is_git_repository(subfolder) is False


def test_is_git_repository_fake_corrupted_git_dir(tmp_path: Path):
    bad_repo = tmp_path / "bad_repo"
    bad_repo.mkdir()
    (bad_repo / ".git").mkdir()
    client = GitClient()
    assert client.is_git_repository(bad_repo) is False


def test_get_git_info_clean_repo(committed_git_repo: Path):
    client = GitClient()
    info = client.get_git_info(committed_git_repo)

    assert isinstance(info, GitInfo)
    assert info.is_git_repo is True
    assert info.is_dirty is False
    assert info.last_commit_message == "feat: initial commit"
    assert info.last_commit_date is not None
    assert isinstance(info.last_commit_date, datetime)
    assert info.last_commit_date.tzinfo == timezone.utc
    assert info.days_inactive == 0


def test_get_git_info_class_call(committed_git_repo: Path):
    info = GitClient.get_git_info(committed_git_repo)
    assert info.is_git_repo is True
    assert info.is_dirty is False
    assert info.last_commit_message == "feat: initial commit"


def test_get_git_info_non_git_directory(tmp_path: Path):
    plain_dir = tmp_path / "not_git"
    plain_dir.mkdir()
    client = GitClient()
    info = client.get_git_info(plain_dir)

    assert info.is_git_repo is False
    assert info.is_dirty is False
    assert info.last_commit_date is None
    assert info.last_commit_message is None
    assert info.days_inactive is None


def test_get_git_info_non_existent_directory(tmp_path: Path):
    non_existent = tmp_path / "ghost_repo"
    client = GitClient()
    info = client.get_git_info(non_existent)
    assert info == GitInfo(is_git_repo=False)


def test_get_git_info_empty_repo_without_commits(empty_git_repo: Path):
    client = GitClient()
    info = client.get_git_info(empty_git_repo)

    assert info.is_git_repo is True
    assert info.last_commit_date is None
    assert info.last_commit_message is None
    assert info.days_inactive is None
    assert info.is_dirty is False


def test_get_git_info_dirty_working_tree_modified_file(committed_git_repo: Path):
    tracked = committed_git_repo / "tracked.txt"
    tracked.write_text("modified uncommitted content", encoding="utf-8")

    client = GitClient()
    info = client.get_git_info(committed_git_repo)

    assert info.is_git_repo is True
    assert info.is_dirty is True


def test_get_git_info_dirty_working_tree_staged_file(committed_git_repo: Path):
    new_file = committed_git_repo / "staged.txt"
    new_file.write_text("staged content", encoding="utf-8")
    subprocess.run(["git", "add", "staged.txt"], cwd=str(committed_git_repo), check=True, capture_output=True)

    client = GitClient()
    info = client.get_git_info(committed_git_repo)

    assert info.is_git_repo is True
    assert info.is_dirty is True


def test_get_git_info_dirty_working_tree_deleted_file(committed_git_repo: Path):
    tracked = committed_git_repo / "tracked.txt"
    tracked.unlink()

    client = GitClient()
    info = client.get_git_info(committed_git_repo)

    assert info.is_git_repo is True
    assert info.is_dirty is True


def test_get_git_info_clean_with_only_untracked_files(committed_git_repo: Path):
    untracked = committed_git_repo / "temporary.log"
    untracked.write_text("build log", encoding="utf-8")

    client = GitClient()
    info = client.get_git_info(committed_git_repo)

    assert info.is_git_repo is True
    assert info.is_dirty is False


def test_get_git_info_dirty_with_both_modified_and_untracked(committed_git_repo: Path):
    tracked = committed_git_repo / "tracked.txt"
    tracked.write_text("modified", encoding="utf-8")
    untracked = committed_git_repo / "untracked.log"
    untracked.write_text("log", encoding="utf-8")

    client = GitClient()
    info = client.get_git_info(committed_git_repo)

    assert info.is_git_repo is True
    assert info.is_dirty is True


def test_get_git_info_inactive_days_calculation(empty_git_repo: Path):
    file_path = empty_git_repo / "old.txt"
    file_path.write_text("old content", encoding="utf-8")
    subprocess.run(["git", "add", "old.txt"], cwd=str(empty_git_repo), check=True, capture_output=True)

    env = os.environ.copy()
    env["GIT_AUTHOR_DATE"] = "2024-01-01T12:00:00Z"
    env["GIT_COMMITTER_DATE"] = "2024-01-01T12:00:00Z"
    subprocess.run(
        ["git", "commit", "-m", "feat: old commit"],
        cwd=str(empty_git_repo),
        check=True,
        capture_output=True,
        env=env,
    )

    client = GitClient()
    info = client.get_git_info(empty_git_repo)

    assert info.is_git_repo is True
    assert info.last_commit_message == "feat: old commit"
    assert info.days_inactive is not None
    assert info.days_inactive >= 60


def test_get_untracked_files_empty(committed_git_repo: Path):
    client = GitClient()
    untracked = client.get_untracked_files(committed_git_repo)
    assert untracked == []


def test_get_untracked_files_single_file(committed_git_repo: Path):
    untracked_file = committed_git_repo / "file1.tmp"
    untracked_file.write_text("tmp", encoding="utf-8")

    client = GitClient()
    untracked = client.get_untracked_files(committed_git_repo)

    assert len(untracked) == 1
    assert untracked[0] == untracked_file
    assert isinstance(untracked[0], Path)


def test_get_untracked_files_multiple_files(committed_git_repo: Path):
    file1 = committed_git_repo / "alpha.log"
    file2 = committed_git_repo / "beta.cache"
    file1.write_text("a", encoding="utf-8")
    file2.write_text("b", encoding="utf-8")

    client = GitClient()
    untracked = client.get_untracked_files(committed_git_repo)

    assert set(untracked) == {file1, file2}


def test_get_untracked_files_with_spaces_in_name(committed_git_repo: Path):
    file_with_spaces = committed_git_repo / "my spaced artifact.tmp"
    file_with_spaces.write_text("spaced", encoding="utf-8")

    client = GitClient()
    untracked = client.get_untracked_files(committed_git_repo)

    assert file_with_spaces in untracked


def test_get_untracked_files_class_call(committed_git_repo: Path):
    untracked_file = committed_git_repo / "via_class.tmp"
    untracked_file.write_text("data", encoding="utf-8")

    untracked = GitClient.get_untracked_files(committed_git_repo)
    assert untracked == [untracked_file]


def test_get_untracked_files_non_git_directory(tmp_path: Path):
    plain_dir = tmp_path / "plain_dir"
    plain_dir.mkdir()
    (plain_dir / "untracked.txt").write_text("test", encoding="utf-8")

    client = GitClient()
    assert client.get_untracked_files(plain_dir) == []


def test_get_untracked_files_non_existent_path(tmp_path: Path):
    ghost = tmp_path / "ghost_path"
    client = GitClient()
    assert client.get_untracked_files(ghost) == []


def test_resilience_timeout_in_is_git_repository():
    client = GitClient(timeout=0.01)
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["git"], timeout=0.01)):
        assert client.is_git_repository(Path("/mock/repo")) is False


def test_resilience_oserror_in_is_git_repository():
    client = GitClient()
    with patch("subprocess.run", side_effect=OSError("Command failed")):
        assert client.is_git_repository(Path("/mock/repo")) is False


def test_resilience_timeout_in_get_git_info():
    client = GitClient(timeout=0.01)
    with patch.object(client, "is_git_repository", return_value=True):
        with patch.object(client, "_run_git_command", return_value=None):
            info = client.get_git_info(Path("/mock/repo"))
            assert info.is_git_repo is True
            assert info.last_commit_date is None
            assert info.is_dirty is False


def test_resilience_malformed_log_output():
    client = GitClient()
    with patch.object(client, "is_git_repository", return_value=True):
        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_res.stdout = "not_a_timestamp|Some commit\n"
        with patch.object(client, "_run_git_command", return_value=mock_res):
            info = client.get_git_info(Path("/mock/repo"))
            assert info.is_git_repo is True
            assert info.last_commit_date is None
            assert info.last_commit_message is None
            assert info.days_inactive is None


def test_resilience_timeout_in_get_untracked_files():
    client = GitClient(timeout=0.01)
    with patch.object(client, "is_git_repository", return_value=True):
        with patch.object(client, "_run_git_command", return_value=None):
            assert client.get_untracked_files(Path("/mock/repo")) == []


def test_resilience_general_exception_handling():
    client = GitClient()
    with patch.object(client, "_resolve_target", side_effect=RuntimeError("Fatal boom")):
        assert client.is_git_repository(Path("/any")) is False
        assert client.get_git_info(Path("/any")) == GitInfo(is_git_repo=False)
        assert client.get_untracked_files(Path("/any")) == []
