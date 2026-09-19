import os
from pathlib import Path
from unittest.mock import MagicMock
import pytest
from dev_local_artifact_pruner.utils import get_directory_size_bytes


def test_get_directory_size_non_existent(tmp_path: Path):
    missing_path = tmp_path / "does_not_exist"
    assert get_directory_size_bytes(missing_path) == 0


def test_get_directory_size_empty_directory(tmp_path: Path):
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    assert get_directory_size_bytes(empty_dir) == 0


def test_get_directory_size_single_file(tmp_path: Path):
    single_file = tmp_path / "file.txt"
    payload = b"A" * 256
    single_file.write_bytes(payload)
    assert get_directory_size_bytes(single_file) == 256


def test_get_directory_size_flat_files(tmp_path: Path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "file1.bin").write_bytes(b"A" * 100)
    (project_dir / "file2.bin").write_bytes(b"B" * 200)
    (project_dir / "file3.bin").write_bytes(b"C" * 300)
    assert get_directory_size_bytes(project_dir) == 600


def test_get_directory_size_nested_subdirectories(tmp_path: Path):
    project_dir = tmp_path / "deep_project"
    sub_1 = project_dir / "level_1"
    sub_2 = sub_1 / "level_2"
    sub_3 = sub_2 / "level_3"
    sub_3.mkdir(parents=True)

    (project_dir / "root.bin").write_bytes(b"X" * 100)
    (sub_1 / "sub1.bin").write_bytes(b"Y" * 250)
    (sub_2 / "sub2.bin").write_bytes(b"Z" * 350)
    (sub_3 / "sub3.bin").write_bytes(b"W" * 500)

    assert get_directory_size_bytes(project_dir) == 1200


def test_get_directory_size_str_argument(tmp_path: Path):
    sample_dir = tmp_path / "str_dir"
    sample_dir.mkdir()
    (sample_dir / "data.bin").write_bytes(b"1" * 64)
    assert get_directory_size_bytes(str(sample_dir)) == 64


def test_get_directory_size_root_permission_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    sample_dir = tmp_path / "locked_dir"
    sample_dir.mkdir()

    def mock_scandir(_path):
        raise PermissionError("Access denied")

    monkeypatch.setattr(os, "scandir", mock_scandir)
    assert get_directory_size_bytes(sample_dir) == 0


def test_get_directory_size_root_exists_permission_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    sample_dir = tmp_path / "locked_exists"
    sample_dir.mkdir()

    def mock_exists(_self):
        raise PermissionError("Access denied")

    monkeypatch.setattr(Path, "exists", mock_exists)
    assert get_directory_size_bytes(sample_dir) == 0


def test_get_directory_size_entry_stat_permission_error(tmp_path: Path):
    sample_dir = tmp_path / "partial_error"
    sample_dir.mkdir()
    (sample_dir / "good.bin").write_bytes(b"G" * 128)

    mock_entry_err = MagicMock()
    mock_entry_err.is_symlink.return_value = False
    mock_entry_err.is_file.return_value = True
    mock_entry_err.stat.side_effect = PermissionError("Permission denied")

    mock_entry_good = MagicMock()
    mock_entry_good.is_symlink.return_value = False
    mock_entry_good.is_file.return_value = True
    stat_result = MagicMock()
    stat_result.st_size = 128
    mock_entry_good.stat.return_value = stat_result

    class MockScandirContext:
        def __enter__(self):
            return [mock_entry_err, mock_entry_good]

        def __exit__(self, exc_type, exc_val, exc_tb):
            return False

    original_scandir = os.scandir

    def patched_scandir(path):
        if str(path) == str(sample_dir):
            return MockScandirContext()
        return original_scandir(path)

    import unittest.mock
    with unittest.mock.patch("os.scandir", side_effect=patched_scandir):
        assert get_directory_size_bytes(sample_dir) == 128


def test_get_directory_size_entry_file_not_found_error(tmp_path: Path):
    sample_dir = tmp_path / "transient_file"
    sample_dir.mkdir()

    mock_entry_err = MagicMock()
    mock_entry_err.is_symlink.return_value = False
    mock_entry_err.is_file.return_value = True
    mock_entry_err.stat.side_effect = FileNotFoundError("File deleted")

    class MockScandirContext:
        def __enter__(self):
            return [mock_entry_err]

        def __exit__(self, exc_type, exc_val, exc_tb):
            return False

    import unittest.mock
    with unittest.mock.patch("os.scandir", return_value=MockScandirContext()):
        assert get_directory_size_bytes(sample_dir) == 0


def test_get_directory_size_ignores_symlink_entries(tmp_path: Path):
    sample_dir = tmp_path / "symlink_dir"
    sample_dir.mkdir()

    mock_symlink_entry = MagicMock()
    mock_symlink_entry.is_symlink.return_value = True
    mock_symlink_entry.is_file.return_value = True
    mock_symlink_entry.stat.return_value.st_size = 99999

    mock_real_entry = MagicMock()
    mock_real_entry.is_symlink.return_value = False
    mock_real_entry.is_file.return_value = True
    mock_real_entry.stat.return_value.st_size = 200

    class MockScandirContext:
        def __enter__(self):
            return [mock_symlink_entry, mock_real_entry]

        def __exit__(self, exc_type, exc_val, exc_tb):
            return False

    import unittest.mock
    with unittest.mock.patch("os.scandir", return_value=MockScandirContext()):
        assert get_directory_size_bytes(sample_dir) == 200


def test_get_directory_size_ignores_real_symlinks_when_supported(tmp_path: Path):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    target_file = source_dir / "target.txt"
    target_file.write_bytes(b"TargetContent" * 10)

    symlink_file = source_dir / "symlink.txt"
    try:
        os.symlink(target_file, symlink_file)
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation not permitted or supported in this environment")

    assert symlink_file.is_symlink()
    assert get_directory_size_bytes(symlink_file) == 0
