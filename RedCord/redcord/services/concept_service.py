from sqlalchemy.orm import Session

from redcord.db.models import Concept


class ConceptService:
    def __init__(self, session: Session):
        self.session = session

    def create_concept(self, project_id: int, title: str, body: str, status: str = "raw", tags: str = "") -> Concept:
        concept = Concept(project_id=project_id, title=title, body=body, status=status, tags=tags)
        self.session.add(concept)
        self.session.flush()
        return concept
