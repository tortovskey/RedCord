from sqlalchemy import func, select
from sqlalchemy.orm import Session

from redcord.db import models


class ProjectRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, name: str, description: str = "") -> models.Project:
        project = models.Project(name=name, description=description)
        self.session.add(project)
        self.session.flush()
        return project

    def list_all(self) -> list[models.Project]:
        return list(self.session.scalars(select(models.Project).order_by(models.Project.created_at.desc())))


class DocumentRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, **kwargs) -> models.Document:
        doc = models.Document(**kwargs)
        self.session.add(doc)
        self.session.flush()
        return doc

    def get(self, document_id: int) -> models.Document | None:
        return self.session.get(models.Document, document_id)

    def by_project(self, project_id: int) -> list[models.Document]:
        stmt = select(models.Document).where(models.Document.project_id == project_id, models.Document.deleted_at.is_(None))
        return list(self.session.scalars(stmt))


class VersionRepository:
    def __init__(self, session: Session):
        self.session = session

    def next_version_number(self, document_id: int) -> int:
        stmt = select(func.max(models.DocumentVersion.version_number)).where(models.DocumentVersion.document_id == document_id)
        current = self.session.scalar(stmt) or 0
        return int(current) + 1

    def add(self, **kwargs) -> models.DocumentVersion:
        version = models.DocumentVersion(**kwargs)
        self.session.add(version)
        self.session.flush()
        return version

    def history(self, document_id: int) -> list[models.DocumentVersion]:
        stmt = select(models.DocumentVersion).where(models.DocumentVersion.document_id == document_id).order_by(models.DocumentVersion.version_number.desc())
        return list(self.session.scalars(stmt))
