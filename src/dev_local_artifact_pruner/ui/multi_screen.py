from pathlib import Path
from typing import List, Optional, Union

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QApplication,
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
from dev_local_artifact_pruner.ui.icons import get_folder_icon
from dev_local_artifact_pruner.ui.project_list import ProjectListWidget
from dev_local_artifact_pruner.ui.single_screen import ACTION_BUTTON_STATES
from dev_local_artifact_pruner.ui.terminal import TerminalWidget
from dev_local_artifact_pruner.utils.formatters import format_bytes, format_relative_time


class ScanWorker(QThread):
    scan_finished = Signal(list)
    project_found = Signal(Project)
    error_occurred = Signal(str)
    progress_message = Signal(str)

    def __init__(self, root_path: Union[Path, str], scanner: Optional[ProjectScanner] = None, max_depth: int = 4, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.root_path = Path(root_path) if not isinstance(root_path, Path) else root_path
        self.scanner = scanner if scanner is not None else ProjectScanner()
        self.max_depth, self._is_cancelled = max_depth, False

    def cancel(self) -> None:
        self._is_cancelled = True

    def run(self) -> None:
        try:
            self.progress_message.emit(f"Iniciando varredura em: {self.root_path}")
            projects = self.scanner.scan_multiple_projects(self.root_path, max_depth=self.max_depth)
            if self._is_cancelled:
                return
            for proj in projects:
                if self._is_cancelled:
                    return
                self.project_found.emit(proj)
            self.scan_finished.emit(projects)
        except Exception as exc:
            self.error_occurred.emit(str(exc))
            self.scan_finished.emit([])


class MultiProjectScreen(QWidget):
    back_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None, scanner: Optional[ProjectScanner] = None, pruner: Optional[ProjectPruner] = None) -> None:
        super().__init__(parent)
        self.scanner, self.pruner = scanner or ProjectScanner(), pruner or ProjectPruner()
        self.current_state, self.scan_worker, self.discovered_projects = ActionState.INITIAL, None, []
        self._init_ui()
        self.set_action_state(ActionState.INITIAL)

    def _create_action_btn(self, text: str, callback: object) -> QPushButton:
        btn = QPushButton(text)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(callback)
        return btn

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(14)

        header = QHBoxLayout()
        self.btn_back = self._create_action_btn("[ ← Voltar ao Início ]", self._on_back_clicked)
        header.addWidget(self.btn_back)
        header.addStretch()
        main_layout.addLayout(header)

        path_lbl = QLabel("Pasta Raiz (contendo projetos):")
        path_lbl.setStyleSheet("font-weight: 600; color: #e6edf3;")
        main_layout.addWidget(path_lbl)

        path_row = QHBoxLayout()
        path_row.setSpacing(8)
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Selecione ou informe a pasta raiz com múltiplos projetos...")
        self.btn_browse = self._create_action_btn("Procurar...", self.browse_folder)
        self.btn_browse.setIcon(get_folder_icon(16))
        path_row.addWidget(self.path_edit, stretch=1)
        path_row.addWidget(self.btn_browse)
        main_layout.addLayout(path_row)

        cols = QHBoxLayout()
        cols.setSpacing(14)
        left_col, right_col = QVBoxLayout(), QVBoxLayout()
        left_col.setSpacing(6)
        right_col.setSpacing(6)

        list_lbl = QLabel("PASTAS COM ARTEFATOS ENCONTRADOS:")
        list_lbl.setStyleSheet("font-weight: 600; color: #8b949e; font-size: 11px;")
        self.project_list = ProjectListWidget()
        self.project_list.selection_changed.connect(self._on_selection_changed)
        self.project_list.project_clicked.connect(self._on_project_clicked)
        left_col.addWidget(list_lbl)
        left_col.addWidget(self.project_list, stretch=1)

        term_lbl = QLabel("TERMINAL / SUGESTÕES E LOGS:")
        term_lbl.setStyleSheet("font-weight: 600; color: #8b949e; font-size: 11px;")
        self.terminal = TerminalWidget()
        right_col.addWidget(term_lbl)
        right_col.addWidget(self.terminal, stretch=1)

        cols.addLayout(left_col, stretch=1)
        cols.addLayout(right_col, stretch=1)
        main_layout.addLayout(cols, stretch=1)

        actions = QHBoxLayout()
        actions.setSpacing(10)
        self.btn_analyze = self._create_action_btn("Analisar", self.analyze_projects)
        self.btn_prune = self._create_action_btn("Apagar", self.request_prune)
        self.btn_confirm = self._create_action_btn("Confirmar", self.confirm_prune)
        self.btn_cancel = self._create_action_btn("Cancelar", self.cancel_prune)
        for btn in (self.btn_analyze, self.btn_prune):
            actions.addWidget(btn)
        actions.addStretch()
        for btn in (self.btn_confirm, self.btn_cancel):
            actions.addWidget(btn)
        main_layout.addLayout(actions)

        self.terminal.append_line("dev-local-artifact-pruner - Modo Múltiplos Projetos")
        self.terminal.append_line("Selecione a pasta raiz e clique em [Analisar].")

    def set_action_state(self, state: ActionState) -> None:
        self.current_state = state
        an, pr, cf, cc = ACTION_BUTTON_STATES.get(state, (True, False, False, False))
        for btn, enabled in ((self.btn_analyze, an), (self.btn_prune, pr), (self.btn_confirm, cf), (self.btn_cancel, cc)):
            btn.setEnabled(enabled)

    def browse_folder(self) -> None:
        init_dir = self.path_edit.text().strip() or str(Path.home())
        chosen = QFileDialog.getExistingDirectory(self, "Selecionar Pasta Raiz com Projetos", init_dir)
        if chosen:
            self.path_edit.setText(chosen)
            self.project_list.clear()
            self.discovered_projects = []
            self.set_action_state(ActionState.INITIAL)

    def _stop_worker(self) -> None:
        if self.scan_worker is not None and self.scan_worker.isRunning():
            self.scan_worker.cancel()
            self.scan_worker.wait(2000)

    def analyze_projects(self) -> None:
        raw_path = self.path_edit.text().strip()
        if not raw_path:
            self.terminal.log_warning("Aviso: Informe ou selecione a pasta raiz antes de analisar.")
            return
        target = Path(raw_path).expanduser().resolve()
        if not target.exists() or not target.is_dir():
            self.terminal.log_error(f"Erro: O caminho especificado não existe ou não é um diretório: {target}")
            return
        self._stop_worker()
        self.set_action_state(ActionState.ANALYZING)
        self.terminal.clear_terminal()
        self.terminal.append_line(f"project-pruner > scan-all {target.name}\nPasta raiz: {target}")
        self.terminal.append_line("Varrendo projetos em segundo plano...")
        self.project_list.clear()
        self.discovered_projects = []

        self.scan_worker = ScanWorker(root_path=target, scanner=self.scanner, parent=self)
        self.scan_worker.scan_finished.connect(self._on_scan_finished)
        self.scan_worker.error_occurred.connect(self._on_scan_error)
        self.scan_worker.start()

    def _on_scan_error(self, err_msg: str) -> None:
        self.terminal.log_error(f"Erro inesperado durante a varredura: {err_msg}")
        self.set_action_state(ActionState.COMPLETED)

    def _on_scan_finished(self, projects: List[Project]) -> None:
        self.discovered_projects = projects
        projects_with_artifacts = [p for p in projects if p.artifacts]
        if not projects_with_artifacts:
            self.terminal.append_line("\nNenhum projeto com artefatos descartáveis encontrado.")
            self.set_action_state(ActionState.COMPLETED)
            return

        self.project_list.populate_projects(projects_with_artifacts)
        self.terminal.append_line("\n💡 SUGESTÕES IDENTIFICADAS:\n")
        for proj in projects_with_artifacts:
            self._log_project_suggestion(proj)

        b_str = format_bytes(self.project_list.get_selected_bytes())
        count = len(self.project_list.get_selected_projects())
        self.terminal.append_line(f"Total selecionado: {b_str} ({count} projeto(s))\n")
        self.terminal.append_line("Aguardando ação: marque/desmarque projetos e clique em [Apagar] para preparar a poda.")
        self.set_action_state(ActionState.ANALYZED)

    def _log_project_suggestion(self, proj: Project) -> None:
        self.terminal.append_line(f"• {proj.name}:")
        if proj.git_info and proj.git_info.is_git_repo:
            rel = format_relative_time(proj.git_info.days_inactive) if proj.git_info.days_inactive is not None else "desconhecido"
            st = " (com alterações pendentes)" if proj.git_info.is_dirty else " (recente)"
            self.terminal.append_line(f"    Inativo {rel}." if proj.is_inactive else f"    Ativo {rel}{st}.")
        else:
            self.terminal.append_line("    Sem dados de versionamento Git.")

        size = format_bytes(proj.reclaimable_bytes if proj.reclaimable_bytes > 0 else proj.total_size_bytes)
        arts = ", ".join(sorted({a.name for a in proj.artifacts}))
        self.terminal.append_line(f"    {arts}: {size}")
        sugg = "    -> Sugestão: Limpar (projeto inativo)" if proj.is_inactive else "    -> Sugestão: Manter (projeto ativo)"
        if proj.is_inactive:
            self.terminal.log_error(sugg)
        else:
            self.terminal.log_success(sugg)
        self.terminal.append_line("")

    def _on_selection_changed(self) -> None:
        if self.current_state in (ActionState.ANALYZED, ActionState.PRUNING_REQUESTED, ActionState.COMPLETED):
            b_str = format_bytes(self.project_list.get_selected_bytes())
            count = len(self.project_list.get_selected_projects())
            self.terminal.append_line(f"Total selecionado atualizado: {b_str} ({count} projeto(s) marcados)")
            if self.current_state == ActionState.PRUNING_REQUESTED:
                self.set_action_state(ActionState.ANALYZED)
                self.terminal.append_line("Seleção alterada. Confirmação anterior cancelada. Clique em [Apagar] para preparar nova poda.")
            elif self.current_state == ActionState.COMPLETED and count > 0:
                self.set_action_state(ActionState.ANALYZED)

    def _on_project_clicked(self, project: Project) -> None:
        self.terminal.append_line(f"\n--- Detalhes: {project.name} ---\nCaminho: {project.root_path}")
        eco = "Node.js (package.json detectado)" if project.ecosystem == EcosystemType.NODE else ("Python (manifesto detectado)" if project.ecosystem == EcosystemType.PYTHON else "Desconhecido")
        self.terminal.append_line(f"Sistema: {eco}")
        if project.git_info and project.git_info.is_git_repo:
            clean = "limpo" if not project.git_info.is_dirty else "alterações pendentes (dirty)"
            rel = format_relative_time(project.git_info.days_inactive) if project.git_info.days_inactive is not None else "desconhecido"
            self.terminal.append_line(f"Último commit: {rel} | Git: {clean}")
        else:
            self.terminal.append_line("Git: Repositório não detectado")
        if project.artifacts:
            self.terminal.append_line("Artefatos elegíveis:")
            for art in project.artifacts:
                self.terminal.append_line(f"  • {art.name} ({format_bytes(art.size_bytes)})")
        self.terminal.append_line(f"Espaço recuperável: {format_bytes(project.reclaimable_bytes)}")
        if project.is_inactive:
            self.terminal.log_error("Status do projeto: Inativo (seguro para poda)")
        else:
            self.terminal.log_success("Status do projeto: Ativo (manter recomendado)")

    def request_prune(self) -> None:
        selected = self.project_list.get_selected_projects()
        if not selected:
            self.terminal.log_warning("Aviso: Nenhum projeto selecionado para poda. Marque pelo menos um projeto.")
            return
        self.terminal.append_line("")
        self.terminal.log_warning(f"Confirmação necessária: Deseja realmente podar os artefatos de {len(selected)} projeto(s) selecionado(s)?")
        self.terminal.append_line(f"Espaço total a ser liberado: {format_bytes(self.project_list.get_selected_bytes())}")
        for p in selected:
            self.terminal.append_line(f"  • {p.name} ({format_bytes(p.reclaimable_bytes)})")
        self.terminal.append_line("Clique em [Confirmar] para executar ou [Cancelar] para desistir.")
        self.set_action_state(ActionState.PRUNING_REQUESTED)

    def confirm_prune(self) -> None:
        selected = self.project_list.get_selected_projects()
        if not selected:
            self.set_action_state(ActionState.COMPLETED)
            return
        self.set_action_state(ActionState.PRUNING)
        self.terminal.append_line(f"\nproject-pruner > prune-multiple ({len(selected)} projetos)\nIniciando poda segura dos projetos selecionados...")
        QApplication.processEvents()
        try:
            summary = self.pruner.prune_multiple_projects(selected)
        except Exception as exc:
            self.terminal.log_error(f"Erro inesperado durante a poda: {exc}")
            self.set_action_state(ActionState.COMPLETED)
            return
        if summary.is_successful:
            self.terminal.log_success(f"Poda concluída com sucesso! Projetos podados: {summary.projects_pruned} | Espaço liberado: {format_bytes(summary.bytes_reclaimed)}")
            if summary.rebuild_scripts_created > 0:
                self.terminal.append_line(f"Scripts de reconstrução gerados: {summary.rebuild_scripts_created} arquivo(s) rebuild_dependencies.py")
        else:
            if summary.projects_pruned > 0:
                self.terminal.log_success(f"Poda parcial: {summary.projects_pruned} projeto(s) podados com sucesso | Espaço liberado: {format_bytes(summary.bytes_reclaimed)}")
            for err in summary.errors:
                self.terminal.log_error(f"Erro durante a poda: {err}")
        self.set_action_state(ActionState.COMPLETED)
        QApplication.processEvents()

    def cancel_prune(self) -> None:
        self.terminal.append_line("\nOperação de poda cancelada pelo usuário.")
        self.terminal.append_line("A seleção pode ser ajustada e você pode clicar em [Apagar] novamente.")
        self.set_action_state(ActionState.ANALYZED)

    def _on_back_clicked(self) -> None:
        self._stop_worker()
        self.back_requested.emit()

    def closeEvent(self, event: QCloseEvent) -> None:
        self._stop_worker()
        super().closeEvent(event)
