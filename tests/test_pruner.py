import os
import stat
from pathlib import Path
from unittest.mock import patch

import pytest

import dev_local_artifact_pruner.core as core_pkg
from dev_local_artifact_pruner.core.models import (
    Artifact,
    EcosystemType,
    Project,
    PruneSummary,
)
from dev_local_artifact_pruner.core.pruner import ProjectPruner


def test_core_reexports() -> None:
    assert "ProjectPruner" in core_pkg.__all__
    assert core_pkg.ProjectPruner is ProjectPruner


def test_pruner_initialization_defaults() -> None:
    default_pruner = ProjectPruner()
    assert default_pruner.overwrite_rebuild_script is True

    custom_pruner = ProjectPruner(overwrite_rebuild_script=False)
    assert custom_pruner.overwrite_rebuild_script is False


def test_prune_project_invalid_inputs(tmp_path: Path) -> None:
    pruner = ProjectPruner()

    summary_none = pruner.prune_project(None)
    assert summary_none.projects_pruned == 0
    assert summary_none.bytes_reclaimed == 0
    assert summary_none.rebuild_scripts_created == 0
    assert summary_none.is_successful is False
    assert "Invalid project provided" in summary_none.errors[0]

    summary_invalid = pruner.prune_project("not a project")
    assert summary_invalid.projects_pruned == 0
    assert summary_invalid.is_successful is False

    summary_class = ProjectPruner.prune_project(None)
    assert summary_class.projects_pruned == 0
    assert summary_class.is_successful is False

    non_existent = tmp_path / "non_existent_root"
    project_missing = Project(name="missing", root_path=non_existent)
    summary_missing = pruner.prune_project(project_missing)
    assert summary_missing.projects_pruned == 0
    assert "does not exist or is not a directory" in summary_missing.errors[0]

    file_root = tmp_path / "file_root.txt"
    file_root.write_text("content", encoding="utf-8")
    project_file = Project(name="file_as_root", root_path=file_root)
    summary_file = pruner.prune_project(project_file)
    assert summary_file.projects_pruned == 0
    assert "protected" in summary_file.errors[0] or "does not exist or is not a directory" in summary_file.errors[0]

    git_root = tmp_path / ".git"
    git_root.mkdir()
    project_git = Project(name="git_root", root_path=git_root)
    summary_git = pruner.prune_project(project_git)
    assert summary_git.projects_pruned == 0
    assert "protected" in summary_git.errors[0]


def test_prune_project_empty_artifacts(tmp_path: Path) -> None:
    proj_dir = tmp_path / "empty_project"
    proj_dir.mkdir()
    (proj_dir / "package.json").write_text('{"name": "empty"}', encoding="utf-8")

    project = Project(
        name="empty_project",
        root_path=proj_dir,
        ecosystem=EcosystemType.NODE,
        artifacts=(),
    )

    pruner = ProjectPruner()
    summary = pruner.prune_project(project)
    assert summary.projects_pruned == 0
    assert summary.bytes_reclaimed == 0
    assert summary.rebuild_scripts_created == 0
    assert summary.is_successful is True
    assert summary.errors == ()


def test_prune_single_project_node_success(tmp_path: Path) -> None:
    proj_dir = tmp_path / "node_app"
    proj_dir.mkdir()
    (proj_dir / "package.json").write_text('{"name": "app"}', encoding="utf-8")

    nm_dir = proj_dir / "node_modules"
    nm_dir.mkdir()
    pkg_file = nm_dir / "pkg.js"
    pkg_file.write_text("module.exports = {};", encoding="utf-8")

    ro_file = nm_dir / "readonly.txt"
    ro_file.write_text("readonly content", encoding="utf-8")
    os.chmod(ro_file, stat.S_IREAD)

    artifact = Artifact(name="node_modules", path=nm_dir, size_bytes=1024)
    project = Project(
        name="node_app",
        root_path=proj_dir,
        ecosystem=EcosystemType.NODE,
        artifacts=(artifact,),
    )

    pruner = ProjectPruner()
    summary = pruner.prune_project(project)

    assert not nm_dir.exists()
    assert summary.projects_pruned == 1
    assert summary.bytes_reclaimed == 1024
    assert summary.rebuild_scripts_created == 1
    assert summary.is_successful is True
    assert summary.errors == ()

    rebuild_script = proj_dir / "rebuild_dependencies.py"
    assert rebuild_script.exists()
    assert "npm install" in rebuild_script.read_text(encoding="utf-8")


