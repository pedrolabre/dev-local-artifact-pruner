import ast
from pathlib import Path

import pytest

from dev_local_artifact_pruner.core import RebuildScriptGenerator
from dev_local_artifact_pruner.core.rebuilder import (
    NODE_NPM_CI_TEMPLATE,
    NODE_NPM_INSTALL_TEMPLATE,
    NODE_PNPM_TEMPLATE,
    NODE_YARN_TEMPLATE,
    PYTHON_FALLBACK_TEMPLATE,
    PYTHON_PIPENV_TEMPLATE,
    PYTHON_POETRY_TEMPLATE,
    PYTHON_REQUIREMENTS_TEMPLATE,
    PYTHON_UV_TEMPLATE,
    REBUILD_SCRIPT_NAME,
)


def test_rebuilder_export() -> None:
    from dev_local_artifact_pruner import core

    assert hasattr(core, "RebuildScriptGenerator")
    assert "RebuildScriptGenerator" in core.__all__


def test_node_package_lock_generates_npm_ci(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text('{"name": "test"}', encoding="utf-8")
    (tmp_path / "package-lock.json").write_text('{"name": "test", "lockfileVersion": 3}', encoding="utf-8")

    generator = RebuildScriptGenerator()
    content = generator.generate_script_content(tmp_path)
    assert content is not None
    assert "npm ci" in content
    assert ast.parse(content)

    script_path = generator.generate_rebuild_script(tmp_path)
    assert script_path is not None
    assert script_path.exists()
    assert script_path.name == REBUILD_SCRIPT_NAME
    assert "npm ci" in script_path.read_text(encoding="utf-8")


def test_node_pnpm_lock_generates_pnpm_install(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text('{"name": "test"}', encoding="utf-8")
    (tmp_path / "pnpm-lock.yaml").write_text("lockfileVersion: '9.0'", encoding="utf-8")

    content = RebuildScriptGenerator.generate_script_content(tmp_path)
    assert content is not None
    assert "pnpm" in content
    assert "--frozen-lockfile" in content
    assert ast.parse(content)

    script_path = RebuildScriptGenerator.generate_rebuild_script(tmp_path)
    assert script_path is not None
    assert "pnpm" in script_path.read_text(encoding="utf-8")


def test_node_yarn_lock_generates_yarn_install(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text('{"name": "test"}', encoding="utf-8")
    (tmp_path / "yarn.lock").write_text("# yarn lockfile v1", encoding="utf-8")

    generator = RebuildScriptGenerator()
    content = generator.generate_script_content(tmp_path)
    assert content is not None
    assert "yarn" in content
    assert "--frozen-lockfile" in content
    assert ast.parse(content)

    script_path = generator.generate_rebuild_script(tmp_path)
    assert script_path is not None
    assert "yarn" in script_path.read_text(encoding="utf-8")


def test_node_package_json_only_generates_npm_install(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text('{"name": "test"}', encoding="utf-8")

    content = RebuildScriptGenerator.generate_script_content(tmp_path)
    assert content is not None
    assert "npm install" in content
    assert "npm ci" not in content
    assert ast.parse(content)

    script_path = RebuildScriptGenerator.generate_rebuild_script(tmp_path)
    assert script_path is not None
    assert "npm install" in script_path.read_text(encoding="utf-8")


def test_python_uv_lock_generates_uv_sync(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "test"\n', encoding="utf-8")
    (tmp_path / "uv.lock").write_text("version = 1\n", encoding="utf-8")

    content = RebuildScriptGenerator.generate_script_content(tmp_path)
    assert content is not None
    assert "uv" in content
    assert "sync" in content
    assert ast.parse(content)

    script_path = RebuildScriptGenerator.generate_rebuild_script(tmp_path)
    assert script_path is not None
    assert "uv" in script_path.read_text(encoding="utf-8")


def test_python_pyproject_toml_with_uv_generates_uv_sync(tmp_path: Path) -> None:
    pyproject_content = """[project]
name = "uv-project"
version = "0.1.0"

[tool.uv]
dev-dependencies = ["pytest"]
"""
    (tmp_path / "pyproject.toml").write_text(pyproject_content, encoding="utf-8")

    generator = RebuildScriptGenerator()
    content = generator.generate_script_content(tmp_path)
    assert content is not None
    assert "uv" in content
    assert "sync" in content
    assert ast.parse(content)


def test_python_poetry_lock_generates_poetry_install(tmp_path: Path) -> None:
    (tmp_path / "poetry.lock").write_text("# poetry lock", encoding="utf-8")

    content = RebuildScriptGenerator.generate_script_content(tmp_path)
    assert content is not None
    assert "Poetry" in content
    assert "poetry" in content
    assert "install" in content
    assert ast.parse(content)


def test_python_pyproject_toml_with_poetry_generates_poetry_install(tmp_path: Path) -> None:
    pyproject_content = """[tool.poetry]
name = "poetry-project"
version = "0.1.0"
description = "test"
"""
    (tmp_path / "pyproject.toml").write_text(pyproject_content, encoding="utf-8")

    generator = RebuildScriptGenerator()
    content = generator.generate_script_content(tmp_path)
    assert content is not None
    assert "Poetry" in content
    assert ast.parse(content)


def test_python_pipfile_generates_pipenv_install(tmp_path: Path) -> None:
    (tmp_path / "Pipfile").write_text('[[source]]\nurl = "https://pypi.org/simple"', encoding="utf-8")

    content = RebuildScriptGenerator.generate_script_content(tmp_path)
    assert content is not None
    assert "Pipenv" in content
    assert "pipenv" in content
    assert ast.parse(content)


def test_python_pipfile_lock_generates_pipenv_install(tmp_path: Path) -> None:
    (tmp_path / "Pipfile.lock").write_text('{"_meta": {}}', encoding="utf-8")

    content = RebuildScriptGenerator.generate_script_content(tmp_path)
    assert content is not None
    assert "Pipenv" in content
    assert ast.parse(content)


def test_python_requirements_txt_generates_venv_pip(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text("requests>=2.28.0\n", encoding="utf-8")

    generator = RebuildScriptGenerator()
    content = generator.generate_script_content(tmp_path)
    assert content is not None
    assert "-m" in content
    assert "venv" in content
    assert "requirements.txt" in content
    assert ast.parse(content)

    script_path = generator.generate_rebuild_script(tmp_path)
    assert script_path is not None
    assert "requirements.txt" in script_path.read_text(encoding="utf-8")


def test_python_fallback_pyproject_without_tool(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "plain-project"\n', encoding="utf-8")

    content = RebuildScriptGenerator.generate_script_content(tmp_path)
    assert content is not None
    assert "-m" in content
    assert "venv" in content
    assert ast.parse(content)


def test_python_fallback_setup_py(tmp_path: Path) -> None:
    (tmp_path / "setup.py").write_text('from setuptools import setup; setup(name="pkg")', encoding="utf-8")

    content = RebuildScriptGenerator.generate_script_content(tmp_path)
    assert content is not None
    assert "-m" in content
    assert "venv" in content
    assert ast.parse(content)


def test_python_fallback_manage_py(tmp_path: Path) -> None:
    (tmp_path / "manage.py").write_text('#!/usr/bin/env python\nimport os', encoding="utf-8")

    content = RebuildScriptGenerator.generate_script_content(tmp_path)
    assert content is not None
    assert "-m" in content
    assert "venv" in content
    assert ast.parse(content)


def test_nonexistent_and_invalid_paths_return_none(tmp_path: Path) -> None:
    non_existent = tmp_path / "does_not_exist"
    assert RebuildScriptGenerator.generate_script_content(non_existent) is None
    assert RebuildScriptGenerator.generate_rebuild_script(non_existent) is None

    file_path = tmp_path / "some_file.txt"
    file_path.write_text("hello", encoding="utf-8")
    assert RebuildScriptGenerator.generate_script_content(file_path) is None
    assert RebuildScriptGenerator.generate_rebuild_script(file_path) is None


def test_protected_paths_return_none(tmp_path: Path) -> None:
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    assert RebuildScriptGenerator.generate_script_content(git_dir) is None
    assert RebuildScriptGenerator.generate_rebuild_script(git_dir) is None


def test_empty_and_unknown_directory_returns_none(tmp_path: Path) -> None:
    assert RebuildScriptGenerator.generate_script_content(tmp_path) is None
    assert RebuildScriptGenerator.generate_rebuild_script(tmp_path) is None

    (tmp_path / "random.dat").write_text("binary", encoding="utf-8")
    assert RebuildScriptGenerator.generate_script_content(tmp_path) is None
    assert RebuildScriptGenerator.generate_rebuild_script(tmp_path) is None


def test_overwrite_protection(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text('{"name": "test"}', encoding="utf-8")
    generator = RebuildScriptGenerator()

    first_path = generator.generate_rebuild_script(tmp_path)
    assert first_path is not None
    assert first_path.exists()

    first_path.write_text("CUSTOM_CONTENT = 42\n", encoding="utf-8")

    refused_path = generator.generate_rebuild_script(tmp_path, overwrite=False)
    assert refused_path is None
    assert first_path.read_text(encoding="utf-8") == "CUSTOM_CONTENT = 42\n"

    refused_by_class = RebuildScriptGenerator.generate_rebuild_script(tmp_path, overwrite=False)
    assert refused_by_class is None
    assert first_path.read_text(encoding="utf-8") == "CUSTOM_CONTENT = 42\n"

    overwritten_path = generator.generate_rebuild_script(tmp_path, overwrite=True)
    assert overwritten_path == first_path
    assert "CUSTOM_CONTENT = 42" not in first_path.read_text(encoding="utf-8")
    assert "npm install" in first_path.read_text(encoding="utf-8")


def test_string_path_argument_support(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text("pytest\n", encoding="utf-8")

    content = RebuildScriptGenerator.generate_script_content(str(tmp_path))
    assert content is not None
    assert "requirements.txt" in content

    script_path = RebuildScriptGenerator.generate_rebuild_script(str(tmp_path))
    assert script_path is not None
    assert script_path.exists()


def test_case_insensitive_manifest_detection(tmp_path: Path) -> None:
    (tmp_path / "PACKAGE.JSON").write_text('{"name": "caps"}', encoding="utf-8")
    content = RebuildScriptGenerator.generate_script_content(tmp_path)
    assert content is not None
    assert "npm install" in content


def test_all_templates_are_valid_python_syntax() -> None:
    templates = [
        NODE_NPM_CI_TEMPLATE,
        NODE_PNPM_TEMPLATE,
        NODE_YARN_TEMPLATE,
        NODE_NPM_INSTALL_TEMPLATE,
        PYTHON_UV_TEMPLATE,
        PYTHON_POETRY_TEMPLATE,
        PYTHON_PIPENV_TEMPLATE,
        PYTHON_REQUIREMENTS_TEMPLATE,
        PYTHON_FALLBACK_TEMPLATE,
    ]
    for template in templates:
        parsed = ast.parse(template)
        assert parsed is not None
