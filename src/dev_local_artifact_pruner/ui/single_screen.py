from pathlib import Path
from typing import Dict, Optional, Tuple

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from dev_local_artifact_pruner.core.models import (
    ActionState,
    EcosystemType,
    Project,
    PruneSummary,
)
from dev_local_artifact_pruner.core.pruner import ProjectPruner
from dev_local_artifact_pruner.core.scanner import ProjectScanner
from dev_local_artifact_pruner.ui.terminal import TerminalWidget
from dev_local_artifact_pruner.utils.formatters import (
    format_bytes,
    format_relative_time,
)

ACTION_BUTTON_STATES: Dict[ActionState, Tuple[bool, bool, bool, bool]] = {
    ActionState.INITIAL: (True, False, False, False),
    ActionState.ANALYZING: (False, False, False, False),
    ActionState.ANALYZED: (True, True, False, False),
    ActionState.PRUNING_REQUESTED: (False, False, True, True),
    ActionState.PRUNING: (False, False, False, False),
    ActionState.COMPLETED: (True, False, False, False),
}


class SingleProjectScreen(QWidget):
    back_requested = Signal()

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        scanner: Optional[ProjectScanner] = None,
        pruner: Optional[ProjectPruner] = None,
    ) -> None:
        super().__init__(parent)
        self.scanner = scanner if scanner is not None else ProjectScanner()
        self.pruner = pruner if pruner is not None else ProjectPruner()
        self.current_state: ActionState = ActionState.INITIAL
        self.current_project: Optional[Project] = None

        self._init_ui()
        self.set_action_state(ActionState.INITIAL)

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        header_layout = QHBoxLayout()
        self.btn_back = QPushButton("[ ← Voltar ao Início ]")
        self.btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_back.clicked.connect(self.back_requested.emit)
        header_layout.addWidget(self.btn_back)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        path_label = QLabel("Pasta do Projeto:")
        path_label.setStyleSheet("font-weight: 600; color: #e6edf3;")
        layout.addWidget(path_label)

        path_row = QHBoxLayout()
        path_row.setSpacing(8)
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Selecione ou informe o caminho do projeto...")
        self.btn_browse = QPushButton("📁 Procurar...")
        self.btn_browse.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_browse.clicked.connect(self.browse_folder)
        path_row.addWidget(self.path_edit, stretch=1)
        path_row.addWidget(self.btn_browse)
        layout.addLayout(path_row)

        terminal_label = QLabel("TERMINAL DE RESPOSTAS / LOG:")
        terminal_label.setStyleSheet("font-weight: 600; color: #8b949e; font-size: 11px;")
        layout.addWidget(terminal_label)

        self.terminal = TerminalWidget()
        layout.addWidget(self.terminal, stretch=1)

        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(10)

        self.btn_analyze = QPushButton("Analisar")
        self.btn_analyze.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_analyze.clicked.connect(self.analyze_project)

        self.btn_prune = QPushButton("Apagar")
        self.btn_prune.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_prune.clicked.connect(self.request_prune)

        self.btn_confirm = QPushButton("Confirmar")
        self.btn_confirm.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_confirm.clicked.connect(self.confirm_prune)

        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.clicked.connect(self.cancel_prune)

        actions_layout.addWidget(self.btn_analyze)
        actions_layout.addWidget(self.btn_prune)
        actions_layout.addStretch()
        actions_layout.addWidget(self.btn_confirm)
        actions_layout.addWidget(self.btn_cancel)
        layout.addLayout(actions_layout)

        self.terminal.append_line("dev-local-artifact-pruner - Modo Projeto Individual")
        self.terminal.append_line("Selecione a pasta do projeto e clique em [Analisar].")

    def set_action_state(self, state: ActionState) -> None:
        self.current_state = state
        can_analyze, can_prune, can_confirm, can_cancel = ACTION_BUTTON_STATES.get(
            state, (True, False, False, False)
        )
        self.btn_analyze.setEnabled(can_analyze)
        self.btn_prune.setEnabled(can_prune)
        self.btn_confirm.setEnabled(can_confirm)
        self.btn_cancel.setEnabled(can_cancel)

    def browse_folder(self) -> None:
        initial_dir = self.path_edit.text().strip() or str(Path.home())
        chosen_dir = QFileDialog.getExistingDirectory(
            self,
            "Selecionar Pasta do Projeto",
            initial_dir,
        )
        if chosen_dir:
            self.path_edit.setText(chosen_dir)
            self.current_project = None
            self.set_action_state(ActionState.INITIAL)

    def analyze_project(self) -> None:
        raw_path = self.path_edit.text().strip()
        if not raw_path:
            self.terminal.log_warning("Aviso: Informe ou selecione a pasta do projeto antes de analisar.")
            return

        target_path = Path(raw_path).expanduser().resolve()
        if not target_path.exists() or not target_path.is_dir():
            self.terminal.log_error(f"Erro: O caminho especificado não existe ou não é um diretório: {target_path}")
            return

        self.set_action_state(ActionState.ANALYZING)
        self.terminal.clear_terminal()
        self.terminal.append_line(f"project-pruner > analyze {target_path.name}")
        self.terminal.append_line("")
        self.terminal.append_line(f"Projeto: {target_path}")

        try:
            project = self.scanner.scan_single_project(target_path)
        except Exception as exc:
            self.terminal.log_error(f"Erro inesperado durante a análise: {exc}")
            self.set_action_state(ActionState.COMPLETED)
            return

        if project is None:
            self.terminal.log_warning("Nenhum manifesto de projeto suportado ou repositório Git válido detectado.")
            self.current_project = None
            self.set_action_state(ActionState.COMPLETED)
            return

        self.current_project = project

        eco_label = "Desconhecido"
        if project.ecosystem == EcosystemType.NODE:
            eco_label = "Node.js (package.json detectado)"
        elif project.ecosystem == EcosystemType.PYTHON:
            eco_label = "Python (manifesto detectado)"
        self.terminal.append_line(f"Sistema: {eco_label}")

        if project.git_info and project.git_info.is_git_repo:
            git_clean = "limpo" if not project.git_info.is_dirty else "alterações pendentes (dirty)"
            time_rel = (
                format_relative_time(project.git_info.days_inactive)
                if project.git_info.days_inactive is not None
                else "desconhecido"
            )
            self.terminal.append_line(f"Último commit: {time_rel} | Git: {git_clean}")
        else:
            self.terminal.append_line("Git: Repositório não detectado")

        self.terminal.append_line("")

        if project.artifacts:
            self.terminal.append_line("Dependências encontradas:")
            for art in project.artifacts:
                size_str = format_bytes(art.size_bytes)
                dots = "." * max(2, 45 - len(art.name) - len(size_str))
                self.terminal.append_line(f"  • {art.name} {dots} {size_str}")

            self.terminal.append_line("")
            reclaimable_str = format_bytes(project.reclaimable_bytes)
            self.terminal.append_line(f"Espaço recuperável: {reclaimable_str}")

            if project.is_inactive:
                days_inactive = project.git_info.days_inactive if project.git_info else 0
                self.terminal.log_success(
                    f"Sugestão: Inativo há mais de 60 dias ({days_inactive} dias). Seguro para poda."
                )
            else:
                self.terminal.append_line("Sugestão: Projeto ativo ou recente.")

            self.terminal.append_line("Aguardando ação: clique em [Apagar] para preparar a poda.")
            self.set_action_state(ActionState.ANALYZED)
        else:
            self.terminal.append_line("Nenhum artefato elegível para poda encontrado.")
            self.set_action_state(ActionState.ANALYZED)

    def request_prune(self) -> None:
        if self.current_project is None or not self.current_project.artifacts:
            self.terminal.log_warning("Aviso: Nenhum artefato disponível para poda neste projeto.")
            return

        reclaimable_str = format_bytes(self.current_project.reclaimable_bytes)
        self.terminal.append_line("")
        self.terminal.log_warning(
            f"Confirmação necessária: Deseja realmente podar os artefatos de '{self.current_project.name}'?"
        )
        self.terminal.append_line(f"Espaço a ser liberado: {reclaimable_str}")
        self.terminal.append_line("Clique em [Confirmar] para executar ou [Cancelar] para desistir.")
        self.set_action_state(ActionState.PRUNING_REQUESTED)

    def confirm_prune(self) -> None:
        if self.current_project is None:
            self.set_action_state(ActionState.COMPLETED)
            return

        self.set_action_state(ActionState.PRUNING)
        self.terminal.append_line("")
        self.terminal.append_line(f"project-pruner > prune {self.current_project.name}")
        self.terminal.append_line("Iniciando poda segura dos artefatos...")

        try:
            summary: PruneSummary = self.pruner.prune_project(self.current_project)
        except Exception as exc:
            self.terminal.log_error(f"Erro inesperado durante a poda: {exc}")
            self.set_action_state(ActionState.COMPLETED)
            return

        if summary.is_successful:
            reclaimed_str = format_bytes(summary.bytes_reclaimed)
            self.terminal.log_success(f"Poda concluída com sucesso! Espaço liberado: {reclaimed_str}")
            if summary.rebuild_scripts_created > 0:
                self.terminal.append_line("Script de reconstrução gerado: rebuild_dependencies.py")
        else:
            for err in summary.errors:
                self.terminal.log_error(f"Erro durante a poda: {err}")

        self.current_project = None
        self.set_action_state(ActionState.COMPLETED)

    def cancel_prune(self) -> None:
        self.terminal.append_line("")
        self.terminal.log_warning("Operação de poda cancelada pelo usuário.")
        self.set_action_state(ActionState.COMPLETED)
