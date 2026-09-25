from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
import pytest

from dev_local_artifact_pruner.core import (
    EcosystemType,
    GitClient,
    GitInfo,
    Project,
    ProjectScanner,
)
from dev_local_artifact_pruner.core.scanner import (
    NODE_MANIFESTS,
    PYTHON_MANIFESTS,
)


@pytest.fixture
def git_repo_factory(tmp_path):
    def _create_git_repo(repo_name="my-repo"):
        repo_dir = tmp_path / repo_name
        repo_dir.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "init"], cwd=str(repo_dir), check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Tester"], cwd=str(repo_dir), check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "tester@example.com"], cwd=str(repo_dir), check=True, capture_output=True)
        return repo_dir

    return _create_git_repo


def test_scanner_reexport():
    scanner = ProjectScanner()
    assert isinstance(scanner, ProjectScanner)
    assert isinstance(scanner.git_client, GitClient)


def test_scanner_custom_git_client():
    custom_client = GitClient(timeout=10.0)
    scanner = ProjectScanner(git_client=custom_client)
    assert scanner.git_client is custom_client


def test_detect_ecosystem_node(tmp_path):
    node_dir = tmp_path / "node_app"
    node_dir.mkdir()
    (node_dir / "package.json").write_text('{"name": "test"}', encoding="utf-8")
    assert ProjectScanner.detect_ecosystem(node_dir) == EcosystemType.NODE


def test_detect_ecosystem_node_case_insensitive(tmp_path):
    node_dir = tmp_path / "node_app_case"
    node_dir.mkdir()
    (node_dir / "PACKAGE.JSON").write_text('{"name": "test"}', encoding="utf-8")
    assert ProjectScanner.detect_ecosystem(node_dir) == EcosystemType.NODE


@pytest.mark.parametrize(
    "manifest_name",
    [
        "pyproject.toml",
        "requirements.txt",
        "Pipfile",
        "setup.py",
        "manage.py",
    ],
)
def test_detect_ecosystem_python(tmp_path, manifest_name):
    py_dir = tmp_path / f"py_{manifest_name.replace('.', '_')}"
    py_dir.mkdir()
    (py_dir / manifest_name).write_text("# config", encoding="utf-8")
    assert ProjectScanner.detect_ecosystem(py_dir) == EcosystemType.PYTHON


def test_detect_ecosystem_unknown(tmp_path):
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    assert ProjectScanner.detect_ecosystem(empty_dir) == EcosystemType.UNKNOWN

    doc_dir = tmp_path / "doc"
    doc_dir.mkdir()
    (doc_dir / "README.md").write_text("# Doc", encoding="utf-8")
    assert ProjectScanner.detect_ecosystem(doc_dir) == EcosystemType.UNKNOWN


def test_detect_ecosystem_nonexistent_or_file(tmp_path):
    assert ProjectScanner.detect_ecosystem(tmp_path / "does_not_exist") == EcosystemType.UNKNOWN
    single_file = tmp_path / "file.txt"
    single_file.write_text("content", encoding="utf-8")
    assert ProjectScanner.detect_ecosystem(single_file) == EcosystemType.UNKNOWN


def test_detect_ecosystem_node_precedence(tmp_path):
    mixed_dir = tmp_path / "mixed"
    mixed_dir.mkdir()
    (mixed_dir / "package.json").write_text("{}", encoding="utf-8")
    (mixed_dir / "requirements.txt").write_text("", encoding="utf-8")
    assert ProjectScanner.detect_ecosystem(mixed_dir) == EcosystemType.NODE


def test_scan_single_project_nonexistent_or_invalid(tmp_path):
    scanner = ProjectScanner()
    assert scanner.scan_single_project(tmp_path / "not_found") is None

    single_file = tmp_path / "my_file.txt"
    single_file.write_text("abc", encoding="utf-8")
    assert scanner.scan_single_project(single_file) is None
    assert scanner.scan_single_project(None) is None


def test_scan_single_project_protected_path(tmp_path):
    scanner = ProjectScanner()
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    assert scanner.scan_single_project(git_dir) is None


def test_scan_single_project_clean_directory(tmp_path):
    clean_dir = tmp_path / "clean_proj"
    clean_dir.mkdir()
    (clean_dir / "README.md").write_text("# Clean", encoding="utf-8")

    scanner = ProjectScanner()
    project = scanner.scan_single_project(clean_dir)

    assert project is not None
    assert project.name == "clean_proj"
    assert project.root_path == clean_dir
    assert project.ecosystem == EcosystemType.UNKNOWN
    assert project.artifacts == ()
    assert project.reclaimable_bytes == 0
    assert project.git_info is not None
    assert project.git_info.is_git_repo is False


