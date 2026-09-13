from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QSplitter, QWidget

from redcord.ui.widgets.document_editor import DocumentEditor
from redcord.ui.widgets.document_inspector import DocumentInspector
from redcord.ui.widgets.project_sidebar import ProjectSidebar


class DocumentsTab(QSplitter):
    def __init__(self, autosave_enabled: bool = True, parent: QWidget | None = None) -> None:
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.sidebar = ProjectSidebar(self)
        self.editor_panel = DocumentEditor(autosave_enabled=autosave_enabled, parent=self)
        self.inspector = DocumentInspector(self)

        self.addWidget(self.sidebar)
        self.addWidget(self.editor_panel)
        self.addWidget(self.inspector)
        self.setStretchFactor(0, 0)
        self.setStretchFactor(1, 1)
        self.setStretchFactor(2, 0)
        self.setSizes([220, 860, 260])

    def set_compact_mode(self, enabled: bool) -> None:
        self.sidebar.set_compact_mode(enabled)
        self.editor_panel.set_compact_mode(enabled)
        self.inspector.set_compact_mode(enabled)
        self.setSizes([180, 900, 220] if enabled else [220, 860, 260])

    def set_focus_mode(self, enabled: bool) -> None:
        self.sidebar.setVisible(not enabled)
        self.inspector.setVisible(not enabled)
        self.setSizes([0, 1100, 0] if enabled else [220, 860, 260])

    def toggle_left_panel(self) -> bool:
        visible = not self.sidebar.isVisible()
        self.sidebar.setVisible(visible)
        return visible

    def toggle_right_panel(self) -> bool:
        visible = not self.inspector.isVisible()
        self.inspector.setVisible(visible)
        return visible
