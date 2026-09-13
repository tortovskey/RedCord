from __future__ import annotations

import logging
import re
import uuid
from pathlib import Path

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QIcon, QKeySequence, QShortcut, QTextCursor, QTextDocument
from PyQt6.QtPrintSupport import QPrinter
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QSplitter,
    QStyle,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from redcord import __version__
from redcord.app.config import get_settings
from redcord.app.theme import build_qss, display_name_by_key, key_by_name, theme_names
from redcord.db.models import Commit, Concept, Document, Project
from redcord.services.account_service import AccountService
from redcord.services.ai_editor_service import AIEditorService
from redcord.services.branch_service import BranchService
from redcord.services.commit_service import CommitService
from redcord.services.concept_service import ConceptService
from redcord.services.document_service import DocumentService
from redcord.services.export_service import ExportErrorForUser, ExportService
from redcord.services.import_service import ImportErrorForUser, ImportService
from redcord.services.search_service import SearchService
from redcord.services.settings_service import SettingsService
from redcord.services.template_service import TemplateService
from redcord.services.text_tools import WRITER_BLOCKS, clear_markdown_marks, number_lines, text_statistics
from redcord.ui.dialogs.commit_dialog import CommitDialog
from redcord.ui.dialogs.commit_history_dialog import CommitHistoryDialog
from redcord.ui.dialogs.new_document_dialog import NewDocumentDialog
from redcord.ui.dialogs.profile_settings_dialog import ProfileSettingsDialog
from redcord.ui.dialogs.template_manager_dialog import TemplateManagerDialog
from redcord.ui.dialogs.update_dialog import UpdateDialog
from redcord.ui.tabs.ai_agent_tab import AIAgentTab
from redcord.ui.tabs.documents_tab import DocumentsTab
from redcord.ui.widgets.ribbon_toolbar import RibbonToolbar
from redcord.ui.widgets.self_healing_panel import SelfHealingPanel
from redcord.ui.widgets.status_bar import RedCordStatusBar

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Tabbed RedCord shell for documents, concepts, AI tools, Git-like tools and settings."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"RedCord {__version__}")
        self._set_window_icon()

        self.document_service = DocumentService()
        self.template_service = TemplateService()
        self.import_service = ImportService()
        self.export_service = ExportService()
        self.commit_service = CommitService()
        self.branch_service = BranchService()
        self.concept_service = ConceptService()
        self.search_service = SearchService()
        self.settings_service = SettingsService()
        self.account_service = AccountService()
        self.ai_editor_service = AIEditorService()

        self.user_settings = self.settings_service.load()
        self.active_account = self.account_service.active_account()

        self.projects: dict[str, Project] = {}
        self.documents: dict[str, Document] = {}
        self.search_results: dict[str, Document] = {}
        self.concepts: dict[str, Concept] = {}
        self.commits: dict[str, Commit] = {}

        self.current_project_id: uuid.UUID | None = None
        self.current_document_id: uuid.UUID | None = None
        self.current_concept_id: uuid.UUID | None = None
        self.is_dirty = False
        self.autosave_enabled = self.user_settings.autosave_enabled

        self.autosave_timer = QTimer(self)
        self.autosave_timer.setInterval(30_000)
        self.autosave_timer.timeout.connect(self.autosave)
        self.autosave_timer.start()

        self.save_feedback_timer = QTimer(self)
        self.save_feedback_timer.setSingleShot(True)
        self.save_feedback_timer.timeout.connect(self._restore_save_button)

        self.compact_mode_enabled = False
        self.focus_mode_enabled = False

        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)

        self.ribbon = RibbonToolbar(self)
        self.ribbon.actionTriggered.connect(self.handle_ribbon_action)
        central_layout.addWidget(self.ribbon)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_documents_tab(), "Документы")
        self.tabs.addTab(self._build_concepts_tab(), "Концепты")
        self.tabs.addTab(self._build_git_tab(), "Git / версии")
        self.tabs.addTab(self._build_ai_agent_tab(), "ИИ-агент")
        self.tabs.addTab(SelfHealingPanel(), "Self-Healing")
        self.tabs.addTab(self._build_settings_tab(), "Настройки")
        central_layout.addWidget(self.tabs, 1)

        self.setCentralWidget(central)
        self.setStatusBar(RedCordStatusBar())
        self._setup_shortcuts()

        self.reload_projects()
        self.refresh_profile_labels()
        self.set_status("Готово")

    def _set_window_icon(self) -> None:
        settings = get_settings()
        icon_path = settings.assets_dir / "redcord_icon.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
            return
        png_path = settings.assets_dir / "redcord_icon.png"
        if png_path.exists():
            self.setWindowIcon(QIcon(str(png_path)))

    def _standard_icon(self, icon_name: QStyle.StandardPixmap) -> QIcon:
        return self.style().standardIcon(icon_name)

    def _panel(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("Panel")
        return frame

    def _section(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("SectionLabel")
        return label

    def _title(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("TitleLabel")
        return label

    def set_status(self, text: str) -> None:
        self.statusBar().showMessage(text)

    def show_error(self, title: str, exc: Exception | str) -> None:
        logger.exception("%s: %s", title, exc)
        QMessageBox.critical(self, title, str(exc))

    # ---------------------------------------------------------------------
    # Documents tab
    # ---------------------------------------------------------------------
    def _build_documents_tab(self) -> QWidget:
        self.documents_tab = DocumentsTab(autosave_enabled=self.autosave_enabled, parent=self)
        sidebar = self.documents_tab.sidebar
        editor_panel = self.documents_tab.editor_panel
        inspector = self.documents_tab.inspector

        self.profile_label = sidebar.profile_label
        self.project_list = sidebar.project_list
        self.document_list = sidebar.document_list
        self.new_project_btn = sidebar.new_project_btn
        self.new_document_btn = sidebar.new_document_btn
        self.import_btn = sidebar.import_btn
        self.import_folder_btn = sidebar.import_folder_btn
        self.types_btn = sidebar.types_btn

        self.title_edit = editor_panel.title_edit
        self.type_combo = editor_panel.type_combo
        self.tags_edit = editor_panel.tags_edit
        self.category_edit = editor_panel.category_edit
        self.editor = editor_panel.editor
        self.save_btn = editor_panel.save_btn
        self.save_as_btn = editor_panel.save_as_btn
        self.autosave_btn = editor_panel.autosave_btn
        self.commit_btn = editor_panel.commit_btn
        self.history_btn = editor_panel.history_btn
        self.save_feedback_label = editor_panel.save_feedback_label

        self.info_label = inspector.info_label
        self.commit_list_side = inspector.commit_list_side
        self.commit_delete_side_btn = inspector.commit_delete_side_btn
        self.search_edit = inspector.search_edit
        self.search_btn = inspector.search_btn
        self.search_results_list = inspector.search_results_list
        self.writer_find_edit = inspector.writer_find_edit
        self.writer_replace_edit = inspector.writer_replace_edit
        self.writer_find_btn = inspector.writer_find_btn
        self.writer_replace_one_btn = inspector.writer_replace_one_btn
        self.writer_replace_all_btn = inspector.writer_replace_all_btn
        self.word_stats_label = inspector.word_stats_label
        self.refresh_stats_btn = inspector.refresh_stats_btn

        self.project_list.currentItemChanged.connect(self.on_project_selected)
        self.document_list.currentItemChanged.connect(self.on_document_selected)
        self.new_project_btn.clicked.connect(self.create_project)
        self.new_document_btn.clicked.connect(self.create_document)
        self.import_btn.clicked.connect(self.import_document)
        self.import_folder_btn.clicked.connect(self.import_folder)
        self.types_btn.clicked.connect(self.open_template_manager)

        self.reload_type_combo()
        for widget in [self.title_edit, self.tags_edit, self.category_edit]:
            widget.textChanged.connect(self.mark_dirty)
        self.type_combo.currentIndexChanged.connect(self.mark_dirty)
        self.editor.textChanged.connect(self.mark_dirty)

        self.save_btn.clicked.connect(self.save_current_document)
        self.save_as_btn.clicked.connect(self.save_as_file)
        self.autosave_btn.clicked.connect(self.toggle_autosave)
        self.commit_btn.clicked.connect(self.create_commit)
        self.history_btn.clicked.connect(self.open_commit_history)

        self.commit_list_side.itemDoubleClicked.connect(lambda _: self.open_commit_history())
        self.commit_delete_side_btn.clicked.connect(self.delete_selected_commit_side)
        self.search_edit.returnPressed.connect(self.search)
        self.search_btn.clicked.connect(self.search)
        self.search_results_list.itemDoubleClicked.connect(self.open_search_result)

        self.writer_find_edit.returnPressed.connect(self.writer_find_next)
        self.writer_find_btn.clicked.connect(self.writer_find_next)
        self.writer_replace_one_btn.clicked.connect(self.writer_replace_one)
        self.writer_replace_all_btn.clicked.connect(self.writer_replace_all)
        self.refresh_stats_btn.clicked.connect(self.refresh_writer_stats)
        return self.documents_tab

    def _build_nav_panel(self) -> QWidget:
        panel = self._panel()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.profile_label = self._title("RedCord")
        layout.addWidget(self.profile_label)

        layout.addWidget(self._section("Проекты"))
        self.project_list = QListWidget()
        self.project_list.currentItemChanged.connect(self.on_project_selected)
        layout.addWidget(self.project_list, 1)

        self.new_project_btn = QPushButton("Новый проект")
        self.new_project_btn.setIcon(self._standard_icon(QStyle.StandardPixmap.SP_FileDialogNewFolder))
        self.new_project_btn.clicked.connect(self.create_project)
        layout.addWidget(self.new_project_btn)

        layout.addWidget(self._section("Документы"))
        self.document_list = QListWidget()
        self.document_list.currentItemChanged.connect(self.on_document_selected)
        layout.addWidget(self.document_list, 2)

        self.new_document_btn = QPushButton("Новый документ")
        self.import_btn = QPushButton("Импорт файла")
        self.import_folder_btn = QPushButton("Импорт папки")
        self.types_btn = QPushButton("Типы документов")
        self.new_document_btn.setIcon(self._standard_icon(QStyle.StandardPixmap.SP_FileIcon))
        self.import_btn.setIcon(self._standard_icon(QStyle.StandardPixmap.SP_DialogOpenButton))
        self.import_folder_btn.setIcon(self._standard_icon(QStyle.StandardPixmap.SP_DirOpenIcon))
        self.types_btn.setIcon(self._standard_icon(QStyle.StandardPixmap.SP_FileDialogInfoView))

        self.new_document_btn.clicked.connect(self.create_document)
        self.import_btn.clicked.connect(self.import_document)
        self.import_folder_btn.clicked.connect(self.import_folder)
        self.types_btn.clicked.connect(self.open_template_manager)

        for button in [self.new_document_btn, self.import_btn, self.import_folder_btn, self.types_btn]:
            layout.addWidget(button)
        return panel

    def _build_editor_panel(self) -> QWidget:
        panel = self._panel()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        layout.addWidget(self._title("Редактор"))
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Название документа")
        self.type_combo = QComboBox()
        self.reload_type_combo()
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("Теги через запятую")
        self.category_edit = QLineEdit()
        self.category_edit.setPlaceholderText("Категория")

        for widget in [self.title_edit, self.tags_edit, self.category_edit]:
            widget.textChanged.connect(self.mark_dirty)
            layout.addWidget(widget)
        self.type_combo.currentIndexChanged.connect(self.mark_dirty)
        layout.addWidget(self.type_combo)

        self.editor = QTextEdit()
        self.editor.setPlaceholderText("Пиши сцену, лор, персонажа или заметку. RedCord держит чернила в узде.")
        self.editor.textChanged.connect(self.mark_dirty)
        layout.addWidget(self.editor, 1)

        buttons = QHBoxLayout()
        self.save_btn = QPushButton("Сохранить")
        self.save_btn.setObjectName("AccentButton")
        self.save_as_btn = QPushButton("Сохранить как...")
        self.autosave_btn = QPushButton("Автосохранение: включено" if self.autosave_enabled else "Автосохранение: выключено")
        self.commit_btn = QPushButton("Коммит")
        self.history_btn = QPushButton("История")
        self.save_btn.setIcon(self._standard_icon(QStyle.StandardPixmap.SP_DialogSaveButton))
        self.save_as_btn.setIcon(self._standard_icon(QStyle.StandardPixmap.SP_DriveFDIcon))
        self.autosave_btn.setIcon(self._standard_icon(QStyle.StandardPixmap.SP_BrowserReload))
        self.commit_btn.setIcon(self._standard_icon(QStyle.StandardPixmap.SP_CommandLink))
        self.history_btn.setIcon(self._standard_icon(QStyle.StandardPixmap.SP_FileDialogDetailedView))

        self.save_btn.clicked.connect(self.save_current_document)
        self.save_as_btn.clicked.connect(self.save_as_file)
        self.autosave_btn.clicked.connect(self.toggle_autosave)
        self.commit_btn.clicked.connect(self.create_commit)
        self.history_btn.clicked.connect(self.open_commit_history)

        for button in [self.save_btn, self.save_as_btn, self.autosave_btn, self.commit_btn, self.history_btn]:
            buttons.addWidget(button)
        layout.addLayout(buttons)

        self.save_feedback_label = QLabel("✔ Сохранено")
        self.save_feedback_label.setObjectName("SuccessLabel")
        self.save_feedback_label.hide()
        layout.addWidget(self.save_feedback_label)
        return panel

    def _build_document_side_panel(self) -> QWidget:
        panel = self._panel()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        layout.addWidget(self._title("Сводка"))
        self.info_label = QLabel("Документ не выбран")
        self.info_label.setObjectName("MutedLabel")
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)

        layout.addWidget(self._section("Последние коммиты"))
        self.commit_list_side = QListWidget()
        self.commit_list_side.itemDoubleClicked.connect(lambda _: self.open_commit_history())
        layout.addWidget(self.commit_list_side, 1)

        commit_buttons = QHBoxLayout()
        self.commit_delete_side_btn = QPushButton("Удалить")
        self.commit_delete_side_btn.setObjectName("DangerButton")
        self.commit_delete_side_btn.clicked.connect(self.delete_selected_commit_side)
        commit_buttons.addWidget(self.commit_delete_side_btn)
        commit_buttons.addStretch(1)
        layout.addLayout(commit_buttons)

        layout.addWidget(self._section("Поиск"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Название, текст, теги, категория")
        self.search_edit.returnPressed.connect(self.search)
        self.search_btn = QPushButton("Искать")
        self.search_btn.clicked.connect(self.search)
        self.search_results_list = QListWidget()
        self.search_results_list.itemDoubleClicked.connect(self.open_search_result)
        layout.addWidget(self.search_edit)
        layout.addWidget(self.search_btn)
        layout.addWidget(self.search_results_list, 1)
        return panel

    # ---------------------------------------------------------------------
    # Concepts tab
    # ---------------------------------------------------------------------
    def _build_concepts_tab(self) -> QWidget:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        left = self._panel()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.addWidget(self._title("Концепты"))
        self.concept_list = QListWidget()
        self.concept_list.currentItemChanged.connect(self.load_selected_concept)
        left_layout.addWidget(self.concept_list, 1)
        self.new_concept_btn = QPushButton("Новый концепт")
        self.delete_concept_btn = QPushButton("Удалить")
        self.delete_concept_btn.setObjectName("DangerButton")
        self.convert_concept_btn = QPushButton("В документ")
        self.new_concept_btn.clicked.connect(self.create_concept)
        self.delete_concept_btn.clicked.connect(self.delete_concept)
        self.convert_concept_btn.clicked.connect(self.convert_concept)
        for button in [self.new_concept_btn, self.convert_concept_btn, self.delete_concept_btn]:
            left_layout.addWidget(button)

        right = self._panel()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(12, 12, 12, 12)
        right_layout.addWidget(self._title("Редактор концепта"))
        self.concept_title_edit = QLineEdit()
        self.concept_title_edit.setPlaceholderText("Название концепта")
        self.concept_status_combo = QComboBox()
        self.concept_status_combo.addItems(["Идея", "В разработке", "Использовано", "Архив"])
        self.concept_editor = QTextEdit()
        self.save_concept_btn = QPushButton("Сохранить концепт")
        self.save_concept_btn.setObjectName("AccentButton")
        self.save_concept_btn.clicked.connect(self.save_concept)
        right_layout.addWidget(self.concept_title_edit)
        right_layout.addWidget(self.concept_status_combo)
        right_layout.addWidget(self.concept_editor, 1)
        right_layout.addWidget(self.save_concept_btn)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        return splitter

    # ---------------------------------------------------------------------
    # Git tab
    # ---------------------------------------------------------------------
    def _build_git_tab(self) -> QWidget:
        splitter = QSplitter(Qt.Orientation.Horizontal)

        commits_panel = self._panel()
        commits_layout = QVBoxLayout(commits_panel)
        commits_layout.setContentsMargins(12, 12, 12, 12)
        commits_layout.addWidget(self._title("Коммиты"))
        self.commit_list_git = QListWidget()
        self.commit_list_git.currentItemChanged.connect(self.preview_selected_commit)
        commits_layout.addWidget(self.commit_list_git, 1)

        commit_buttons_1 = QHBoxLayout()
        self.commit_new_git_btn = QPushButton("Создать")
        self.commit_rename_git_btn = QPushButton("Переименовать")
        self.commit_delete_git_btn = QPushButton("Удалить")
        self.commit_delete_git_btn.setObjectName("DangerButton")
        self.commit_new_git_btn.clicked.connect(self.create_commit)
        self.commit_rename_git_btn.clicked.connect(self.rename_selected_commit)
        self.commit_delete_git_btn.clicked.connect(self.delete_selected_commit_git)
        for button in [self.commit_new_git_btn, self.commit_rename_git_btn, self.commit_delete_git_btn]:
            commit_buttons_1.addWidget(button)
        commits_layout.addLayout(commit_buttons_1)

        self.commit_preview = QTextEdit()
        self.commit_preview.setReadOnly(True)
        commits_layout.addWidget(self.commit_preview, 1)
        self.rollback_git_btn = QPushButton("Откатить к выбранному коммиту")
        self.rollback_git_btn.clicked.connect(self.rollback_selected_commit)
        commits_layout.addWidget(self.rollback_git_btn)

        branch_panel = self._panel()
        branch_layout = QVBoxLayout(branch_panel)
        branch_layout.setContentsMargins(12, 12, 12, 12)
        branch_layout.addWidget(self._title("Ветки"))
        self.branch_list = QListWidget()
        branch_layout.addWidget(self.branch_list, 1)
        self.branch_new_btn = QPushButton("Новая ветка")
        self.branch_save_btn = QPushButton("Сохранить снимок")
        self.branch_checkout_btn = QPushButton("Переключиться")
        self.branch_delete_btn = QPushButton("Удалить ветку")
        self.branch_delete_btn.setObjectName("DangerButton")
        self.branch_new_btn.clicked.connect(self.create_branch)
        self.branch_save_btn.clicked.connect(self.save_branch_snapshot)
        self.branch_checkout_btn.clicked.connect(self.checkout_branch)
        self.branch_delete_btn.clicked.connect(self.delete_branch)
        for button in [self.branch_new_btn, self.branch_save_btn, self.branch_checkout_btn, self.branch_delete_btn]:
            branch_layout.addWidget(button)

        splitter.addWidget(commits_panel)
        splitter.addWidget(branch_panel)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        return splitter

    # ---------------------------------------------------------------------
    # AI agent tab
    # ---------------------------------------------------------------------
    def _build_ai_agent_tab(self) -> QWidget:
        self.ai_agent_tab = AIAgentTab(
            get_document_text=self.current_selected_or_all_text,
            insert_result=self.ai_insert_result_text,
            replace_document=self.ai_replace_document_text,
            replace_selection=self.ai_replace_selection_text,
            create_document_from_result=self.ai_create_document_from_result,
            set_status=self.set_status,
            parent=self,
        )
        return self.ai_agent_tab

    def _build_ai_editor_tab(self) -> QWidget:
        splitter = QSplitter(Qt.Orientation.Horizontal)

        left = self._panel()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(14, 14, 14, 14)
        left_layout.setSpacing(8)
        left_layout.addWidget(self._title("ИИ-агент текста"))
        hint = QLabel(
            "Локальная mock-версия: текст никуда не отправляется. "
            "Позже сюда можно подключить OpenAI или локальную модель."
        )
        hint.setObjectName("MutedLabel")
        hint.setWordWrap(True)
        left_layout.addWidget(hint)

        self.ai_source = QTextEdit()
        self.ai_source.setPlaceholderText("Вставь сюда текст или нажми «Взять из документа».")
        left_layout.addWidget(self.ai_source, 1)

        source_buttons = QHBoxLayout()
        self.ai_take_btn = QPushButton("Взять из документа")
        self.ai_apply_btn = QPushButton("Применить результат")
        self.ai_insert_btn = QPushButton("Вставить в документ")
        self.ai_take_btn.clicked.connect(self.ai_take_from_document)
        self.ai_apply_btn.clicked.connect(self.ai_apply_result_to_document)
        self.ai_insert_btn.clicked.connect(self.ai_insert_result_to_document)
        for button in [self.ai_take_btn, self.ai_apply_btn, self.ai_insert_btn]:
            source_buttons.addWidget(button)
        left_layout.addLayout(source_buttons)

        actions = self._panel()
        actions_layout = QVBoxLayout(actions)
        actions_layout.setContentsMargins(14, 14, 14, 14)
        actions_layout.setSpacing(8)
        actions_layout.addWidget(self._title("Действия"))

        action_map = [
            ("Улучшить текст", self.ai_improve_text),
            ("Краткое содержание", self.ai_summarize),
            ("Развить сцену", self.ai_expand_scene),
            ("Найти противоречия", self.ai_find_contradictions),
            ("Вопросы персонажу", self.ai_character_questions),
            ("Названия главы", self.ai_title_ideas),
            ("Почистить диалоги", self.ai_fix_dialogue),
        ]
        for label, handler in action_map:
            btn = QPushButton(label)
            btn.clicked.connect(handler)
            actions_layout.addWidget(btn)
        actions_layout.addStretch(1)

        right = self._panel()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(14, 14, 14, 14)
        right_layout.addWidget(self._title("Результат"))
        self.ai_result = QTextEdit()
        self.ai_result.setPlaceholderText("Здесь появится результат ИИ-агента.")
        right_layout.addWidget(self.ai_result, 1)

        splitter.addWidget(left)
        splitter.addWidget(actions)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 2)
        return splitter

    # ---------------------------------------------------------------------
    # Legacy writer tools panel kept for compatibility; 0.8 uses the new ribbon UI.
    # ---------------------------------------------------------------------
    def _build_writer_tools_tab(self) -> QWidget:
        panel = self._panel()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        layout.addWidget(self._title("Инструменты писателя"))
        hint = QLabel(
            "Инструменты работают с текущим документом. Форматирование применяется как Markdown-разметка."
        )
        hint.setObjectName("MutedLabel")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        stats_row = QHBoxLayout()
        self.word_stats_label = QLabel("Статистика: документ не выбран")
        self.refresh_stats_btn = QPushButton("Обновить статистику")
        self.refresh_stats_btn.clicked.connect(self.refresh_writer_stats)
        stats_row.addWidget(self.word_stats_label, 1)
        stats_row.addWidget(self.refresh_stats_btn)
        layout.addLayout(stats_row)

        find_panel = self._panel()
        find_layout = QVBoxLayout(find_panel)
        find_layout.setContentsMargins(12, 12, 12, 12)
        find_layout.addWidget(self._section("Поиск и замена"))
        self.writer_find_edit = QLineEdit()
        self.writer_find_edit.setPlaceholderText("Найти")
        self.writer_replace_edit = QLineEdit()
        self.writer_replace_edit.setPlaceholderText("Заменить на")
        find_buttons = QHBoxLayout()
        self.writer_find_btn = QPushButton("Найти")
        self.writer_replace_one_btn = QPushButton("Заменить")
        self.writer_replace_all_btn = QPushButton("Заменить всё")
        self.writer_find_btn.clicked.connect(self.writer_find_next)
        self.writer_replace_one_btn.clicked.connect(self.writer_replace_one)
        self.writer_replace_all_btn.clicked.connect(self.writer_replace_all)
        for button in [self.writer_find_btn, self.writer_replace_one_btn, self.writer_replace_all_btn]:
            find_buttons.addWidget(button)
        find_layout.addWidget(self.writer_find_edit)
        find_layout.addWidget(self.writer_replace_edit)
        find_layout.addLayout(find_buttons)
        layout.addWidget(find_panel)

        format_panel = self._panel()
        format_layout = QVBoxLayout(format_panel)
        format_layout.setContentsMargins(12, 12, 12, 12)
        format_layout.addWidget(self._section("Разметка и вставки"))
        row1 = QHBoxLayout()
        tools_1 = [
            ("Жирный", lambda: self.wrap_selection("**", "**")),
            ("Курсив", lambda: self.wrap_selection("*", "*")),
            ("Подчёрк.", lambda: self.wrap_selection("<u>", "</u>")),
            ("Зачёрк.", lambda: self.wrap_selection("~~", "~~")),
            ("Цитата", lambda: self.prefix_selection("> ")),
        ]
        for label, handler in tools_1:
            btn = QPushButton(label)
            btn.clicked.connect(handler)
            row1.addWidget(btn)
        format_layout.addLayout(row1)

        row2 = QHBoxLayout()
        tools_2 = [
            ("H1", lambda: self.insert_block("# Заголовок\n\n")),
            ("H2", lambda: self.insert_block("## Заголовок\n\n")),
            ("H3", lambda: self.insert_block("### Заголовок\n\n")),
            ("Сцена", lambda: self.insert_block("\n---\n\n## Сцена\n\n**Цель:** ...\n\n**Конфликт:** ...\n\n**Последствие:** ...\n\n")),
            ("Диалог", lambda: self.insert_block("\n— Реплика персонажа.\n— Ответ другого персонажа.\n")),
            ("Заметка автора", lambda: self.insert_block("\n> [!NOTE] Заметка автора: ...\n")),
        ]
        for label, handler in tools_2:
            btn = QPushButton(label)
            btn.clicked.connect(handler)
            row2.addWidget(btn)
        format_layout.addLayout(row2)
        layout.addWidget(format_panel)

        edit_panel = self._panel()
        edit_layout = QVBoxLayout(edit_panel)
        edit_layout.setContentsMargins(12, 12, 12, 12)
        edit_layout.addWidget(self._section("Быстрое редактирование"))
        row3 = QHBoxLayout()
        tools_3 = [
            ("Undo", lambda: self.editor.undo()),
            ("Redo", lambda: self.editor.redo()),
            ("Cut", lambda: self.editor.cut()),
            ("Copy", lambda: self.editor.copy()),
            ("Paste", lambda: self.editor.paste()),
            ("Очистить формат", self.clear_markdown_marks),
        ]
        for label, handler in tools_3:
            btn = QPushButton(label)
            btn.clicked.connect(handler)
            row3.addWidget(btn)
        edit_layout.addLayout(row3)
        layout.addWidget(edit_panel)
        layout.addStretch(1)
        return panel

    # ---------------------------------------------------------------------
    # Settings tab
    # ---------------------------------------------------------------------
    def _build_settings_tab(self) -> QWidget:
        panel = self._panel()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        layout.addWidget(self._title("Настройки и обслуживание"))
        self.settings_profile_label = QLabel("")
        self.settings_profile_label.setObjectName("MutedLabel")
        layout.addWidget(self.settings_profile_label)

        self.theme_combo_settings = QComboBox()
        self.theme_combo_settings.addItems(theme_names())
        self.theme_combo_settings.setCurrentText(display_name_by_key(self.user_settings.theme))
        self.theme_combo_settings.currentTextChanged.connect(self.apply_theme_from_settings)
        layout.addWidget(QLabel("Тема"))
        layout.addWidget(self.theme_combo_settings)

        self.profile_btn = QPushButton("Локальные аккаунты и профиль")
        self.template_btn_settings = QPushButton("Типы документов")
        self.update_btn = QPushButton("Обновить из ZIP-архива")
        self.profile_btn.clicked.connect(self.open_profile_settings)
        self.template_btn_settings.clicked.connect(self.open_template_manager)
        self.update_btn.clicked.connect(self.open_update_dialog)
        for button in [self.profile_btn, self.template_btn_settings, self.update_btn]:
            layout.addWidget(button)
        layout.addStretch(1)
        return panel

    # ---------------------------------------------------------------------
    # Reload helpers
    # ---------------------------------------------------------------------
    def refresh_profile_labels(self) -> None:
        self.active_account = self.account_service.active_account()
        self.setWindowTitle(f"RedCord {__version__} — {self.active_account.display_name}")
        if hasattr(self, "profile_label"):
            self.profile_label.setText(f"RedCord {__version__}\n{self.active_account.display_name}")
        if hasattr(self, "settings_profile_label"):
            self.settings_profile_label.setText(
                f"Аккаунт: {self.active_account.display_name} @{self.active_account.username}\n"
                f"Данные: {get_settings().data_dir}"
            )

    def reload_type_combo(self) -> None:
        if not hasattr(self, "type_combo"):
            return
        current = self.type_combo.currentData()
        self.type_combo.blockSignals(True)
        self.type_combo.clear()
        for template_type, name in self.template_service.list_templates():
            self.type_combo.addItem(name, template_type)
        if current:
            index = self.type_combo.findData(current)
            if index >= 0:
                self.type_combo.setCurrentIndex(index)
        self.type_combo.blockSignals(False)

    def reload_projects(self) -> None:
        current = str(self.current_project_id) if self.current_project_id else None
        self.project_list.blockSignals(True)
        self.project_list.clear()
        self.projects.clear()
        for project in self.document_service.list_projects():
            item = QListWidgetItem(project.title)
            item.setData(256, str(project.id))
            self.project_list.addItem(item)
            self.projects[str(project.id)] = project
        self.project_list.blockSignals(False)

        if self.project_list.count() > 0:
            target_row = 0
            if current:
                for row in range(self.project_list.count()):
                    if self.project_list.item(row).data(256) == current:
                        target_row = row
                        break
            self.project_list.setCurrentRow(target_row)
        else:
            self.reload_documents()
            self.reload_concepts()

    def reload_documents(self, select_document_id: uuid.UUID | None = None) -> None:
        self.document_list.blockSignals(True)
        self.document_list.clear()
        self.documents.clear()
        if self.current_project_id is not None:
            for document in self.document_service.list_documents(self.current_project_id):
                item = QListWidgetItem(f"{document.title} · {document.type}")
                item.setData(256, str(document.id))
                self.document_list.addItem(item)
                self.documents[str(document.id)] = document
        self.document_list.blockSignals(False)

        target = str(select_document_id or self.current_document_id) if (select_document_id or self.current_document_id) else None
        if target:
            for row in range(self.document_list.count()):
                if self.document_list.item(row).data(256) == target:
                    self.document_list.setCurrentRow(row)
                    return

    def reload_concepts(self) -> None:
        if not hasattr(self, "concept_list"):
            return
        self.concept_list.blockSignals(True)
        self.concept_list.clear()
        self.concepts.clear()
        if self.current_project_id is not None:
            for concept in self.concept_service.list_concepts(self.current_project_id):
                item = QListWidgetItem(f"[{concept.status}] {concept.title}")
                item.setData(256, str(concept.id))
                self.concept_list.addItem(item)
                self.concepts[str(concept.id)] = concept
        self.concept_list.blockSignals(False)

    def reload_commits(self) -> None:
        for widget in [getattr(self, "commit_list_side", None), getattr(self, "commit_list_git", None)]:
            if widget is not None:
                widget.clear()
        self.commits.clear()
        if self.current_document_id is None:
            if hasattr(self, "commit_preview"):
                self.commit_preview.clear()
            return
        commits = self.commit_service.list_commits(self.current_document_id)
        for commit in commits:
            text = f"{commit.created_at:%Y-%m-%d %H:%M:%S} — {commit.message}"
            self.commits[str(commit.id)] = commit
            item_git = QListWidgetItem(text)
            item_git.setData(256, str(commit.id))
            self.commit_list_git.addItem(item_git)
        for commit in commits[:10]:
            item = QListWidgetItem(f"{commit.created_at:%H:%M:%S} — {commit.message}")
            item.setData(256, str(commit.id))
            self.commit_list_side.addItem(item)

    def reload_branches(self) -> None:
        if not hasattr(self, "branch_list"):
            return
        self.branch_list.clear()
        if self.current_document_id is None:
            return
        for branch in self.branch_service.list_branches(self.current_document_id):
            item = QListWidgetItem(f"{branch.name} · {branch.updated_at.replace('T', ' ')}")
            item.setData(256, branch.id)
            self.branch_list.addItem(item)

    # ---------------------------------------------------------------------
    # Project/document operations
    # ---------------------------------------------------------------------
    def on_project_selected(self) -> None:
        item = self.project_list.currentItem()
        self.current_project_id = uuid.UUID(str(item.data(256))) if item else None
        self.current_document_id = None
        self.clear_editor()
        self.reload_documents()
        self.reload_concepts()

    def on_document_selected(self) -> None:
        item = self.document_list.currentItem()
        if item:
            self.load_document(uuid.UUID(str(item.data(256))))

    def clear_editor(self) -> None:
        self.current_document_id = None
        for widget in [self.title_edit, self.tags_edit, self.category_edit]:
            widget.clear()
        self.editor.clear()
        self.info_label.setText("Документ не выбран")
        self.is_dirty = False
        self.reload_commits()
        self.reload_branches()
        self._restore_save_button()

    def load_document(self, document_id: uuid.UUID) -> None:
        try:
            document = self.document_service.get_document(document_id)
            if document is None:
                raise ValueError("Документ не найден")
            self.current_document_id = document.id
            self.current_project_id = document.project_id

            for widget in [self.title_edit, self.tags_edit, self.category_edit, self.editor, self.type_combo]:
                widget.blockSignals(True)
            self.title_edit.setText(document.title)
            index = self.type_combo.findData(document.type)
            self.type_combo.setCurrentIndex(index if index >= 0 else 0)
            self.tags_edit.setText(document.tags)
            self.category_edit.setText(document.category)
            self.editor.setPlainText(document.content)
            for widget in [self.title_edit, self.tags_edit, self.category_edit, self.editor, self.type_combo]:
                widget.blockSignals(False)

            self.is_dirty = False
            self.update_info(document)
            self.reload_commits()
            self.reload_branches()
            self._restore_save_button()
            self.set_status("Документ открыт")
        except Exception as exc:  # noqa: BLE001
            self.show_error("Ошибка открытия документа", exc)

    def update_info(self, document: Document) -> None:
        self.info_label.setText(
            f"Название: {document.title}\n"
            f"Тип: {document.type}\n"
            f"Теги: {document.tags or '—'}\n"
            f"Категория: {document.category or '—'}\n"
            f"Создан: {document.created_at}\n"
            f"Изменён: {document.updated_at}"
        )

    def require_project(self) -> bool:
        if self.current_project_id is None:
            QMessageBox.information(self, "Нужен проект", "Сначала создай или выбери проект.")
            return False
        return True

    def create_project(self) -> None:
        title, ok = QInputDialog.getText(self, "Новый проект", "Название проекта:")
        if not ok or not title.strip():
            return
        description, _ = QInputDialog.getMultiLineText(self, "Описание", "Описание проекта:")
        try:
            project = self.document_service.create_project(title, description)
            self.current_project_id = project.id
            self.reload_projects()
            self.set_status("Проект создан")
        except Exception as exc:  # noqa: BLE001
            self.show_error("Ошибка создания проекта", exc)

    def create_document(self) -> None:
        if not self.require_project():
            return
        dialog = NewDocumentDialog(self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        title, doc_type = dialog.values()
        try:
            document = self.document_service.create_document(self.current_project_id, title, doc_type)
            self.reload_documents(document.id)
            self.load_document(document.id)
            self.set_status("Документ создан")
        except Exception as exc:  # noqa: BLE001
            self.show_error("Ошибка создания документа", exc)

    def mark_dirty(self) -> None:
        if self.current_document_id is not None:
            self.is_dirty = True
            self._restore_save_button()
            self.set_status("Есть несохранённые изменения")

    def save_current_document(self) -> bool:
        if self.current_document_id is None:
            QMessageBox.information(self, "Сохранение", "Сначала открой документ.")
            return False
        try:
            document = self.document_service.save_document(
                self.current_document_id,
                self.title_edit.text(),
                str(self.type_combo.currentData() or "note"),
                self.editor.toPlainText(),
                self.tags_edit.text(),
                self.category_edit.text(),
            )
            self.is_dirty = False
            self.update_info(document)
            self.reload_documents(document.id)
            self._show_save_feedback("Сохранено")
            self.set_status("Сохранено")
            return True
        except Exception as exc:  # noqa: BLE001
            self.show_error("Ошибка сохранения", exc)
            return False

    def autosave(self) -> None:
        if not self.autosave_enabled or not self.is_dirty:
            return
        if self.save_current_document():
            self._show_save_feedback("Автосохранено")

    def toggle_autosave(self) -> None:
        self.autosave_enabled = not self.autosave_enabled
        self.autosave_btn.setText("Автосохранение: включено" if self.autosave_enabled else "Автосохранение: выключено")
        self.user_settings.autosave_enabled = self.autosave_enabled
        self.settings_service.save(self.user_settings)
        self.set_status(self.autosave_btn.text())

    def _show_save_feedback(self, message: str) -> None:
        self.save_feedback_label.setText(f"✔ {message}")
        self.save_feedback_label.show()
        self.save_btn.setText(f"✔ {message}")
        self.save_btn.setIcon(self._standard_icon(QStyle.StandardPixmap.SP_DialogApplyButton))
        self.save_feedback_timer.start(2500)

    def _restore_save_button(self) -> None:
        self.save_feedback_label.hide()
        self.save_btn.setText("Сохранить")
        self.save_btn.setIcon(self._standard_icon(QStyle.StandardPixmap.SP_DialogSaveButton))

    # ---------------------------------------------------------------------
    # Import/export
    # ---------------------------------------------------------------------
    def import_document(self) -> None:
        if not self.require_project():
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Импорт документа",
            str(Path.home()),
            "Documents (*.docx *.doc *.txt *.md *.markdown)",
        )
        if not path:
            return
        try:
            text = self.import_service.read_file_text(path)
            file_path = Path(path)
            document = self.document_service.create_document(
                self.current_project_id,
                file_path.stem,
                "note",
                text,
                tags="import",
                category="Импорт",
            )
            self.reload_documents(document.id)
            self.load_document(document.id)
            self.set_status("Документ импортирован")
        except ImportErrorForUser as exc:
            QMessageBox.warning(self, "Импорт невозможен", str(exc))
        except Exception as exc:  # noqa: BLE001
            self.show_error("Ошибка импорта", exc)

    def import_folder(self) -> None:
        if not self.require_project():
            return
        directory = QFileDialog.getExistingDirectory(self, "Импорт папки", str(Path.home()))
        if not directory:
            return
        try:
            files = self.import_service.list_importable_files(directory)
            imported = 0
            skipped = 0
            for file_path in files:
                try:
                    text = self.import_service.read_file_text(file_path)
                    category = f"Импорт папки/{file_path.parent.name}"
                    self.document_service.create_document(
                        self.current_project_id,
                        file_path.stem,
                        "note",
                        text,
                        tags="import, folder",
                        category=category,
                    )
                    imported += 1
                except Exception:
                    skipped += 1
            self.reload_documents()
            QMessageBox.information(
                self,
                "Импорт папки",
                f"Импортировано файлов: {imported}\nПропущено файлов: {skipped}",
            )
            self.set_status(f"Импортировано: {imported}; пропущено: {skipped}")
        except Exception as exc:  # noqa: BLE001
            self.show_error("Ошибка импорта папки", exc)

    def save_as_file(self) -> None:
        if self.current_document_id is None:
            QMessageBox.information(self, "Сохранить как", "Сначала открой документ.")
            return
        raw_title = self.title_edit.text().strip() or "document"
        safe_title = re.sub(r'[\\/:*?"<>|]+', "_", raw_title)
        path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Сохранить документ как",
            str(Path.home() / f"{safe_title}.md"),
            "Markdown (*.md);;Text file (*.txt);;Word DOCX (*.docx);;Word DOC (*.doc);;PDF (*.pdf)",
        )
        if not path:
            return
        export_path = Path(path)
        if export_path.suffix == "":
            if "Text file" in selected_filter:
                export_path = export_path.with_suffix(".txt")
            elif "Word DOCX" in selected_filter:
                export_path = export_path.with_suffix(".docx")
            elif "Word DOC" in selected_filter:
                export_path = export_path.with_suffix(".doc")
            elif "PDF" in selected_filter:
                export_path = export_path.with_suffix(".pdf")
            else:
                export_path = export_path.with_suffix(".md")
        try:
            title = self.title_edit.text().strip() or "Без названия"
            content = self.editor.toPlainText()
            if export_path.suffix.lower() == ".pdf":
                self._export_pdf(export_path, title, content)
            else:
                export_path = self.export_service.export_text(export_path, title, content)
            self._show_save_feedback("Экспортировано")
            self.set_status(f"Сохранено как: {export_path}")
        except ExportErrorForUser as exc:
            QMessageBox.warning(self, "Экспорт невозможен", str(exc))
        except Exception as exc:  # noqa: BLE001
            self.show_error("Ошибка 'Сохранить как'", exc)

    def export_pdf(self) -> None:
        if self.current_document_id is None:
            QMessageBox.information(self, "Экспорт PDF", "Сначала открой документ.")
            return
        raw_title = self.title_edit.text().strip() or "document"
        safe_title = re.sub(r'[\\/:*?"<>|]+', "_", raw_title)
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Экспорт PDF",
            str(Path.home() / f"{safe_title}.pdf"),
            "PDF (*.pdf)",
        )
        if not path:
            return
        export_path = Path(path)
        if export_path.suffix.lower() != ".pdf":
            export_path = export_path.with_suffix(".pdf")
        try:
            self._export_pdf(export_path, self.title_edit.text().strip() or "Без названия", self.editor.toPlainText())
            self._show_save_feedback("PDF экспортирован")
            self.set_status(f"PDF экспортирован: {export_path}")
        except Exception as exc:  # noqa: BLE001
            self.show_error("Ошибка экспорта PDF", exc)

    def _export_pdf(self, path: Path, title: str, content: str) -> None:
        document = QTextDocument()
        safe_title = title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        safe_content = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
        document.setHtml(f"<h1>{safe_title}</h1><p>{safe_content}</p>")
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(str(path))
        document.print(printer)

    # ---------------------------------------------------------------------
    # Commits and branches
    # ---------------------------------------------------------------------
    def selected_commit_id(self, source: str = "git") -> uuid.UUID | None:
        widget = self.commit_list_side if source == "side" else self.commit_list_git
        item = widget.currentItem()
        if item is None:
            return None
        return uuid.UUID(str(item.data(256)))

    def create_commit(self) -> None:
        if self.current_document_id is None:
            QMessageBox.information(self, "Коммит", "Сначала открой документ.")
            return
        if self.is_dirty:
            self.save_current_document()
        dialog = CommitDialog(self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        try:
            commit = self.commit_service.create_commit(self.current_document_id, dialog.message())
            self.reload_commits()
            self.set_status(f"Коммит создан: {commit.message}")
        except Exception as exc:  # noqa: BLE001
            self.show_error("Ошибка коммита", exc)

    def open_commit_history(self) -> None:
        if self.current_document_id is None:
            QMessageBox.information(self, "История", "Сначала открой документ.")
            return
        dialog = CommitHistoryDialog(self.current_document_id, self)
        result = dialog.exec()
        if result == dialog.DialogCode.Accepted:
            self.load_document(self.current_document_id)
        self.reload_commits()

    def preview_selected_commit(self) -> None:
        commit_id = self.selected_commit_id("git")
        if commit_id is None:
            return
        commit = self.commits.get(str(commit_id))
        if commit:
            self.commit_preview.setPlainText(commit.content_snapshot)

    def rename_selected_commit(self) -> None:
        commit_id = self.selected_commit_id("git")
        if commit_id is None:
            QMessageBox.information(self, "Коммит", "Выбери коммит.")
            return
        commit = self.commits.get(str(commit_id))
        message, ok = QInputDialog.getText(self, "Коммит", "Новое сообщение:", text=commit.message if commit else "")
        if not ok:
            return
        try:
            self.commit_service.update_commit_message(commit_id, message)
            self.reload_commits()
        except Exception as exc:  # noqa: BLE001
            self.show_error("Ошибка изменения коммита", exc)

    def delete_selected_commit_side(self) -> None:
        self._delete_selected_commit("side")

    def delete_selected_commit_git(self) -> None:
        self._delete_selected_commit("git")

    def _delete_selected_commit(self, source: str) -> None:
        commit_id = self.selected_commit_id(source)
        if commit_id is None:
            QMessageBox.information(self, "Коммит", "Выбери коммит.")
            return
        if QMessageBox.question(self, "Удалить коммит", "Удалить выбранный коммит?") != QMessageBox.StandardButton.Yes:
            return
        try:
            self.commit_service.delete_commit(commit_id)
            self.reload_commits()
            self.set_status("Коммит удалён")
        except Exception as exc:  # noqa: BLE001
            self.show_error("Ошибка удаления коммита", exc)

    def rollback_selected_commit(self) -> None:
        commit_id = self.selected_commit_id("git")
        if commit_id is None:
            QMessageBox.information(self, "Откат", "Выбери коммит.")
            return
        if QMessageBox.question(self, "Откат", "Откатить документ к выбранному коммиту?") != QMessageBox.StandardButton.Yes:
            return
        try:
            commit = self.commit_service.rollback_to_commit(commit_id)
            self.load_document(commit.document_id)
            self.set_status("Откат выполнен")
        except Exception as exc:  # noqa: BLE001
            self.show_error("Ошибка отката", exc)

    def selected_branch_id(self) -> str | None:
        item = self.branch_list.currentItem()
        if item is None:
            return None
        return str(item.data(256))

    def create_branch(self) -> None:
        if self.current_document_id is None:
            QMessageBox.information(self, "Ветка", "Сначала открой документ.")
            return
        if self.is_dirty:
            self.save_current_document()
        name, ok = QInputDialog.getText(self, "Новая ветка", "Название ветки:")
        if not ok or not name.strip():
            return
        try:
            branch = self.branch_service.create_branch(self.current_document_id, name.strip())
            self.reload_branches()
            self.set_status(f"Ветка создана: {branch.name}")
        except Exception as exc:  # noqa: BLE001
            self.show_error("Ошибка ветки", exc)

    def save_branch_snapshot(self) -> None:
        branch_id = self.selected_branch_id()
        if branch_id is None:
            QMessageBox.information(self, "Ветка", "Выбери ветку.")
            return
        if self.is_dirty:
            self.save_current_document()
        try:
            branch = self.branch_service.save_current_to_branch(branch_id)
            self.reload_branches()
            self.set_status(f"Снимок сохранён: {branch.name}")
        except Exception as exc:  # noqa: BLE001
            self.show_error("Ошибка ветки", exc)

    def checkout_branch(self) -> None:
        branch_id = self.selected_branch_id()
        if branch_id is None:
            QMessageBox.information(self, "Ветка", "Выбери ветку.")
            return
        if QMessageBox.question(self, "Ветка", "Заменить текущий документ снимком ветки?") != QMessageBox.StandardButton.Yes:
            return
        try:
            branch = self.branch_service.checkout_branch(branch_id)
            self.commit_service.create_commit(uuid.UUID(branch.document_id), f"Checkout branch {branch.name}")
            self.load_document(uuid.UUID(branch.document_id))
            self.set_status(f"Переключено на ветку: {branch.name}")
        except Exception as exc:  # noqa: BLE001
            self.show_error("Ошибка ветки", exc)

    def delete_branch(self) -> None:
        branch_id = self.selected_branch_id()
        if branch_id is None:
            QMessageBox.information(self, "Ветка", "Выбери ветку.")
            return
        if QMessageBox.question(self, "Ветка", "Удалить ветку?") != QMessageBox.StandardButton.Yes:
            return
        try:
            self.branch_service.delete_branch(branch_id)
            self.reload_branches()
            self.set_status("Ветка удалена")
        except Exception as exc:  # noqa: BLE001
            self.show_error("Ошибка ветки", exc)

    # ---------------------------------------------------------------------
    # Concepts
    # ---------------------------------------------------------------------
    def load_selected_concept(self) -> None:
        item = self.concept_list.currentItem()
        if item is None:
            self.current_concept_id = None
            self.concept_title_edit.clear()
            self.concept_editor.clear()
            return
        concept = self.concepts.get(str(item.data(256)))
        if concept is None:
            return
        self.current_concept_id = concept.id
        self.concept_title_edit.setText(concept.title)
        self.concept_status_combo.setCurrentText(concept.status)
        self.concept_editor.setPlainText(concept.content)

    def create_concept(self) -> None:
        if not self.require_project():
            return
        title, ok = QInputDialog.getText(self, "Новый концепт", "Название:")
        if not ok or not title.strip():
            return
        try:
            concept = self.concept_service.create_concept(self.current_project_id, title.strip(), f"# {title.strip()}\n\n", "Идея")
            self.reload_concepts()
            self.current_concept_id = concept.id
            self.set_status("Концепт создан")
        except Exception as exc:  # noqa: BLE001
            self.show_error("Ошибка концепта", exc)

    def save_concept(self) -> None:
        if self.current_concept_id is None:
            QMessageBox.information(self, "Концепт", "Выбери концепт.")
            return
        try:
            self.concept_service.save_concept(
                self.current_concept_id,
                self.concept_title_edit.text(),
                self.concept_editor.toPlainText(),
                self.concept_status_combo.currentText(),
            )
            self.reload_concepts()
            self.set_status("Концепт сохранён")
        except Exception as exc:  # noqa: BLE001
            self.show_error("Ошибка концепта", exc)

    def delete_concept(self) -> None:
        if self.current_concept_id is None:
            QMessageBox.information(self, "Концепт", "Выбери концепт.")
            return
        if QMessageBox.question(self, "Концепт", "Удалить концепт?") != QMessageBox.StandardButton.Yes:
            return
        try:
            self.concept_service.delete_concept(self.current_concept_id)
            self.current_concept_id = None
            self.reload_concepts()
            self.concept_title_edit.clear()
            self.concept_editor.clear()
            self.set_status("Концепт удалён")
        except Exception as exc:  # noqa: BLE001
            self.show_error("Ошибка концепта", exc)

    def convert_concept(self) -> None:
        if self.current_concept_id is None:
            QMessageBox.information(self, "Концепт", "Выбери концепт.")
            return
        try:
            document = self.concept_service.convert_to_document(self.current_concept_id)
            self.tabs.setCurrentIndex(0)
            self.reload_documents(document.id)
            self.load_document(document.id)
            self.reload_concepts()
            self.set_status("Концепт преобразован в документ")
        except Exception as exc:  # noqa: BLE001
            self.show_error("Ошибка концепта", exc)

    # ---------------------------------------------------------------------
    # Search/settings/update
    # ---------------------------------------------------------------------
    def search(self) -> None:
        query = self.search_edit.text().strip()
        self.search_results_list.clear()
        self.search_results.clear()
        if not query:
            return
        try:
            for document in self.search_service.search_documents(query, self.current_project_id):
                item = QListWidgetItem(f"{document.title} · {document.type} · {document.tags}")
                item.setData(256, str(document.id))
                self.search_results_list.addItem(item)
                self.search_results[str(document.id)] = document
            self.set_status(f"Найдено: {self.search_results_list.count()}")
        except Exception as exc:  # noqa: BLE001
            self.show_error("Ошибка поиска", exc)

    def open_search_result(self) -> None:
        item = self.search_results_list.currentItem()
        if item is None:
            return
        document_id = uuid.UUID(str(item.data(256)))
        document = self.search_results.get(str(document_id))
        if document is None:
            return
        self.current_project_id = document.project_id
        self.reload_documents(document.id)
        self.load_document(document.id)
        self.tabs.setCurrentIndex(0)

    def apply_theme_from_settings(self, name: str) -> None:
        key = key_by_name(name)
        QApplication.instance().setStyleSheet(build_qss(key))
        self.user_settings = self.settings_service.update_theme(key)
        self.set_status(f"Тема применена: {name}")

    def open_profile_settings(self) -> None:
        dialog = ProfileSettingsDialog(self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        value, account_id = dialog.values()
        if account_id:
            self.account_service.set_active(account_id)
        self.user_settings = self.settings_service.update_profile(value.profile_name, value.theme, value.autosave_enabled)
        self.autosave_enabled = value.autosave_enabled
        self.autosave_btn.setText("Автосохранение: включено" if self.autosave_enabled else "Автосохранение: выключено")
        self.theme_combo_settings.setCurrentText(display_name_by_key(value.theme))
        QApplication.instance().setStyleSheet(build_qss(value.theme))
        self.refresh_profile_labels()
        self.set_status("Профиль сохранён")

    def open_template_manager(self) -> None:
        dialog = TemplateManagerDialog(self)
        dialog.exec()
        self.reload_type_combo()
        self.set_status("Типы документов обновлены")

    # ---------------------------------------------------------------------
    # Shortcuts, AI and writer tools
    # ---------------------------------------------------------------------
    def handle_ribbon_action(self, action: str) -> None:
        actions = {
            "new_project": self.create_project,
            "new_document": self.create_document,
            "save": self.save_current_document,
            "save_as": self.save_as_file,
            "import_file": self.import_document,
            "import_folder": self.import_folder,
            "export_pdf": self.export_pdf,
            "commit": self.create_commit,
            "undo": self.editor.undo,
            "redo": self.editor.redo,
            "cut": self.editor.cut,
            "copy": self.editor.copy,
            "paste": self.editor.paste,
            "find": self.focus_writer_find,
            "replace": self.focus_writer_replace,
            "bold": lambda: self.wrap_selection("**", "**"),
            "italic": lambda: self.wrap_selection("*", "*"),
            "underline": lambda: self.wrap_selection("<u>", "</u>"),
            "strike": lambda: self.wrap_selection("~~", "~~"),
            "quote": lambda: self.prefix_selection("> "),
            "h1": lambda: self.heading_selection("# "),
            "h2": lambda: self.heading_selection("## "),
            "h3": lambda: self.heading_selection("### "),
            "list": lambda: self.prefix_selection("- "),
            "numbered_list": self.numbered_selection,
            "separator": lambda: self.insert_block("\n\n---\n\n"),
            "insert_scene": lambda: self.insert_block(WRITER_BLOCKS["scene"]),
            "insert_dialogue": lambda: self.insert_block(WRITER_BLOCKS["dialogue"]),
            "insert_author_note": lambda: self.insert_block(WRITER_BLOCKS["author_note"]),
            "insert_character_card": lambda: self.insert_block(WRITER_BLOCKS["character_card"]),
            "insert_chapter_plan": lambda: self.insert_block(WRITER_BLOCKS["chapter_plan"]),
            "insert_beat_sheet": lambda: self.insert_block(WRITER_BLOCKS["beat_sheet"]),
            "text_stats": self.show_text_statistics,
            "toggle_left": self.toggle_left_panel,
            "toggle_right": self.toggle_right_panel,
            "focus_mode": self.toggle_focus_mode,
            "compact_mode": self.toggle_compact_mode,
            "font_increase": self.increase_editor_font,
            "font_decrease": self.decrease_editor_font,
        }
        handler = actions.get(action)
        if handler is not None:
            handler()

    def _setup_shortcuts(self) -> None:
        QShortcut(QKeySequence.StandardKey.Save, self, activated=self.save_current_document)
        QShortcut(QKeySequence("Ctrl+Shift+S"), self, activated=self.save_as_file)
        QShortcut(QKeySequence("Ctrl+F"), self, activated=self.focus_writer_find)
        QShortcut(QKeySequence("Ctrl+H"), self, activated=self.focus_writer_replace)
        QShortcut(QKeySequence("Ctrl+N"), self, activated=self.create_document)
        QShortcut(QKeySequence("Ctrl+Shift+N"), self, activated=self.create_project)
        QShortcut(QKeySequence("Ctrl+B"), self, activated=lambda: self.wrap_selection("**", "**"))
        QShortcut(QKeySequence("Ctrl+I"), self, activated=lambda: self.wrap_selection("*", "*"))
        QShortcut(QKeySequence("Ctrl+U"), self, activated=lambda: self.wrap_selection("<u>", "</u>"))
        QShortcut(QKeySequence("Ctrl+Z"), self, activated=lambda: self.editor.undo())
        QShortcut(QKeySequence("Ctrl+Y"), self, activated=lambda: self.editor.redo())
        QShortcut(QKeySequence("Ctrl+A"), self, activated=lambda: self.editor.selectAll())
        QShortcut(QKeySequence("Ctrl+P"), self, activated=self.export_pdf)
        QShortcut(QKeySequence("F11"), self, activated=self.toggle_focus_mode)

    def current_editor_text(self) -> str:
        return self.editor.toPlainText() if hasattr(self, "editor") else ""

    def current_selected_or_all_text(self) -> str:
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            return cursor.selectedText().replace("\u2029", "\n")
        return self.current_editor_text()

    def ai_insert_result_text(self, result: str) -> None:
        if self.current_document_id is None:
            QMessageBox.information(self, "ИИ-агент", "Сначала открой документ.")
            return
        self.editor.textCursor().insertText("\n\n" + result)
        self.mark_dirty()
        self.tabs.setCurrentIndex(0)

    def ai_replace_document_text(self, result: str) -> None:
        if self.current_document_id is None:
            QMessageBox.information(self, "ИИ-агент", "Сначала открой документ.")
            return
        self.editor.setPlainText(result)
        self.mark_dirty()
        self.tabs.setCurrentIndex(0)

    def ai_replace_selection_text(self, result: str) -> None:
        if self.current_document_id is None:
            QMessageBox.information(self, "ИИ-агент", "Сначала открой документ.")
            return
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            cursor.insertText(result)
        else:
            cursor.insertText(result)
        self.mark_dirty()
        self.tabs.setCurrentIndex(0)

    def ai_create_document_from_result(self, title: str, result: str) -> None:
        if not self.require_project():
            return
        try:
            document = self.document_service.create_document(
                self.current_project_id,
                title,
                "note",
                result,
                tags="ai",
                category="ИИ-агент",
            )
            self.reload_documents(document.id)
            self.load_document(document.id)
            self.tabs.setCurrentIndex(0)
            self.set_status("ИИ-агент создал новый документ")
        except Exception as exc:  # noqa: BLE001
            self.show_error("Ошибка создания документа из ИИ-результата", exc)

    def ai_take_from_document(self) -> None:
        self.ai_source.setPlainText(self.current_selected_or_all_text())

    def _run_ai_action(self, action: str) -> None:
        source = self.ai_source.toPlainText().strip() or self.current_selected_or_all_text()
        if not source:
            QMessageBox.information(self, "ИИ-агент", "Нет текста для обработки.")
            return
        methods = {
            "improve": self.ai_editor_service.improve_text,
            "summarize": self.ai_editor_service.summarize,
            "expand": self.ai_editor_service.expand_scene,
            "contradictions": self.ai_editor_service.find_contradictions,
            "character": self.ai_editor_service.character_questions,
            "titles": self.ai_editor_service.title_ideas,
            "dialogue": self.ai_editor_service.fix_dialogue,
        }
        result = methods[action](source)
        self.ai_result.setPlainText(f"# {result.title}\n\n{result.text}")
        self.set_status(f"ИИ-агент: {result.title}")

    def ai_improve_text(self) -> None:
        self._run_ai_action("improve")

    def ai_summarize(self) -> None:
        self._run_ai_action("summarize")

    def ai_expand_scene(self) -> None:
        self._run_ai_action("expand")

    def ai_find_contradictions(self) -> None:
        self._run_ai_action("contradictions")

    def ai_character_questions(self) -> None:
        self._run_ai_action("character")

    def ai_title_ideas(self) -> None:
        self._run_ai_action("titles")

    def ai_fix_dialogue(self) -> None:
        self._run_ai_action("dialogue")

    def ai_apply_result_to_document(self) -> None:
        if self.current_document_id is None:
            QMessageBox.information(self, "ИИ-агент", "Сначала открой документ.")
            return
        result = self.ai_result.toPlainText()
        if not result.strip():
            QMessageBox.information(self, "ИИ-агент", "Нет результата для применения.")
            return
        self.editor.setPlainText(result)
        self.mark_dirty()
        self.tabs.setCurrentIndex(0)

    def ai_insert_result_to_document(self) -> None:
        if self.current_document_id is None:
            QMessageBox.information(self, "ИИ-агент", "Сначала открой документ.")
            return
        result = self.ai_result.toPlainText()
        if not result.strip():
            QMessageBox.information(self, "ИИ-агент", "Нет результата для вставки.")
            return
        self.editor.textCursor().insertText("\n\n" + result)
        self.mark_dirty()
        self.tabs.setCurrentIndex(0)

    def focus_writer_find(self) -> None:
        if hasattr(self, "writer_find_edit"):
            self.tabs.setCurrentIndex(0)
            self.writer_find_edit.setFocus()

    def focus_writer_replace(self) -> None:
        if hasattr(self, "writer_replace_edit"):
            self.tabs.setCurrentIndex(0)
            self.writer_replace_edit.setFocus()

    def toggle_left_panel(self) -> None:
        if hasattr(self, "documents_tab"):
            visible = self.documents_tab.toggle_left_panel()
            self.set_status("Левая панель показана" if visible else "Левая панель скрыта")

    def toggle_right_panel(self) -> None:
        if hasattr(self, "documents_tab"):
            visible = self.documents_tab.toggle_right_panel()
            self.set_status("Правая панель показана" if visible else "Правая панель скрыта")

    def toggle_focus_mode(self) -> None:
        self.focus_mode_enabled = not self.focus_mode_enabled
        self.tabs.setCurrentIndex(0)
        if hasattr(self, "documents_tab"):
            self.documents_tab.set_focus_mode(self.focus_mode_enabled)
        if hasattr(self, "ribbon"):
            self.ribbon.set_focus_mode(self.focus_mode_enabled)
        self.tabs.tabBar().setVisible(not self.focus_mode_enabled)
        self.set_status("Focus Mode включен" if self.focus_mode_enabled else "Focus Mode выключен")

    def toggle_compact_mode(self) -> None:
        self.compact_mode_enabled = not self.compact_mode_enabled
        if hasattr(self, "documents_tab"):
            self.documents_tab.set_compact_mode(self.compact_mode_enabled)
        if hasattr(self, "ribbon"):
            self.ribbon.set_compact_mode(self.compact_mode_enabled)
        self.set_status("Compact Mode включен" if self.compact_mode_enabled else "Compact Mode выключен")

    def increase_editor_font(self) -> None:
        if hasattr(self, "documents_tab"):
            self.documents_tab.editor_panel.increase_font()

    def decrease_editor_font(self) -> None:
        if hasattr(self, "documents_tab"):
            self.documents_tab.editor_panel.decrease_font()

    def show_text_statistics(self) -> None:
        self.refresh_writer_stats()
        QMessageBox.information(self, "Статистика текста", self.word_stats_label.text())

    def refresh_writer_stats(self) -> None:
        text = self.current_editor_text()
        self.word_stats_label.setText(text_statistics(text).as_status_text())

    def writer_find_next(self) -> None:
        query = self.writer_find_edit.text()
        if not query:
            return
        if not self.editor.find(query):
            cursor = self.editor.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            self.editor.setTextCursor(cursor)
            self.editor.find(query)

    def writer_replace_one(self) -> None:
        cursor = self.editor.textCursor()
        find_text = self.writer_find_edit.text()
        replace_text = self.writer_replace_edit.text()
        if not find_text:
            return
        if not cursor.hasSelection():
            self.writer_find_next()
            cursor = self.editor.textCursor()
        if cursor.hasSelection():
            cursor.insertText(replace_text)
            self.mark_dirty()

    def writer_replace_all(self) -> None:
        find_text = self.writer_find_edit.text()
        replace_text = self.writer_replace_edit.text()
        if not find_text:
            return
        text = self.editor.toPlainText()
        count = text.count(find_text)
        self.editor.setPlainText(text.replace(find_text, replace_text))
        self.mark_dirty()
        QMessageBox.information(self, "Замена", f"Заменено вхождений: {count}")

    def wrap_selection(self, before: str, after: str) -> None:
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            selected = cursor.selectedText().replace("\u2029", "\n")
            cursor.insertText(f"{before}{selected}{after}")
        else:
            cursor.insertText(f"{before}текст{after}")
        self.mark_dirty()

    def prefix_selection(self, prefix: str) -> None:
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            selected = cursor.selectedText().replace("\u2029", "\n")
            prefixed = "\n".join(prefix + line if line.strip() else line for line in selected.splitlines())
            cursor.insertText(prefixed)
        else:
            cursor.insertText(prefix)
        self.mark_dirty()

    def heading_selection(self, prefix: str) -> None:
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            selected = cursor.selectedText().replace("\u2029", "\n")
            lines = [re.sub(r"^#{1,6}\s*", "", line) for line in selected.splitlines()]
            cursor.insertText("\n".join(prefix + line if line.strip() else line for line in lines))
        else:
            cursor.insertText(prefix + "Заголовок")
        self.mark_dirty()

    def numbered_selection(self) -> None:
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            cursor.insertText(number_lines(cursor.selectedText()))
        else:
            cursor.insertText("1. ")
        self.mark_dirty()

    def insert_block(self, text: str) -> None:
        self.editor.textCursor().insertText(text)
        self.mark_dirty()

    def clear_markdown_marks(self) -> None:
        cursor = self.editor.textCursor()
        selected_only = cursor.hasSelection()
        text = cursor.selectedText().replace("\u2029", "\n") if selected_only else self.editor.toPlainText()
        cleaned = clear_markdown_marks(text)
        if selected_only:
            cursor.insertText(cleaned)
        else:
            self.editor.setPlainText(cleaned)
        self.mark_dirty()

    def open_update_dialog(self) -> None:
        dialog = UpdateDialog(self)
        dialog.exec()
