from pathlib import Path
from typing import List, Sequence, Union

PROTECTED_EXTENSIONS: frozenset[str] = frozenset({
    ".md",
    ".txt",
    ".html",
    ".sqlite",
    ".db",
    ".sqlite3",
})

PROTECTED_PREFIXES: frozenset[str] = frozenset({
    ".env",
})

PROTECTED_SPECIAL_NAMES: frozenset[str] = frozenset({
    ".git",
})

CLEANABLE_ARTIFACT_NAMES: frozenset[str] = frozenset({
    "node_modules",
    "venv",
    ".venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
})

CLEANABLE_EXTENSIONS: frozenset[str] = frozenset({
    ".pyc",
    ".pyo",
})


def is_protected_path(path: Union[Path, str]) -> bool:
    if path is None:
        return True
    if not isinstance(path, Path):
        path = Path(path)
    clean_str = str(path).strip()
    if not clean_str or clean_str == ".":
        return True
    if path == Path(path.anchor):
        return True
    lower_parts = [part.lower() for part in path.parts]
    if any(part in PROTECTED_SPECIAL_NAMES for part in lower_parts):
        return True
    file_name = path.name.lower()
    if any(file_name.startswith(prefix) for prefix in PROTECTED_PREFIXES):
        return True
    if path.suffix.lower() in PROTECTED_EXTENSIONS:
        return True
    return False


def is_cleanable_artifact(path: Union[Path, str]) -> bool:
    if path is None:
        return False
    if not isinstance(path, Path):
        path = Path(path)
    if is_protected_path(path):
        return False
    if path.name.lower() in CLEANABLE_ARTIFACT_NAMES:
        return True
    if path.suffix.lower() in CLEANABLE_EXTENSIONS:
        return True
    return False


def filter_untracked_files(file_paths: Sequence[Union[Path, str]]) -> List[Path]:
    result: List[Path] = []
    for file_path in file_paths:
        if file_path is None:
            continue
        p = Path(file_path) if not isinstance(file_path, Path) else file_path
        if not str(p).strip():
            continue
        if not is_protected_path(p):
            result.append(p)
    return result


class RuleEngine:
    @staticmethod
    def is_protected_path(path: Union[Path, str]) -> bool:
        return is_protected_path(path)

    @staticmethod
    def is_cleanable_artifact(path: Union[Path, str]) -> bool:
        return is_cleanable_artifact(path)

    @staticmethod
    def filter_untracked_files(file_paths: Sequence[Union[Path, str]]) -> List[Path]:
        return filter_untracked_files(file_paths)


__all__ = [
    "CLEANABLE_ARTIFACT_NAMES",
    "CLEANABLE_EXTENSIONS",
    "PROTECTED_EXTENSIONS",
    "PROTECTED_PREFIXES",
    "PROTECTED_SPECIAL_NAMES",
    "RuleEngine",
    "filter_untracked_files",
    "is_cleanable_artifact",
    "is_protected_path",
]
