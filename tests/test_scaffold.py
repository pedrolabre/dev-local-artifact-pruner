from pathlib import Path
import dev_local_artifact_pruner


def test_package_version() -> None:
    assert dev_local_artifact_pruner.__version__ == "0.1.0"


def test_package_structure(project_root: Path) -> None:
    assert (project_root / "pyproject.toml").is_file()
    assert (project_root / "src" / "dev_local_artifact_pruner" / "__init__.py").is_file()