def test_scan_single_project_node_with_node_modules_and_pruning(tmp_path):
    node_proj = tmp_path / "my_node_proj"
    node_proj.mkdir()
    (node_proj / "package.json").write_text('{"name": "app"}', encoding="utf-8")

    nm = node_proj / "node_modules"
    deep_nm = nm / "lodash" / "nested" / "deep"
    deep_nm.mkdir(parents=True)
    (deep_nm / "index.js").write_text("console.log(1);", encoding="utf-8")
    (nm / "package.json").write_text("{}", encoding="utf-8")

    scanner = ProjectScanner()
    project = scanner.scan_single_project(node_proj)

    assert project is not None
    assert project.name == "my_node_proj"
    assert project.ecosystem == EcosystemType.NODE
    assert len(project.artifacts) == 1
    artifact = project.artifacts[0]
    assert artifact.name == "node_modules"
    assert artifact.path == nm
    assert artifact.size_bytes > 0
    assert artifact.is_untracked is False
    assert project.reclaimable_bytes == artifact.size_bytes
    assert project.total_size_bytes >= project.reclaimable_bytes


def test_scan_single_project_python_with_venv_and_pycache(tmp_path):
    py_proj = tmp_path / "my_py_proj"
    py_proj.mkdir()
    (py_proj / "pyproject.toml").write_text("[project]\nname='test'", encoding="utf-8")

    venv_dir = py_proj / ".venv" / "Lib"
    venv_dir.mkdir(parents=True)
    (venv_dir / "site.py").write_text("# site", encoding="utf-8")

    cache_dir = py_proj / "src" / "__pycache__"
    cache_dir.mkdir(parents=True)
    (cache_dir / "app.cpython-314.pyc").write_text("bytecode", encoding="utf-8")

    scanner = ProjectScanner()
    project = scanner.scan_single_project(py_proj)

    assert project is not None
    assert project.ecosystem == EcosystemType.PYTHON
    artifact_names = {a.name for a in project.artifacts}
    assert ".venv" in artifact_names
    assert "__pycache__" in artifact_names
    assert project.reclaimable_bytes > 0


def test_scan_single_project_inviolable_protected_paths(tmp_path):
    proj_dir = tmp_path / "protected_proj"
    proj_dir.mkdir()
    (proj_dir / "package.json").write_text("{}", encoding="utf-8")

    (proj_dir / "README.md").write_text("# Readme", encoding="utf-8")
    (proj_dir / "architecture.txt").write_text("notes", encoding="utf-8")
    (proj_dir / "index.html").write_text("<h1>Hi</h1>", encoding="utf-8")
    (proj_dir / ".env").write_text("SECRET=123", encoding="utf-8")
    (proj_dir / ".env.local").write_text("SECRET=456", encoding="utf-8")
    (proj_dir / "db.sqlite3").write_text("database", encoding="utf-8")
    (proj_dir / "app.db").write_text("database", encoding="utf-8")

    nm = proj_dir / "node_modules"
    nm.mkdir()
    (nm / "dep.js").write_text("var a = 1;", encoding="utf-8")

    scanner = ProjectScanner()
    project = scanner.scan_single_project(proj_dir)

    assert project is not None
    assert len(project.artifacts) == 1
    assert project.artifacts[0].name == "node_modules"
    for a in project.artifacts:
        assert not a.name.endswith(".md")
        assert not a.name.endswith(".txt")
        assert not a.name.endswith(".html")
        assert not a.name.startswith(".env")
        assert not a.name.endswith(".sqlite3")
        assert not a.name.endswith(".db")


def test_scan_single_project_with_git_integration(git_repo_factory):
    repo_dir = git_repo_factory("git_proj")
    (repo_dir / "pyproject.toml").write_text("[project]\nname='git_proj'", encoding="utf-8")
    subprocess.run(["git", "add", "pyproject.toml"], cwd=str(repo_dir), check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "feat: initial"], cwd=str(repo_dir), check=True, capture_output=True)

    scanner = ProjectScanner()
    project = scanner.scan_single_project(repo_dir)

    assert project is not None
    assert project.git_info is not None
    assert project.git_info.is_git_repo is True
    assert project.git_info.last_commit_message == "feat: initial"
    assert project.git_info.is_dirty is False
    assert project.git_info.days_inactive == 0


