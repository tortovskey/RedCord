from sqlalchemy.orm import Session

from redcord.db.repositories import DocumentRepository, VersionRepository
from redcord.utils.diff_utils import create_diff
from redcord.utils.hash_utils import sha256_text


class VersionService:
    def __init__(self, session: Session):
        self.doc_repo = DocumentRepository(session)
        self.ver_repo = VersionRepository(session)

    def create_commit(self, document_id: int, commit_message: str, mark_stable: bool = False):
        doc = self.doc_repo.get(document_id)
        if not doc:
            return None
        history = self.ver_repo.history(document_id)
        prev = history[0].content_snapshot if history else ""
        return self.ver_repo.add(
            document_id=document_id,
            version_number=self.ver_repo.next_version_number(document_id),
            commit_message=commit_message,
            content_snapshot=doc.content,
            content_hash=sha256_text(doc.content),
            diff_text=create_diff(prev, doc.content),
            is_stable=mark_stable,
        )

    def rollback_to_version(self, document_id: int, version_number: int):
        doc = self.doc_repo.get(document_id)
        if not doc:
            return None
        versions = self.ver_repo.history(document_id)
        selected = next((v for v in versions if v.version_number == version_number), None)
        if not selected:
            return None
        doc.content = selected.content_snapshot
        doc.content_hash = selected.content_hash
        return doc
