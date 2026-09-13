from __future__ import annotations

from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from redcord.ai.ai_settings_service import AISettingsService
from redcord.ai.base import AISettings


class AISettingsDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Настройки ИИ-агента")
        self.service = AISettingsService()

        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["mock", "openai_compatible"])
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.base_url_edit = QLineEdit()
        self.model_edit = QLineEdit()
        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setRange(0, 2)
        self.temperature_spin.setSingleStep(0.1)
        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(128, 64000)

        form = QFormLayout()
        form.addRow("Provider", self.provider_combo)
        form.addRow("API Key", self.api_key_edit)
        form.addRow("Base URL", self.base_url_edit)
        form.addRow("Model", self.model_edit)
        form.addRow("Temperature", self.temperature_spin)
        form.addRow("Max tokens", self.max_tokens_spin)

        self.save_btn = QPushButton("Сохранить")
        self.cancel_btn = QPushButton("Отмена")
        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(self.save_btn)
        buttons.addWidget(self.cancel_btn)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(buttons)
        self.load()

    def load(self) -> None:
        value = self.service.load()
        self.provider_combo.setCurrentText(value.provider)
        self.api_key_edit.setText(value.api_key)
        self.base_url_edit.setText(value.base_url)
        self.model_edit.setText(value.model)
        self.temperature_spin.setValue(value.temperature)
        self.max_tokens_spin.setValue(value.max_tokens)

    def values(self) -> AISettings:
        return AISettings(
            provider=self.provider_combo.currentText(),
            api_key=self.api_key_edit.text(),
            base_url=self.base_url_edit.text(),
            model=self.model_edit.text(),
            temperature=self.temperature_spin.value(),
            max_tokens=self.max_tokens_spin.value(),
        )

    def accept(self) -> None:
        self.service.save(self.values())
        super().accept()