def test_scan_single_project_with_untracked_files(git_repo_factory):
    repo_dir = git_repo_factory("untracked_proj")
    (repo_dir / "pyproject.toml").write_text("[project]", encoding="utf-8")
    subprocess.run(["git", "add", "pyproject.toml"], cwd=str(repo_dir), check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "feat: base"], cwd=str(repo_dir), check=True, capture_output=True)

    venv_dir = repo_dir / ".venv"
    venv_dir.mkdir()
    (venv_dir / "venv_file.txt").write_text("data", encoding="utf-8")

    (repo_dir / "build_output.log").write_text("build log data", encoding="utf-8")
    (repo_dir / "notes.md").write_text("# Protected Untracked", encoding="utf-8")
    (repo_dir / ".env").write_text("SECRET=xyz", encoding="utf-8")

    scanner = ProjectScanner()
    project = scanner.scan_single_project(repo_dir)

    assert project is not None
    artifact_names = {a.name for a in project.artifacts}
    assert ".venv" in artifact_names
    assert "build_output.log" in artifact_names
    assert "notes.md" not in artifact_names
    assert ".env" not in artifact_names

    untracked_log = next(a for a in project.artifacts if a.name == "build_output.log")
    assert untracked_log.is_untracked is True

    venv_art = next(a for a in project.artifacts if a.name == ".venv")
    assert venv_art.is_untracked is False


def test_scan_single_project_class_level_call(tmp_path):
    proj_dir = tmp_path / "class_proj"
    proj_dir.mkdir()
    (proj_dir / "package.json").write_text("{}", encoding="utf-8")

    project = ProjectScanner.scan_single_project(proj_dir)
    assert project is not None
    assert project.name == "class_proj"
    assert project.ecosystem == EcosystemType.NODE


def test_scan_multiple_projects_nonexistent_or_empty(tmp_path):
    scanner = ProjectScanner()
    assert scanner.scan_multiple_projects(tmp_path / "missing") == []

    empty_dir = tmp_path / "empty_root"
    empty_dir.mkdir()
    assert scanner.scan_multiple_projects(empty_dir) == []


def test_scan_multiple_projects_single_project_root(tmp_path):
    single_root = tmp_path / "standalone_app"
    single_root.mkdir()
    (single_root / "package.json").write_text("{}", encoding="utf-8")

    scanner = ProjectScanner()
    projects = scanner.scan_multiple_projects(single_root)
    assert len(projects) == 1
    assert projects[0].name == "standalone_app"
    assert projects[0].ecosystem == EcosystemType.NODE


def test_scan_multiple_projects_discovery(tmp_path, git_repo_factory):
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    proj1 = workspace / "01-node-app"
    proj1.mkdir()
    (proj1 / "package.json").write_text("{}", encoding="utf-8")
    nm = proj1 / "node_modules"
    nm.mkdir()
    (nm / "mod.js").write_text("foo", encoding="utf-8")

    proj2 = workspace / "02-python-api"
    proj2.mkdir()
    (proj2 / "pyproject.toml").write_text("[project]", encoding="utf-8")
    venv = proj2 / ".venv"
    venv.mkdir()
    (venv / "cfg.cfg").write_text("bar", encoding="utf-8")

    proj3 = workspace / "03-git-repo"
    proj3.mkdir()
    subprocess.run(["git", "init"], cwd=str(proj3), check=True, capture_output=True)

    non_proj = workspace / "plain_docs"
    non_proj.mkdir()
    (non_proj / "guide.txt").write_text("text", encoding="utf-8")

    scanner = ProjectScanner()
    projects = scanner.scan_multiple_projects(workspace)

    assert len(projects) == 3
    names = [p.name for p in projects]
    assert names == ["01-node-app", "02-python-api", "03-git-repo"]

    node_p = next(p for p in projects if p.name == "01-node-app")
    assert node_p.ecosystem == EcosystemType.NODE
    assert len(node_p.artifacts) == 1

    py_p = next(p for p in projects if p.name == "02-python-api")
    assert py_p.ecosystem == EcosystemType.PYTHON
    assert len(py_p.artifacts) == 1


def test_scan_multiple_projects_nested_categories(tmp_path):
    workspace = tmp_path / "categorized_workspace"
    workspace.mkdir()

    fe_dir = workspace / "frontend"
    fe_dir.mkdir()
    web_app = fe_dir / "web-app"
    web_app.mkdir()
    (web_app / "package.json").write_text("{}", encoding="utf-8")

    be_dir = workspace / "backend"
    be_dir.mkdir()
    api_app = be_dir / "api-service"
    api_app.mkdir()
    (api_app / "pyproject.toml").write_text("[project]", encoding="utf-8")

    scanner = ProjectScanner()
    projects = scanner.scan_multiple_projects(workspace, max_depth=3)

    assert len(projects) == 2
    names = {p.name for p in projects}
    assert names == {"web-app", "api-service"}


