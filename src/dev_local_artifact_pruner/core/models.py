from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Tuple

PROTECTED_EXTENSIONS = {".md", ".txt", ".html", ".sqlite", ".db", ".sqlite3"}


class EcosystemType(Enum):
    NODE = "node"
    PYTHON = "python"
    UNKNOWN = "unknown"


class ActionState(Enum):
    INITIAL = "initial"
    ANALYZING = "analyzing"
    ANALYZED = "analyzed"
    PRUNING_REQUESTED = "pruning_requested"
    PRUNING = "pruning"
    COMPLETED = "completed"


@dataclass(frozen=True)
class Artifact:
    name: str
    path: Path
    size_bytes: int = 0
    rebuild_command: Optional[str] = None
    is_untracked: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.path, Path):
            object.__setattr__(self, "path", Path(self.path))
        if self.size_bytes < 0:
            raise ValueError(f"Artifact size_bytes cannot be negative: {self.size_bytes}")
        file_name = self.path.name.lower()
        suffix = self.path.suffix.lower()
        if (
            suffix in PROTECTED_EXTENSIONS
            or file_name.startswith(".env")
            or file_name == ".git"
            or ".git" in self.path.parts
        ):
            raise ValueError(f"Protected path cannot be instantiated as Artifact: {self.path}")


@dataclass(frozen=True)
class GitInfo:
    is_git_repo: bool = False
    last_commit_date: Optional[datetime] = None
    last_commit_message: Optional[str] = None
    is_dirty: bool = False
    days_inactive: Optional[int] = None

    def __post_init__(self) -> None:
        if self.days_inactive is not None and self.days_inactive < 0:
            raise ValueError(f"days_inactive cannot be negative: {self.days_inactive}")


@dataclass(frozen=True)
class Project:
    name: str
    root_path: Path
    ecosystem: EcosystemType = EcosystemType.UNKNOWN
    git_info: Optional[GitInfo] = None
    artifacts: Tuple[Artifact, ...] = ()
    total_size_bytes: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.root_path, Path):
            object.__setattr__(self, "root_path", Path(self.root_path))
        if not isinstance(self.artifacts, tuple):
            object.__setattr__(self, "artifacts", tuple(self.artifacts))
        if self.total_size_bytes < 0:
            raise ValueError(f"total_size_bytes cannot be negative: {self.total_size_bytes}")

    @property
    def is_inactive(self) -> bool:
        if self.git_info is None or not self.git_info.is_git_repo:
            return False
        if self.git_info.days_inactive is None:
            return False
        return self.git_info.days_inactive >= 60 and not self.git_info.is_dirty

    @property
    def reclaimable_bytes(self) -> int:
        return sum(artifact.size_bytes for artifact in self.artifacts)


@dataclass(frozen=True)
class PruneSummary:
    projects_pruned: int = 0
    bytes_reclaimed: int = 0
    rebuild_scripts_created: int = 0
    errors: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.errors, tuple):
            object.__setattr__(self, "errors", tuple(self.errors))
        if self.projects_pruned < 0:
            raise ValueError(f"projects_pruned cannot be negative: {self.projects_pruned}")
        if self.bytes_reclaimed < 0:
            raise ValueError(f"bytes_reclaimed cannot be negative: {self.bytes_reclaimed}")
        if self.rebuild_scripts_created < 0:
            raise ValueError(f"rebuild_scripts_created cannot be negative: {self.rebuild_scripts_created}")

    @property
    def is_successful(self) -> bool:
        return len(self.errors) == 0
