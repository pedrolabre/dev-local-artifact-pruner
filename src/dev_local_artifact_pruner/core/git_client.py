import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional, Tuple, Union

from dev_local_artifact_pruner.core.models import GitInfo

DEFAULT_GIT_TIMEOUT = 5.0


class GitClient:
    def __init__(self, timeout: float = DEFAULT_GIT_TIMEOUT) -> None:
        self.timeout = float(timeout) if timeout > 0 else DEFAULT_GIT_TIMEOUT

    @staticmethod
    def _resolve_target(
        self_or_path: Any,
        target_path: Optional[Union[Path, str]] = None,
    ) -> Tuple["GitClient", Path]:
        if isinstance(self_or_path, GitClient):
            if target_path is None:
                raise ValueError("Path is required")
            p = target_path if isinstance(target_path, Path) else Path(target_path)
            return self_or_path, p
        client = GitClient()
        p = self_or_path if isinstance(self_or_path, Path) else Path(self_or_path)
        return client, p

    def _run_git_command(
        self,
        args: List[str],
        cwd: Path,
    ) -> Optional[subprocess.CompletedProcess[str]]:
        try:
            return subprocess.run(
                ["git", "-c", "core.quotepath=false", *args],
                cwd=str(cwd),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout,
            )
        except (subprocess.SubprocessError, OSError, ValueError):
            return None

    def is_git_repository(
        self,
        path: Optional[Union[Path, str]] = None,
    ) -> bool:
        try:
            client, target_path = GitClient._resolve_target(self, path)
            if target_path.exists() and not target_path.is_dir():
                return False
            if target_path.exists() and not (target_path / ".git").exists():
                return False
            res = client._run_git_command(["rev-parse", "--is-inside-work-tree"], cwd=target_path)
            if res is None or res.returncode != 0:
                return False
            return res.stdout.strip().lower() == "true"
        except Exception:
            return False

    def get_git_info(
        self,
        path: Optional[Union[Path, str]] = None,
    ) -> GitInfo:
        try:
            client, target_path = GitClient._resolve_target(self, path)
            if not client.is_git_repository(target_path):
                return GitInfo(is_git_repo=False)

            is_dirty = False
            status_res = client._run_git_command(["status", "--porcelain"], cwd=target_path)
            if status_res is not None and status_res.returncode == 0:
                status_lines = [
                    line.rstrip("\r\n")
                    for line in status_res.stdout.splitlines()
                    if line.strip()
                ]
                is_dirty = any(
                    not line.startswith("??") and not line.startswith("!!")
                    for line in status_lines
                )

            last_commit_date: Optional[datetime] = None
            last_commit_message: Optional[str] = None
            days_inactive: Optional[int] = None

            log_res = client._run_git_command(
                ["log", "-1", "--format=%ct|%s"],
                cwd=target_path,
            )
            if log_res is not None and log_res.returncode == 0:
                raw_log = log_res.stdout.strip()
                if raw_log:
                    parts = raw_log.split("|", 1)
                    timestamp_str = parts[0].strip()
                    commit_msg = parts[1].strip() if len(parts) > 1 else ""
                    try:
                        timestamp = int(timestamp_str)
                        last_commit_date = datetime.fromtimestamp(timestamp, tz=timezone.utc)
                        now = datetime.now(timezone.utc)
                        days_inactive = max(0, (now - last_commit_date).days)
                        last_commit_message = commit_msg
                    except (ValueError, OverflowError, OSError):
                        last_commit_date = None
                        last_commit_message = None
                        days_inactive = None

            return GitInfo(
                is_git_repo=True,
                last_commit_date=last_commit_date,
                last_commit_message=last_commit_message,
                is_dirty=is_dirty,
                days_inactive=days_inactive,
            )
        except Exception:
            return GitInfo(is_git_repo=False)

    def get_untracked_files(
        self,
        path: Optional[Union[Path, str]] = None,
    ) -> List[Path]:
        try:
            client, target_path = GitClient._resolve_target(self, path)
            if not client.is_git_repository(target_path):
                return []

            res = client._run_git_command(["status", "--porcelain"], cwd=target_path)
            if res is None or res.returncode != 0:
                return []

            untracked: List[Path] = []
            for raw_line in res.stdout.splitlines():
                line = raw_line.rstrip("\r\n")
                if line.startswith("?? "):
                    rel_candidate = line[3:].strip()
                    if (
                        rel_candidate.startswith('"')
                        and rel_candidate.endswith('"')
                        and len(rel_candidate) >= 2
                    ):
                        rel_candidate = rel_candidate[1:-1]
                    if rel_candidate:
                        untracked.append(target_path / rel_candidate)

            return untracked
        except Exception:
            return []


__all__ = [
    "DEFAULT_GIT_TIMEOUT",
    "GitClient",
]
