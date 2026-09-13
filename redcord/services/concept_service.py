from __future__ import annotations

import uuid

from redcord.db.database import new_session
from redcord.db.models import Concept, Document
from redcord.db.repositories import ConceptRepository, DocumentRepository


class ConceptService:
    def list_concepts(self, project_id: uuid.UUID) -> list[Concept]:
        with new_session() as session:
            return ConceptRepository(session).list_by_project(project_id)

    def create_concept(self, project_id: uuid.UUID, title: str, content: str = "", status: str = "Идея") -> Concept:
        with new_session() as session:
            return ConceptRepository(session).create(project_id, title, content, status)

    def save_concept(self, concept_id: uuid.UUID, title: str, content: str, status: str) -> Concept:
        with new_session() as session:
            repo = ConceptRepository(session)
            concept = repo.get(concept_id)
            if concept is None:
                raise ValueError("Концепт не найден")
            concept.title = title.strip() or "Без названия"
            concept.content = content
            concept.status = status
            return repo.save(concept)

    def delete_concept(self, concept_id: uuid.UUID) -> None:
        with new_session() as session:
            repo = ConceptRepository(session)
            concept = repo.get(concept_id)
            if concept is None:
                raise ValueError("Концепт не найден")
            repo.delete(concept)

    def convert_to_document(self, concept_id: uuid.UUID) -> Document:
        with new_session() as session:
            concepts = ConceptRepository(session)
            docs = DocumentRepository(session)
            concept = concepts.get(concept_id)
            if concept is None:
                raise ValueError("Концепт не найден")
            document = docs.create(
                project_id=concept.project_id,
                title=concept.title,
                doc_type="concept",
                content=concept.content,
                tags="concept",
                category="Концепты",
            )
            concept.status = "Использовано"
            concepts.save(concept)
            return document
