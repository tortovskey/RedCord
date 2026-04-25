from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from redcord.db.models import Base, Project
from redcord.services.document_service import DocumentService


def test_create_document_sets_hash():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, future=True)
    with Session() as session:
        p = Project(name="P1", description="")
        session.add(p)
        session.flush()
        svc = DocumentService(session)
        doc = svc.create_document(project_id=p.id, title="Hero", document_type="Character", content="abc")
        assert doc.content_hash
