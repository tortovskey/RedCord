import json
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from redcord.db.models import Autosave, Document, RecoveryEvent


class RecoveryService:
    def __init__(self, session: Session):
        self.session = session

    def restore_from_autosave(self, document_id: int) -> bool:
        autosave = (
            self.session.query(Autosave)
            .filter(Autosave.document_id == document_id, Autosave.recovered.is_(False))
            .order_by(Autosave.created_at.desc())
            .first()
        )
        doc = self.session.get(Document, document_id)
        if not autosave or not doc:
            return False
        doc.content = autosave.content_snapshot
        doc.content_hash = autosave.content_hash
        autosave.recovered = True
        autosave.recovered_at = datetime.utcnow()
        self.session.add(RecoveryEvent(project_id=doc.project_id, document_id=document_id, event_type="autosave_restore", message="Document restored from autosave", source="autosave"))
        return True

    def restore_from_backup_file(self, project_id: int, backup_path: str) -> int:
        data = json.loads(Path(backup_path).read_text(encoding="utf-8"))
        restored = 0
        for item in data:
            doc = self.session.get(Document, item["id"])
            if doc:
                doc.content = item["content"]
                doc.content_hash = item["hash"]
                restored += 1
        self.session.add(RecoveryEvent(project_id=project_id, document_id=None, event_type="backup_restore", message=f"Restored {restored} documents", source="backup"))
        return restored
