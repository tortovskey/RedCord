from __future__ import annotations

import uuid

from redcord.db.database import new_session
from redcord.db.models import Document
from redcord.db.repositories import DocumentRepository


class SearchService:
    def search_documents(self, query: str, project_id: uuid.UUID | None = None) -> list[Document]:
        if not query.strip():
            return []
        with new_session() as session:
            return DocumentRepository(session).search(project_id, query)