def test_prune_single_project_python_success_class_call(tmp_path: Path) -> None:
    proj_dir = tmp_path / "py_app"
    proj_dir.mkdir()
    (proj_dir / "requirements.txt").write_text("requests==2.28.0\n", encoding="utf-8")

    venv_dir = proj_dir / ".venv"
    venv_dir.mkdir()
    (venv_dir / "pyvenv.cfg").write_text("home = /usr/bin", encoding="utf-8")

    artifact = Artifact(name=".venv", path=venv_dir, size_bytes=2048)
    project = Project(
        name="py_app",
        root_path=proj_dir,
        ecosystem=EcosystemType.PYTHON,
        artifacts=(artifact,),
    )

    summary = ProjectPruner.prune_project(project)

    assert not venv_dir.exists()
    assert summary.projects_pruned == 1
    assert summary.bytes_reclaimed == 2048
    assert summary.rebuild_scripts_created == 1
    assert summary.is_successful is True

    rebuild_script = proj_dir / "rebuild_dependencies.py"
    assert rebuild_script.exists()
    assert "requirements.txt" in rebuild_script.read_text(encoding="utf-8")


def test_prune_project_preserves_protected_files(tmp_path: Path) -> None:
    proj_dir = tmp_path / "protected_app"
    proj_dir.mkdir()
    (proj_dir / "package.json").write_text('{"name": "protected"}', encoding="utf-8")

    nm_dir = proj_dir / "node_modules"
    nm_dir.mkdir()
    (nm_dir / "dep.js").write_text("console.log('hi');", encoding="utf-8")

    readme = proj_dir / "README.md"
    readme.write_text("# Documentation", encoding="utf-8")

    notes = proj_dir / "notes.txt"
    notes.write_text("Important notes", encoding="utf-8")

    html_doc = proj_dir / "index.html"
    html_doc.write_text("<h1>Home</h1>", encoding="utf-8")

    sqlite_db = proj_dir / "data.sqlite"
    sqlite_db.write_text("SQLite format 3", encoding="utf-8")

    app_db = proj_dir / "database.db"
    app_db.write_text("db content", encoding="utf-8")

    sqlite3_db = proj_dir / "local.sqlite3"
    sqlite3_db.write_text("sqlite3 content", encoding="utf-8")

    env_file = proj_dir / ".env"
    env_file.write_text("SECRET=123", encoding="utf-8")

    env_prod = proj_dir / ".env.production"
    env_prod.write_text("SECRET=prod", encoding="utf-8")

    git_dir = proj_dir / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text("[core]", encoding="utf-8")

    cleanable_artifact = Artifact(name="node_modules", path=nm_dir, size_bytes=512)

    fake_protected_artifact = object.__new__(Artifact)
    object.__setattr__(fake_protected_artifact, "name", "readme")
    object.__setattr__(fake_protected_artifact, "path", readme)
    object.__setattr__(fake_protected_artifact, "size_bytes", 100)
    object.__setattr__(fake_protected_artifact, "rebuild_command", None)
    object.__setattr__(fake_protected_artifact, "is_untracked", False)

    fake_env_artifact = object.__new__(Artifact)
    object.__setattr__(fake_env_artifact, "name", ".env")
    object.__setattr__(fake_env_artifact, "path", env_file)
    object.__setattr__(fake_env_artifact, "size_bytes", 50)
    object.__setattr__(fake_env_artifact, "rebuild_command", None)
    object.__setattr__(fake_env_artifact, "is_untracked", False)

    fake_git_artifact = object.__new__(Artifact)
    object.__setattr__(fake_git_artifact, "name", ".git")
    object.__setattr__(fake_git_artifact, "path", git_dir)
    object.__setattr__(fake_git_artifact, "size_bytes", 200)
    object.__setattr__(fake_git_artifact, "rebuild_command", None)
    object.__setattr__(fake_git_artifact, "is_untracked", False)

    project = Project(
        name="protected_app",
        root_path=proj_dir,
        ecosystem=EcosystemType.NODE,
        artifacts=(cleanable_artifact, fake_protected_artifact, fake_env_artifact, fake_git_artifact),
    )

    pruner = ProjectPruner()
    summary = pruner.prune_project(project)

    assert not nm_dir.exists()
    assert readme.exists()
    assert notes.exists()
    assert html_doc.exists()
    assert sqlite_db.exists()
    assert app_db.exists()
    assert sqlite3_db.exists()
    assert env_file.exists()
    assert env_prod.exists()
    assert git_dir.exists()
    assert (git_dir / "config").exists()

    assert summary.projects_pruned == 1
    assert summary.bytes_reclaimed == 512
    assert summary.rebuild_scripts_created == 1
    assert summary.is_successful is False
    assert len(summary.errors) == 3


