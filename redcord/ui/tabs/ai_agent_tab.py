from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from redcord.ai.ai_settings_service import AISettingsService
from redcord.ai.base import AIProviderError, AISettings
from redcord.ai.prompts import PROMPTS
from redcord.ai.provider_factory import create_provider


class AIAgentTab(QWidget):
    def __init__(
        self,
        get_document_text: Callable[[], str],
        insert_result: Callable[[str], None],
        replace_document: Callable[[str], None],
        replace_selection: Callable[[str], None],
        create_document_from_result: Callable[[str, str], None],
        set_status: Callable[[str], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.get_document_text = get_document_text
        self.insert_result = insert_result
        self.replace_document = replace_document
        self.replace_selection = replace_selection
        self.create_document_from_result = create_document_from_result
        self.set_status = set_status
        self.settings_service = AISettingsService()
        self._api_key_visible = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self._build_settings_panel())
        splitter.addWidget(self._build_workspace_panel())
        splitter.addWidget(self._build_result_panel())
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 1)
        splitter.setSizes([320, 500, 500])
        layout.addWidget(splitter, 1)
        self.load_settings()

    def _build_settings_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("Panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        title = QLabel("ИИ-агент")
        title.setObjectName("TitleLabel")
        layout.addWidget(title)

        settings_box = QGroupBox("Провайдер")
        settings_layout = QGridLayout(settings_box)
        settings_layout.setContentsMargins(8, 8, 8, 8)
        settings_layout.setHorizontalSpacing(6)
        settings_layout.setVerticalSpacing(5)

        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["mock", "openai_compatible"])
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_edit.setPlaceholderText("API key")
        self.show_key_btn = QPushButton("Показать")
        self.save_key_btn = QPushButton("Сохранить ключ")
        self.base_url_edit = QLineEdit()
        self.base_url_edit.setPlaceholderText("https://api.openai.com/v1")
        self.model_edit = QLineEdit()
        self.model_edit.setPlaceholderText("gpt-4o-mini / local-model / mistral")
        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setRange(0.0, 2.0)
        self.temperature_spin.setSingleStep(0.1)
        self.temperature_spin.setDecimals(2)
        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(128, 64000)
        self.max_tokens_spin.setSingleStep(100)
        self.test_btn = QPushButton("Test connection")
        self.save_settings_btn = QPushButton("Сохранить настройки")

        settings_layout.addWidget(QLabel("Provider"), 0, 0)
        settings_layout.addWidget(self.provider_combo, 0, 1, 1, 2)
        settings_layout.addWidget(QLabel("API Key"), 1, 0)
        settings_layout.addWidget(self.api_key_edit, 1, 1)
        settings_layout.addWidget(self.show_key_btn, 1, 2)
        settings_layout.addWidget(self.save_key_btn, 2, 1, 1, 2)
        settings_layout.addWidget(QLabel("Base URL"), 3, 0)
        settings_layout.addWidget(self.base_url_edit, 3, 1, 1, 2)
        settings_layout.addWidget(QLabel("Model"), 4, 0)
        settings_layout.addWidget(self.model_edit, 4, 1, 1, 2)
        settings_layout.addWidget(QLabel("Temperature"), 5, 0)
        settings_layout.addWidget(self.temperature_spin, 5, 1, 1, 2)
        settings_layout.addWidget(QLabel("Max tokens"), 6, 0)
        settings_layout.addWidget(self.max_tokens_spin, 6, 1, 1, 2)
        settings_layout.addWidget(self.test_btn, 7, 1)
        settings_layout.addWidget(self.save_settings_btn, 7, 2)
        layout.addWidget(settings_box)

        self.show_key_btn.clicked.connect(self.toggle_api_key_visibility)
        self.save_key_btn.clicked.connect(self.save_settings)
        self.save_settings_btn.clicked.connect(self.save_settings)
        self.test_btn.clicked.connect(self.test_connection)

        actions_box = QGroupBox("Действия")
        actions_layout = QGridLayout(actions_box)
        actions_layout.setContentsMargins(8, 8, 8, 8)
        actions_layout.setSpacing(5)
        action_labels = [
            ("improve_text", "Улучшить текст"),
            ("fix_style", "Исправить стиль"),
            ("vivid", "Сделать живее"),
            ("shorten", "Сократить"),
            ("expand", "Расширить"),
            ("summarize", "Краткое содержание"),
            ("contradictions", "Противоречия"),
            ("scene_development", "Развитие сцены"),
            ("chapter_title", "Название главы"),
            ("character_questions", "Вопросы персонажу"),
            ("rewrite_tone", "Другой тон"),
            ("check_dialogues", "Проверить диалоги"),
            ("chapter_plan", "План главы"),
            ("beat_sheet", "Beat-sheet"),
            ("character_card", "Карточка персонажа"),
        ]
        for index, (action, label) in enumerate(action_labels):
            button = QPushButton(label)
            button.clicked.connect(lambda _checked=False, key=action: self.run_action(key))
            actions_layout.addWidget(button, index // 2, index % 2)
        layout.addWidget(actions_box, 1)
        return panel

    def _build_workspace_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("Panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        title = QLabel("Исходный текст")
        title.setObjectName("TitleLabel")
        layout.addWidget(title)
        self.source_edit = QTextEdit()
        self.source_edit.setPlaceholderText("Нажми «Взять из документа» или вставь текст сюда.")
        layout.addWidget(self.source_edit, 1)
        row = QHBoxLayout()
        self.take_btn = QPushButton("Взять из документа")
        self.clear_source_btn = QPushButton("Очистить")
        self.take_btn.clicked.connect(self.take_from_document)
        self.clear_source_btn.clicked.connect(self.source_edit.clear)
        row.addWidget(self.take_btn)
        row.addWidget(self.clear_source_btn)
        row.addStretch(1)
        layout.addLayout(row)
        return panel

    def _build_result_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("Panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        title = QLabel("Результат")
        title.setObjectName("TitleLabel")
        layout.addWidget(title)
        self.result_edit = QTextEdit()
        self.result_edit.setPlaceholderText("Здесь появится результат ИИ-агента.")
        layout.addWidget(self.result_edit, 1)
        row = QHBoxLayout()
        self.insert_btn = QPushButton("Вставить")
        self.replace_selection_btn = QPushButton("Заменить выделение")
        self.replace_document_btn = QPushButton("Заменить документ")
        self.new_doc_btn = QPushButton("В новый документ")
        self.insert_btn.clicked.connect(self.apply_insert)
        self.replace_selection_btn.clicked.connect(self.apply_replace_selection)
        self.replace_document_btn.clicked.connect(self.apply_replace_document)
        self.new_doc_btn.clicked.connect(self.apply_new_document)
        for button in [self.insert_btn, self.replace_selection_btn, self.replace_document_btn, self.new_doc_btn]:
            row.addWidget(button)
        layout.addLayout(row)
        return panel

    def load_settings(self) -> None:
        settings = self.settings_service.load()
        self.provider_combo.setCurrentText(settings.provider)
        self.api_key_edit.setText(settings.api_key)
        self.base_url_edit.setText(settings.base_url)
        self.model_edit.setText(settings.model)
        self.temperature_spin.setValue(settings.temperature)
        self.max_tokens_spin.setValue(settings.max_tokens)

    def current_settings(self) -> AISettings:
        return AISettings(
            provider=self.provider_combo.currentText(),
            api_key=self.api_key_edit.text(),
            base_url=self.base_url_edit.text(),
            model=self.model_edit.text(),
            temperature=float(self.temperature_spin.value()),
            max_tokens=int(self.max_tokens_spin.value()),
        )

    def save_settings(self) -> None:
        self.settings_service.save(self.current_settings())
        self.set_status("ИИ-настройки сохранены в data/ai_settings.json")

    def toggle_api_key_visibility(self) -> None:
        self._api_key_visible = not self._api_key_visible
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Normal if self._api_key_visible else QLineEdit.EchoMode.Password)
        self.show_key_btn.setText("Скрыть" if self._api_key_visible else "Показать")

    def test_connection(self) -> None:
        settings = self.current_settings()
        self.settings_service.save(settings)
        provider = create_provider(settings)
        try:
            message = provider.test_connection(settings)
            QMessageBox.information(self, "ИИ-агент", message)
            self.set_status("ИИ-агент: подключение проверено")
        except AIProviderError as exc:
            QMessageBox.warning(self, "ИИ-агент", str(exc))
            self.set_status("ИИ-агент: ошибка подключения")

    def take_from_document(self) -> None:
        self.source_edit.setPlainText(self.get_document_text())
        self.set_status("ИИ-агент взял текст из текущего документа")

    def run_action(self, action: str) -> None:
        text = self.source_edit.toPlainText().strip() or self.get_document_text().strip()
        if not text:
            QMessageBox.information(self, "ИИ-агент", "Нет текста для обработки.")
            return
        settings = self.current_settings()
        self.settings_service.save(settings)
        provider = create_provider(settings)
        prompt = PROMPTS.get(action)
        try:
            response = provider.generate(action, text, settings)
        except AIProviderError as exc:
            QMessageBox.warning(self, "ИИ-агент", str(exc))
            self.set_status("ИИ-агент: ошибка генерации")
            return
        title = response.title if prompt is None else prompt.title
        self.result_edit.setPlainText(f"# {title}\n\n{response.text}")
        self.set_status(f"ИИ-агент: {title}")

    def _result_text(self) -> str | None:
        result = self.result_edit.toPlainText()
        if not result.strip():
            QMessageBox.information(self, "ИИ-агент", "Нет результата для применения.")
            return None
        return result

    def apply_insert(self) -> None:
        result = self._result_text()
        if result is not None:
            self.insert_result(result)

    def apply_replace_selection(self) -> None:
        result = self._result_text()
        if result is not None:
            self.replace_selection(result)

    def apply_replace_document(self) -> None:
        result = self._result_text()
        if result is not None:
            self.replace_document(result)

    def apply_new_document(self) -> None:
        result = self._result_text()
        if result is not None:
            self.create_document_from_result("ИИ-результат", result)
