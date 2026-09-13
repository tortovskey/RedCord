from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from redcord.services.update_service import UpdateErrorForUser, UpdateResult, UpdateService


class UpdateDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Обновление RedCord")
        self.resize(780, 460)
        self.service = UpdateService()
        self.archive_path: Path | None = None
        self.last_result: UpdateResult | None = None

        self.info = QTextEdit()
        self.info.setReadOnly(True)
        self.info.setPlainText(
            "Выберите ZIP-архив новой версии RedCord.\n\n"
            "0.8 обновлятор умеет два режима и поддерживает manifest-based ZIP:\n\n"
            "1. Source-режим: файлы копируются сразу в папку проекта.\n"
            "2. EXE-режим: обновление подготавливается в data/pending_update/, "
            "создаётся apply_update.bat, который применит обновление после закрытия RedCord.exe.\n\n"
            "Всегда сохраняются: data/, commits/, .env, redcord.db, redcord_08.db, settings.json, "
            "accounts.json, branches.json и redcord.log.\n\n"
            "Перед обновлением создаётся резервная копия в data/update_backups/."
        )

        self.path_label = QLabel("Архив не выбран")
        self.result_label = QLabel("")
        self.result_label.setWordWrap(True)
        self.result_label.setObjectName("MutedLabel")

        self.choose_btn = QPushButton("Выбрать архив")
        self.update_btn = QPushButton("Подготовить / установить")
        self.launch_btn = QPushButton("Запустить применитель")
        self.close_btn = QPushButton("Закрыть")

        self.launch_btn.setEnabled(False)

        self.choose_btn.clicked.connect(self.choose_archive)
        self.update_btn.clicked.connect(self.apply_update)
        self.launch_btn.clicked.connect(self.launch_applicator)
        self.close_btn.clicked.connect(self.close)

        buttons = QHBoxLayout()
        buttons.addWidget(self.choose_btn)
        buttons.addWidget(self.update_btn)
        buttons.addWidget(self.launch_btn)
        buttons.addStretch(1)
        buttons.addWidget(self.close_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(self.info)
        layout.addWidget(self.path_label)
        layout.addWidget(self.result_label)
        layout.addLayout(buttons)

    def choose_archive(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Архив обновления",
            str(Path.home()),
            "ZIP archives (*.zip)",
        )
        if path:
            self.archive_path = Path(path)
            self.path_label.setText(str(self.archive_path))
            self.result_label.clear()
            self.last_result = None
            self.launch_btn.setEnabled(False)

    def apply_update(self) -> None:
        if self.archive_path is None:
            QMessageBox.information(self, "Обновление", "Сначала выберите ZIP-архив.")
            return

        answer = QMessageBox.question(
            self,
            "Установить обновление",
            "Подготовить или установить обновление из выбранного архива?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            result = self.service.apply_update_from_archive(self.archive_path)
            self.last_result = result
            self.result_label.setText(
                f"Текущая версия: {result.current_version}\n"
                f"Новая версия: {result.detected_version}\n\n"
                f"{result.message}"
            )

            if result.mode == "staged" and result.apply_script is not None:
                self.launch_btn.setEnabled(True)
                QMessageBox.information(
                    self,
                    "Обновление подготовлено",
                    result.message + f"\n\nБэкап: {result.backup_dir}",
                )
            else:
                QMessageBox.information(
                    self,
                    "Обновление установлено",
                    result.message + f"\n\nБэкап: {result.backup_dir}",
                )
                self.accept()

        except UpdateErrorForUser as exc:
            QMessageBox.warning(self, "Обновление невозможно", str(exc))
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Ошибка обновления", str(exc))

    def launch_applicator(self) -> None:
        if self.last_result is None or self.last_result.apply_script is None:
            QMessageBox.information(self, "Обновление", "Сначала подготовьте обновление.")
            return

        answer = QMessageBox.question(
            self,
            "Запустить применитель",
            "RedCord сейчас закроется. apply_update.bat дождётся закрытия приложения, "
            "скопирует новые файлы и попробует снова запустить RedCord.\n\nПродолжить?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        try:
            self.service.launch_apply_script(self.last_result.apply_script)
            QApplication.quit()
        except UpdateErrorForUser as exc:
            QMessageBox.warning(self, "Обновление невозможно", str(exc))
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Ошибка запуска применителя", str(exc))