def test_prune_untracked_files_eligible_vs_protected(tmp_path: Path) -> None:
    proj_dir = tmp_path / "untracked_app"
    proj_dir.mkdir()
    (proj_dir / "package.json").write_text('{"name": "untracked"}', encoding="utf-8")

    dist_dir = proj_dir / "dist"
    dist_dir.mkdir()
    (dist_dir / "bundle.js").write_text("console.log('bundle');", encoding="utf-8")

    notes_file = proj_dir / "untracked_notes.txt"
    notes_file.write_text("Keep this note", encoding="utf-8")

    eligible_untracked = Artifact(
        name="dist",
        path=dist_dir,
        size_bytes=300,
        is_untracked=True,
    )

    protected_untracked = object.__new__(Artifact)
    object.__setattr__(protected_untracked, "name", "untracked_notes.txt")
    object.__setattr__(protected_untracked, "path", notes_file)
    object.__setattr__(protected_untracked, "size_bytes", 100)
    object.__setattr__(protected_untracked, "rebuild_command", None)
    object.__setattr__(protected_untracked, "is_untracked", True)

    project = Project(
        name="untracked_app",
        root_path=proj_dir,
        ecosystem=EcosystemType.NODE,
        artifacts=(eligible_untracked, protected_untracked),
    )

    pruner = ProjectPruner()
    summary = pruner.prune_project(project)

    assert not dist_dir.exists()
    assert notes_file.exists()
    assert summary.projects_pruned == 1
    assert summary.bytes_reclaimed == 300
    assert summary.is_successful is False
    assert any("Protected path" in err for err in summary.errors)


def test_prune_boundary_safety_outside_root(tmp_path: Path) -> None:
    proj_dir = tmp_path / "project_root"
    proj_dir.mkdir()
    (proj_dir / "package.json").write_text('{"name": "boundary"}', encoding="utf-8")

    outside_dir = tmp_path / "outside_project"
    outside_dir.mkdir()
    (outside_dir / "file.txt").write_text("outside data", encoding="utf-8")

    outside_artifact = Artifact(name="node_modules", path=outside_dir, size_bytes=400)

    root_artifact = object.__new__(Artifact)
    object.__setattr__(root_artifact, "name", "project_root")
    object.__setattr__(root_artifact, "path", proj_dir)
    object.__setattr__(root_artifact, "size_bytes", 500)
    object.__setattr__(root_artifact, "rebuild_command", None)
    object.__setattr__(root_artifact, "is_untracked", False)

    project = Project(
        name="boundary_project",
        root_path=proj_dir,
        ecosystem=EcosystemType.NODE,
        artifacts=(outside_artifact, root_artifact),
    )

    pruner = ProjectPruner()
    summary = pruner.prune_project(project)

    assert outside_dir.exists()
    assert proj_dir.exists()
    assert summary.projects_pruned == 0
    assert summary.bytes_reclaimed == 0
    assert summary.is_successful is False
    assert any("outside project root" in err for err in summary.errors)
    assert any("project root as artifact" in err for err in summary.errors)


