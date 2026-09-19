import os
from pathlib import Path
from typing import Union


def get_directory_size_bytes(target_path: Union[Path, str]) -> int:
    path = Path(target_path)
    try:
        if path.is_symlink():
            return 0
        if not path.exists():
            return 0
        if path.is_file():
            return path.stat().st_size
    except (PermissionError, FileNotFoundError, OSError):
        return 0

    total_size = 0
    stack = [str(path)]

    while stack:
        current_dir = stack.pop()
        try:
            with os.scandir(current_dir) as entries:
                for entry in entries:
                    try:
                        if entry.is_symlink():
                            continue
                        if entry.is_file(follow_symlinks=False):
                            total_size += entry.stat(follow_symlinks=False).st_size
                        elif entry.is_dir(follow_symlinks=False):
                            stack.append(entry.path)
                    except (PermissionError, FileNotFoundError, OSError):
                        continue
        except (PermissionError, FileNotFoundError, OSError):
            continue

    return total_size
