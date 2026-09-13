from __future__ import annotations

import uuid
from typing import TypeVar

from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session

from redcord.db.models import Commit, Concept, Document, Project, Template

T = TypeVar("T")


class ProjectRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self) -> list[Project]:
        return list(self.session.scalars(select(Project).order_by(Project.created_at.desc())))

    def get(self, project_id: uuid.UUID) -> Project | None:
        return self.session.get(Project, project_id)

    def create(self, title: str, description: str = "") -> Project:
        project = Project(title=title, description=description)
        self.session.add(project)
        self.session.commit()
        self.session.refresh(project)
        return project


class DocumentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_by_project(self, project_id: uuid.UUID) -> list[Document]:
        stmt = select(Document).where(Document.project_id == project_id).order_by(Document.updated_at.desc())
        return list(self.session.scalars(stmt))

    def get(self, document_id: uuid.UUID) -> Document | None:
        return self.session.get(Document, document_id)

    def create(
        self,
        project_id: uuid.UUID,
        title: str,
        doc_type: str,
        content: str,
        tags: str = "",
        category: str = "",
    ) -> Document:
        document = Document(
            project_id=project_id,
            title=title,
            type=doc_type,
            content=content,
            tags=tags,
            category=category,
        )
        self.session.add(document)
        self.session.commit()
        self.session.refresh(document)
        return document

    def save(self, document: Document) -> Document:
        self.session.add(document)
        self.session.commit()
        self.session.refresh(document)
        return document

    def search(self, project_id: uuid.UUID | None, query: str) -> list[Document]:
        pattern = f"%{query.strip()}%"
        stmt: Select[tuple[Document]] = select(Document).where(
            or_(
                Document.title.ilike(pattern),
                Document.content.ilike(pattern),
                Document.tags.ilike(pattern),
                Document.category.ilike(pattern),
            )
        )
        if project_id is not None:
            stmt = stmt.where(Document.project_id == project_id)
        stmt = stmt.order_by(Document.updated_at.desc()).limit(50)
        return list(self.session.scalars(stmt))


class TemplateRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self) -> list[Template]:
        return list(self.session.scalars(select(Template).order_by(Template.name.asc())))

    def get_by_type(self, template_type: str) -> Template | None:
        return self.session.scalar(select(Template).where(Template.type == template_type))

    def upsert(self, name: str, template_type: str, content: str) -> Template:
        template = self.get_by_type(template_type)
        if template is None:
            template = Template(name=name, type=template_type, content=content)
            self.session.add(template)
        else:
            template.name = name
            template.content = content
        self.session.commit()
        self.session.refresh(template)
        return template


class CommitRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_by_document(self, document_id: uuid.UUID) -> list[Commit]:
        stmt = select(Commit).where(Commit.document_id == document_id).order_by(Commit.created_at.desc())
        return list(self.session.scalars(stmt))

    def get(self, commit_id: uuid.UUID) -> Commit | None:
        return self.session.get(Commit, commit_id)

    def create(
        self, document_id: uuid.UUID, message: str, content_snapshot: str, commit_file_path: str
    ) -> Commit:
        commit = Commit(
            document_id=document_id,
            message=message,
            content_snapshot=content_snapshot,
            commit_file_path=commit_file_path,
        )
        self.session.add(commit)
        self.session.commit()
        self.session.refresh(commit)
        return commit

    def update_message(self, commit: Commit, message: str) -> Commit:
        commit.message = message.strip() or "Без сообщения"
        self.session.add(commit)
        self.session.commit()
        self.session.refresh(commit)
        return commit

    def delete(self, commit: Commit) -> None:
        self.session.delete(commit)
        self.session.commit()


class ConceptRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_by_project(self, project_id: uuid.UUID) -> list[Concept]:
        stmt = select(Concept).where(Concept.project_id == project_id).order_by(Concept.updated_at.desc())
        return list(self.session.scalars(stmt))

    def get(self, concept_id: uuid.UUID) -> Concept | None:
        return self.session.get(Concept, concept_id)

    def create(self, project_id: uuid.UUID, title: str, content: str = "", status: str = "Идея") -> Concept:
        concept = Concept(project_id=project_id, title=title, content=content, status=status)
        self.session.add(concept)
        self.session.commit()
        self.session.refresh(concept)
        return concept

    def save(self, concept: Concept) -> Concept:
        self.session.add(concept)
        self.session.commit()
        self.session.refresh(concept)
        return concept

    def delete(self, concept: Concept) -> None:
        self.session.delete(concept)
        self.session.commit()
