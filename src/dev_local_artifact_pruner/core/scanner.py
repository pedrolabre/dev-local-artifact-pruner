from collections import deque
import os
from pathlib import Path
from typing import Any, List, Optional, Set, Tuple, Union

from dev_local_artifact_pruner.core.git_client import GitClient
from dev_local_artifact_pruner.core.models import (
    Artifact,
    EcosystemType,
    GitInfo,
    Project,
)
from dev_local_artifact_pruner.core.rules import (
    CLEANABLE_ARTIFACT_NAMES,
    RuleEngine,
    filter_untracked_files,
    is_cleanable_artifact,
    is_protected_path,
)
from dev_local_artifact_pruner.utils.disk_usage import get_directory_size_bytes

NODE_MANIFESTS: frozenset[str] = frozenset({
    "package.json",
})

PYTHON_MANIFESTS: frozenset[str] = frozenset({
    "pyproject.toml",
    "requirements.txt",
    "Pipfile",
    "setup.py",
    "manage.py",
})

CODE_AND_CONFIG_EXTENSIONS: frozenset[str] = frozenset({
    ".py", ".pyw", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs",
    ".vue", ".svelte", ".c", ".h", ".cpp", ".hpp", ".cc", ".cxx",
    ".cs", ".go", ".rs", ".java", ".kt", ".kts", ".swift", ".rb",
    ".php", ".dart", ".scala", ".sql", ".graphql", ".gql", ".proto",
    ".sh", ".bash", ".zsh", ".bat", ".ps1", ".cmd", ".lua", ".r",
    ".css", ".scss", ".sass", ".less", ".xml", ".svg",
    ".json", ".json5", ".jsonc", ".yaml", ".yml", ".toml", ".ini",
    ".cfg", ".conf", ".lock",
})

CODE_DIR_NAMES: frozenset[str] = frozenset({
    "src", "lib", "app", "components", "pages", "utils", "services",
    "hooks", "models", "tests", "test", "__tests__", "docs", "doc",
    "documentation", "scripts", "script", "assets", "data", "views",
    "controllers", "routes", "api", "config", "modules", "packages",
})


def _contains_unversioned_code(directory: Path) -> bool:
    if directory.name.lower() in CODE_DIR_NAMES:
        return True
    try:
        for root, dirs, files in os.walk(directory):
            dirs[:] = [d for d in dirs if d.lower() not in CLEANABLE_ARTIFACT_NAMES]
            for f in files:
                ext = Path(f).suffix.lower()
                if ext in CODE_AND_CONFIG_EXTENSIONS or is_protected_path(Path(root) / f):
                    return True
    except (OSError, PermissionError):
        return True
    return False


def _is_code_or_config_file(file_path: Path) -> bool:
    ext = file_path.suffix.lower()
    if ext in CODE_AND_CONFIG_EXTENSIONS:
        return True
    if file_path.name.lower() in ("dockerfile", "makefile", "procfile", "gemfile"):
        return True
    return False



