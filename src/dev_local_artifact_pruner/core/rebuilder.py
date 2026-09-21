import ast
import os
from pathlib import Path
from typing import Dict, Optional, Union

from dev_local_artifact_pruner.core.rules import is_protected_path

REBUILD_SCRIPT_NAME = "rebuild_dependencies.py"

NODE_NPM_CI_TEMPLATE: str = '''"""Script gerado automaticamente por dev-local-artifact-pruner."""
import shutil
import subprocess
import sys

print("Instalando dependencias com npm ci...")
cmd = shutil.which("npm") or "npm"
try:
    subprocess.check_call([cmd, "ci"], shell=(sys.platform == "win32"))
    print("\\nDependencias restauradas com sucesso!")
except Exception as err:
    print(f"\\nERRO ao executar npm ci: {err}")
    sys.exit(1)
'''

NODE_PNPM_TEMPLATE: str = '''"""Script gerado automaticamente por dev-local-artifact-pruner."""
import shutil
import subprocess
import sys

print("Instalando dependencias com pnpm...")
cmd = shutil.which("pnpm") or "pnpm"
try:
    subprocess.check_call([cmd, "install", "--frozen-lockfile"], shell=(sys.platform == "win32"))
    print("\\nDependencias restauradas com sucesso!")
except Exception as err:
    print(f"\\nERRO ao executar pnpm install: {err}")
    sys.exit(1)
'''

NODE_YARN_TEMPLATE: str = '''"""Script gerado automaticamente por dev-local-artifact-pruner."""
import shutil
import subprocess
import sys

print("Instalando dependencias com yarn...")
cmd = shutil.which("yarn") or "yarn"
try:
    subprocess.check_call([cmd, "install", "--frozen-lockfile"], shell=(sys.platform == "win32"))
    print("\\nDependencias restauradas com sucesso!")
except Exception as err:
    print(f"\\nERRO ao executar yarn install: {err}")
    sys.exit(1)
'''

NODE_NPM_INSTALL_TEMPLATE: str = '''"""Script gerado automaticamente por dev-local-artifact-pruner."""
import shutil
import subprocess
import sys

print("Instalando dependencias com npm install...")
cmd = shutil.which("npm") or "npm"
try:
    subprocess.check_call([cmd, "install"], shell=(sys.platform == "win32"))
    print("\\nDependencias restauradas com sucesso!")
except Exception as err:
    print(f"\\nERRO ao executar npm install: {err}")
    sys.exit(1)
'''

PYTHON_UV_TEMPLATE: str = '''"""Script gerado automaticamente por dev-local-artifact-pruner."""
import shutil
import subprocess
import sys

print("Sincronizando ambiente com uv...")
cmd = shutil.which("uv") or "uv"
try:
    subprocess.check_call([cmd, "sync"], shell=(sys.platform == "win32"))
    print("\\nAmbiente restaurado com sucesso!")
except Exception as err:
    print(f"\\nERRO ao sincronizar ambiente com uv: {err}")
    sys.exit(1)
'''

PYTHON_POETRY_TEMPLATE: str = '''"""Script gerado automaticamente por dev-local-artifact-pruner."""
import shutil
import subprocess
import sys

print("Instalando dependencias com Poetry...")
cmd = shutil.which("poetry") or "poetry"
try:
    subprocess.check_call([cmd, "install"], shell=(sys.platform == "win32"))
    print("\\nAmbiente restaurado com sucesso!")
except Exception as err:
    print(f"\\nERRO ao instalar dependencias com Poetry: {err}")
    sys.exit(1)
'''

PYTHON_PIPENV_TEMPLATE: str = '''"""Script gerado automaticamente por dev-local-artifact-pruner."""
import shutil
import subprocess
import sys

print("Instalando dependencias com Pipenv...")
cmd = shutil.which("pipenv") or "pipenv"
try:
    subprocess.check_call([cmd, "install"], shell=(sys.platform == "win32"))
    print("\\nAmbiente restaurado com sucesso!")
except Exception as err:
    print(f"\\nERRO ao instalar dependencias com Pipenv: {err}")
    sys.exit(1)
'''

