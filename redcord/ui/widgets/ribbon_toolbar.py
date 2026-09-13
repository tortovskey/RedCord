from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QSizePolicy,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from redcord.services.command_registry import Command, CommandRegistry


TOGGLE_COMMANDS = {
    "bold",
    "italic",
    "underline",
    "strike",
    "h1",
    "h2",
    "h3",
    "bullet_list",
    "numbered_list",
    "quote",
}

QUICK_COMMANDS = [
    "save",
    "undo",
    "redo",
    "new_document",
    "find",
    "export_pdf",
    "new_art",
    "save_art",
    "focus",
]

RIBBON_PAGES: dict[str, tuple[str, ...]] = {
    "Home": ("File / Document", "Edit", "Format"),
    "Insert": ("Writer", "Concepts"),
    "Art": ("Art / BoC Lite",),
    "Review": ("Git / Versions",),
    "View": ("View",),
    "Settings": ("Settings",),
}


class RibbonToolbar(QScrollArea):
    actionTriggered = pyqtSignal(str)

    def __init__(self, registry: CommandRegistry | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.registry = registry or CommandRegistry()
        self.setObjectName("RibbonToolbar")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setFixedHeight(146)

        self._buttons: dict[str, list[QToolButton]] = {}
        self._groups: dict[str, QFrame] = {}
        self._page_buttons: dict[str, QToolButton] = {}
        self._active_page = "Home"
        self._compact = False
        self._focus = False

        content = QWidget()
        content.setObjectName("RibbonContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        content_layout.addWidget(self._build_quick_bar())
        content_layout.addWidget(self._build_page_tabs())

        self._group_row = QWidget()
        self._group_row.setObjectName("RibbonGroupRow")
        self._group_layout = QHBoxLayout(self._group_row)
        self._group_layout.setContentsMargins(8, 6, 8, 6)
        self._group_layout.setSpacing(8)
        for group, commands in self.registry.groups().items():
            self._add_group(self._group_layout, group, commands)
        self._group_layout.addStretch(1)
        content_layout.addWidget(self._group_row)

        self.setWidget(content)
        self.set_active_page("Home")

    def set_compact_mode(self, enabled: bool) -> None:
        self._compact = enabled
        self.setFixedHeight(108 if enabled else 146)
        for buttons in self._buttons.values():
            for button in buttons:
                if button.objectName() == "QuickBarButton":
                    button.setFixedHeight(22 if enabled else 24)
                    button.setMaximumWidth(36 if enabled else 96)
                    continue
                button.setToolButtonStyle(
                    Qt.ToolButtonStyle.ToolButtonIconOnly
                    if enabled
                    else Qt.ToolButtonStyle.ToolButtonTextBesideIcon
                )
                button.setFixedHeight(24 if enabled else 28)
                button.setMaximumWidth(56 if enabled else 132)
        if self._focus:
            self.set_focus_mode(True)

    def set_focus_mode(self, enabled: bool) -> None:
        self._focus = enabled
        focus_actions = {
            "save",
            "undo",
            "redo",
            "find",
            "replace",
            "bold",
            "italic",
            "underline",
            "h1",
            "h2",
            "scene",
            "stats",
            "focus",
            "compact",
        }
        for action, buttons in self._buttons.items():
            for button in buttons:
                button.setVisible((action in focus_actions) if enabled else True)
        self._group_row.setVisible(not enabled)
        for button in self._page_buttons.values():
            button.setVisible(not enabled)
        self.setFixedHeight(42 if enabled else (108 if self._compact else 146))

    def set_action_checked(self, command_id: str, checked: bool) -> None:
        for button in self._buttons.get(command_id, []):
            if button.isCheckable() and button.isChecked() != checked:
                button.blockSignals(True)
                button.setChecked(checked)
                button.blockSignals(False)

    def set_active_page(self, page: str) -> None:
        if page not in RIBBON_PAGES:
            return
        self._active_page = page
        visible_groups = set(RIBBON_PAGES[page])
        for name, group in self._groups.items():
            group.setVisible(name in visible_groups)
        for name, button in self._page_buttons.items():
            button.blockSignals(True)
            button.setChecked(name == page)
            button.blockSignals(False)

    def _build_quick_bar(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("QuickBar")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(5)

        title = QLabel("RedCord 0.8.3")
        title.setObjectName("QuickBarTitle")
        layout.addWidget(title)
        layout.addSpacing(8)

        for command_id in QUICK_COMMANDS:
            command = self.registry.by_id(command_id)
            button = self._build_button(command, quick=True)
            layout.addWidget(button)

        layout.addSpacing(10)
        self.command_hint = QLineEdit()
        self.command_hint.setObjectName("RibbonCommandHint")
        self.command_hint.setReadOnly(True)
        self.command_hint.setText("Home: document, edit and format")
        self.command_hint.setMaximumWidth(260)
        layout.addWidget(self.command_hint)
        layout.addStretch(1)
        return frame

    def _build_page_tabs(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("RibbonTabs")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(2)
        hints = {
            "Home": "Home: document, edit and format",
            "Insert": "Insert: writer blocks and concepts",
            "Art": "Art: BoC Lite canvas and covers",
            "Review": "Review: commits and branches",
            "View": "View: panels, focus and density",
            "Settings": "Settings: theme, sync and updates",
        }
        for page in RIBBON_PAGES:
            button = QToolButton()
            button.setObjectName("RibbonTabButton")
            button.setText(page)
            button.setCheckable(True)
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
            button.clicked.connect(lambda _checked=False, value=page: self._select_page(value, hints[value]))
            self._page_buttons[page] = button
            layout.addWidget(button)
        layout.addStretch(1)
        return frame

    def _select_page(self, page: str, hint: str) -> None:
        self.set_active_page(page)
        self.command_hint.setText(hint)

    def _add_group(self, parent_layout: QHBoxLayout, group_name: str, commands: list[Command]) -> None:
        group = QFrame()
        group.setObjectName("RibbonGroup")
        self._groups[group_name] = group
        layout = QVBoxLayout(group)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(3)

        title_label = QLabel(group_name)
        title_label.setObjectName("RibbonGroupTitle")
        layout.addWidget(title_label)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(3)
        columns = 4 if group_name in {"File / Document", "Format", "Writer", "Art / BoC Lite"} else 3
        for index, command in enumerate(commands):
            button = self._build_button(command)
            grid.addWidget(button, index // columns, index % columns)
        layout.addLayout(grid)
        parent_layout.addWidget(group)

    def _build_button(self, command: Command, quick: bool = False) -> QToolButton:
        button = QToolButton()
        button.setObjectName("QuickBarButton" if quick else "RibbonButton")
        button.setText(command.label)
        tooltip = command.tooltip
        if command.shortcut:
            tooltip = f"{tooltip} ({command.shortcut})"
        button.setToolTip(tooltip)
        button.setCheckable(command.id in TOGGLE_COMMANDS)
        button.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        button.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonIconOnly
            if quick
            else Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        )
        button.setFixedHeight(24 if quick else 28)
        button.setMaximumWidth(40 if quick else 132)
        icon_name = self._icon_for(command.id)
        if icon_name is not None:
            button.setIcon(self.style().standardIcon(icon_name))
        button.clicked.connect(lambda _checked=False, name=command.id: self.actionTriggered.emit(name))
        self._buttons.setdefault(command.id, []).append(button)
        return button

    def _icon_for(self, command_id: str) -> QStyle.StandardPixmap | None:
        icons = {
            "new_project": QStyle.StandardPixmap.SP_FileDialogNewFolder,
            "new_document": QStyle.StandardPixmap.SP_FileIcon,
            "save": QStyle.StandardPixmap.SP_DialogSaveButton,
            "save_as": QStyle.StandardPixmap.SP_DriveFDIcon,
            "import_file": QStyle.StandardPixmap.SP_DialogOpenButton,
            "import_folder": QStyle.StandardPixmap.SP_DirOpenIcon,
            "export_pdf": QStyle.StandardPixmap.SP_FileDialogDetailedView,
            "commit": QStyle.StandardPixmap.SP_DialogApplyButton,
            "undo": QStyle.StandardPixmap.SP_ArrowBack,
            "redo": QStyle.StandardPixmap.SP_ArrowForward,
            "find": QStyle.StandardPixmap.SP_FileDialogContentsView,
            "replace": QStyle.StandardPixmap.SP_BrowserReload,
            "replace_all": QStyle.StandardPixmap.SP_BrowserReload,
            "new_concept": QStyle.StandardPixmap.SP_FileIcon,
            "save_concept": QStyle.StandardPixmap.SP_DialogSaveButton,
            "delete_concept": QStyle.StandardPixmap.SP_TrashIcon,
            "convert_concept": QStyle.StandardPixmap.SP_ArrowForward,
            "new_art": QStyle.StandardPixmap.SP_FileIcon,
            "save_art": QStyle.StandardPixmap.SP_DialogSaveButton,
            "export_art": QStyle.StandardPixmap.SP_DialogOpenButton,
            "clear_canvas": QStyle.StandardPixmap.SP_DialogResetButton,
            "brush_tool": QStyle.StandardPixmap.SP_FileDialogContentsView,
            "eraser_tool": QStyle.StandardPixmap.SP_DialogDiscardButton,
            "fill_tool": QStyle.StandardPixmap.SP_DialogApplyButton,
            "toggle_art_grid": QStyle.StandardPixmap.SP_FileDialogDetailedView,
            "apply_art_preset": QStyle.StandardPixmap.SP_DesktopIcon,
            "commit_history": QStyle.StandardPixmap.SP_FileDialogDetailedView,
            "preview_commit": QStyle.StandardPixmap.SP_FileDialogInfoView,
            "rollback_commit": QStyle.StandardPixmap.SP_BrowserReload,
            "new_branch": QStyle.StandardPixmap.SP_DirIcon,
            "save_branch": QStyle.StandardPixmap.SP_DialogSaveButton,
            "checkout_branch": QStyle.StandardPixmap.SP_DialogApplyButton,
            "delete_branch": QStyle.StandardPixmap.SP_TrashIcon,
            "template_manager": QStyle.StandardPixmap.SP_FileDialogListView,
            "custom_theme": QStyle.StandardPixmap.SP_DialogHelpButton,
            "update_dialog": QStyle.StandardPixmap.SP_BrowserReload,
            "sync_status": QStyle.StandardPixmap.SP_DriveNetIcon,
            "toggle_left": QStyle.StandardPixmap.SP_ArrowLeft,
            "toggle_right": QStyle.StandardPixmap.SP_ArrowRight,
            "focus": QStyle.StandardPixmap.SP_TitleBarMaxButton,
            "compact": QStyle.StandardPixmap.SP_TitleBarShadeButton,
            "font_increase": QStyle.StandardPixmap.SP_ArrowUp,
            "font_decrease": QStyle.StandardPixmap.SP_ArrowDown,
            "help": QStyle.StandardPixmap.SP_DialogHelpButton,
        }
        return icons.get(command_id)
