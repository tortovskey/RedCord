import json
from pathlib import Path

from sqlalchemy.orm import Session

from redcord.core.config import get_settings
from redcord.db.models import Backup, Document


class BackupService:
    def __init__(self, session: Session):
        self.session = session
        self.settings = get_settings()

    def create_backup(self, project_id: int, backup_type: str = "manual", notes: str = "") -> Backup:
        docs = self.session.query(Document).filter(Document.project_id == project_id).all()
        payload = [{"id": d.id, "title": d.title, "content": d.content, "hash": d.content_hash} for d in docs]
        folder = Path(self.settings.backup_dir)
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"project_{project_id}_{len(payload)}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        backup = Backup(project_id=project_id, path=str(path), backup_type=backup_type, verified=True, notes=notes)
        self.session.add(backup)
        self.session.flush()
        return backup
