from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from redcord.db.models import Base, Document, Project
from redcord.services.integrity_service import IntegrityService
from redcord.utils.hash_utils import sha256_text


def test_integrity_ok():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, future=True)
    with Session() as session:
        p = Project(name="P1", description="")
        session.add(p)
        session.flush()
        content = "stable"
        d = Document(project_id=p.id, title="D", document_type="Note", content=content, content_hash=sha256_text(content), status="active", tags="")
        session.add(d)
        session.flush()
        assert IntegrityService(session).check_document(d.id)
