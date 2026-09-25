import os
import shutil
import stat
import sys
import time
from pathlib import Path
from typing import Any, Callable, Union


def _to_extended_path(p: Union[Path, str]) -> str:
    path_str = os.path.abspath(str(p))
    if sys.platform == "win32" and not path_str.startswith("\\\\?\\"):
        if path_str.startswith("\\\\"):
            return f"\\\\?\\UNC\\{path_str[2:]}"
        return f"\\\\?\\{path_str}"
    return path_str


def _handle_remove_readonly(func: Callable[..., Any], path: str, exc_info: Any) -> None:
    try:
        os.chmod(path, stat.S_IWRITE)
    except OSError:
        pass
    func(path)


def _rmtree_with_error_handler(path: Union[Path, str]) -> None:
    target = _to_extended_path(path)
    try:
        shutil.rmtree(target, onexc=_handle_remove_readonly)
    except TypeError:
        shutil.rmtree(target, onerror=_handle_remove_readonly)


def safe_remove_tree(
    target_path: Union[Path, str],
    retries: int = 3,
    base_delay: float = 0.1,
) -> bool:
    try:
        if target_path is None:
            return False
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
            ext_path = _to_extended_path(path)
            if not os.path.lexists(ext_path):
                return True

            if path.is_file() or path.is_symlink() or os.path.islink(path) or getattr(path, "is_junction", lambda: False)():
                try:
                    os.chmod(ext_path, stat.S_IWRITE)
                except OSError:
                    pass
                try:
                    os.unlink(ext_path)
                except OSError:
                    try:
                        os.rmdir(ext_path)
                    except OSError:
                        pass
                return True

            try:
                os.chmod(ext_path, stat.S_IWRITE)
            except OSError:
                pass

            _rmtree_with_error_handler(ext_path)
            return True
        except Exception:
            if attempt < attempts - 1:
                time.sleep(current_base_delay * (2**attempt))
            else:
                return False

    return not os.path.lexists(_to_extended_path(path))
