from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from redcord.db.models import Autosave, Base, Document, Project
from redcord.services.recovery_service import RecoveryService


def test_restore_from_autosave():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, future=True)
    with Session() as session:
        p = Project(name="P1", description="")
        session.add(p)
        session.flush()
        d = Document(project_id=p.id, title="D", document_type="Note", content="old", content_hash="x", status="active", tags="")
        session.add(d)
        session.flush()
        session.add(Autosave(document_id=d.id, content_snapshot="new", content_hash="h"))
        assert RecoveryService(session).restore_from_autosave(d.id)
