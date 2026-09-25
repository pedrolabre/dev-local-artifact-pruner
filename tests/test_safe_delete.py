import os
import shutil
import stat
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import dev_local_artifact_pruner.utils as utils_pkg
import dev_local_artifact_pruner.utils.safe_delete as safe_delete_module
from dev_local_artifact_pruner.utils.safe_delete import (
    _handle_remove_readonly,
    _rmtree_with_error_handler,
    safe_remove_tree,
)


def test_utils_reexports():
    assert "safe_remove_tree" in utils_pkg.__all__
    assert callable(utils_pkg.safe_remove_tree)


def test_safe_remove_tree_non_existent_path(tmp_path: Path):
    non_existent = tmp_path / "does_not_exist"
    assert safe_remove_tree(non_existent) is True


def test_safe_remove_tree_string_argument(tmp_path: Path):
    target = tmp_path / "string_path_dir"
    target.mkdir()
    (target / "file.txt").write_text("content", encoding="utf-8")
    assert safe_remove_tree(str(target)) is True
    assert not target.exists()


def test_safe_remove_tree_empty_directory(tmp_path: Path):
    empty_dir = tmp_path / "empty_folder"
    empty_dir.mkdir()
    assert empty_dir.exists()
    assert safe_remove_tree(empty_dir) is True
    assert not empty_dir.exists()


def test_safe_remove_tree_nested_structure(tmp_path: Path):
    parent = tmp_path / "parent"
    child = parent / "level1" / "level2"
    child.mkdir(parents=True)
    (parent / "file1.txt").write_text("1", encoding="utf-8")
    (child / "file2.txt").write_text("2", encoding="utf-8")

    assert safe_remove_tree(parent) is True
    assert not parent.exists()


def test_safe_remove_tree_single_file(tmp_path: Path):
    file_path = tmp_path / "standalone.txt"
    file_path.write_text("data", encoding="utf-8")
    assert file_path.exists()
    assert safe_remove_tree(file_path) is True
    assert not file_path.exists()


def test_safe_remove_tree_read_only_file(tmp_path: Path):
    target_dir = tmp_path / "dir_with_ro_file"
    target_dir.mkdir()
    ro_file = target_dir / "readonly.txt"
    ro_file.write_text("protected", encoding="utf-8")
    os.chmod(ro_file, stat.S_IREAD)

    assert safe_remove_tree(target_dir) is True
    assert not target_dir.exists()


def test_safe_remove_tree_read_only_single_file(tmp_path: Path):
    ro_file = tmp_path / "standalone_ro.txt"
    ro_file.write_text("protected", encoding="utf-8")
    os.chmod(ro_file, stat.S_IREAD)

    assert safe_remove_tree(ro_file) is True
    assert not ro_file.exists()


def test_safe_remove_tree_read_only_subdirectory(tmp_path: Path):
    target_dir = tmp_path / "dir_with_ro_subdir"
    sub_dir = target_dir / "protected_sub"
    sub_dir.mkdir(parents=True)
    ro_file = sub_dir / "nested_ro.txt"
    ro_file.write_text("nested", encoding="utf-8")
    os.chmod(ro_file, stat.S_IREAD)
    try:
        os.chmod(sub_dir, stat.S_IREAD)
    except OSError:
        pass

    assert safe_remove_tree(target_dir) is True
    assert not target_dir.exists()


def test_safe_remove_tree_read_only_root_directory(tmp_path: Path):
    ro_root = tmp_path / "ro_root_dir"
    ro_root.mkdir()
    (ro_root / "sample.txt").write_text("sample", encoding="utf-8")
    try:
        os.chmod(ro_root, stat.S_IREAD)
    except OSError:
        pass

    assert safe_remove_tree(ro_root) is True
    assert not ro_root.exists()


def test_safe_remove_tree_dangerous_paths():
    assert safe_remove_tree("") is False
    assert safe_remove_tree("   ") is False
    assert safe_remove_tree(Path.cwd()) is False
    assert safe_remove_tree(Path(Path.cwd().anchor)) is False
    assert safe_remove_tree(None) is False


def test_safe_remove_tree_retry_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    target_dir = tmp_path / "retry_dir"
    target_dir.mkdir()
    (target_dir / "file.txt").write_text("content", encoding="utf-8")

    attempts = {"count": 0}
    original_rmtree = safe_delete_module._rmtree_with_error_handler

    def fake_rmtree(path: Path):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise PermissionError("File locked by process")
        original_rmtree(path)

    monkeypatch.setattr(
        safe_delete_module,
        "_rmtree_with_error_handler",
        fake_rmtree,
    )

    result = safe_remove_tree(target_dir, retries=3, base_delay=0.01)
    assert result is True
    assert attempts["count"] == 2
    assert not target_dir.exists()


