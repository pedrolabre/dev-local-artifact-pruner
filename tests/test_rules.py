from pathlib import Path
import pytest

from dev_local_artifact_pruner.core.rules import (
    CLEANABLE_ARTIFACT_NAMES,
    CLEANABLE_EXTENSIONS,
    PROTECTED_EXTENSIONS,
    PROTECTED_PREFIXES,
    PROTECTED_SPECIAL_NAMES,
    RuleEngine,
    filter_untracked_files,
    is_cleanable_artifact,
    is_protected_path,
)


@pytest.mark.parametrize(
    "filename",
    [
        "README.md",
        "notes.txt",
        "index.html",
        "data.sqlite",
        "app.db",
        "users.sqlite3",
    ],
)
def test_protected_extensions_lowercase(filename: str) -> None:
    path = Path(filename)
    assert is_protected_path(path) is True
    assert is_cleanable_artifact(path) is False


@pytest.mark.parametrize(
    "filename",
    [
        "README.MD",
        "NOTES.TXT",
        "INDEX.HTML",
        "DATA.SQLITE",
        "APP.DB",
        "USERS.SQLITE3",
        "Document.Md",
        "Log.Txt",
        "Page.Html",
    ],
)
def test_protected_extensions_case_insensitive(filename: str) -> None:
    path = Path(filename)
    assert is_protected_path(path) is True
    assert is_cleanable_artifact(path) is False


@pytest.mark.parametrize(
    "filepath",
    [
        "nested/docs/README.md",
        "deeply/nested/folder/notes.txt",
        "public/assets/index.html",
        "storage/database/app.db",
        "db/sqlite/records.sqlite3",
    ],
)
def test_protected_extensions_nested_paths(filepath: str) -> None:
    path = Path(filepath)
    assert is_protected_path(path) is True
    assert is_cleanable_artifact(path) is False


@pytest.mark.parametrize(
    "filename",
    [
        ".env",
        ".env.local",
        ".env.development",
        ".env.production",
        ".env.test",
        ".envrc",
        ".env.example",
        ".env_backup",
        ".ENV",
        ".ENV.LOCAL",
        ".Env.Production",
    ],
)
def test_protected_prefixes_env(filename: str) -> None:
    path = Path(filename)
    assert is_protected_path(path) is True
    assert is_cleanable_artifact(path) is False


@pytest.mark.parametrize(
    "filepath",
    [
        "nested/config/.env",
        "secrets/production/.env.local",
        "app/backend/.ENV",
    ],
)
def test_protected_prefixes_env_nested(filepath: str) -> None:
    path = Path(filepath)
    assert is_protected_path(path) is True
    assert is_cleanable_artifact(path) is False


@pytest.mark.parametrize(
    "filepath",
    [
        ".git",
        ".GIT",
        ".git/HEAD",
        ".git/config",
        ".git/refs/heads/main",
        ".git/objects/4b/825dc",
        "my_project/.git",
        "my_project/.git/index",
        "subfolder/repo/.GIT/config",
    ],
)
def test_protected_git_metadata(filepath: str) -> None:
    path = Path(filepath)
    assert is_protected_path(path) is True
    assert is_cleanable_artifact(path) is False


def test_protected_edge_cases() -> None:
    assert is_protected_path("") is True
    assert is_protected_path("   ") is True
    assert is_protected_path(".") is True
    assert is_protected_path(Path(".")) is True
    assert is_protected_path(Path(Path.cwd().anchor)) is True


@pytest.mark.parametrize(
    "artifact_name",
    [
        "node_modules",
        "venv",
        ".venv",
        "env",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
    ],
)
def test_cleanable_artifacts_names(artifact_name: str) -> None:
    path = Path(artifact_name)
    assert is_cleanable_artifact(path) is True
    assert is_protected_path(path) is False


@pytest.mark.parametrize(
    "artifact_name",
    [
        "NODE_MODULES",
        "VENV",
        ".VENV",
        "ENV",
        "__PYCACHE__",
        ".PYTEST_CACHE",
        ".MYPY_CACHE",
        ".RUFF_CACHE",
        "Node_Modules",
        ".Venv",
    ],
)
def test_cleanable_artifacts_names_case_insensitive(artifact_name: str) -> None:
    path = Path(artifact_name)
    assert is_cleanable_artifact(path) is True
    assert is_protected_path(path) is False


