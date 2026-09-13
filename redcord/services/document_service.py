from __future__ import annotations

import uuid

from redcord.db.database import new_session
from redcord.db.models import Document, Project
from redcord.db.repositories import DocumentRepository, ProjectRepository
from redcord.services.template_service import TemplateService


class DocumentService:
    def list_projects(self) -> list[Project]:
        with new_session() as session:
            return ProjectRepository(session).list()

    def create_project(self, title: str, description: str = "") -> Project:
        with new_session() as session:
            return ProjectRepository(session).create(title=title.strip(), description=description.strip())

    def list_documents(self, project_id: uuid.UUID) -> list[Document]:
        with new_session() as session:
            return DocumentRepository(session).list_by_project(project_id)

    def get_document(self, document_id: uuid.UUID) -> Document | None:
        with new_session() as session:
            return DocumentRepository(session).get(document_id)

    def create_document(
        self,
        project_id: uuid.UUID,
        title: str,
        doc_type: str,
        content: str | None = None,
        tags: str = "",
        category: str = "",
    ) -> Document:
        if content is None:
            content = TemplateService().get_template_content(doc_type)
        with new_session() as session:
            return DocumentRepository(session).create(
                project_id=project_id,
                title=title.strip() or "Без названия",
                doc_type=doc_type,
                content=content,
                tags=tags,
                category=category,
            )

    def save_document(
        self, document_id: uuid.UUID, title: str, doc_type: str, content: str, tags: str, category: str
    ) -> Document:
        with new_session() as session:
            repo = DocumentRepository(session)
            document = repo.get(document_id)
            if document is None:
                raise ValueError("Документ не найден")
            document.title = title.strip() or "Без названия"
            document.type = doc_type.strip() or "note"
            document.content = content
            document.tags = tags.strip()
            document.category = category.strip()
            return repo.save(document)