class ProjectScanner:
    def __init__(self, git_client: Optional[GitClient] = None) -> None:
        self.git_client = git_client if git_client is not None else GitClient()

    @staticmethod
    def detect_ecosystem(project_path: Union[Path, str]) -> EcosystemType:
        try:
            p = Path(project_path) if not isinstance(project_path, Path) else project_path
            if not p.exists() or not p.is_dir():
                return EcosystemType.UNKNOWN
            with os.scandir(p) as entries:
                file_names = {entry.name.lower() for entry in entries if entry.is_file()}
            if any(m.lower() in file_names for m in NODE_MANIFESTS):
                return EcosystemType.NODE
            if any(m.lower() in file_names for m in PYTHON_MANIFESTS):
                return EcosystemType.PYTHON
        except (PermissionError, OSError):
            return EcosystemType.UNKNOWN
        return EcosystemType.UNKNOWN

    def _is_project_dir(self, path: Path) -> bool:
        try:
            if not path.is_dir() or path.is_symlink():
                return False
            if is_protected_path(path) or path.name.lower() in CLEANABLE_ARTIFACT_NAMES:
                return False
            if (path / ".git").exists() or self.git_client.is_git_repository(path):
                return True
            with os.scandir(path) as entries:
                for entry in entries:
                    if entry.is_file():
                        name_lower = entry.name.lower()
                        if (
                            name_lower in NODE_MANIFESTS
                            or name_lower in PYTHON_MANIFESTS
                        ):
                            return True
        except (PermissionError, OSError):
            return False
        return False

    def _discover_artifacts(self, target_path: Path, git_info: GitInfo) -> List[Artifact]:
        discovered: List[Artifact] = []
        artifact_paths: Set[Path] = set()
        stack: List[Tuple[Path, int]] = [(target_path, 0)]

        while stack:
            current_dir, depth = stack.pop()
            if depth > 10:
                continue
            try:
                with os.scandir(current_dir) as entries:
                    for entry in entries:
                        try:
                            if entry.is_symlink():
                                continue
                            entry_path = Path(entry.path)
                            if is_protected_path(entry_path):
                                continue

                            if entry.is_dir(follow_symlinks=False):
                                if is_cleanable_artifact(entry_path):
                                    size = get_directory_size_bytes(entry_path)
                                    art = Artifact(
                                        name=entry.name,
                                        path=entry_path,
                                        size_bytes=size,
                                        is_untracked=False,
                                    )
                                    discovered.append(art)
                                    artifact_paths.add(entry_path)
                                else:
                                    stack.append((entry_path, depth + 1))
                            else:
                                if is_cleanable_artifact(entry_path):
                                    size = get_directory_size_bytes(entry_path)
                                    art = Artifact(
                                        name=entry.name,
                                        path=entry_path,
                                        size_bytes=size,
                                        is_untracked=False,
                                    )
                                    discovered.append(art)
                                    artifact_paths.add(entry_path)
                        except (PermissionError, FileNotFoundError, OSError):
                            continue
            except (PermissionError, FileNotFoundError, OSError):
                continue

        if git_info.is_git_repo:
            raw_untracked = self.git_client.get_untracked_files(target_path)
            eligible_untracked = filter_untracked_files(raw_untracked)
            for u_path in eligible_untracked:
                if u_path in artifact_paths:
                    continue
                if any(parent in artifact_paths for parent in u_path.parents):
                    continue
                try:
                    if not u_path.exists():
                        continue
                    if is_protected_path(u_path):
                        continue
                    if u_path.is_dir():
                        if not is_cleanable_artifact(u_path) and _contains_unversioned_code(u_path):
                            continue
                    else:
                        if _is_code_or_config_file(u_path) and not is_cleanable_artifact(u_path):
                            continue

                    u_size = get_directory_size_bytes(u_path)
                    art = Artifact(
                        name=u_path.name,
                        path=u_path,
                        size_bytes=u_size,
                        is_untracked=True,
                    )
                    discovered.append(art)
                    artifact_paths.add(u_path)
                except (PermissionError, FileNotFoundError, OSError):
                    continue

        discovered.sort(key=lambda a: str(a.path))
        return discovered

    def scan_single_project(
        self,
        project_path: Optional[Union[Path, str]] = None,
    ) -> Optional[Project]:
        try:
            if isinstance(self, ProjectScanner):
                if project_path is None:
                    return None
                scanner = self
                target = project_path if isinstance(project_path, Path) else Path(project_path)
            else:
                scanner = ProjectScanner()
                target = self if isinstance(self, Path) else Path(self)

            if not target.exists() or not target.is_dir() or is_protected_path(target):
                return None

            name = target.name or str(target)
            ecosystem = scanner.detect_ecosystem(target)
            git_info = scanner.git_client.get_git_info(target)
            artifacts = scanner._discover_artifacts(target, git_info)
            total_size = get_directory_size_bytes(target)

            return Project(
                name=name,
                root_path=target,
                ecosystem=ecosystem,
                git_info=git_info,
                artifacts=tuple(artifacts),
                total_size_bytes=total_size,
            )
        except Exception:
            return None

    def scan_multiple_projects(
        self,
        root_path: Optional[Union[Path, str]] = None,
        max_depth: int = 4,
    ) -> List[Project]:
        try:
            if isinstance(self, ProjectScanner):
                if root_path is None:
                    return []
                scanner = self
                target_root = root_path if isinstance(root_path, Path) else Path(root_path)
                depth_limit = max_depth
            else:
                scanner = ProjectScanner()
                target_root = self if isinstance(self, Path) else Path(self)
                depth_limit = int(root_path) if isinstance(root_path, int) else max_depth

            if not target_root.exists() or not target_root.is_dir() or is_protected_path(target_root):
                return []

            discovered_projects: List[Project] = []
            queue: deque[Tuple[Path, int]] = deque([(target_root, 0)])

            while queue:
                current_dir, current_depth = queue.popleft()
                if current_depth > depth_limit:
                    continue

                try:
                    with os.scandir(current_dir) as entries:
                        subdirs: List[Path] = []
                        for entry in entries:
                            try:
                                if entry.is_symlink():
                                    continue
                                if not entry.is_dir(follow_symlinks=False):
                                    continue
                                entry_path = Path(entry.path)
                                if is_protected_path(entry_path):
                                    continue
                                if entry.name.lower() in CLEANABLE_ARTIFACT_NAMES:
                                    continue
                                subdirs.append(entry_path)
                            except (PermissionError, FileNotFoundError, OSError):
                                continue
                except (PermissionError, FileNotFoundError, OSError):
                    continue

                for subdir in subdirs:
                    if scanner._is_project_dir(subdir):
                        proj = scanner.scan_single_project(subdir)
                        if proj is not None:
                            discovered_projects.append(proj)
                    else:
                        if current_depth + 1 <= depth_limit:
                            queue.append((subdir, current_depth + 1))

            if not discovered_projects and scanner._is_project_dir(target_root):
                root_proj = scanner.scan_single_project(target_root)
                if root_proj is not None:
                    discovered_projects.append(root_proj)

            discovered_projects.sort(key=lambda p: str(p.root_path))
            return discovered_projects
        except Exception:
            return []


__all__ = [
    "NODE_MANIFESTS",
    "PYTHON_MANIFESTS",
    "ProjectScanner",
]
