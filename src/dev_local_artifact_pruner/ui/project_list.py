from typing import List, Optional, Sequence
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from dev_local_artifact_pruner.core.models import EcosystemType, Project
from dev_local_artifact_pruner.ui.icons import get_folder_icon
from dev_local_artifact_pruner.ui.styles import (
    COLOR_ACCENT_BLUE,
    COLOR_STATUS_ERROR,
    COLOR_TEXT_MUTED,
)
from dev_local_artifact_pruner.utils.formatters import format_bytes


class ProjectListWidget(QWidget):
    selection_changed = Signal()
    project_clicked = Signal(Project)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(8)

        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)
        top_bar.setSpacing(8)

        self.btn_select_inactive = QPushButton("[ Marcar Inativos ]")
        self.btn_select_inactive.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_mark_inactive = self.btn_select_inactive

        self.btn_deselect_all = QPushButton("[ Desmarcar Todos ]")
        self.btn_deselect_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_uncheck_all = self.btn_deselect_all

        top_bar.addWidget(self.btn_select_inactive)
        top_bar.addWidget(self.btn_deselect_all)
        main_layout.addLayout(top_bar)

        self.list_widget = QListWidget()
        self.list_widget.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        v_bar = self.list_widget.verticalScrollBar()
        if v_bar is not None:
            v_bar.setSingleStep(15)
        self.items_list = self.list_widget
        self.project_list = self.list_widget
        main_layout.addWidget(self.list_widget)

        self.btn_select_inactive.clicked.connect(self.select_inactive)
        self.btn_deselect_all.clicked.connect(self.deselect_all)
        self.list_widget.itemChanged.connect(self._on_item_changed)
        self.list_widget.itemClicked.connect(self._on_item_clicked)

    def populate_projects(self, projects: Sequence[Project]) -> None:
        self.list_widget.blockSignals(True)
        self.list_widget.clear()

        for project in projects:
            item = QListWidgetItem()
            item.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsUserCheckable
            )

            is_inactive = project.is_inactive
            item.setCheckState(
                Qt.CheckState.Checked if is_inactive else Qt.CheckState.Unchecked
            )
            item.setData(Qt.ItemDataRole.UserRole, project)

            eco_name = "Desconhecido"
            if project.ecosystem == EcosystemType.NODE:
                eco_name = "Node.js"
            elif project.ecosystem == EcosystemType.PYTHON:
                eco_name = "Python"

            size_val = (
                project.reclaimable_bytes
                if project.reclaimable_bytes > 0
                else project.total_size_bytes
            )
            size_str = format_bytes(size_val)
            status_tag = "[Inativo]" if is_inactive else "[Ativo]"
            item.setText(f"{project.name}\n  {eco_name} • {size_str} {status_tag}")
            icon_color = COLOR_STATUS_ERROR if is_inactive else COLOR_ACCENT_BLUE
            item.setIcon(get_folder_icon(size=18, color=icon_color))
            if is_inactive:
                item.setForeground(QColor(COLOR_STATUS_ERROR))
            else:
                item.setForeground(QColor(COLOR_TEXT_MUTED))
            self.list_widget.addItem(item)

        self.list_widget.blockSignals(False)
        self.selection_changed.emit()

    def get_selected_projects(self) -> List[Project]:
        selected: List[Project] = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                project = item.data(Qt.ItemDataRole.UserRole)
                if isinstance(project, Project):
                    selected.append(project)
        return selected

    def get_selected_bytes(self) -> int:
        return sum(
            p.reclaimable_bytes if p.reclaimable_bytes > 0 else p.total_size_bytes
            for p in self.get_selected_projects()
        )

    def get_all_projects(self) -> List[Project]:
        all_projects: List[Project] = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            project = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(project, Project):
                all_projects.append(project)
        return all_projects

    def select_inactive(self) -> None:
        self.list_widget.blockSignals(True)
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            project = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(project, Project) and project.is_inactive:
                item.setCheckState(Qt.CheckState.Checked)
            else:
                item.setCheckState(Qt.CheckState.Unchecked)
        self.list_widget.blockSignals(False)
        self.selection_changed.emit()

    def deselect_all(self) -> None:
        self.list_widget.blockSignals(True)
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setCheckState(Qt.CheckState.Unchecked)
        self.list_widget.blockSignals(False)
        self.selection_changed.emit()

    def select_all(self) -> None:
        self.list_widget.blockSignals(True)
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setCheckState(Qt.CheckState.Checked)
        self.list_widget.blockSignals(False)
        self.selection_changed.emit()

    def clear(self) -> None:
        self.list_widget.clear()
        self.selection_changed.emit()

    def count(self) -> int:
        return self.list_widget.count()

    def _on_item_changed(self, item: QListWidgetItem) -> None:
        self.selection_changed.emit()

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        project = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(project, Project):
            self.project_clicked.emit(project)


ProjectListWidget.mark_inactive = ProjectListWidget.select_inactive
ProjectListWidget.uncheck_all = ProjectListWidget.deselect_all
