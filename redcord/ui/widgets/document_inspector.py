from __future__ import annotations

from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class DocumentInspector(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Panel")
        self.setMinimumWidth(240)
        self.setMaximumWidth(320)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        title = QLabel("Инспектор")
        title.setObjectName("TitleLabel")
        layout.addWidget(title)

        self.info_label = QLabel("Документ не выбран")
        self.info_label.setObjectName("MutedLabel")
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)

        commits_label = QLabel("Последние коммиты")
        commits_label.setObjectName("SectionLabel")
        layout.addWidget(commits_label)
        self.commit_list_side = QListWidget()
        self.commit_list_side.setObjectName("CompactList")
        layout.addWidget(self.commit_list_side, 1)

        commit_row = QHBoxLayout()
        self.commit_delete_side_btn = QPushButton("Удалить")
        self.commit_delete_side_btn.setObjectName("DangerButton")
        commit_row.addWidget(self.commit_delete_side_btn)
        commit_row.addStretch(1)
        layout.addLayout(commit_row)

        find_label = QLabel("Find / Replace")
        find_label.setObjectName("SectionLabel")
        layout.addWidget(find_label)
        self.writer_find_edit = QLineEdit()
        self.writer_find_edit.setPlaceholderText("Найти в документе")
        self.writer_replace_edit = QLineEdit()
        self.writer_replace_edit.setPlaceholderText("Заменить на")
        find_buttons = QHBoxLayout()
        self.writer_find_btn = QPushButton("Найти")
        self.writer_replace_one_btn = QPushButton("Заменить")
        self.writer_replace_all_btn = QPushButton("Все")
        for button in [self.writer_find_btn, self.writer_replace_one_btn, self.writer_replace_all_btn]:
            find_buttons.addWidget(button)
        layout.addWidget(self.writer_find_edit)
        layout.addWidget(self.writer_replace_edit)
        layout.addLayout(find_buttons)

        stats_label = QLabel("Статистика")
        stats_label.setObjectName("SectionLabel")
        layout.addWidget(stats_label)
        self.word_stats_label = QLabel("Документ не выбран")
        self.word_stats_label.setObjectName("MutedLabel")
        self.word_stats_label.setWordWrap(True)
        self.refresh_stats_btn = QPushButton("Обновить")
        layout.addWidget(self.word_stats_label)
        layout.addWidget(self.refresh_stats_btn)

        search_label = QLabel("Поиск по проекту")
        search_label.setObjectName("SectionLabel")
        layout.addWidget(search_label)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Название, текст, теги, категория")
        self.search_btn = QPushButton("Искать")
        self.search_results_list = QListWidget()
        self.search_results_list.setObjectName("CompactList")
        layout.addWidget(self.search_edit)
        layout.addWidget(self.search_btn)
        layout.addWidget(self.search_results_list, 1)

    def set_compact_mode(self, enabled: bool) -> None:
        self.setMinimumWidth(205 if enabled else 240)
        self.setMaximumWidth(260 if enabled else 320)
        margins = 5 if enabled else 8
        spacing = 4 if enabled else 6
        self.layout().setContentsMargins(margins, margins, margins, margins)
        self.layout().setSpacing(spacing)
