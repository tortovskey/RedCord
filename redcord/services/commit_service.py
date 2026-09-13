from __future__ import annotations

import re
import uuid
from datetime import datetime
from pathlib import Path

from redcord.app.config import get_settings
from redcord.db.database import new_session
from redcord.db.models import Commit
from redcord.db.repositories import CommitRepository, DocumentRepository


def _safe_filename(value: str) -> str:
    value = re.sub(r"[^\w\-.а-яА-ЯёЁ]+", "_", value, flags=re.UNICODE)
    return value.strip("_")[:80] or "commit"


class CommitService:
    def list_commits(self, document_id: uuid.UUID) -> list[Commit]:
        with new_session() as session:
            return CommitRepository(session).list_by_document(document_id)

    def create_commit(self, document_id: uuid.UUID, message: str) -> Commit:
        settings = get_settings()
        with new_session() as session:
            docs = DocumentRepository(session)
            document = docs.get(document_id)
            if document is None:
                raise ValueError("Документ не найден")

            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            clean_message = message.strip() or "Без сообщения"
            commit_dir = settings.commit_dir / f"document_{document.id}"
            commit_dir.mkdir(parents=True, exist_ok=True)
            filename = f"{timestamp}_{_safe_filename(clean_message)}.md"
            commit_path = commit_dir / filename
            body = (
                "---\n"
                f"document_id: {document.id}\n"
                f"document_title: {document.title}\n"
                f"commit_message: {clean_message}\n"
                f"created_at: {timestamp}\n"
                "---\n\n"
                "# Snapshot\n\n"
                f"{document.content}"
            )
            commit_path.write_text(body, encoding="utf-8")

            return CommitRepository(session).create(
                document_id=document.id,
                message=clean_message,
                content_snapshot=document.content,
                commit_file_path=str(commit_path),
            )

    def update_commit_message(self, commit_id: uuid.UUID, message: str) -> Commit:
        with new_session() as session:
            repo = CommitRepository(session)
            commit = repo.get(commit_id)
            if commit is None:
                raise ValueError("Коммит не найден")
            return repo.update_message(commit, message)

    def delete_commit(self, commit_id: uuid.UUID, delete_file: bool = False) -> None:
        with new_session() as session:
            repo = CommitRepository(session)
            commit = repo.get(commit_id)
            if commit is None:
                raise ValueError("Коммит не найден")

            file_path = Path(commit.commit_file_path) if commit.commit_file_path else None
            repo.delete(commit)

        if delete_file and file_path and file_path.exists():
            file_path.unlink()

    def rollback_to_commit(self, commit_id: uuid.UUID) -> Commit:
        with new_session() as session:
            commits = CommitRepository(session)
            docs = DocumentRepository(session)
            commit = commits.get(commit_id)
            if commit is None:
                raise ValueError("Коммит не найден")
            document = docs.get(commit.document_id)
            if document is None:
                raise ValueError("Документ не найден")
            document.content = commit.content_snapshot
            docs.save(document)

        return self.create_commit(commit.document_id, f"Rollback to commit {commit.id}")
