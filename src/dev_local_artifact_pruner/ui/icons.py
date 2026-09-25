from pathlib import Path
from typing import Union

from PySide6.QtCore import QByteArray, QSize
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from dev_local_artifact_pruner.ui.styles import COLOR_ACCENT_BLUE

FOLDER_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="{size}" height="{size}" fill="none">
  <path d="M3 5a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h18a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-8l-2-2H3z" fill="{color}"/>
  <path d="M1 10h22" stroke="#ffffff" stroke-width="1.2" opacity="0.25"/>
</svg>"""

MULTI_FOLDER_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="{size}" height="{size}" fill="none">
  <path d="M6 3a2 2 0 0 0-2 2v1h15a2 2 0 0 1 2 2v8h1a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-8l-2-2H6z" fill="{color}" opacity="0.45"/>
  <path d="M3 7a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h18a2 2 0 0 0 2-2v-8a2 2 0 0 0-2-2h-8l-2-2H3z" fill="{color}"/>
  <path d="M1 12h22" stroke="#ffffff" stroke-width="1.2" opacity="0.25"/>
</svg>"""


def render_svg_pixmap(svg_template: str, size: int = 48, color: str = COLOR_ACCENT_BLUE) -> QPixmap:
    svg_data = svg_template.format(size=size, color=color).encode("utf-8")
    renderer = QSvgRenderer(QByteArray(svg_data))
    pixmap = QPixmap(size, size)
    pixmap.fill("transparent")
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return pixmap


def get_folder_pixmap(size: int = 48, color: str = COLOR_ACCENT_BLUE) -> QPixmap:
    return render_svg_pixmap(FOLDER_SVG, size=size, color=color)


def get_multi_folder_pixmap(size: int = 48, color: str = COLOR_ACCENT_BLUE) -> QPixmap:
    return render_svg_pixmap(MULTI_FOLDER_SVG, size=size, color=color)


def get_folder_icon(size: int = 18, color: str = COLOR_ACCENT_BLUE) -> QIcon:
    return QIcon(get_folder_pixmap(size=size, color=color))


def get_multi_folder_icon(size: int = 18, color: str = COLOR_ACCENT_BLUE) -> QIcon:
    return QIcon(get_multi_folder_pixmap(size=size, color=color))


__all__ = [
    "FOLDER_SVG",
    "MULTI_FOLDER_SVG",
    "get_folder_icon",
    "get_folder_pixmap",
    "get_multi_folder_icon",
    "get_multi_folder_pixmap",
    "render_svg_pixmap",
]