def test_scan_multiple_projects_depth_limit(tmp_path):
    workspace = tmp_path / "deep_workspace"
    workspace.mkdir()

    deep_proj = workspace / "level1" / "level2" / "level3" / "deep_app"
    deep_proj.mkdir(parents=True)
    (deep_proj / "package.json").write_text("{}", encoding="utf-8")

    scanner = ProjectScanner()
    assert len(scanner.scan_multiple_projects(workspace, max_depth=4)) == 1
    assert len(scanner.scan_multiple_projects(workspace, max_depth=2)) == 0


def test_scan_multiple_projects_prunes_loose_dependency_dirs(tmp_path):
    workspace = tmp_path / "workspace_with_loose_deps"
    workspace.mkdir()

    loose_nm = workspace / "node_modules"
    fake_inner = loose_nm / "fake_package"
    fake_inner.mkdir(parents=True)
    (fake_inner / "package.json").write_text("{}", encoding="utf-8")

    scanner = ProjectScanner()
    projects = scanner.scan_multiple_projects(workspace)
    assert len(projects) == 0


def test_scan_multiple_projects_class_level_call(tmp_path):
    workspace = tmp_path / "class_workspace"
    workspace.mkdir()

    app = workspace / "my_app"
    app.mkdir()
    (app / "package.json").write_text("{}", encoding="utf-8")

    projects = ProjectScanner.scan_multiple_projects(workspace)
    assert len(projects) == 1
    assert projects[0].name == "my_app"


def test_scan_single_project_inactive_calculation():
    old_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
    mock_git_info = GitInfo(
        is_git_repo=True,
        last_commit_date=old_date,
        last_commit_message="old commit",
        is_dirty=False,
        days_inactive=90,
    )

    class MockGitClient(GitClient):
        def get_git_info(self, path=None):
            return mock_git_info

        def get_untracked_files(self, path=None):
            return []

    scanner = ProjectScanner(git_client=MockGitClient())
    temp_dir = Path(os.environ.get("TEMP", "/tmp")) / "temp_inactive_test"
    temp_dir.mkdir(parents=True, exist_ok=True)
    (temp_dir / "package.json").write_text("{}", encoding="utf-8")

    try:
        project = scanner.scan_single_project(temp_dir)
        assert project is not None
        assert project.is_inactive is True
    finally:
        try:
            (temp_dir / "package.json").unlink()
            temp_dir.rmdir()
        except OSError:
            pass


def test_scan_ignores_docs_scripts_and_unversioned_code(git_repo_factory):
    repo_dir = git_repo_factory("code_and_docs_proj")
    (repo_dir / "package.json").write_text('{"name": "test"}', encoding="utf-8")
    subprocess.run(["git", "add", "package.json"], cwd=str(repo_dir), check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=str(repo_dir), check=True, capture_output=True)

    # 1. Pastas docs e scripts
    docs_dir = repo_dir / "docs"
    docs_dir.mkdir()
    (docs_dir / "guide.md").write_text("# Guide", encoding="utf-8")
    scripts_dir = repo_dir / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "deploy.py").write_text("print('deploy')", encoding="utf-8")

    # 2. rebuild_dependencies.py
    (repo_dir / "rebuild_dependencies.py").write_text("# rebuild", encoding="utf-8")

    # 3. Código não versionado solto
    (repo_dir / "LoginLogo.tsx").write_text("export const Logo = () => null;", encoding="utf-8")
    (repo_dir / "index.ts").write_text("console.log('hi');", encoding="utf-8")

    # 4. Pastas contendo código não versionado
    account_dir = repo_dir / "account"
    account_dir.mkdir()
    (account_dir / "AccountScreen.tsx").write_text("export default null;", encoding="utf-8")

    # 5. Artefatos reais que DEVEM ser identificados
    nm = repo_dir / "node_modules"
    nm.mkdir()
    (nm / "dep.js").write_text("module.exports = 1;", encoding="utf-8")
    (repo_dir / "temp.log").write_text("log data", encoding="utf-8")

    scanner = ProjectScanner()
    project = scanner.scan_single_project(repo_dir)

    assert project is not None
    artifact_names = {a.name for a in project.artifacts}

    # Deve conter os artefatos reais
    assert "node_modules" in artifact_names
    assert "temp.log" in artifact_names

    # NÃO deve conter docs, scripts, rebuild_dependencies.py ou código fonte
    assert "docs" not in artifact_names
    assert "scripts" not in artifact_names
    assert "rebuild_dependencies.py" not in artifact_names
    assert "LoginLogo.tsx" not in artifact_names
    assert "index.ts" not in artifact_names
    assert "account" not in artifact_names

