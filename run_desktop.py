from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def run() -> int:
    try:
        from dev_local_artifact_pruner.main import main
    except ImportError as exc:
        print(
            f"Erro ao importar os módulos da aplicação: {exc}\n"
            "Certifique-se de que as dependências estão instaladas executando:\n"
            "  pip install -e .\n"
            "ou instalando os requisitos necessários (como PySide6).",
            file=sys.stderr,
        )
        return 1

    return main(sys.argv)


if __name__ == "__main__":
    sys.exit(run())
