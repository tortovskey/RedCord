from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from redcord.db.models import Autosave, Document
from redcord.utils.hash_utils import sha256_text


class AutosaveService:
    def __init__(self, session: Session):
        self.session = session
        self.scheduler = BackgroundScheduler(daemon=True)

    def start(self, interval_seconds: int = 10):
        self.scheduler.add_job(self.run_autosave_cycle, "interval", seconds=interval_seconds, id="autosave")
        self.scheduler.start()

    def stop(self):
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    def run_autosave_cycle(self):
        docs = self.session.query(Document).filter(Document.deleted_at.is_(None)).all()
        for doc in docs:
            self.save_document(doc.id, doc.content)
        self.session.commit()

    def save_document(self, document_id: int, content: str):
        self.session.add(Autosave(document_id=document_id, content_snapshot=content, content_hash=sha256_text(content)))
