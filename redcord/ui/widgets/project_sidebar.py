from __future__ import annotations

from PyQt6.QtWidgets import QLabel, QListWidget, QPushButton, QStyle, QVBoxLayout, QWidget, QFrame


class ProjectSidebar(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Panel")
        self.setMinimumWidth(210)
        self.setMaximumWidth(280)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self.profile_label = QLabel("RedCord")
        self.profile_label.setObjectName("TitleLabel")
        layout.addWidget(self.profile_label)

        projects_label = QLabel("Проекты")
        projects_label.setObjectName("SectionLabel")
        layout.addWidget(projects_label)

        self.project_list = QListWidget()
        self.project_list.setObjectName("CompactList")
        layout.addWidget(self.project_list, 1)

        self.new_project_btn = QPushButton("Новый проект")
        self.new_project_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder))
        layout.addWidget(self.new_project_btn)

        documents_label = QLabel("Документы")
        documents_label.setObjectName("SectionLabel")
        layout.addWidget(documents_label)

        self.document_list = QListWidget()
        self.document_list.setObjectName("CompactList")
        layout.addWidget(self.document_list, 2)

        self.new_document_btn = QPushButton("Новый документ")
        self.import_btn = QPushButton("Импорт файла")
        self.import_folder_btn = QPushButton("Импорт папки")
        self.types_btn = QPushButton("Шаблоны / типы")
        self.new_document_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))
        self.import_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton))
        self.import_folder_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon))
        self.types_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogInfoView))

        for button in [self.new_document_btn, self.import_btn, self.import_folder_btn, self.types_btn]:
            layout.addWidget(button)

    def set_compact_mode(self, enabled: bool) -> None:
        self.setMinimumWidth(176 if enabled else 210)
        self.setMaximumWidth(218 if enabled else 280)
        margins = 5 if enabled else 8
        spacing = 4 if enabled else 6
        self.layout().setContentsMargins(margins, margins, margins, margins)
        self.layout().setSpacing(spacing)
