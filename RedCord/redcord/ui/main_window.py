from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from redcord.services.ai_assistant_service import AIAssistantService
from redcord.ui.widgets.ai_assistant_widget import AIAssistantWidget
from redcord.ui.widgets.concept_vault_widget import ConceptVaultWidget
from redcord.ui.widgets.document_tree import DocumentTreeWidget
from redcord.ui.widgets.editor_widget import EditorWidget
from redcord.ui.widgets.health_dashboard_widget import HealthDashboardWidget
from redcord.ui.widgets.settings_widget import SettingsWidget
from redcord.ui.widgets.version_history_widget import VersionHistoryWidget


class RedCordMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RedCord - Desktop Writer")
        self.resize(1400, 850)

        self.ai_service = AIAssistantService()
        self._build_ui()
        self._bind_actions()

        self.autosave_timer = QTimer(self)
        self.autosave_timer.setInterval(10_000)
        self.autosave_timer.timeout.connect(self._tick_autosave)
        self.autosave_timer.start()

    def _build_ui(self) -> None:
        root = QWidget()
        root_layout = QVBoxLayout(root)
        self.setCentralWidget(root)

        splitter = QSplitter()

        # Left panel
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        self.doc_tree = DocumentTreeWidget()
        self.doc_tree.load_sample()
        self.btn_new_doc = QPushButton("New Document")
        self.btn_new_concept = QPushButton("New Concept")
        left_layout.addWidget(self.doc_tree)
        left_layout.addWidget(self.btn_new_doc)
        left_layout.addWidget(self.btn_new_concept)

        # Center tabs
        self.tabs = QTabWidget()
        self.editor_widget = EditorWidget()
        self.concept_widget = ConceptVaultWidget()
        self.version_widget = VersionHistoryWidget()
        self.ai_widget = AIAssistantWidget()
        self.health_widget = HealthDashboardWidget()
        self.settings_widget = SettingsWidget()

        self.tabs.addTab(self.editor_widget, "Editor")
        self.tabs.addTab(self.concept_widget, "Concept Vault")
        self.tabs.addTab(self.version_widget, "Version History")
        self.tabs.addTab(self.ai_widget, "AI Assistant")
        self.tabs.addTab(self.health_widget, "Health")
        self.tabs.addTab(self.settings_widget, "Settings")

        # Right panel
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        self.version_widget_side = VersionHistoryWidget()
        self.meta_label = QLabel("Metadata: type=Character, tags=hero,arc")
        right_layout.addWidget(self.version_widget_side)
        right_layout.addWidget(self.meta_label)

        splitter.addWidget(left_panel)
        splitter.addWidget(self.tabs)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(1, 1)

        root_layout.addWidget(splitter)

        status = QStatusBar()
        self.setStatusBar(status)
        self.status_autosave = QLabel("Autosave: active")
        self.status_db = QLabel("Database: unknown")
        self.status_ver = QLabel("Version: v0")
        self.status_health = QLabel("Health: yellow")
        status.addPermanentWidget(self.status_autosave)
        status.addPermanentWidget(self.status_db)
        status.addPermanentWidget(self.status_ver)
        status.addPermanentWidget(self.status_health)

    def _bind_actions(self) -> None:
        self.ai_widget.improve_btn.clicked.connect(self._ai_improve)
        self.ai_widget.suggest_btn.clicked.connect(self._ai_suggest)
        self.health_widget.sim_crash.clicked.connect(self._simulate_crash)
        self.health_widget.corrupt_doc.clicked.connect(self._simulate_corrupt)

    def _ai_improve(self) -> None:
        text = self.editor_widget.get_text()
        self.ai_widget.output.setPlainText(self.ai_service.improve_text(text))

    def _ai_suggest(self) -> None:
        text = self.editor_widget.get_text()
        self.ai_widget.output.setPlainText(self.ai_service.suggest_ideas(text))

    def _simulate_crash(self) -> None:
        self.health_widget.set_status_text("Simulation: editor crash emulated safely")

    def _simulate_corrupt(self) -> None:
        current = self.editor_widget.get_text()
        self.editor_widget.set_text(current + "\n[CORRUPTED-MOCK]")
        self.health_widget.set_status_text("Simulation: document corruption mock applied")

    def _tick_autosave(self) -> None:
        self.statusBar().showMessage("Autosave draft captured", 2000)