def test_prune_rebuild_script_overwrite_behavior(tmp_path: Path) -> None:
    proj_dir = tmp_path / "overwrite_test"
    proj_dir.mkdir()
    (proj_dir / "package.json").write_text('{"name": "overwrite"}', encoding="utf-8")

    nm_dir = proj_dir / "node_modules"
    nm_dir.mkdir()
    (nm_dir / "test.js").write_text("code", encoding="utf-8")

    existing_rebuild = proj_dir / "rebuild_dependencies.py"
    existing_rebuild.write_text("CUSTOM_CONTENT = 123\n", encoding="utf-8")

    artifact = Artifact(name="node_modules", path=nm_dir, size_bytes=100)
    project = Project(
        name="overwrite_test",
        root_path=proj_dir,
        ecosystem=EcosystemType.NODE,
        artifacts=(artifact,),
    )

    pruner_no_overwrite = ProjectPruner(overwrite_rebuild_script=False)
    summary_no_overwrite = pruner_no_overwrite.prune_project(project)
    assert not nm_dir.exists()
    assert summary_no_overwrite.projects_pruned == 1
    assert summary_no_overwrite.rebuild_scripts_created == 0
    assert existing_rebuild.read_text(encoding="utf-8") == "CUSTOM_CONTENT = 123\n"

    nm_dir.mkdir()
    (nm_dir / "test.js").write_text("code", encoding="utf-8")

    pruner_overwrite = ProjectPruner(overwrite_rebuild_script=True)
    summary_overwrite = pruner_overwrite.prune_project(project)
    assert not nm_dir.exists()
    assert summary_overwrite.projects_pruned == 1
    assert summary_overwrite.rebuild_scripts_created == 1
    assert "npm install" in existing_rebuild.read_text(encoding="utf-8")


def test_prune_multiple_projects_success(tmp_path: Path) -> None:
    proj1 = tmp_path / "proj1"
    proj1.mkdir()
    (proj1 / "package.json").write_text('{"name": "p1"}', encoding="utf-8")
    p1_nm = proj1 / "node_modules"
    p1_nm.mkdir()
    (p1_nm / "mod.js").write_text("mod", encoding="utf-8")

    proj2 = tmp_path / "proj2"
    proj2.mkdir()
    (proj2 / "requirements.txt").write_text("flake8\n", encoding="utf-8")
    p2_venv = proj2 / ".venv"
    p2_venv.mkdir()
    (p2_venv / "cfg.txt").write_text("cfg", encoding="utf-8")

    project1 = Project(
        name="proj1",
        root_path=proj1,
        ecosystem=EcosystemType.NODE,
        artifacts=(Artifact(name="node_modules", path=p1_nm, size_bytes=1000),),
    )
    project2 = Project(
        name="proj2",
        root_path=proj2,
        ecosystem=EcosystemType.PYTHON,
        artifacts=(Artifact(name=".venv", path=p2_venv, size_bytes=2000),),
    )

    pruner = ProjectPruner()
    summary = pruner.prune_multiple_projects([project1, project2])

    assert not p1_nm.exists()
    assert not p2_venv.exists()
    assert summary.projects_pruned == 2
    assert summary.bytes_reclaimed == 3000
    assert summary.rebuild_scripts_created == 2
    assert summary.is_successful is True
    assert summary.errors == ()
    assert (proj1 / "rebuild_dependencies.py").exists()
    assert (proj2 / "rebuild_dependencies.py").exists()

    summary_class = ProjectPruner.prune_multiple_projects([project1, project2])
    assert summary_class.is_successful is True


def test_prune_multiple_projects_invalid_collections(tmp_path: Path) -> None:
    pruner = ProjectPruner()

    summary_none = pruner.prune_multiple_projects(None)
    assert summary_none.projects_pruned == 0
    assert summary_none.is_successful is False
    assert "Invalid projects collection" in summary_none.errors[0]

    summary_non_seq = pruner.prune_multiple_projects(123)
    assert summary_non_seq.projects_pruned == 0
    assert summary_non_seq.is_successful is False

    summary_empty = pruner.prune_multiple_projects([])
    assert summary_empty.projects_pruned == 0
    assert summary_empty.bytes_reclaimed == 0
    assert summary_empty.rebuild_scripts_created == 0
    assert summary_empty.is_successful is True

    valid_dir = tmp_path / "valid_dir"
    valid_dir.mkdir()
    (valid_dir / "package.json").write_text('{"name": "valid"}', encoding="utf-8")
    valid_nm = valid_dir / "node_modules"
    valid_nm.mkdir()
    (valid_nm / "file.js").write_text("code", encoding="utf-8")
    valid_proj = Project(
        name="valid",
        root_path=valid_dir,
        artifacts=(Artifact(name="node_modules", path=valid_nm, size_bytes=100),),
    )

    summary_mixed = pruner.prune_multiple_projects([valid_proj, "invalid_item"])
    assert summary_mixed.projects_pruned == 1
    assert summary_mixed.bytes_reclaimed == 100
    assert summary_mixed.is_successful is False
    assert len(summary_mixed.errors) == 1
    assert "Invalid project provided" in summary_mixed.errors[0]


