from __future__ import annotations

from PyQt6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QVBoxLayout

from redcord.services.template_service import TemplateService


class NewDocumentDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Новый документ")
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Название документа")
        self.type_combo = QComboBox()

        service = TemplateService()
        for template_type, name in service.list_templates():
            self.type_combo.addItem(name, template_type)

        form = QFormLayout()
        form.addRow("Название", self.title_edit)
        form.addRow("Тип", self.type_combo)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def values(self) -> tuple[str, str]:
        return self.title_edit.text().strip(), str(self.type_combo.currentData())
