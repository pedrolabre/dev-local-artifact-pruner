from typing import Optional, Union

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QMouseEvent, QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from dev_local_artifact_pruner.ui.icons import get_folder_pixmap, get_multi_folder_pixmap
from dev_local_artifact_pruner.ui.styles import (
    COLOR_BG_PANEL,
    COLOR_BG_SURFACE,
    COLOR_BORDER,
    COLOR_BORDER_FOCUS,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
)

MODE_CARD_QSS = f"""
QFrame#modeCard {{
    background-color: {COLOR_BG_PANEL};
    border: 2px solid {COLOR_BORDER};
    border-radius: 12px;
}}

QFrame#modeCard:hover {{
    background-color: {COLOR_BG_SURFACE};
    border: 2px solid {COLOR_BORDER_FOCUS};
}}

QFrame#modeCard QLabel {{
    background-color: transparent;
}}
"""


class ModeCard(QFrame):
    clicked = Signal()

    def __init__(
        self,
        icon: Union[str, QPixmap],
        title: str,
        subtitle: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("modeCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(220, 190)
        self.setStyleSheet(MODE_CARD_QSS)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 20, 16, 20)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.icon_label = QLabel(self)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if isinstance(icon, QPixmap):
            self.icon_label.setPixmap(icon)
        else:
            self.icon_label.setText(str(icon))
            icon_font = QFont()
            icon_font.setPointSize(36)
            self.icon_label.setFont(icon_font)

        self.title_label = QLabel(title, self)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-weight: bold;")

        self.subtitle_label = QLabel(subtitle, self)
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_font = QFont()
        subtitle_font.setPointSize(10)
        self.subtitle_label.setFont(subtitle_font)
        self.subtitle_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")

        layout.addWidget(self.icon_label)
        layout.addWidget(self.title_label)
        layout.addWidget(self.subtitle_label)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class HomeScreen(QWidget):
    single_mode_selected = Signal()
    multi_mode_selected = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(20)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        main_layout.addStretch(1)

        self.title_label = QLabel("dev-local-artifact-pruner", self)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(22)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet(f"color: {COLOR_TEXT_PRIMARY}; font-weight: bold;")

        self.subtitle_label = QLabel("Selecione o tipo de análise", self)
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub_font = QFont()
        sub_font.setPointSize(12)
        self.subtitle_label.setFont(sub_font)
        self.subtitle_label.setStyleSheet(f"color: {COLOR_TEXT_SECONDARY};")

        main_layout.addWidget(self.title_label)
        main_layout.addWidget(self.subtitle_label)
        main_layout.addSpacing(24)

        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(32)
        cards_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.card_single = ModeCard(
            icon=get_folder_pixmap(size=54),
            title="Projeto",
            subtitle="Analisar uma pasta",
            parent=self,
        )
        self.card_multi = ModeCard(
            icon=get_multi_folder_pixmap(size=54),
            title="Múltiplos",
            subtitle="Analisar vários projetos",
            parent=self,
        )

        self.card_single.clicked.connect(self.single_mode_selected.emit)
        self.card_multi.clicked.connect(self.multi_mode_selected.emit)

        cards_layout.addWidget(self.card_single)
        cards_layout.addWidget(self.card_multi)

        main_layout.addLayout(cards_layout)
        main_layout.addStretch(1)
