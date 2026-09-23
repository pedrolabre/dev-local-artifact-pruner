import os
from pathlib import Path
from typing import Any, List, Optional, Sequence, Union

from dev_local_artifact_pruner.core.models import (
    PROTECTED_EXTENSIONS,
    Artifact,
    Project,
    PruneSummary,
)
from dev_local_artifact_pruner.core.rebuilder import RebuildScriptGenerator
from dev_local_artifact_pruner.core.rules import is_cleanable_artifact, is_protected_path
from dev_local_artifact_pruner.utils.disk_usage import get_directory_size_bytes
from dev_local_artifact_pruner.utils.safe_delete import safe_remove_tree


class ProjectPruner:
    def __init__(self, overwrite_rebuild_script: bool = True) -> None:
        self.overwrite_rebuild_script = overwrite_rebuild_script

    def _prune_single_project(
        self,
        project: Optional[Project],
        overwrite_rebuild_script: bool,
    ) -> PruneSummary:
        if project is None or not isinstance(project, Project):
            return PruneSummary(
                projects_pruned=0,
                bytes_reclaimed=0,
                rebuild_scripts_created=0,
                errors=("Invalid project provided",),
            )

        root_path = project.root_path if isinstance(project.root_path, Path) else Path(project.root_path)

        if is_protected_path(root_path):
            return PruneSummary(
                projects_pruned=0,
                bytes_reclaimed=0,
                rebuild_scripts_created=0,
                errors=(f"Project root path is protected: {root_path}",),
            )

        if not root_path.exists() or not root_path.is_dir():
            return PruneSummary(
                projects_pruned=0,
                bytes_reclaimed=0,
                rebuild_scripts_created=0,
                errors=(f"Project root path does not exist or is not a directory: {root_path}",),
            )

        if not project.artifacts:
            return PruneSummary(
                projects_pruned=0,
                bytes_reclaimed=0,
                rebuild_scripts_created=0,
                errors=(),
            )

        errors: List[str] = []
        bytes_reclaimed = 0
        artifacts_removed = 0
        abs_root = Path(os.path.abspath(root_path))

        for artifact in project.artifacts:
            if not isinstance(artifact, Artifact):
                errors.append(f"Invalid artifact instance: {artifact}")
                continue

            artifact_path = artifact.path if isinstance(artifact.path, Path) else Path(artifact.path)

            if is_protected_path(artifact_path):
                errors.append(f"Protected path cannot be removed: {artifact_path}")
                continue

            file_name = artifact_path.name.lower()
            suffix = artifact_path.suffix.lower()
            if (
                suffix in PROTECTED_EXTENSIONS
                or file_name.startswith(".env")
                or file_name == ".git"
                or ".git" in artifact_path.parts
                or file_name == "rebuild_dependencies.py"
            ):
                errors.append(f"Protected path cannot be removed: {artifact_path}")
                continue

            try:
                abs_artifact = Path(os.path.abspath(artifact_path))
                if abs_artifact == abs_root:
                    errors.append(f"Cannot prune project root as artifact: {artifact_path}")
                    continue
                if abs_artifact == Path(abs_artifact.anchor) or abs_artifact in abs_root.parents:
                    errors.append(f"Cannot prune root filesystem or parent path: {artifact_path}")
                    continue
                if abs_root not in abs_artifact.parents:
                    errors.append(f"Artifact path is outside project root: {artifact_path}")
                    continue
            except Exception:
                errors.append(f"Failed to resolve artifact path: {artifact_path}")
                continue

            if not is_cleanable_artifact(artifact_path) and not artifact.is_untracked:
                errors.append(f"Artifact is neither cleanable nor untracked: {artifact_path}")
                continue

            size = artifact.size_bytes
            if size <= 0 and abs_artifact.exists():
                size = get_directory_size_bytes(abs_artifact)

            if safe_remove_tree(abs_artifact):
                bytes_reclaimed += size
                artifacts_removed += 1
            else:
                errors.append(f"Failed to remove artifact: {artifact_path}")

        projects_pruned = 0
        rebuild_scripts_created = 0

        if artifacts_removed > 0:
            projects_pruned = 1
            rebuild_path = RebuildScriptGenerator.generate_rebuild_script(
                root_path,
                overwrite=overwrite_rebuild_script,
            )
            if rebuild_path is not None and rebuild_path.exists():
                rebuild_scripts_created = 1

        return PruneSummary(
            projects_pruned=projects_pruned,
            bytes_reclaimed=bytes_reclaimed,
            rebuild_scripts_created=rebuild_scripts_created,
            errors=tuple(errors),
        )

    def prune_project(
        self_or_project: Any = None,
        project: Optional[Project] = None,
        overwrite_rebuild_script: Optional[bool] = None,
        **kwargs: Any,
    ) -> PruneSummary:
        instance: ProjectPruner
        target_project: Optional[Project] = None
        overwrite: Optional[bool] = (
            overwrite_rebuild_script
            if overwrite_rebuild_script is not None
            else kwargs.get("overwrite_rebuild_script")
        )

        if isinstance(self_or_project, ProjectPruner):
            instance = self_or_project
            target_project = project if project is not None else kwargs.get("project")
        else:
            instance = ProjectPruner()
            target_project = (
                project
                if project is not None
                else (
                    self_or_project
                    if self_or_project is not None
                    else kwargs.get("project")
                )
            )
            if project is not None and isinstance(project, bool) and overwrite is None:
                overwrite = project

        if overwrite is None:
            overwrite = instance.overwrite_rebuild_script

        return instance._prune_single_project(target_project, overwrite)

    def prune_multiple_projects(
        self_or_projects: Any = None,
        projects: Optional[Sequence[Project]] = None,
        overwrite_rebuild_script: Optional[bool] = None,
        **kwargs: Any,
    ) -> PruneSummary:
        instance: ProjectPruner
        target_projects: Optional[Sequence[Project]] = None
        overwrite: Optional[bool] = (
            overwrite_rebuild_script
            if overwrite_rebuild_script is not None
            else kwargs.get("overwrite_rebuild_script")
        )

        if isinstance(self_or_projects, ProjectPruner):
            instance = self_or_projects
            target_projects = projects if projects is not None else kwargs.get("projects")
        else:
            instance = ProjectPruner()
            target_projects = (
                projects
                if projects is not None
                else (
                    self_or_projects
                    if self_or_projects is not None
                    else kwargs.get("projects")
                )
            )
            if projects is not None and isinstance(projects, bool) and overwrite is None:
                overwrite = projects

        if overwrite is None:
            overwrite = instance.overwrite_rebuild_script

        if target_projects is None or not isinstance(target_projects, (list, tuple, Sequence)):
            return PruneSummary(
                projects_pruned=0,
                bytes_reclaimed=0,
                rebuild_scripts_created=0,
                errors=("Invalid projects collection provided",),
            )

        total_projects_pruned = 0
        total_bytes_reclaimed = 0
        total_rebuild_scripts_created = 0
        all_errors: List[str] = []

        for proj in target_projects:
            single_summary = instance._prune_single_project(proj, overwrite)
            total_projects_pruned += single_summary.projects_pruned
            total_bytes_reclaimed += single_summary.bytes_reclaimed
            total_rebuild_scripts_created += single_summary.rebuild_scripts_created
            all_errors.extend(single_summary.errors)

        return PruneSummary(
            projects_pruned=total_projects_pruned,
            bytes_reclaimed=total_bytes_reclaimed,
            rebuild_scripts_created=total_rebuild_scripts_created,
            errors=tuple(all_errors),
        )
