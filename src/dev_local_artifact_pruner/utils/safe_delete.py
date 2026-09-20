import os
import shutil
import stat
import time
from pathlib import Path
from typing import Any, Callable, Union


def _handle_remove_readonly(func: Callable[..., Any], path: str, exc_info: Any) -> None:
    try:
        os.chmod(path, stat.S_IWRITE)
    except OSError:
        pass
    func(path)


def _rmtree_with_error_handler(path: Path) -> None:
    try:
        shutil.rmtree(path, onexc=_handle_remove_readonly)
    except TypeError:
        shutil.rmtree(path, onerror=_handle_remove_readonly)


def safe_remove_tree(
    target_path: Union[Path, str],
    retries: int = 3,
    base_delay: float = 0.1,
) -> bool:
    try:
        if isinstance(target_path, str) and not target_path.strip():
            return False
        path = Path(os.path.abspath(target_path))
        if path == Path(path.anchor) or path == Path.cwd():
            return False
    except Exception:
        return False

    attempts = max(1, retries)
    current_base_delay = max(0.0, float(base_delay))

    for attempt in range(attempts):
        try:
            if not os.path.lexists(path):
                return True

            if path.is_file() or path.is_symlink() or os.path.islink(path) or getattr(path, "is_junction", lambda: False)():
                try:
                    os.chmod(path, stat.S_IWRITE)
                except OSError:
                    pass
                try:
                    path.unlink()
                except OSError:
                    path.rmdir()
                return True

            try:
                os.chmod(path, stat.S_IWRITE)
            except OSError:
                pass

            _rmtree_with_error_handler(path)
            return True
        except Exception:
            if attempt < attempts - 1:
                time.sleep(current_base_delay * (2**attempt))
            else:
                return False

    return not os.path.lexists(path)
