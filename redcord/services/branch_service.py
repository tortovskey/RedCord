from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime

from redcord.app.config import get_settings
from redcord.services.document_service import DocumentService


@dataclass
class LocalBranch:
    id: str
    document_id: str
    name: str
    content_snapshot: str
    created_at: str
    updated_at: str


class BranchService:
    """Simple local branch system for story alternatives.

    This is Git-like, not real Git: each branch stores a named snapshot for a document.
    """

    def __init__(self) -> None:
        settings = get_settings()
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        self.path = settings.data_dir / "branches.json"
        self.document_service = DocumentService()

    def _read(self) -> dict:
        if not self.path.exists():
            return {"branches": []}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {"branches": []}

    def _write(self, data: dict) -> None:
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def list_branches(self, document_id: uuid.UUID) -> list[LocalBranch]:
        data = self._read()
        result = []
        for item in data.get("branches", []):
            if str(item.get("document_id")) == str(document_id):
                result.append(LocalBranch(**item))
        return sorted(result, key=lambda b: b.updated_at, reverse=True)

    def create_branch(self, document_id: uuid.UUID, name: str) -> LocalBranch:
        document = self.document_service.get_document(document_id)
        if document is None:
            raise ValueError("Документ не найден")
        clean_name = name.strip() or "new-branch"

        for branch in self.list_branches(document_id):
            if branch.name.lower() == clean_name.lower():
                raise ValueError("Ветка с таким именем уже существует")

        now = datetime.now().isoformat(timespec="seconds")
        branch = LocalBranch(
            id=str(uuid.uuid4()),
            document_id=str(document_id),
            name=clean_name,
            content_snapshot=document.content,
            created_at=now,
            updated_at=now,
        )
        data = self._read()
        data.setdefault("branches", []).append(asdict(branch))
        self._write(data)
        return branch

    def get_branch(self, branch_id: str) -> LocalBranch | None:
        for item in self._read().get("branches", []):
            if item.get("id") == branch_id:
                return LocalBranch(**item)
        return None

    def save_current_to_branch(self, branch_id: str) -> LocalBranch:
        branch = self.get_branch(branch_id)
        if branch is None:
            raise ValueError("Ветка не найдена")
        document = self.document_service.get_document(uuid.UUID(branch.document_id))
        if document is None:
            raise ValueError("Документ не найден")

        data = self._read()
        now = datetime.now().isoformat(timespec="seconds")
        for item in data.get("branches", []):
            if item.get("id") == branch_id:
                item["content_snapshot"] = document.content
                item["updated_at"] = now
                self._write(data)
                return LocalBranch(**item)
        raise ValueError("Ветка не найдена")

    def checkout_branch(self, branch_id: str) -> LocalBranch:
        branch = self.get_branch(branch_id)
        if branch is None:
            raise ValueError("Ветка не найдена")
        document_id = uuid.UUID(branch.document_id)
        document = self.document_service.get_document(document_id)
        if document is None:
            raise ValueError("Документ не найден")

        self.document_service.save_document(
            document_id=document_id,
            title=document.title,
            doc_type=document.type,
            content=branch.content_snapshot,
            tags=document.tags,
            category=document.category,
        )
        return branch

    def rename_branch(self, branch_id: str, name: str) -> LocalBranch:
        data = self._read()
        clean_name = name.strip() or "branch"
        for item in data.get("branches", []):
            if item.get("id") == branch_id:
                item["name"] = clean_name
                item["updated_at"] = datetime.now().isoformat(timespec="seconds")
                self._write(data)
                return LocalBranch(**item)
        raise ValueError("Ветка не найдена")

    def delete_branch(self, branch_id: str) -> None:
        data = self._read()
        data["branches"] = [item for item in data.get("branches", []) if item.get("id") != branch_id]
        self._write(data)