def test_prune_project_safe_remove_failure_handling(tmp_path: Path) -> None:
    proj_dir = tmp_path / "failure_proj"
    proj_dir.mkdir()
    (proj_dir / "package.json").write_text('{"name": "fail"}', encoding="utf-8")
    nm_dir = proj_dir / "node_modules"
    nm_dir.mkdir()
    (nm_dir / "x.js").write_text("x", encoding="utf-8")

    project = Project(
        name="failure_proj",
        root_path=proj_dir,
        artifacts=(Artifact(name="node_modules", path=nm_dir, size_bytes=500),),
    )

    pruner = ProjectPruner()
    with patch("dev_local_artifact_pruner.core.pruner.safe_remove_tree", return_value=False):
        summary = pruner.prune_project(project)

    assert summary.projects_pruned == 0
    assert summary.bytes_reclaimed == 0
    assert summary.rebuild_scripts_created == 0
    assert summary.is_successful is False
    assert any("Failed to remove artifact" in err for err in summary.errors)


def test_prune_project_disk_measurement_fallback(tmp_path: Path) -> None:
    proj_dir = tmp_path / "fallback_size"
    proj_dir.mkdir()
    (proj_dir / "package.json").write_text('{"name": "fallback"}', encoding="utf-8")

    nm_dir = proj_dir / "node_modules"
    nm_dir.mkdir()
    payload = b"A" * 2048
    (nm_dir / "big.bin").write_bytes(payload)

    artifact = Artifact(name="node_modules", path=nm_dir, size_bytes=0)
    project = Project(
        name="fallback_size",
        root_path=proj_dir,
        artifacts=(artifact,),
    )

    pruner = ProjectPruner()
    summary = pruner.prune_project(project)

    assert not nm_dir.exists()
    assert summary.projects_pruned == 1
    assert summary.bytes_reclaimed == 2048
    assert summary.is_successful is True


def test_prune_project_invocation_styles(tmp_path: Path) -> None:
    pruner = ProjectPruner()

    p1_dir = tmp_path / "p1"
    p1_dir.mkdir()
    (p1_dir / "package.json").write_text('{"name": "p1"}', encoding="utf-8")
    p1_nm = p1_dir / "node_modules"
    p1_nm.mkdir()
    (p1_nm / "a.js").write_text("a", encoding="utf-8")
    proj1 = Project(name="p1", root_path=p1_dir, artifacts=(Artifact(name="node_modules", path=p1_nm, size_bytes=10),))

    s1 = pruner.prune_project(project=proj1)
    assert s1.projects_pruned == 1

    p2_dir = tmp_path / "p2"
    p2_dir.mkdir()
    (p2_dir / "package.json").write_text('{"name": "p2"}', encoding="utf-8")
    p2_nm = p2_dir / "node_modules"
    p2_nm.mkdir()
    (p2_nm / "b.js").write_text("b", encoding="utf-8")
    proj2 = Project(name="p2", root_path=p2_dir, artifacts=(Artifact(name="node_modules", path=p2_nm, size_bytes=10),))

    s2 = ProjectPruner.prune_project(project=proj2)
    assert s2.projects_pruned == 1

    p3_dir = tmp_path / "p3"
    p3_dir.mkdir()
    (p3_dir / "package.json").write_text('{"name": "p3"}', encoding="utf-8")
    p3_nm = p3_dir / "node_modules"
    p3_nm.mkdir()
    (p3_nm / "c.js").write_text("c", encoding="utf-8")
    proj3 = Project(name="p3", root_path=p3_dir, artifacts=(Artifact(name="node_modules", path=p3_nm, size_bytes=10),))

    s3 = ProjectPruner.prune_multiple_projects(projects=[proj3])
    assert s3.projects_pruned == 1

    p4_dir = tmp_path / "p4"
    p4_dir.mkdir()
    (p4_dir / "package.json").write_text('{"name": "p4"}', encoding="utf-8")
    p4_nm = p4_dir / "node_modules"
    p4_nm.mkdir()
    (p4_nm / "d.js").write_text("d", encoding="utf-8")
    proj4 = Project(name="p4", root_path=p4_dir, artifacts=(Artifact(name="node_modules", path=p4_nm, size_bytes=10),))

    s4 = ProjectPruner.prune_project(pruner, proj4)
    assert s4.projects_pruned == 1

    p5_dir = tmp_path / "p5"
    p5_dir.mkdir()
    (p5_dir / "package.json").write_text('{"name": "p5"}', encoding="utf-8")
    p5_nm = p5_dir / "node_modules"
    p5_nm.mkdir()
    (p5_nm / "e.js").write_text("e", encoding="utf-8")
    proj5 = Project(name="p5", root_path=p5_dir, artifacts=(Artifact(name="node_modules", path=p5_nm, size_bytes=10),))

    s5 = ProjectPruner.prune_multiple_projects(pruner, [proj5])
    assert s5.projects_pruned == 1


