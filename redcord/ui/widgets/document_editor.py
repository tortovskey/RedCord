from __future__ import annotations

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStyle,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class DocumentEditor(QFrame):
    def __init__(self, autosave_enabled: bool = True, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Panel")
        self._font_size = 12

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        header = QGridLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setHorizontalSpacing(6)
        header.setVerticalSpacing(4)

        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Название документа")
        self.type_combo = QComboBox()
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("Теги")
        self.category_edit = QLineEdit()
        self.category_edit.setPlaceholderText("Категория")

        header.addWidget(QLabel("Название"), 0, 0)
        header.addWidget(self.title_edit, 0, 1, 1, 3)
        header.addWidget(QLabel("Тип"), 0, 4)
        header.addWidget(self.type_combo, 0, 5)
        header.addWidget(QLabel("Теги"), 1, 0)
        header.addWidget(self.tags_edit, 1, 1, 1, 2)
        header.addWidget(QLabel("Категория"), 1, 3)
        header.addWidget(self.category_edit, 1, 4, 1, 2)
        header.setColumnStretch(1, 2)
        header.setColumnStretch(2, 1)
        layout.addLayout(header)

        self.editor = QTextEdit()
        self.editor.setObjectName("MainDocumentEditor")
        self.editor.setAcceptRichText(True)
        self.editor.setPlaceholderText("Пиши сцену, лор, персонажа или заметку. Форматирование видно сразу.")
        self._apply_editor_font()
        layout.addWidget(self.editor, 1)

        footer = QHBoxLayout()
        footer.setContentsMargins(0, 0, 0, 0)
        footer.setSpacing(5)
        self.save_btn = QPushButton("Сохранить")
        self.save_btn.setObjectName("AccentButton")
        self.save_as_btn = QPushButton("Сохранить как")
        self.autosave_btn = QPushButton("Автосохранение: включено" if autosave_enabled else "Автосохранение: выключено")
        self.commit_btn = QPushButton("Коммит")
        self.history_btn = QPushButton("История")
        self.save_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
        self.save_as_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DriveFDIcon))
        self.autosave_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.commit_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton))
        self.history_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView))
        for button in [self.save_btn, self.save_as_btn, self.autosave_btn, self.commit_btn, self.history_btn]:
            footer.addWidget(button)
        footer.addStretch(1)
        self.save_feedback_label = QLabel("Сохранено")
        self.save_feedback_label.setObjectName("SuccessLabel")
        self.save_feedback_label.hide()
        footer.addWidget(self.save_feedback_label)
        layout.addLayout(footer)

    def set_compact_mode(self, enabled: bool) -> None:
        margins = 5 if enabled else 8
        spacing = 4 if enabled else 6
        self.layout().setContentsMargins(margins, margins, margins, margins)
        self.layout().setSpacing(spacing)
        for button in [self.save_btn, self.save_as_btn, self.autosave_btn, self.commit_btn, self.history_btn]:
            button.setFixedHeight(24 if enabled else 28)

    def increase_font(self) -> None:
        self._font_size = min(22, self._font_size + 1)
        self._apply_editor_font()

    def decrease_font(self) -> None:
        self._font_size = max(9, self._font_size - 1)
        self._apply_editor_font()

    def _apply_editor_font(self) -> None:
        font = QFont("Segoe UI", self._font_size)
        font.setStyleHint(QFont.StyleHint.SansSerif)
        self.editor.setFont(font)
