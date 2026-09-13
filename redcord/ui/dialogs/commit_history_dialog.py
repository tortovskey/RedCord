from __future__ import annotations

import uuid

from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QInputDialog,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from redcord.db.models import Commit
from redcord.services.commit_service import CommitService


class CommitHistoryDialog(QDialog):
    def __init__(self, document_id: uuid.UUID, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("История коммитов")
        self.resize(940, 590)
        self.document_id = document_id
        self.commit_service = CommitService()
        self.commits: dict[str, Commit] = {}

        self.list_widget = QListWidget()
        self.snapshot_view = QTextEdit()
        self.snapshot_view.setReadOnly(True)

        self.view_btn = QPushButton("Просмотр")
        self.rollback_btn = QPushButton("Откатить")
        self.rename_btn = QPushButton("Изменить сообщение")
        self.delete_btn = QPushButton("Удалить коммит")
        self.delete_btn.setObjectName("DangerButton")
        self.delete_file_checkbox = QCheckBox("Удалять markdown-файл тоже")
        self.close_btn = QPushButton("Закрыть")

        self.view_btn.clicked.connect(self.preview_selected)
        self.rollback_btn.clicked.connect(self.rollback_selected)
        self.rename_btn.clicked.connect(self.rename_selected)
        self.delete_btn.clicked.connect(self.delete_selected)
        self.close_btn.clicked.connect(self.close)
        self.list_widget.itemDoubleClicked.connect(lambda _: self.preview_selected())

        buttons = QHBoxLayout()
        buttons.addWidget(self.view_btn)
        buttons.addWidget(self.rollback_btn)
        buttons.addWidget(self.rename_btn)
        buttons.addWidget(self.delete_btn)
        buttons.addWidget(self.delete_file_checkbox)
        buttons.addStretch(1)
        buttons.addWidget(self.close_btn)

        layout = QVBoxLayout(self)
        content = QHBoxLayout()
        content.addWidget(self.list_widget, 1)
        content.addWidget(self.snapshot_view, 2)
        layout.addLayout(content)
        layout.addLayout(buttons)
        self.reload()

    def reload(self) -> None:
        self.list_widget.clear()
        self.commits.clear()
        for commit in self.commit_service.list_commits(self.document_id):
            item = QListWidgetItem(f"{commit.created_at:%Y-%m-%d %H:%M:%S} — {commit.message}")
            item.setData(256, str(commit.id))
            self.list_widget.addItem(item)
            self.commits[str(commit.id)] = commit

    def selected_commit(self) -> Commit | None:
        item = self.list_widget.currentItem()
        if item is None:
            return None
        return self.commits.get(item.data(256))

    def preview_selected(self) -> None:
        commit = self.selected_commit()
        if commit is None:
            return
        self.snapshot_view.setPlainText(commit.content_snapshot)

    def rename_selected(self) -> None:
        commit = self.selected_commit()
        if commit is None:
            return
        message, ok = QInputDialog.getText(
            self,
            "Изменить сообщение коммита",
            "Новое сообщение:",
            text=commit.message,
        )
        if not ok:
            return
        try:
            self.commit_service.update_commit_message(commit.id, message)
            self.reload()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Ошибка изменения", str(exc))

    def delete_selected(self) -> None:
        commit = self.selected_commit()
        if commit is None:
            return
        answer = QMessageBox.question(
            self,
            "Удалить коммит",
            f"Удалить коммит из истории?\n\n{commit.message}\n\nЭто действие нельзя отменить.",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.commit_service.delete_commit(commit.id, self.delete_file_checkbox.isChecked())
            self.snapshot_view.clear()
            self.reload()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Ошибка удаления", str(exc))

    def rollback_selected(self) -> None:
        commit = self.selected_commit()
        if commit is None:
            return
        answer = QMessageBox.question(
            self,
            "Откат к коммиту",
            f"Откатить документ к коммиту:\n{commit.message}?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.commit_service.rollback_to_commit(commit.id)
            QMessageBox.information(self, "Откат", "Документ откатан. Создан rollback-коммит.")
            self.reload()
            self.accept()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Ошибка отката", str(exc))
