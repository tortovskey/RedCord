from sqlalchemy.orm import Session

from redcord.db.models import Document, RecoveryEvent
from redcord.utils.hash_utils import sha256_text


class IntegrityService:
    def __init__(self, session: Session):
        self.session = session

    def check_document(self, document_id: int) -> bool:
        doc = self.session.get(Document, document_id)
        if not doc:
            return False
        ok = doc.content_hash == sha256_text(doc.content)
        if not ok:
            doc.status = "corrupted"
            self.session.add(
                RecoveryEvent(
                    project_id=doc.project_id,
                    document_id=doc.id,
                    event_type="integrity_failed",
                    message="Content hash mismatch",
                    source="integrity",
                )
            )
        return ok