def test_prune_project_without_manifest_creates_no_rebuild_script(tmp_path: Path) -> None:
    proj_dir = tmp_path / "unknown_project"
    proj_dir.mkdir()
    nm_dir = proj_dir / "node_modules"
    nm_dir.mkdir()
    (nm_dir / "lib.js").write_text("lib", encoding="utf-8")

    project = Project(
        name="unknown_project",
        root_path=proj_dir,
        ecosystem=EcosystemType.UNKNOWN,
        artifacts=(Artifact(name="node_modules", path=nm_dir, size_bytes=100),),
    )

    pruner = ProjectPruner()
    summary = pruner.prune_project(project)

    assert not nm_dir.exists()
    assert summary.projects_pruned == 1
    assert summary.bytes_reclaimed == 100
    assert summary.rebuild_scripts_created == 0
    assert summary.is_successful is True
    assert not (proj_dir / "rebuild_dependencies.py").exists()


def test_prune_project_rejects_non_cleanable_tracked_files(tmp_path: Path) -> None:
    proj_dir = tmp_path / "source_app"
    proj_dir.mkdir()
    (proj_dir / "package.json").write_text('{"name": "source"}', encoding="utf-8")

    src_file = proj_dir / "app.js"
    src_file.write_text("const a = 1;", encoding="utf-8")

    neutral_artifact = object.__new__(Artifact)
    object.__setattr__(neutral_artifact, "name", "app.js")
    object.__setattr__(neutral_artifact, "path", src_file)
    object.__setattr__(neutral_artifact, "size_bytes", 50)
    object.__setattr__(neutral_artifact, "rebuild_command", None)
    object.__setattr__(neutral_artifact, "is_untracked", False)

    project = Project(
        name="source_app",
        root_path=proj_dir,
        artifacts=(neutral_artifact,),
    )

    pruner = ProjectPruner()
    summary = pruner.prune_project(project)

    assert src_file.exists()
    assert summary.projects_pruned == 0
    assert summary.bytes_reclaimed == 0
    assert summary.is_successful is False
    assert any("neither cleanable nor untracked" in err for err in summary.errors)


def test_prune_project_invalid_artifact_item(tmp_path: Path) -> None:
    proj_dir = tmp_path / "bad_item_app"
    proj_dir.mkdir()
    (proj_dir / "package.json").write_text('{"name": "bad"}', encoding="utf-8")

    project = Project(
        name="bad_item_app",
        root_path=proj_dir,
        artifacts=("not an artifact instance",),  # type: ignore[arg-type]
    )

    pruner = ProjectPruner()
    summary = pruner.prune_project(project)

    assert summary.projects_pruned == 0
    assert summary.is_successful is False
    assert any("Invalid artifact instance" in err for err in summary.errors)


def test_prune_project_path_resolution_exception(tmp_path: Path) -> None:
    proj_dir = tmp_path / "exc_app"
    proj_dir.mkdir()
    (proj_dir / "package.json").write_text('{"name": "exc"}', encoding="utf-8")
    nm_dir = proj_dir / "node_modules"
    nm_dir.mkdir()

    artifact = Artifact(name="node_modules", path=nm_dir, size_bytes=10)
    project = Project(
        name="exc_app",
        root_path=proj_dir,
        artifacts=(artifact,),
    )

    pruner = ProjectPruner()
    original_abspath = os.path.abspath

    def failing_abspath(path: Any) -> str:
        if "node_modules" in str(path):
            raise OSError("Simulated path error")
        return original_abspath(path)

    with patch("os.path.abspath", side_effect=failing_abspath):
        summary = pruner.prune_project(project)

    assert summary.projects_pruned == 0
    assert summary.is_successful is False
    assert any("Failed to resolve artifact path" in err for err in summary.errors)
