from typing import Optional


def format_bytes(size_bytes: int) -> str:
    if size_bytes < 0:
        raise ValueError("Size in bytes cannot be negative")
    size = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if size < 1024.0 or unit == "PB":
            if unit == "B":
                return f"{int(size)} B"
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"


def format_relative_time(days: Optional[int]) -> str:
    if days is None:
        return "desconhecido"
    if days <= 0:
        return "hoje"
    if days == 1:
        return "há 1 dia"
    if days < 30:
        return f"há {days} dias"
    if days < 365:
        months = days // 30
        if months <= 1:
            return "há 1 mês"
        return f"há {months} meses"
    years = days // 365
    if years <= 1:
        return "há 1 ano"
    return f"há {years} anos"
