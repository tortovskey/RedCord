from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from redcord.db.models import Base, Project
from redcord.services.document_service import DocumentService
from redcord.services.version_service import VersionService


def test_commit_created():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, future=True)
    with Session() as session:
        p = Project(name="P1", description="")
        session.add(p)
        session.flush()
        doc = DocumentService(session).create_document(p.id, "D", "Note", "v1")
        ver = VersionService(session).create_commit(doc.id, "init")
        assert ver.version_number == 1