@pytest.mark.parametrize(
    "filepath",
    [
        "frontend/node_modules",
        "backend/.venv",
        "legacy/project/venv",
        "services/worker/env",
        "src/package/__pycache__",
        "tests/.pytest_cache",
        ".mypy_cache",
        "tools/.ruff_cache",
    ],
)
def test_cleanable_artifacts_nested(filepath: str) -> None:
    path = Path(filepath)
    assert is_cleanable_artifact(path) is True
    assert is_protected_path(path) is False


@pytest.mark.parametrize(
    "filename",
    [
        "module.pyc",
        "script.pyo",
        "MODULE.PYC",
        "SCRIPT.PYO",
        "compiled/app.pyc",
    ],
)
def test_cleanable_extensions(filename: str) -> None:
    path = Path(filename)
    assert is_cleanable_artifact(path) is True
    assert is_protected_path(path) is False


@pytest.mark.parametrize(
    "filepath",
    [
        "src/main.py",
        "package.json",
        "Cargo.toml",
        "styles.css",
        "script.js",
        "Dockerfile",
        "Makefile",
        "pyproject.toml",
    ],
)
def test_uncleanable_unprotected_paths(filepath: str) -> None:
    path = Path(filepath)
    assert is_protected_path(path) is False
    assert is_cleanable_artifact(path) is False


def test_protected_artifact_conflict() -> None:
    path = Path("node_modules/README.md")
    assert is_protected_path(path) is True
    assert is_cleanable_artifact(path) is False

    path_env = Path(".venv/.env")
    assert is_protected_path(path_env) is True
    assert is_cleanable_artifact(path_env) is False


def test_filter_untracked_files_mixed() -> None:
    untracked_inputs = [
        "README.md",
        "build.log",
        ".env",
        "temp.tmp",
        "data.db",
        ".git/HEAD",
        "dist_bundle.js",
        "notes.txt",
        "index.html",
        "users.sqlite",
        "debug.log",
    ]
    filtered = filter_untracked_files(untracked_inputs)

    expected = [
        Path("build.log"),
        Path("temp.tmp"),
        Path("dist_bundle.js"),
        Path("debug.log"),
    ]
    assert filtered == expected
    for item in filtered:
        assert isinstance(item, Path)


def test_filter_untracked_files_empty_and_all_protected() -> None:
    assert filter_untracked_files([]) == []
    all_protected = [".env", "README.md", "app.sqlite", ".git/config", "notes.txt"]
    assert filter_untracked_files(all_protected) == []


def test_filter_untracked_files_preserves_paths_and_ignores_blanks() -> None:
    raw_list = [Path("temp_file.log"), "", "   ", Path("extra.json")]
    filtered = filter_untracked_files(raw_list)
    assert filtered == [Path("temp_file.log"), Path("extra.json")]


def test_rule_engine_wrapper() -> None:
    assert RuleEngine.is_protected_path("README.md") is True
    assert RuleEngine.is_protected_path("node_modules") is False

    assert RuleEngine.is_cleanable_artifact("node_modules") is True
    assert RuleEngine.is_cleanable_artifact("README.md") is False

    filtered = RuleEngine.filter_untracked_files(["README.md", "temp.log"])
    assert filtered == [Path("temp.log")]


def test_collections_immutability() -> None:
    assert isinstance(PROTECTED_EXTENSIONS, frozenset)
    assert isinstance(PROTECTED_PREFIXES, frozenset)
    assert isinstance(PROTECTED_SPECIAL_NAMES, frozenset)
    assert isinstance(CLEANABLE_ARTIFACT_NAMES, frozenset)
    assert isinstance(CLEANABLE_EXTENSIONS, frozenset)

    with pytest.raises(AttributeError):
        PROTECTED_EXTENSIONS.add(".custom")  # type: ignore[attr-defined]

    with pytest.raises(AttributeError):
        PROTECTED_PREFIXES.add(".secret")  # type: ignore[attr-defined]

    with pytest.raises(AttributeError):
        CLEANABLE_ARTIFACT_NAMES.add("custom_cache")  # type: ignore[attr-defined]


def test_string_and_path_parity() -> None:
    str_path = "node_modules"
    path_obj = Path("node_modules")

    assert is_protected_path(str_path) == is_protected_path(path_obj)
    assert is_cleanable_artifact(str_path) == is_cleanable_artifact(path_obj)