PYTHON_REQUIREMENTS_TEMPLATE: str = '''"""Script gerado automaticamente por dev-local-artifact-pruner."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
VENV_DIR = ROOT / ".venv"

print("Recriando ambiente virtual Python (.venv)...")
subprocess.check_call([sys.executable, "-m", "venv", str(VENV_DIR)])

pip_executable = VENV_DIR / ("Scripts/pip.exe" if sys.platform == "win32" else "bin/pip")

print("Instalando dependencias do requirements.txt...")
subprocess.check_call([str(pip_executable), "install", "-r", str(ROOT / "requirements.txt")])

print("\\nAmbiente restaurado com sucesso!")
'''

PYTHON_FALLBACK_TEMPLATE: str = '''"""Script gerado automaticamente por dev-local-artifact-pruner."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
VENV_DIR = ROOT / ".venv"

print("Recriando ambiente virtual Python (.venv)...")
subprocess.check_call([sys.executable, "-m", "venv", str(VENV_DIR)])

pip_executable = VENV_DIR / ("Scripts/pip.exe" if sys.platform == "win32" else "bin/pip")

if (ROOT / "requirements.txt").exists():
    print("Instalando dependencias do requirements.txt...")
    subprocess.check_call([str(pip_executable), "install", "-r", str(ROOT / "requirements.txt")])
elif (ROOT / "setup.py").exists() or (ROOT / "pyproject.toml").exists():
    print("Instalando projeto em modo editavel...")
    subprocess.check_call([str(pip_executable), "install", "-e", str(ROOT)])
else:
    print("Ambiente virtual (.venv) criado com sucesso.")

print("\\nAmbiente restaurado com sucesso!")
'''


def _get_project_files(target: Path) -> Dict[str, str]:
    try:
        with os.scandir(target) as entries:
            return {entry.name.lower(): entry.name for entry in entries if entry.is_file()}
    except (PermissionError, FileNotFoundError, OSError):
        return {}


def _read_text_safely(file_path: Path) -> str:
    try:
        return file_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


class RebuildScriptGenerator:
    @classmethod
    def generate_script_content(
        cls,
        project_path: Optional[Union[Path, str]] = None,
    ) -> Optional[str]:
        if project_path is None:
            return None

        try:
            target = project_path if isinstance(project_path, Path) else Path(project_path)
        except (TypeError, ValueError):
            return None

        if not target.exists() or not target.is_dir() or is_protected_path(target):
            return None

        files = _get_project_files(target)
        if not files:
            return None

        template: Optional[str] = None

        if "package-lock.json" in files:
            template = NODE_NPM_CI_TEMPLATE
        elif "pnpm-lock.yaml" in files:
            template = NODE_PNPM_TEMPLATE
        elif "yarn.lock" in files:
            template = NODE_YARN_TEMPLATE
        elif "uv.lock" in files:
            template = PYTHON_UV_TEMPLATE
        elif "poetry.lock" in files:
            template = PYTHON_POETRY_TEMPLATE
        elif "pipfile.lock" in files or "pipfile" in files:
            template = PYTHON_PIPENV_TEMPLATE
        elif "package.json" in files:
            template = NODE_NPM_INSTALL_TEMPLATE
        elif "pyproject.toml" in files:
            content = _read_text_safely(target / files["pyproject.toml"]).lower()
            if "tool.uv" in content:
                template = PYTHON_UV_TEMPLATE
            elif "tool.poetry" in content:
                template = PYTHON_POETRY_TEMPLATE
            elif "requirements.txt" in files:
                template = PYTHON_REQUIREMENTS_TEMPLATE
            else:
                template = PYTHON_FALLBACK_TEMPLATE
        elif "requirements.txt" in files:
            template = PYTHON_REQUIREMENTS_TEMPLATE
        elif "setup.py" in files or "manage.py" in files:
            template = PYTHON_FALLBACK_TEMPLATE

        if template is None:
            return None

        try:
            ast.parse(template)
        except SyntaxError:
            return None

        return template

    @classmethod
    def generate_rebuild_script(
        cls,
        project_path: Optional[Union[Path, str]] = None,
        overwrite: bool = False,
    ) -> Optional[Path]:
        if project_path is None:
            return None

        try:
            target = project_path if isinstance(project_path, Path) else Path(project_path)
        except (TypeError, ValueError):
            return None

        content = cls.generate_script_content(target)
        if content is None:
            return None

        target_file = target / REBUILD_SCRIPT_NAME
        if target_file.exists() and not overwrite:
            return None

        try:
            target_file.write_text(content, encoding="utf-8")
            try:
                current_mode = target_file.stat().st_mode
                target_file.chmod(current_mode | 0o111)
            except OSError:
                pass
            return target_file
        except OSError:
            return None
