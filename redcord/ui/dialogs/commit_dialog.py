from __future__ import annotations

from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QLineEdit, QVBoxLayout


class CommitDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Создать коммит")
        self.message_edit = QLineEdit()
        self.message_edit.setPlaceholderText("Что изменилось?")

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Сообщение коммита:"))
        layout.addWidget(self.message_edit)
        layout.addWidget(buttons)

    def message(self) -> str:
        return self.message_edit.text().strip() or "Без сообщения"
