from __future__ import annotations

from html import escape
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QColor, QFont, QKeySequence, QTextBlockFormat, QTextCharFormat, QTextCursor, QTextDocument, QTextListFormat
from PyQt6.QtPrintSupport import QPrinter
from PyQt6.QtWidgets import (
    QApplication,
    QColorDialog,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from redcord import __version__
from redcord.domain.entities import Concept, Document, utc_now_iso
from redcord.services.command_registry import CommandRegistry
from redcord.services.html_tools import plain_to_html
from redcord.services.settings_service import SettingsService
from redcord.services.template_service import DEFAULT_TEMPLATES
from redcord.services.text_tools import text_statistics
from redcord.services.theme08 import CUSTOM_THEME_KEY, THEMES_08, build_qss_08, load_custom_theme, save_custom_theme, theme_key
from redcord.storage.sqlite_store import DEFAULT_OWNER_ID, SQLiteStore
from redcord.sync.client import SyncClient, SyncError
from redcord.ui.dialogs.update_dialog import UpdateDialog
from redcord.ui.tabs.ai_agent_tab import AIAgentTab
from redcord.ui.tabs.art_studio_tab import ArtStudioTab
from redcord.ui.tabs.documents_tab import DocumentsTab
from redcord.ui.widgets.ribbon_toolbar import RibbonToolbar
from redcord.ui.widgets.self_healing_panel import SelfHealingPanel


WRITER_BLOCKS_HTML = {
    "scene": "<hr><h2>Сцена</h2><p><b>Цель:</b> ...</p><p><b>Конфликт:</b> ...</p><p><b>Поворот:</b> ...</p><p><b>Последствие:</b> ...</p>",
    "dialogue": "<p><b>Диалог</b></p><p>Персонаж: ...<br>Другой персонаж: ...</p>",
    "author_note": "<blockquote><b>Заметка автора:</b> ...</blockquote>",
    "character_card": "<h2>Карточка персонажа</h2><p><b>Имя:</b> ...</p><p><b>Цель:</b> ...</p><p><b>Страх:</b> ...</p><p><b>Арка:</b> ...</p>",
    "chapter_plan": "<h2>План главы</h2><ol><li>Крючок</li><li>Цель героя</li><li>Препятствие</li><li>Выбор</li><li>Последствие</li></ol>",
    "beat_sheet": "<h2>Beat-sheet</h2><ul><li>Opening image</li><li>Catalyst</li><li>Midpoint</li><li>Crisis</li><li>Finale</li></ul>",
}


class MainWindow08(QMainWindow):
    def __init__(self, store: SQLiteStore) -> None:
        super().__init__()
        self.store = store
        self.registry = CommandRegistry()
        self.settings_service = SettingsService()
        self.user_settings = self.settings_service.load()
        self.custom_theme = load_custom_theme()
        self.current_project_id: str | None = None
        self.current_document_id: str | None = None
        self.current_document: Document | None = None
        self.current_concept_id: str | None = None
        self.dirty = False
        self.concept_dirty = False
        self.focus_mode = False
        self.compact_mode = False
        self._loading_document = False
        self._loading_concept = False

        self.setWindowTitle(f"RedCord {__version__} Writer Desktop")
        self.resize(1366, 768)
        self.setMinimumSize(1100, 650)
        self._build_ui()
        self._wire_commands()
        self._wire_autosave()
        self.reload_projects()
        self.set_status("Готово")

    @property
    def editor(self) -> QTextEdit:
        return self.documents_tab.editor_panel.editor

    def _build_ui(self) -> None:
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.ribbon = RibbonToolbar(self.registry)
        self.ribbon.actionTriggered.connect(self.run_command)
        root_layout.addWidget(self.ribbon)

        self.tabs = QTabWidget()
        self.documents_tab = DocumentsTab(autosave_enabled=True)
        self.documents_tab_index = self.tabs.addTab(self.documents_tab, "Документы")
        self.concepts_tab_index = self.tabs.addTab(self._build_concepts_tab(), "Концепты")
        self.art_tab = ArtStudioTab(self.store, lambda: self.current_project_id, self.set_status)
        self.art_tab_index = self.tabs.addTab(self.art_tab, "Арты / BoC Lite")
        self.git_tab_index = self.tabs.addTab(self._build_git_tab(), "Git / версии")
        self.ai_tab = AIAgentTab(
            get_document_text=self.current_selected_or_all_text,
            insert_result=self.ai_insert_result_text,
            replace_document=self.ai_replace_document_text,
            replace_selection=self.ai_replace_selection_text,
            create_document_from_result=self.ai_create_document_from_result,
            set_status=self.set_status,
        )
        self.ai_tab_index = self.tabs.addTab(self.ai_tab, "ИИ-агент")
        self.self_healing_tab_index = self.tabs.addTab(SelfHealingPanel(), "Self-Healing")
        self.settings_tab_index = self.tabs.addTab(self._build_settings_tab(), "Настройки")
        root_layout.addWidget(self.tabs, 1)

        self.setCentralWidget(root)
        self._wire_document_widgets()

    def _wire_document_widgets(self) -> None:
        sidebar = self.documents_tab.sidebar
        inspector = self.documents_tab.inspector
        editor_panel = self.documents_tab.editor_panel

        sidebar.project_list.currentItemChanged.connect(self.on_project_selected)
        sidebar.document_list.currentItemChanged.connect(self.on_document_selected)
        sidebar.new_project_btn.clicked.connect(self.create_project)
        sidebar.new_document_btn.clicked.connect(self.create_document)
        sidebar.import_btn.clicked.connect(self.import_file)
        sidebar.import_folder_btn.clicked.connect(self.import_folder)
        sidebar.types_btn.clicked.connect(lambda: self.tabs.setCurrentIndex(self.settings_tab_index))

        editor_panel.save_btn.clicked.connect(self.save_document)
        editor_panel.save_as_btn.clicked.connect(self.save_as_html)
        editor_panel.autosave_btn.clicked.connect(self.toggle_autosave)
        editor_panel.commit_btn.clicked.connect(self.create_commit)
        editor_panel.history_btn.clicked.connect(lambda: self.tabs.setCurrentIndex(self.git_tab_index))
        editor_panel.editor.textChanged.connect(self.mark_dirty)
        editor_panel.editor.currentCharFormatChanged.connect(self.update_format_state)
        editor_panel.editor.cursorPositionChanged.connect(self.update_format_state)
        editor_panel.title_edit.textChanged.connect(self.mark_dirty)
        editor_panel.tags_edit.textChanged.connect(self.mark_dirty)
        editor_panel.category_edit.textChanged.connect(self.mark_dirty)
        editor_panel.type_combo.currentIndexChanged.connect(self.mark_dirty)

        inspector.commit_list_side.itemDoubleClicked.connect(lambda _item: self.preview_selected_commit("side"))
        inspector.commit_delete_side_btn.clicked.connect(lambda: self.delete_selected_commit("side"))
        inspector.writer_find_btn.clicked.connect(self.find_text)
        inspector.writer_replace_one_btn.clicked.connect(self.replace_text)
        inspector.writer_replace_all_btn.clicked.connect(lambda: self.replace_text(replace_all=True))
        inspector.writer_find_edit.returnPressed.connect(self.find_text)
        inspector.writer_replace_edit.returnPressed.connect(self.replace_text)
        inspector.refresh_stats_btn.clicked.connect(self.refresh_stats)
        inspector.search_btn.clicked.connect(self.search_documents)
        inspector.search_edit.returnPressed.connect(self.search_documents)
        inspector.search_results_list.itemDoubleClicked.connect(self.open_search_result)

    def _wire_commands(self) -> None:
        for command in self.registry.commands.values():
            if command.shortcut:
                action = QAction(self)
                action.setShortcut(QKeySequence(command.shortcut))
                action.triggered.connect(lambda _checked=False, command_id=command.id: self.run_command(command_id))
                self.addAction(action)

    def _wire_autosave(self) -> None:
        self.autosave_enabled = True
        self.autosave_timer = QTimer(self)
        self.autosave_timer.setInterval(45_000)
        self.autosave_timer.timeout.connect(self.autosave)
        self.autosave_timer.start()

    def _build_concepts_tab(self) -> QWidget:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        left = QFrame()
        left.setObjectName("Panel")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(8, 8, 8, 8)
        left_layout.setSpacing(6)
        left_layout.addWidget(QLabel("Концепты проекта"))
        self.concept_list = QListWidget()
        self.concept_list.setObjectName("CompactList")
        left_layout.addWidget(self.concept_list, 1)
        concept_buttons = QGridLayout()
        self.new_concept_btn = QPushButton("Новый")
        self.save_concept_btn = QPushButton("Сохранить")
        self.delete_concept_btn = QPushButton("Удалить")
        self.convert_concept_btn = QPushButton("В документ")
        for index, button in enumerate([self.new_concept_btn, self.save_concept_btn, self.delete_concept_btn, self.convert_concept_btn]):
            concept_buttons.addWidget(button, index // 2, index % 2)
        left_layout.addLayout(concept_buttons)

        editor = QFrame()
        editor.setObjectName("Panel")
        editor_layout = QVBoxLayout(editor)
        editor_layout.setContentsMargins(8, 8, 8, 8)
        meta = QHBoxLayout()
        self.concept_title_edit = QLineEdit()
        self.concept_title_edit.setPlaceholderText("Название концепта")
        self.concept_status_edit = QLineEdit("Idea")
        self.concept_status_edit.setMaximumWidth(160)
        meta.addWidget(self.concept_title_edit, 1)
        meta.addWidget(self.concept_status_edit)
        editor_layout.addLayout(meta)
        self.concept_editor = QTextEdit()
        self.concept_editor.setObjectName("WriterEditor")
        self.concept_editor.setAcceptRichText(True)
        self.concept_editor.setPlaceholderText("Опиши лор, персонажа, идею, предмет или правило мира.")
        editor_layout.addWidget(self.concept_editor, 1)

        splitter.addWidget(left)
        splitter.addWidget(editor)
        splitter.setSizes([270, 980])

        self.concept_list.currentItemChanged.connect(self.on_concept_selected)
        self.new_concept_btn.clicked.connect(self.create_concept)
        self.save_concept_btn.clicked.connect(self.save_concept)
        self.delete_concept_btn.clicked.connect(self.delete_concept)
        self.convert_concept_btn.clicked.connect(self.convert_concept)
        self.concept_title_edit.textChanged.connect(self.mark_concept_dirty)
        self.concept_status_edit.textChanged.connect(self.mark_concept_dirty)
        self.concept_editor.textChanged.connect(self.mark_concept_dirty)
        return splitter

    def _build_git_tab(self) -> QWidget:
        splitter = QSplitter(Qt.Orientation.Horizontal)

        commits = QFrame()
        commits.setObjectName("Panel")
        commits_layout = QVBoxLayout(commits)
        commits_layout.setContentsMargins(8, 8, 8, 8)
        commits_layout.addWidget(QLabel("Коммиты документа"))
        self.git_commit_list = QListWidget()
        self.git_commit_list.setObjectName("CompactList")
        commits_layout.addWidget(self.git_commit_list, 1)
        commit_buttons = QGridLayout()
        self.git_commit_btn = QPushButton("Коммит")
        self.git_preview_btn = QPushButton("Preview")
        self.git_rename_btn = QPushButton("Rename")
        self.git_delete_btn = QPushButton("Delete")
        self.git_rollback_btn = QPushButton("Rollback")
        for index, button in enumerate([self.git_commit_btn, self.git_preview_btn, self.git_rename_btn, self.git_delete_btn, self.git_rollback_btn]):
            commit_buttons.addWidget(button, index // 2, index % 2)
        commits_layout.addLayout(commit_buttons)

        branches = QFrame()
        branches.setObjectName("Panel")
        branches_layout = QVBoxLayout(branches)
        branches_layout.setContentsMargins(8, 8, 8, 8)
        branches_layout.addWidget(QLabel("Ветки / альтернативы"))
        self.branch_list = QListWidget()
        self.branch_list.setObjectName("CompactList")
        branches_layout.addWidget(self.branch_list, 1)
        branch_buttons = QGridLayout()
        self.new_branch_btn = QPushButton("Новая")
        self.save_branch_btn = QPushButton("Save")
        self.checkout_branch_btn = QPushButton("Checkout")
        self.delete_branch_btn = QPushButton("Delete")
        for index, button in enumerate([self.new_branch_btn, self.save_branch_btn, self.checkout_branch_btn, self.delete_branch_btn]):
            branch_buttons.addWidget(button, index // 2, index % 2)
        branches_layout.addLayout(branch_buttons)

        preview = QFrame()
        preview.setObjectName("Panel")
        preview_layout = QVBoxLayout(preview)
        preview_layout.setContentsMargins(8, 8, 8, 8)
        preview_layout.addWidget(QLabel("Preview"))
        self.git_preview = QTextEdit()
        self.git_preview.setReadOnly(True)
        self.git_preview.setObjectName("MainDocumentEditor")
        preview_layout.addWidget(self.git_preview, 1)

        splitter.addWidget(commits)
        splitter.addWidget(branches)
        splitter.addWidget(preview)
        splitter.setSizes([330, 300, 680])

        self.git_commit_btn.clicked.connect(self.create_commit)
        self.git_preview_btn.clicked.connect(lambda: self.preview_selected_commit("git"))
        self.git_rename_btn.clicked.connect(self.rename_selected_commit)
        self.git_delete_btn.clicked.connect(lambda: self.delete_selected_commit("git"))
        self.git_rollback_btn.clicked.connect(self.rollback_selected_commit)
        self.git_commit_list.itemDoubleClicked.connect(lambda _item: self.preview_selected_commit("git"))
        self.new_branch_btn.clicked.connect(self.create_branch)
        self.save_branch_btn.clicked.connect(self.save_branch_snapshot)
        self.checkout_branch_btn.clicked.connect(self.checkout_branch)
        self.delete_branch_btn.clicked.connect(self.delete_branch)
        return splitter

    def _build_settings_tab(self) -> QWidget:
        panel = QWidget()
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        appearance = QGroupBox("Вид")
        appearance_layout = QVBoxLayout(appearance)
        self.theme_combo = QComboBox()
        for key, theme in THEMES_08.items():
            self.theme_combo.addItem(theme["name"], key)
        self.theme_combo.addItem("Custom Dark", CUSTOM_THEME_KEY)
        self.theme_combo.currentIndexChanged.connect(self.apply_theme)
        appearance_layout.addWidget(QLabel("Dark Color's theme"))
        appearance_layout.addWidget(self.theme_combo)
        self._set_combo_value(self.theme_combo, theme_key(self.user_settings.theme))
        custom_group = QGroupBox("Custom dark color")
        custom_layout = QGridLayout(custom_group)
        self.custom_color_buttons: dict[str, QPushButton] = {}
        for row, (key, label) in enumerate(
            [
                ("bg", "Фон"),
                ("panel", "Панели"),
                ("surface", "Поверхность"),
                ("accent", "Акцент"),
                ("text", "Текст"),
                ("border", "Граница"),
            ]
        ):
            button = QPushButton(self.custom_theme[key])
            button.clicked.connect(lambda _checked=False, value=key: self.pick_custom_theme_color(value))
            self.custom_color_buttons[key] = button
            custom_layout.addWidget(QLabel(label), row, 0)
            custom_layout.addWidget(button, row, 1)
        self.save_custom_theme_btn = QPushButton("Сохранить custom")
        self.save_custom_theme_btn.clicked.connect(self.save_custom_theme_settings)
        custom_layout.addWidget(self.save_custom_theme_btn, 6, 0, 1, 2)
        appearance_layout.addWidget(custom_group)
        self.compact_btn = QPushButton("Compact Mode")
        self.focus_btn = QPushButton("Focus Mode")
        self.help_btn = QPushButton("Help Center")
        self.update_btn = QPushButton("Обновление из ZIP")
        self.compact_btn.clicked.connect(self.toggle_compact)
        self.focus_btn.clicked.connect(self.toggle_focus)
        self.help_btn.clicked.connect(self.show_help_center)
        self.update_btn.clicked.connect(self.open_update_dialog)
        for button in [self.compact_btn, self.focus_btn, self.help_btn, self.update_btn]:
            appearance_layout.addWidget(button)
        appearance_layout.addStretch(1)

        sync = QGroupBox("Аккаунт и синхронизация")
        sync_layout = QVBoxLayout(sync)
        self.sync_url_edit = QLineEdit("http://localhost:8088")
        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("email@example.com")
        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("Код из письма")
        request_btn = QPushButton("Запросить код")
        verify_btn = QPushButton("Войти")
        push_btn = QPushButton("Push local changes")
        status_btn = QPushButton("Sync status")
        self.sync_log = QTextEdit()
        self.sync_log.setReadOnly(True)
        request_btn.clicked.connect(self.request_email_code)
        verify_btn.clicked.connect(self.verify_email_code)
        push_btn.clicked.connect(self.push_sync)
        status_btn.clicked.connect(self.sync_status)
        for widget in [QLabel("Backend URL"), self.sync_url_edit, self.email_edit, self.code_edit, request_btn, verify_btn, push_btn, status_btn, self.sync_log]:
            sync_layout.addWidget(widget)

        templates = QGroupBox("Шаблоны")
        templates_layout = QVBoxLayout(templates)
        self.template_list = QListWidget()
        self.template_list.setObjectName("CompactList")
        self.template_type_edit = QLineEdit()
        self.template_type_edit.setPlaceholderText("type")
        self.template_name_edit = QLineEdit()
        self.template_name_edit.setPlaceholderText("Название")
        self.template_editor = QTextEdit()
        self.template_editor.setPlaceholderText("HTML или обычный текст шаблона")
        template_buttons = QHBoxLayout()
        self.save_template_btn = QPushButton("Сохранить")
        self.delete_template_btn = QPushButton("Удалить")
        self.insert_template_btn = QPushButton("Вставить")
        self.save_template_btn.clicked.connect(self.save_template)
        self.delete_template_btn.clicked.connect(self.delete_template)
        self.insert_template_btn.clicked.connect(self.insert_template)
        for button in [self.save_template_btn, self.delete_template_btn, self.insert_template_btn]:
            template_buttons.addWidget(button)
        templates_layout.addWidget(self.template_list, 1)
        templates_layout.addWidget(self.template_type_edit)
        templates_layout.addWidget(self.template_name_edit)
        templates_layout.addWidget(self.template_editor, 2)
        templates_layout.addLayout(template_buttons)
        self.template_list.currentItemChanged.connect(self.on_template_selected)

        layout.addWidget(appearance)
        layout.addWidget(sync, 1)
        layout.addWidget(templates, 1)
        self._sync_custom_theme_buttons()
        return panel

    def run_command(self, command_id: str) -> None:
        aliases = {
            "insert_scene": "scene",
            "insert_dialogue": "dialogue",
            "insert_author_note": "author_note",
            "insert_character_card": "character_card",
            "insert_chapter_plan": "chapter_plan",
            "insert_beat_sheet": "beat_sheet",
            "text_stats": "stats",
            "focus_mode": "focus",
            "compact_mode": "compact",
            "list": "bullet_list",
        }
        command_id = aliases.get(command_id, command_id)
        handlers = {
            "new_project": self.create_project,
            "new_document": self.create_document,
            "save": self.save_document,
            "save_as": self.save_as_html,
            "import_file": self.import_file,
            "import_folder": self.import_folder,
            "export_pdf": self.export_pdf,
            "commit": self.create_commit,
            "undo": self.editor.undo,
            "redo": self.editor.redo,
            "cut": self.editor.cut,
            "copy": self.editor.copy,
            "paste": self.editor.paste,
            "select_all": self.editor.selectAll,
            "find": self.find_text,
            "replace": self.replace_text,
            "replace_all": lambda: self.replace_text(replace_all=True),
            "bold": lambda: self.toggle_char_format("bold"),
            "italic": lambda: self.toggle_char_format("italic"),
            "underline": lambda: self.toggle_char_format("underline"),
            "strike": lambda: self.toggle_char_format("strike"),
            "h1": lambda: self.toggle_heading(1),
            "h2": lambda: self.toggle_heading(2),
            "h3": lambda: self.toggle_heading(3),
            "bullet_list": lambda: self.toggle_list(QTextListFormat.Style.ListDisc),
            "numbered_list": lambda: self.toggle_list(QTextListFormat.Style.ListDecimal),
            "quote": self.toggle_quote,
            "separator": lambda: self.insert_html_block("<hr>"),
            "table": self.insert_table,
            "scene": lambda: self.insert_html_block(WRITER_BLOCKS_HTML["scene"]),
            "dialogue": lambda: self.insert_html_block(WRITER_BLOCKS_HTML["dialogue"]),
            "author_note": lambda: self.insert_html_block(WRITER_BLOCKS_HTML["author_note"]),
            "character_card": lambda: self.insert_html_block(WRITER_BLOCKS_HTML["character_card"]),
            "chapter_plan": lambda: self.insert_html_block(WRITER_BLOCKS_HTML["chapter_plan"]),
            "beat_sheet": lambda: self.insert_html_block(WRITER_BLOCKS_HTML["beat_sheet"]),
            "stats": self.refresh_stats,
            "new_concept": self.create_concept,
            "save_concept": self.save_concept,
            "delete_concept": self.delete_concept,
            "convert_concept": self.convert_concept,
            "new_art": self.open_new_art,
            "save_art": self.save_current_art,
            "export_art": self.export_current_art,
            "clear_canvas": self.clear_current_canvas,
            "brush_tool": self.use_art_brush,
            "eraser_tool": self.use_art_eraser,
            "fill_tool": self.use_art_fill,
            "toggle_art_grid": self.toggle_art_grid,
            "apply_art_preset": self.apply_art_preset,
            "commit_history": lambda: self.tabs.setCurrentIndex(self.git_tab_index),
            "preview_commit": lambda: self.preview_selected_commit("git"),
            "rename_commit": self.rename_selected_commit,
            "delete_commit": lambda: self.delete_selected_commit("git"),
            "rollback_commit": self.rollback_selected_commit,
            "new_branch": self.create_branch,
            "save_branch": self.save_branch_snapshot,
            "checkout_branch": self.checkout_branch,
            "delete_branch": self.delete_branch,
            "template_manager": lambda: self.tabs.setCurrentIndex(self.settings_tab_index),
            "custom_theme": self.focus_custom_theme_settings,
            "update_dialog": self.open_update_dialog,
            "sync_status": self.sync_status,
            "toggle_left": self.toggle_left_panel,
            "toggle_right": self.toggle_right_panel,
            "compact": self.toggle_compact,
            "focus": self.toggle_focus,
            "help": self.show_help_center,
            "font_increase": self.documents_tab.editor_panel.increase_font,
            "font_decrease": self.documents_tab.editor_panel.decrease_font,
        }
        handler = handlers.get(command_id)
        if handler:
            handler()

    def reload_projects(self) -> None:
        project_list = self.documents_tab.sidebar.project_list
        project_list.blockSignals(True)
        project_list.clear()
        for project in self.store.list_projects():
            item = QListWidgetItem(project.title)
            item.setData(256, project.id)
            project_list.addItem(item)
        project_list.blockSignals(False)
        if project_list.count() == 0:
            project = self.store.create_project("Мой первый проект", "Создан RedCord 0.8.3")
            self.reload_projects()
            self.select_project(project.id)
        elif self.current_project_id is None:
            project_list.setCurrentRow(0)
        self.refresh_account_label()
        self.reload_templates()

    def select_project(self, project_id: str) -> None:
        project_list = self.documents_tab.sidebar.project_list
        for row in range(project_list.count()):
            if project_list.item(row).data(256) == project_id:
                project_list.setCurrentRow(row)
                return

    def reload_documents(self, select_document_id: str | None = None) -> None:
        document_list = self.documents_tab.sidebar.document_list
        document_list.blockSignals(True)
        document_list.clear()
        if self.current_project_id:
            for document in self.store.list_documents(self.current_project_id):
                item = QListWidgetItem(document.title)
                item.setData(256, document.id)
                document_list.addItem(item)
        document_list.blockSignals(False)
        if select_document_id:
            for row in range(document_list.count()):
                if document_list.item(row).data(256) == select_document_id:
                    document_list.setCurrentRow(row)
                    return

    def on_project_selected(self, current: QListWidgetItem | None = None, _previous: QListWidgetItem | None = None) -> None:
        item = current or self.documents_tab.sidebar.project_list.currentItem()
        self.current_project_id = str(item.data(256)) if item else None
        self.reload_documents()
        self.reload_concepts()
        self.art_tab.reload_assets()

    def on_document_selected(self, current: QListWidgetItem | None = None, _previous: QListWidgetItem | None = None) -> None:
        item = current or self.documents_tab.sidebar.document_list.currentItem()
        if item:
            self.load_document(str(item.data(256)))

    def load_document(self, document_id: str) -> None:
        document = self.store.get_document(document_id)
        if not document:
            return
        self.current_document = document
        self.current_document_id = document.id
        panel = self.documents_tab.editor_panel
        self._loading_document = True
        panel.title_edit.setText(document.title)
        self._ensure_type_choice(document.doc_type)
        panel.type_combo.setCurrentText(document.doc_type)
        panel.tags_edit.setText(document.tags)
        panel.category_edit.setText(document.category)
        panel.editor.setHtml(document.content_html)
        self._loading_document = False
        self.dirty = False
        self.update_document_info(document)
        self.reload_commits()
        self.reload_branches()
        self.refresh_stats()

    def update_document_info(self, document: Document) -> None:
        self.documents_tab.inspector.info_label.setText(
            f"{document.title}\nТип: {document.doc_type}\nОбновлён: {document.updated_at}\nSync: {document.sync_state}\nRevision: {document.revision}"
        )

    def create_project(self) -> None:
        title, ok = QInputDialog.getText(self, "Новый проект", "Название проекта:")
        if not ok or not title.strip():
            return
        project = self.store.create_project(title)
        self.reload_projects()
        self.select_project(project.id)
        self.set_status("Проект создан")

    def create_document(self) -> None:
        if not self.current_project_id:
            self.create_project()
        if not self.current_project_id:
            return
        title, ok = QInputDialog.getText(self, "Новый документ", "Название документа:")
        if not ok or not title.strip():
            return
        doc_type = self.documents_tab.editor_panel.type_combo.currentText() or "note"
        document = self.store.create_document(self.current_project_id, title, doc_type)
        self.reload_documents(document.id)
        self.load_document(document.id)
        self.set_status("Документ создан")

    def save_document(self) -> bool:
        if not self.current_document_id:
            self.create_document()
            return bool(self.current_document_id)
        panel = self.documents_tab.editor_panel
        document = Document(
            id=self.current_document_id,
            owner_id=DEFAULT_OWNER_ID,
            project_id=self.current_project_id or "",
            title=panel.title_edit.text().strip() or "Без названия",
            doc_type=panel.type_combo.currentText().strip() or "note",
            content_html=panel.editor.toHtml(),
            content_plain=panel.editor.toPlainText(),
            tags=panel.tags_edit.text().strip(),
            category=panel.category_edit.text().strip(),
            updated_at=utc_now_iso(),
            sync_state="local",
            revision=(self.current_document.revision + 1) if self.current_document else 0,
        )
        self.store.upsert_document(document)
        self.current_document = document
        self.dirty = False
        self.reload_documents(document.id)
        self.load_document(document.id)
        self._show_save_feedback("Сохранено")
        return True

    def autosave(self) -> None:
        if self.autosave_enabled and self.dirty and self.current_document_id:
            self.save_document()

    def toggle_autosave(self) -> None:
        self.autosave_enabled = not self.autosave_enabled
        text = "Автосохранение: включено" if self.autosave_enabled else "Автосохранение: выключено"
        self.documents_tab.editor_panel.autosave_btn.setText(text)
        self.set_status(text)

    def _show_save_feedback(self, message: str) -> None:
        label = self.documents_tab.editor_panel.save_feedback_label
        label.setText(message)
        label.show()
        QTimer.singleShot(1600, label.hide)
        self.set_status(message)

    def save_as_html(self) -> None:
        if not self.current_document_id:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить как HTML", str(Path.home() / "document.html"), "HTML (*.html)")
        if path:
            Path(path).write_text(self.editor.toHtml(), encoding="utf-8")
            self.set_status(f"HTML экспортирован: {path}")

    def import_file(self) -> None:
        if not self.current_project_id:
            self.create_project()
        if not self.current_project_id:
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Импорт файла",
            str(Path.home()),
            "Documents (*.txt *.md *.html *.htm *.docx);;All files (*.*)",
        )
        if path:
            document = self._import_path(Path(path))
            if document:
                self.reload_documents(document.id)
                self.load_document(document.id)

    def import_folder(self) -> None:
        if not self.current_project_id:
            self.create_project()
        if not self.current_project_id:
            return
        folder = QFileDialog.getExistingDirectory(self, "Импорт папки", str(Path.home()))
        if not folder:
            return
        imported = 0
        for path in Path(folder).rglob("*"):
            if path.is_file() and path.suffix.lower() in {".txt", ".md", ".html", ".htm", ".docx"}:
                imported += 1 if self._import_path(path) else 0
        self.reload_documents()
        self.set_status(f"Импортировано файлов: {imported}")

    def _import_path(self, path: Path) -> Document | None:
        if not self.current_project_id:
            return None
        title = path.stem
        suffix = path.suffix.lower()
        try:
            if suffix == ".docx":
                from docx import Document as DocxDocument

                plain = "\n".join(p.text for p in DocxDocument(str(path)).paragraphs)
                html = plain_to_html(plain)
            else:
                text = path.read_text(encoding="utf-8", errors="ignore")
                if suffix in {".html", ".htm"}:
                    html = text
                    document_for_plain = QTextDocument()
                    document_for_plain.setHtml(text)
                    plain = document_for_plain.toPlainText()
                else:
                    plain = text
                    html = plain_to_html(text)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Импорт", f"Не удалось импортировать {path.name}: {exc}")
            return None
        document = self.store.create_document(self.current_project_id, title, "imported")
        document.content_html = html
        document.content_plain = plain
        document.updated_at = utc_now_iso()
        self.store.upsert_document(document)
        return document

    def export_pdf(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Экспорт PDF", str(Path.home() / "document.pdf"), "PDF (*.pdf)")
        if not path:
            return
        target = Path(path)
        if target.suffix.lower() != ".pdf":
            target = target.with_suffix(".pdf")
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(str(target))
        document = QTextDocument()
        document.setHtml(self.editor.toHtml())
        document.print(printer)
        self.set_status(f"PDF экспортирован: {target}")

    def create_commit(self) -> None:
        if self.dirty:
            self.save_document()
        if not self.current_document:
            QMessageBox.information(self, "Коммит", "Сначала открой документ.")
            return
        message, ok = QInputDialog.getText(self, "Коммит", "Сообщение:")
        if not ok:
            return
        self.store.create_commit(self.current_document, message)
        self.reload_commits()
        self.set_status("Коммит создан")

    def reload_commits(self) -> None:
        for widget in [self.documents_tab.inspector.commit_list_side, self.git_commit_list]:
            widget.clear()
        if not self.current_document_id:
            return
        for commit in self.store.list_commits(self.current_document_id):
            text = f"{commit.created_at} - {commit.message}"
            for widget in [self.documents_tab.inspector.commit_list_side, self.git_commit_list]:
                item = QListWidgetItem(text)
                item.setData(256, commit.id)
                widget.addItem(item)

    def selected_commit_id(self, source: str = "git") -> str | None:
        widget = self.documents_tab.inspector.commit_list_side if source == "side" else self.git_commit_list
        item = widget.currentItem()
        return str(item.data(256)) if item else None

    def preview_selected_commit(self, source: str = "git") -> None:
        commit_id = self.selected_commit_id(source)
        if not commit_id:
            return
        commit = self.store.get_commit(commit_id)
        if commit:
            self.git_preview.setHtml(commit.content_html)
            self.tabs.setCurrentIndex(self.git_tab_index)

    def rename_selected_commit(self) -> None:
        commit_id = self.selected_commit_id("git")
        if not commit_id:
            return
        message, ok = QInputDialog.getText(self, "Rename commit", "Новое сообщение:")
        if ok:
            self.store.rename_commit(commit_id, message)
            self.reload_commits()

    def delete_selected_commit(self, source: str = "git") -> None:
        commit_id = self.selected_commit_id(source)
        if not commit_id:
            return
        if QMessageBox.question(self, "Удалить коммит", "Удалить выбранный коммит?") == QMessageBox.StandardButton.Yes:
            self.store.delete_commit(commit_id)
            self.reload_commits()

    def rollback_selected_commit(self) -> None:
        commit_id = self.selected_commit_id("git")
        if not commit_id:
            return
        if QMessageBox.question(self, "Rollback", "Откатить документ к выбранному коммиту?") != QMessageBox.StandardButton.Yes:
            return
        document = self.store.rollback_commit(commit_id)
        if document:
            self.load_document(document.id)
            self.set_status("Документ восстановлен из коммита")

    def reload_branches(self) -> None:
        self.branch_list.clear()
        if not self.current_document_id:
            return
        for branch in self.store.list_branches(self.current_document_id):
            item = QListWidgetItem(f"{branch.updated_at} - {branch.name}")
            item.setData(256, branch.id)
            self.branch_list.addItem(item)

    def selected_branch_id(self) -> str | None:
        item = self.branch_list.currentItem()
        return str(item.data(256)) if item else None

    def create_branch(self) -> None:
        if self.dirty:
            self.save_document()
        if not self.current_document:
            return
        name, ok = QInputDialog.getText(self, "Новая ветка", "Название ветки:")
        if ok:
            self.store.create_branch(self.current_document, name)
            self.reload_branches()

    def save_branch_snapshot(self) -> None:
        branch_id = self.selected_branch_id()
        if not branch_id or not self.current_document:
            return
        if self.dirty:
            self.save_document()
        if self.current_document:
            self.store.save_document_to_branch(branch_id, self.current_document)
            self.reload_branches()
            self.set_status("Ветка обновлена")

    def checkout_branch(self) -> None:
        branch_id = self.selected_branch_id()
        if not branch_id:
            return
        if QMessageBox.question(self, "Checkout", "Загрузить выбранную ветку в документ?") != QMessageBox.StandardButton.Yes:
            return
        document = self.store.checkout_branch(branch_id)
        if document:
            self.load_document(document.id)
            self.set_status("Ветка загружена")

    def delete_branch(self) -> None:
        branch_id = self.selected_branch_id()
        if branch_id:
            self.store.delete_branch(branch_id)
            self.reload_branches()

    def reload_concepts(self) -> None:
        self.concept_list.blockSignals(True)
        self.concept_list.clear()
        if self.current_project_id:
            for concept in self.store.list_concepts(self.current_project_id):
                item = QListWidgetItem(f"{concept.title} [{concept.status}]")
                item.setData(256, concept.id)
                self.concept_list.addItem(item)
        self.concept_list.blockSignals(False)

    def on_concept_selected(self, current: QListWidgetItem | None = None, _previous: QListWidgetItem | None = None) -> None:
        item = current or self.concept_list.currentItem()
        if not item:
            return
        concept = self.store.get_concept(str(item.data(256)))
        if not concept:
            return
        self.current_concept_id = concept.id
        self._loading_concept = True
        self.concept_title_edit.setText(concept.title)
        self.concept_status_edit.setText(concept.status)
        self.concept_editor.setHtml(concept.content_html)
        self._loading_concept = False
        self.concept_dirty = False

    def create_concept(self) -> None:
        if not self.current_project_id:
            self.create_project()
        if not self.current_project_id:
            return
        title, ok = QInputDialog.getText(self, "Новый концепт", "Название:")
        if not ok:
            return
        concept = self.store.create_concept(self.current_project_id, title)
        self.reload_concepts()
        self._select_concept(concept.id)

    def _select_concept(self, concept_id: str) -> None:
        for row in range(self.concept_list.count()):
            if self.concept_list.item(row).data(256) == concept_id:
                self.concept_list.setCurrentRow(row)
                return

    def save_concept(self) -> bool:
        if not self.current_concept_id:
            self.create_concept()
            return bool(self.current_concept_id)
        concept = Concept(
            id=self.current_concept_id,
            owner_id=DEFAULT_OWNER_ID,
            project_id=self.current_project_id or "",
            title=self.concept_title_edit.text().strip() or "Без названия",
            content_html=self.concept_editor.toHtml(),
            content_plain=self.concept_editor.toPlainText(),
            status=self.concept_status_edit.text().strip() or "Idea",
            updated_at=utc_now_iso(),
            sync_state="local",
            revision=(self.store.get_concept(self.current_concept_id).revision + 1) if self.store.get_concept(self.current_concept_id) else 0,
        )
        self.store.upsert_concept(concept)
        self.concept_dirty = False
        self.reload_concepts()
        self._select_concept(concept.id)
        self.set_status("Концепт сохранён")
        return True

    def delete_concept(self) -> None:
        if self.current_concept_id:
            self.store.delete_concept(self.current_concept_id)
            self.current_concept_id = None
            self.concept_title_edit.clear()
            self.concept_status_edit.setText("Idea")
            self.concept_editor.clear()
            self.reload_concepts()

    def convert_concept(self) -> None:
        if self.concept_dirty:
            self.save_concept()
        if not self.current_concept_id or not self.current_project_id:
            return
        concept = self.store.get_concept(self.current_concept_id)
        if not concept:
            return
        document = self.store.create_document(self.current_project_id, concept.title, "concept")
        document.content_html = concept.content_html
        document.content_plain = concept.content_plain
        self.store.upsert_document(document)
        self.reload_documents(document.id)
        self.load_document(document.id)
        self.tabs.setCurrentIndex(self.documents_tab_index)

    def merge_char_format(self, weight: QFont.Weight | None = None, italic: bool | None = None, underline: bool | None = None, strike: bool | None = None) -> None:
        fmt = QTextCharFormat()
        if weight is not None:
            fmt.setFontWeight(weight)
        if italic is not None:
            fmt.setFontItalic(italic)
        if underline is not None:
            fmt.setFontUnderline(underline)
        if strike is not None:
            fmt.setFontStrikeOut(strike)
        self.editor.textCursor().mergeCharFormat(fmt)
        self.editor.mergeCurrentCharFormat(fmt)

    def set_heading(self, level: int) -> None:
        cursor = self.editor.textCursor()
        block = QTextBlockFormat()
        fmt = QTextCharFormat()
        fmt.setFontWeight(QFont.Weight.Bold)
        fmt.setFontPointSize({1: 24, 2: 18, 3: 15}[level])
        cursor.mergeBlockFormat(block)
        cursor.mergeCharFormat(fmt)

    def insert_list(self, style: QTextListFormat.Style) -> None:
        fmt = QTextListFormat()
        fmt.setStyle(style)
        self.editor.textCursor().createList(fmt)

    def insert_quote(self) -> None:
        self.insert_html_block("<blockquote>Цитата или заметка...</blockquote>")

    def toggle_char_format(self, kind: str) -> None:
        cursor = self.editor.textCursor()
        current = cursor.charFormat()
        fmt = QTextCharFormat()
        if kind == "bold":
            enabled = current.fontWeight() >= QFont.Weight.Bold
            fmt.setFontWeight(QFont.Weight.Normal if enabled else QFont.Weight.Bold)
        elif kind == "italic":
            fmt.setFontItalic(not current.fontItalic())
        elif kind == "underline":
            fmt.setFontUnderline(not current.fontUnderline())
        elif kind == "strike":
            fmt.setFontStrikeOut(not current.fontStrikeOut())
        else:
            return
        if cursor.hasSelection():
            cursor.mergeCharFormat(fmt)
            self.editor.setTextCursor(cursor)
        self.editor.mergeCurrentCharFormat(fmt)
        self.mark_dirty()
        self.update_format_state()

    def toggle_heading(self, level: int) -> None:
        sizes = {1: 24, 2: 18, 3: 15}
        target_size = sizes[level]
        cursor = self.editor.textCursor()
        current = cursor.charFormat()
        current_size = current.fontPointSize()
        enabled = abs(current_size - target_size) < 0.5 and current.fontWeight() >= QFont.Weight.Bold
        fmt = QTextCharFormat()
        fmt.setFontWeight(QFont.Weight.Normal if enabled else QFont.Weight.Bold)
        fmt.setFontPointSize(12 if enabled else target_size)
        cursor.mergeCharFormat(fmt)
        self.editor.setTextCursor(cursor)
        self.editor.mergeCurrentCharFormat(fmt)
        self.mark_dirty()
        self.update_format_state()

    def toggle_list(self, style: QTextListFormat.Style) -> None:
        cursor = self.editor.textCursor()
        current_list = cursor.currentList()
        if current_list and current_list.format().style() == style:
            current_list.remove(cursor.block())
            block = cursor.blockFormat()
            block.setIndent(0)
            cursor.setBlockFormat(block)
        else:
            fmt = QTextListFormat()
            fmt.setStyle(style)
            cursor.createList(fmt)
        self.mark_dirty()
        self.update_format_state()

    def toggle_quote(self) -> None:
        cursor = self.editor.textCursor()
        block = cursor.blockFormat()
        enabled = block.leftMargin() >= 24
        block.setLeftMargin(0 if enabled else 32)
        block.setRightMargin(0 if enabled else 12)
        cursor.setBlockFormat(block)
        fmt = QTextCharFormat()
        fmt.setFontItalic(not enabled)
        cursor.mergeCharFormat(fmt)
        self.editor.setTextCursor(cursor)
        self.mark_dirty()
        self.update_format_state()

    def update_format_state(self, *_args: object) -> None:
        fmt = self.editor.currentCharFormat()
        self.ribbon.set_action_checked("bold", fmt.fontWeight() >= QFont.Weight.Bold)
        self.ribbon.set_action_checked("italic", fmt.fontItalic())
        self.ribbon.set_action_checked("underline", fmt.fontUnderline())
        self.ribbon.set_action_checked("strike", fmt.fontStrikeOut())
        point_size = fmt.fontPointSize()
        for level, size in {1: 24, 2: 18, 3: 15}.items():
            self.ribbon.set_action_checked(f"h{level}", abs(point_size - size) < 0.5 and fmt.fontWeight() >= QFont.Weight.Bold)
        current_list = self.editor.textCursor().currentList()
        self.ribbon.set_action_checked(
            "bullet_list",
            bool(current_list and current_list.format().style() == QTextListFormat.Style.ListDisc),
        )
        self.ribbon.set_action_checked(
            "numbered_list",
            bool(current_list and current_list.format().style() == QTextListFormat.Style.ListDecimal),
        )
        self.ribbon.set_action_checked("quote", self.editor.textCursor().blockFormat().leftMargin() >= 24)

    def insert_table(self) -> None:
        self.editor.textCursor().insertTable(2, 2)
        self.mark_dirty()

    def insert_html_block(self, html: str) -> None:
        self.editor.textCursor().insertHtml(html)
        self.mark_dirty()

    def find_text(self) -> None:
        query = self.documents_tab.inspector.writer_find_edit.text().strip()
        if query and not self.editor.find(query):
            cursor = self.editor.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            self.editor.setTextCursor(cursor)
            self.editor.find(query)

    def replace_text(self, replace_all: bool = False) -> None:
        query = self.documents_tab.inspector.writer_find_edit.text()
        replacement = self.documents_tab.inspector.writer_replace_edit.text()
        if not query:
            return
        if replace_all:
            count = 0
            cursor = QTextCursor(self.editor.document())
            cursor.beginEditBlock()
            while True:
                found = self.editor.document().find(query, cursor)
                if found.isNull():
                    break
                found.insertText(replacement)
                cursor = found
                count += 1
            cursor.endEditBlock()
            if count:
                self.mark_dirty()
            self.set_status(f"Заменено: {count}")
            return
        cursor = self.editor.textCursor()
        selected = cursor.selectedText().replace("\u2029", "\n")
        if not cursor.hasSelection() or selected != query:
            self.find_text()
            cursor = self.editor.textCursor()
        if cursor.hasSelection():
            cursor.insertText(replacement)
            self.mark_dirty()
            self.set_status("Заменено")

    def refresh_stats(self) -> None:
        stats = text_statistics(self.editor.toPlainText())
        self.documents_tab.inspector.word_stats_label.setText(stats.as_status_text())
        self.set_status(stats.as_status_text())

    def search_documents(self) -> None:
        query = self.documents_tab.inspector.search_edit.text().strip()
        results = self.documents_tab.inspector.search_results_list
        results.clear()
        if not query:
            return
        for document in self.store.search_documents(query):
            item = QListWidgetItem(f"{document.title} [{document.doc_type}]")
            item.setData(256, document.id)
            results.addItem(item)

    def open_search_result(self, item: QListWidgetItem) -> None:
        self.load_document(str(item.data(256)))
        self.tabs.setCurrentIndex(self.documents_tab_index)

    def current_selected_or_all_text(self) -> str:
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            return cursor.selectedText().replace("\u2029", "\n")
        return self.editor.toPlainText()

    def ai_insert_result_text(self, result: str) -> None:
        self.editor.textCursor().insertText(result)
        self.mark_dirty()

    def ai_replace_document_text(self, result: str) -> None:
        self.editor.setHtml(plain_to_html(result))
        self.mark_dirty()

    def ai_replace_selection_text(self, result: str) -> None:
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            cursor.insertText(result)
        else:
            cursor.insertText(result)
        self.mark_dirty()

    def ai_create_document_from_result(self, title: str, result: str) -> None:
        if not self.current_project_id:
            self.create_project()
        if not self.current_project_id:
            return
        document = self.store.create_document(self.current_project_id, title, "ai")
        document.content_html = plain_to_html(result)
        document.content_plain = result
        self.store.upsert_document(document)
        self.reload_documents(document.id)
        self.load_document(document.id)
        self.tabs.setCurrentIndex(self.documents_tab_index)

    def reload_templates(self) -> None:
        self.documents_tab.editor_panel.type_combo.blockSignals(True)
        self.documents_tab.editor_panel.type_combo.clear()
        template_types = list(DEFAULT_TEMPLATES)
        for template in self.store.list_templates():
            if template.type not in template_types:
                template_types.append(template.type)
        for template_type in template_types:
            self.documents_tab.editor_panel.type_combo.addItem(template_type)
        self.documents_tab.editor_panel.type_combo.blockSignals(False)

        self.template_list.clear()
        for template in self.store.list_templates():
            item = QListWidgetItem(f"{template.type} - {template.name}")
            item.setData(256, template.type)
            self.template_list.addItem(item)

    def _ensure_type_choice(self, doc_type: str) -> None:
        combo = self.documents_tab.editor_panel.type_combo
        if combo.findText(doc_type) < 0:
            combo.addItem(doc_type)

    def on_template_selected(self, current: QListWidgetItem | None = None, _previous: QListWidgetItem | None = None) -> None:
        if not current:
            return
        template = self.store.get_template_by_type(str(current.data(256)))
        if not template:
            return
        self.template_type_edit.setText(template.type)
        self.template_name_edit.setText(template.name)
        self.template_editor.setHtml(template.content_html)

    def save_template(self) -> None:
        template_type = self.template_type_edit.text().strip()
        if not template_type:
            return
        html = self.template_editor.toHtml()
        plain = self.template_editor.toPlainText()
        self.store.create_or_update_template(template_type, self.template_name_edit.text(), html, plain)
        self.reload_templates()
        self.set_status("Шаблон сохранён")

    def delete_template(self) -> None:
        template_type = self.template_type_edit.text().strip()
        if template_type:
            self.store.delete_template(template_type)
            self.reload_templates()

    def insert_template(self) -> None:
        template_type = self.template_type_edit.text().strip()
        template = self.store.get_template_by_type(template_type)
        if template:
            self.insert_html_block(template.content_html)

    def open_new_art(self) -> None:
        self.tabs.setCurrentIndex(self.art_tab_index)
        self.art_tab.new_art()

    def save_current_art(self) -> None:
        self.tabs.setCurrentIndex(self.art_tab_index)
        self.art_tab.save_art()

    def export_current_art(self) -> None:
        self.tabs.setCurrentIndex(self.art_tab_index)
        self.art_tab.export_art()

    def clear_current_canvas(self) -> None:
        self.tabs.setCurrentIndex(self.art_tab_index)
        self.art_tab.clear_canvas()

    def use_art_brush(self) -> None:
        self.tabs.setCurrentIndex(self.art_tab_index)
        self.art_tab.set_tool("brush")

    def use_art_eraser(self) -> None:
        self.tabs.setCurrentIndex(self.art_tab_index)
        self.art_tab.set_tool("eraser")

    def use_art_fill(self) -> None:
        self.tabs.setCurrentIndex(self.art_tab_index)
        self.art_tab.set_tool("fill")

    def toggle_art_grid(self) -> None:
        self.tabs.setCurrentIndex(self.art_tab_index)
        self.art_tab.toggle_grid()

    def apply_art_preset(self) -> None:
        self.tabs.setCurrentIndex(self.art_tab_index)
        self.art_tab.apply_canvas_preset()

    def request_email_code(self) -> None:
        try:
            message = SyncClient(self.sync_url_edit.text()).request_code(self.email_edit.text())
            self.sync_log.append(message)
        except SyncError as exc:
            self.sync_log.append(str(exc))

    def verify_email_code(self) -> None:
        try:
            token = SyncClient(self.sync_url_edit.text()).verify_code(self.email_edit.text(), self.code_edit.text())
            self.store.save_account(self.email_edit.text(), token)
            self.refresh_account_label()
            self.sync_log.append("Вход выполнен.")
        except SyncError as exc:
            self.sync_log.append(str(exc))

    def push_sync(self) -> None:
        account = self.store.active_account()
        if not account.token:
            self.sync_log.append("Сначала войди по email code.")
            return
        try:
            result = SyncClient(self.sync_url_edit.text()).push(self.store.outgoing_changes(), account.token)
            self.sync_log.append(str(result))
            conflict_copies = self._create_sync_conflict_copies(result)
            if conflict_copies:
                self.reload_documents()
                self.sync_log.append(f"Created local conflict copies: {conflict_copies}")
        except SyncError as exc:
            self.sync_log.append(str(exc))

    def _create_sync_conflict_copies(self, result: dict[str, object]) -> int:
        conflicts = result.get("conflicts", [])
        if not isinstance(conflicts, list):
            return 0
        created = 0
        for conflict in conflicts:
            if not isinstance(conflict, dict) or conflict.get("entity_type") != "document":
                continue
            document_id = str(conflict.get("entity_id", ""))
            server_revision = str(conflict.get("server_revision", "unknown"))
            if document_id and self.store.create_document_conflict_copy(document_id, f"Server revision {server_revision} is newer."):
                created += 1
        return created

    def sync_status(self) -> None:
        account = self.store.active_account()
        if not account.token:
            self.sync_log.append("Offline account.")
            return
        try:
            self.sync_log.append(str(SyncClient(self.sync_url_edit.text()).status(account.token)))
        except SyncError as exc:
            self.sync_log.append(str(exc))

    def refresh_account_label(self) -> None:
        account = self.store.active_account()
        self.documents_tab.sidebar.profile_label.setText(account.email or "RedCord")

    def show_help_center(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("RedCord Help Center")
        dialog.resize(820, 620)
        layout = QVBoxLayout(dialog)
        search = QLineEdit()
        search.setPlaceholderText("Поиск по справке")
        view = QTextEdit()
        view.setReadOnly(True)
        view.setPlainText(self.registry.help_markdown())
        layout.addWidget(search)
        layout.addWidget(view, 1)

        def filter_help(text: str) -> None:
            source = self.registry.help_markdown()
            if not text.strip():
                view.setPlainText(source)
                return
            lines = [line for line in source.splitlines() if text.lower() in line.lower() or line.startswith("#")]
            view.setPlainText("\n".join(lines))

        search.textChanged.connect(filter_help)
        dialog.exec()

    def open_update_dialog(self) -> None:
        UpdateDialog(self).exec()

    def apply_theme(self, _index: int | None = None) -> None:
        key = str(self.theme_combo.currentData() or "dark_crimson")
        resolved = theme_key(key)
        self.user_settings = self.settings_service.update_theme(resolved)
        QApplication.instance().setStyleSheet(build_qss_08(resolved, self.custom_theme))
        self.set_status(f"Тема: {self.theme_combo.currentText()}")

    def pick_custom_theme_color(self, key: str) -> None:
        current = QColor(self.custom_theme.get(key, "#b93649"))
        color = QColorDialog.getColor(current, self, "Custom dark color")
        if not color.isValid():
            return
        self.custom_theme[key] = color.name()
        self._sync_custom_theme_buttons()

    def save_custom_theme_settings(self) -> None:
        self.custom_theme = save_custom_theme(self.custom_theme)
        self._sync_custom_theme_buttons()
        self._set_combo_value(self.theme_combo, CUSTOM_THEME_KEY)
        self.apply_theme()

    def focus_custom_theme_settings(self) -> None:
        self.tabs.setCurrentIndex(self.settings_tab_index)
        self._set_combo_value(self.theme_combo, CUSTOM_THEME_KEY)
        self.apply_theme()

    def _sync_custom_theme_buttons(self) -> None:
        for key, button in self.custom_color_buttons.items():
            color = self.custom_theme.get(key, "#b93649")
            button.setText(color)
            text_color = "#111111" if key in {"text"} else "#ffffff"
            button.setStyleSheet(f"background: {color}; color: {text_color};")

    def _set_combo_value(self, combo: QComboBox, value: str) -> None:
        for index in range(combo.count()):
            if combo.itemData(index) == value:
                combo.setCurrentIndex(index)
                return

    def toggle_left_panel(self) -> None:
        visible = self.documents_tab.toggle_left_panel()
        self.set_status("Левая панель показана" if visible else "Левая панель скрыта")

    def toggle_right_panel(self) -> None:
        visible = self.documents_tab.toggle_right_panel()
        self.set_status("Правая панель показана" if visible else "Правая панель скрыта")

    def toggle_focus(self) -> None:
        self.focus_mode = not self.focus_mode
        self.documents_tab.set_focus_mode(self.focus_mode)
        self.ribbon.set_focus_mode(self.focus_mode)
        self.tabs.tabBar().setVisible(not self.focus_mode)
        self.set_status("Focus Mode включён" if self.focus_mode else "Focus Mode выключен")

    def toggle_compact(self) -> None:
        self.compact_mode = not self.compact_mode
        self.documents_tab.set_compact_mode(self.compact_mode)
        self.ribbon.set_compact_mode(self.compact_mode)
        self.set_status("Compact Mode включён" if self.compact_mode else "Compact Mode выключен")

    def mark_dirty(self, *_args: object) -> None:
        if not self._loading_document and self.current_document_id:
            self.dirty = True
            self.set_status("Есть несохранённые изменения")

    def mark_concept_dirty(self, *_args: object) -> None:
        if not self._loading_concept and self.current_concept_id:
            self.concept_dirty = True

    def set_status(self, text: str) -> None:
        self.statusBar().showMessage(text)
