from __future__ import annotations

import shutil
import sqlite3
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from redcord.domain.entities import Branch, Commit, Concept, Document, Project, Template, UserAccount, new_id, utc_now_iso
from redcord.services.html_tools import plain_to_html
from redcord.storage.sqlite_store import DEFAULT_OWNER_ID, SQLiteStore


@dataclass(frozen=True)
class ImportReport:
    projects: int = 0
    documents: int = 0
    concepts: int = 0
    commits: int = 0
    templates: int = 0
    branches: int = 0
    accounts: int = 0
    backup_path: Path | None = None
    skipped: bool = False
    message: str = ""


class Legacy07Importer:
    def __init__(self, store: SQLiteStore, legacy_db: str | Path, backup_dir: str | Path) -> None:
        self.store = store
        self.legacy_db = Path(legacy_db)
        self.backup_dir = Path(backup_dir)

    def import_once(self) -> ImportReport:
        if self.store.meta("legacy_07_imported") == "true":
            return ImportReport(skipped=True, message="0.7.x data already imported.")
        if not self.legacy_db.exists():
            self.store.set_meta("legacy_07_imported", "true")
            return ImportReport(skipped=True, message="No 0.7.x database found.")

        backup_path = self._backup()
        projects = documents = concepts = commits = templates = branches = accounts = 0
        legacy = sqlite3.connect(self.legacy_db)
        legacy.row_factory = sqlite3.Row
        try:
            for row in self._safe_rows(legacy, "SELECT id, title, description, updated_at FROM projects"):
                self.store.upsert_project(
                    Project(
                        id=str(row["id"]),
                        owner_id=DEFAULT_OWNER_ID,
                        title=str(row["title"] or "Imported project"),
                        description=str(row["description"] or ""),
                        updated_at=str(row["updated_at"] or utc_now_iso()),
                        sync_state="local",
                    )
                )
                projects += 1

            for row in self._safe_rows(
                legacy,
                "SELECT id, project_id, title, type, content, tags, category, updated_at FROM documents",
            ):
                content = str(row["content"] or "")
                self.store.upsert_document(
                    Document(
                        id=str(row["id"]),
                        owner_id=DEFAULT_OWNER_ID,
                        project_id=str(row["project_id"]),
                        title=str(row["title"] or "Imported document"),
                        doc_type=str(row["type"] or "note"),
                        content_html=plain_to_html(content),
                        content_plain=content,
                        tags=str(row["tags"] or ""),
                        category=str(row["category"] or ""),
                        updated_at=str(row["updated_at"] or utc_now_iso()),
                        sync_state="local",
                    )
                )
                documents += 1

            for row in self._safe_rows(
                legacy,
                "SELECT id, project_id, title, content, status, updated_at FROM concepts",
            ):
                content = str(row["content"] or "")
                self.store.upsert_concept(
                    Concept(
                        id=str(row["id"]),
                        owner_id=DEFAULT_OWNER_ID,
                        project_id=str(row["project_id"]),
                        title=str(row["title"] or "Imported concept"),
                        content_html=plain_to_html(content),
                        content_plain=content,
                        status=str(row["status"] or "Idea"),
                        updated_at=str(row["updated_at"] or utc_now_iso()),
                        sync_state="local",
                    )
                )
                concepts += 1

            for row in self._safe_rows(
                legacy,
                "SELECT id, document_id, message, content_snapshot, created_at FROM commits",
            ):
                content = str(row["content_snapshot"] or "")
                self.store.upsert_commit(
                    Commit(
                        id=str(row["id"]),
                        owner_id=DEFAULT_OWNER_ID,
                        document_id=str(row["document_id"]),
                        message=str(row["message"] or "Imported commit"),
                        content_html=plain_to_html(content),
                        content_plain=content,
                        created_at=str(row["created_at"] or utc_now_iso()),
                        sync_state="local",
                    )
                )
                commits += 1

            for row in self._safe_rows(
                legacy,
                "SELECT id, name, type, content, updated_at FROM templates",
            ):
                content = str(row["content"] or "")
                self.store.upsert_template(
                    Template(
                        id=str(row["id"] or new_id()),
                        owner_id=DEFAULT_OWNER_ID,
                        name=str(row["name"] or row["type"] or "Imported template"),
                        type=str(row["type"] or "custom"),
                        content_html=plain_to_html(content),
                        content_plain=content,
                        updated_at=str(row["updated_at"] or utc_now_iso()),
                        sync_state="local",
                    )
                )
                templates += 1

            for row in self._safe_rows(
                legacy,
                "SELECT id, email, display_name, token, updated_at FROM accounts",
            ):
                self.store.upsert_account(
                    UserAccount(
                        id=str(row["id"] or new_id()),
                        email=str(row["email"] or ""),
                        display_name=str(row["display_name"] or row["email"] or "Автор"),
                        token=str(row["token"] or ""),
                        updated_at=str(row["updated_at"] or utc_now_iso()),
                    )
                )
                accounts += 1
        finally:
            legacy.close()

        json_accounts = self._import_accounts_json()
        json_branches = self._import_branches_json()
        accounts += json_accounts
        branches += json_branches

        self.store.set_meta("legacy_07_imported", "true")
        return ImportReport(
            projects=projects,
            documents=documents,
            concepts=concepts,
            commits=commits,
            templates=templates,
            branches=branches,
            accounts=accounts,
            backup_path=backup_path,
            message="0.7.x import completed.",
        )

    def _backup(self) -> Path:
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        target = self.backup_dir / f"redcord_07_{datetime.now():%Y-%m-%d_%H-%M-%S}.db"
        shutil.copy2(self.legacy_db, target)
        return target

    def _safe_rows(self, connection: sqlite3.Connection, query: str) -> list[sqlite3.Row]:
        try:
            return list(connection.execute(query).fetchall())
        except sqlite3.Error:
            return []

    def _read_json_file(self, name: str) -> dict:
        path = self.legacy_db.parent / name
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _import_accounts_json(self) -> int:
        data = self._read_json_file("accounts.json")
        raw_accounts = data.get("accounts", data if isinstance(data, list) else [])
        if not isinstance(raw_accounts, list):
            return 0
        imported = 0
        for item in raw_accounts:
            if not isinstance(item, dict):
                continue
            email = str(item.get("email", ""))
            display_name = str(item.get("display_name") or item.get("username") or email or "Автор")
            self.store.upsert_account(
                UserAccount(
                    id=str(item.get("id") or new_id()),
                    email=email,
                    display_name=display_name,
                    token=str(item.get("token", "")),
                    updated_at=str(item.get("updated_at") or utc_now_iso()),
                )
            )
            imported += 1
        return imported

    def _import_branches_json(self) -> int:
        data = self._read_json_file("branches.json")
        raw_branches = data.get("branches", data if isinstance(data, list) else [])
        if not isinstance(raw_branches, list):
            return 0
        imported = 0
        for item in raw_branches:
            if not isinstance(item, dict):
                continue
            document_id = str(item.get("document_id") or "")
            document = self.store.get_document(document_id)
            if document is None:
                continue
            content = str(item.get("content_snapshot") or item.get("content_plain") or "")
            content_html = str(item.get("content_html") or plain_to_html(content))
            self.store.upsert_branch(
                Branch(
                    id=str(item.get("id") or new_id()),
                    owner_id=DEFAULT_OWNER_ID,
                    project_id=document.project_id,
                    document_id=document.id,
                    name=str(item.get("name") or "imported-branch"),
                    description=str(item.get("description") or ""),
                    content_html=content_html,
                    content_plain=content or document.content_plain,
                    created_at=str(item.get("created_at") or utc_now_iso()),
                    updated_at=str(item.get("updated_at") or utc_now_iso()),
                    sync_state="local",
                )
            )
            imported += 1
        return imported
