from __future__ import annotations

import uuid

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from redcord.db.models import Concept
from redcord.services.concept_service import ConceptService

STATUSES = ["Идея", "В разработке", "Использовано", "Архив"]


class ConceptDialog(QDialog):
    def __init__(self, project_id: uuid.UUID, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Концепты")
        self.resize(950, 620)
        self.project_id = project_id
        self.service = ConceptService()
        self.concepts: dict[str, Concept] = {}
        self.current_id: uuid.UUID | None = None

        self.list_widget = QListWidget()
        self.title_btn = QPushButton("Переименовать")
        self.status_combo = QComboBox()
        self.status_combo.addItems(STATUSES)
        self.editor = QTextEdit()

        self.new_btn = QPushButton("Новый концепт")
        self.save_btn = QPushButton("Сохранить")
        self.delete_btn = QPushButton("Удалить")
        self.convert_btn = QPushButton("В документ")
        self.close_btn = QPushButton("Закрыть")

        form = QFormLayout()
        form.addRow("Статус", self.status_combo)

        left_buttons = QVBoxLayout()
        left_buttons.addWidget(self.new_btn)
        left_buttons.addWidget(self.delete_btn)
        left_buttons.addWidget(self.convert_btn)

        left = QVBoxLayout()
        left.addWidget(self.list_widget)
        left.addLayout(left_buttons)

        right_buttons = QHBoxLayout()
        right_buttons.addWidget(self.title_btn)
        right_buttons.addWidget(self.save_btn)
        right_buttons.addStretch(1)
        right_buttons.addWidget(self.close_btn)

        content = QHBoxLayout()
        content.addLayout(left, 1)
        right = QVBoxLayout()
        right.addLayout(form)
        right.addWidget(self.editor, 1)
        right.addLayout(right_buttons)
        content.addLayout(right, 2)
        self.setLayout(content)

        self.list_widget.currentItemChanged.connect(self.load_selected)
        self.new_btn.clicked.connect(self.create_concept)
        self.save_btn.clicked.connect(self.save_current)
        self.delete_btn.clicked.connect(self.delete_current)
        self.convert_btn.clicked.connect(self.convert_current)
        self.title_btn.clicked.connect(self.rename_current)
        self.close_btn.clicked.connect(self.close)
        self.reload()

    def reload(self) -> None:
        self.list_widget.clear()
        self.concepts.clear()
        for concept in self.service.list_concepts(self.project_id):
            item = QListWidgetItem(f"[{concept.status}] {concept.title}")
            item.setData(256, str(concept.id))
            self.list_widget.addItem(item)
            self.concepts[str(concept.id)] = concept

    def load_selected(self) -> None:
        item = self.list_widget.currentItem()
        if item is None:
            self.current_id = None
            self.editor.clear()
            return
        concept = self.concepts.get(item.data(256))
        if concept is None:
            return
        self.current_id = concept.id
        self.editor.setPlainText(concept.content)
        self.status_combo.setCurrentText(concept.status)

    def create_concept(self) -> None:
        title, ok = QInputDialog.getText(self, "Новый концепт", "Название:")
        if not ok or not title.strip():
            return
        self.service.create_concept(self.project_id, title.strip(), "# " + title.strip() + "\n\n", "Идея")
        self.reload()

    def save_current(self) -> None:
        if self.current_id is None:
            return
        concept = self.concepts.get(str(self.current_id))
        if concept is None:
            return
        self.service.save_concept(
            self.current_id,
            concept.title,
            self.editor.toPlainText(),
            self.status_combo.currentText(),
        )
        self.reload()

    def rename_current(self) -> None:
        if self.current_id is None:
            return
        concept = self.concepts.get(str(self.current_id))
        if concept is None:
            return
        title, ok = QInputDialog.getText(self, "Переименовать", "Название:", text=concept.title)
        if not ok or not title.strip():
            return
        self.service.save_concept(
            self.current_id,
            title.strip(),
            self.editor.toPlainText(),
            self.status_combo.currentText(),
        )
        self.reload()

    def delete_current(self) -> None:
        if self.current_id is None:
            return
        if QMessageBox.question(self, "Удалить", "Удалить концепт?") != QMessageBox.StandardButton.Yes:
            return
        self.service.delete_concept(self.current_id)
        self.current_id = None
        self.reload()
        self.editor.clear()

    def convert_current(self) -> None:
        if self.current_id is None:
            return
        document = self.service.convert_to_document(self.current_id)
        QMessageBox.information(self, "Готово", f"Концепт преобразован в документ: {document.title}")
        self.reload()