def test_safe_remove_tree_retry_exhausted_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    target_dir = tmp_path / "locked_dir"
    target_dir.mkdir()

    attempts = {"count": 0}

    def failing_rmtree(path: Path):
        attempts["count"] += 1
        raise PermissionError("Permanently locked")

    monkeypatch.setattr(
        safe_delete_module,
        "_rmtree_with_error_handler",
        failing_rmtree,
    )

    result = safe_remove_tree(target_dir, retries=2, base_delay=0.01)
    assert result is False
    assert attempts["count"] == 2


def test_safe_remove_tree_zero_retries_and_negative_delay(tmp_path: Path):
    target_dir = tmp_path / "instant_dir"
    target_dir.mkdir()
    assert safe_remove_tree(target_dir, retries=0, base_delay=-1.0) is True
    assert not target_dir.exists()


def test_safe_remove_tree_symlink_file(tmp_path: Path):
    real_file = tmp_path / "real.txt"
    real_file.write_text("keep this", encoding="utf-8")
    link_file = tmp_path / "link.txt"
    try:
        os.symlink(real_file, link_file)
    except OSError:
        pytest.skip("Symlink creation not permitted in this environment")

    assert safe_remove_tree(link_file) is True
    assert not os.path.lexists(link_file)
    assert real_file.exists()


def test_safe_remove_tree_broken_symlink(tmp_path: Path):
    non_existent_target = tmp_path / "missing.txt"
    broken_link = tmp_path / "broken_link.txt"
    try:
        os.symlink(non_existent_target, broken_link)
    except OSError:
        pytest.skip("Symlink creation not permitted in this environment")

    assert safe_remove_tree(broken_link) is True
    assert not os.path.lexists(broken_link)


def test_safe_remove_tree_symlink_directory(tmp_path: Path):
    real_dir = tmp_path / "real_dir"
    real_dir.mkdir()
    (real_dir / "nested.txt").write_text("keep", encoding="utf-8")
    link_dir = tmp_path / "link_dir"
    try:
        os.symlink(real_dir, link_dir, target_is_directory=True)
    except OSError:
        pytest.skip("Directory symlink creation not permitted in this environment")

    assert safe_remove_tree(link_dir) is True
    assert not os.path.lexists(link_dir)
    assert real_dir.exists()
    assert (real_dir / "nested.txt").exists()


def test_handle_remove_readonly_direct(tmp_path: Path):
    ro_file = tmp_path / "direct_ro.txt"
    ro_file.write_text("text", encoding="utf-8")
    os.chmod(ro_file, stat.S_IREAD)

    mock_func = MagicMock()
    _handle_remove_readonly(mock_func, str(ro_file), None)

    mock_func.assert_called_once_with(str(ro_file))
    assert bool(os.stat(ro_file).st_mode & stat.S_IWRITE)


def test_rmtree_with_error_handler_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    target = tmp_path / "fallback_dir"
    target.mkdir()
    (target / "sample.txt").write_text("sample", encoding="utf-8")

    calls = {"onexc": False, "onerror": False}
    original_rmtree = shutil.rmtree

    def fake_rmtree(path, **kwargs):
        if "onexc" in kwargs:
            calls["onexc"] = True
            raise TypeError("onexc not supported in this mock")
        if "onerror" in kwargs:
            calls["onerror"] = True
            original_rmtree(path)

    monkeypatch.setattr(
        safe_delete_module.shutil,
        "rmtree",
        fake_rmtree,
    )

    _rmtree_with_error_handler(target)
    assert calls["onexc"] is True
    assert calls["onerror"] is True
    assert not target.exists()


def test_safe_remove_tree_windows_long_path(tmp_path: Path):
    from dev_local_artifact_pruner.utils.safe_delete import _to_extended_path

    long_dir = tmp_path
    for i in range(8):
        long_dir = long_dir / f"nested_folder_with_a_very_long_name_level_{i}"

    ext_long_dir = _to_extended_path(str(long_dir))
    os.makedirs(ext_long_dir, exist_ok=True)
    deep_file = os.path.join(ext_long_dir, "deeply_nested_file_with_long_name_sample.txt")
    with open(deep_file, "w", encoding="utf-8") as f:
        f.write("deep")

    assert len(str(deep_file)) > 260
    assert safe_remove_tree(tmp_path / "nested_folder_with_a_very_long_name_level_0") is True
    assert not (tmp_path / "nested_folder_with_a_very_long_name_level_0").exists()

