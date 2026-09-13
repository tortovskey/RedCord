from __future__ import annotations

import re

from PyQt6.QtWidgets import (
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
    QLineEdit,
)

from redcord.services.template_service import TemplateService


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-zа-я0-9_ -]+", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\s+", "_", value)
    return value or "custom_type"


class TemplateManagerDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Типы документов")
        self.resize(900, 600)
        self.service = TemplateService()
        self.templates: dict[str, str] = {}

        self.list_widget = QListWidget()
        self.name_edit = QLineEdit()
        self.type_edit = QLineEdit()
        self.editor = QTextEdit()

        self.new_btn = QPushButton("Новый тип")
        self.save_btn = QPushButton("Сохранить тип")
        self.delete_btn = QPushButton("Удалить тип")
        self.close_btn = QPushButton("Закрыть")

        self.delete_btn.setObjectName("DangerButton")

        self.list_widget.currentItemChanged.connect(self.load_selected)
        self.new_btn.clicked.connect(self.new_type)
        self.save_btn.clicked.connect(self.save_type)
        self.delete_btn.clicked.connect(self.delete_type)
        self.close_btn.clicked.connect(self.close)

        left = QVBoxLayout()
        left.addWidget(self.list_widget)
        left.addWidget(self.new_btn)
        left.addWidget(self.delete_btn)

        form = QFormLayout()
        form.addRow("Название", self.name_edit)
        form.addRow("Ключ типа", self.type_edit)

        right_buttons = QHBoxLayout()
        right_buttons.addWidget(self.save_btn)
        right_buttons.addStretch(1)
        right_buttons.addWidget(self.close_btn)

        right = QVBoxLayout()
        right.addLayout(form)
        right.addWidget(self.editor, 1)
        right.addLayout(right_buttons)

        layout = QHBoxLayout(self)
        layout.addLayout(left, 1)
        layout.addLayout(right, 2)
        self.reload()

    def reload(self) -> None:
        current = self.type_edit.text().strip()
        self.list_widget.clear()
        self.templates.clear()
        for template_type, name in self.service.list_templates():
            item = QListWidgetItem(f"{name} · {template_type}")
            item.setData(256, template_type)
            self.list_widget.addItem(item)
            self.templates[template_type] = name
            if current and current == template_type:
                self.list_widget.setCurrentItem(item)

    def load_selected(self) -> None:
        item = self.list_widget.currentItem()
        if item is None:
            return
        template_type = str(item.data(256))
        self.type_edit.setText(template_type)
        self.name_edit.setText(self.templates.get(template_type, template_type))
        self.editor.setPlainText(self.service.get_template_content(template_type))

    def new_type(self) -> None:
        name, ok = QInputDialog.getText(self, "Новый тип", "Название типа:")
        if not ok or not name.strip():
            return
        template_type = slugify(name)
        self.name_edit.setText(name.strip())
        self.type_edit.setText(template_type)
        self.editor.setPlainText(f"# {name.strip()}\n\n## Описание\n...\n\n## Заметки автора\n...\n")

    def save_type(self) -> None:
        name = self.name_edit.text().strip()
        template_type = slugify(self.type_edit.text())
        content = self.editor.toPlainText()
        if not name:
            QMessageBox.information(self, "Тип", "Введи название типа.")
            return
        self.service.create_or_update_template(template_type, name, content)
        self.type_edit.setText(template_type)
        self.reload()
        QMessageBox.information(self, "Тип", "Тип документа сохранён.")

    def delete_type(self) -> None:
        template_type = self.type_edit.text().strip()
        if not template_type:
            return
        if QMessageBox.question(self, "Удалить тип", f"Удалить тип {template_type}?") != QMessageBox.StandardButton.Yes:
            return
        try:
            self.service.delete_template(template_type)
            self.name_edit.clear()
            self.type_edit.clear()
            self.editor.clear()
            self.reload()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Ошибка удаления", str(exc))
