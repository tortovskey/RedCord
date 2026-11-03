from sqlalchemy.orm import Session

from redcord.db.repositories import DocumentRepository
from redcord.utils.hash_utils import sha256_text


class DocumentService:
    def __init__(self, session: Session):
        self.repo = DocumentRepository(session)

    def create_document(self, project_id: int, title: str, document_type: str, content: str = "", tags: str = ""):
        return self.repo.create(
            project_id=project_id,
            title=title,
            document_type=document_type,
            content=content,
            content_hash=sha256_text(content),
            tags=tags,
            status="active",
        )

    def update_content(self, document_id: int, content: str):
        doc = self.repo.get(document_id)
        if not doc:
            return None
        doc.content = content
        doc.content_hash = sha256_text(content)
        return doc
