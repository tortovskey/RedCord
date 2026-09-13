from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from redcord.domain.entities import (
    ArtAsset,
    Branch,
    Commit,
    Concept,
    Document,
    Project,
    Template,
    UserAccount,
    new_id,
    utc_now_iso,
)
from redcord.sync.conflicts import create_conflict_copy_id

DEFAULT_OWNER_ID = "local"


class SQLiteStore:
    """Offline-first RedCord 0.8.x SQLite store."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS app_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS accounts (
                    id TEXT PRIMARY KEY,
                    email TEXT NOT NULL DEFAULT '',
                    display_name TEXT NOT NULL DEFAULT 'Автор',
                    token TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY,
                    owner_id TEXT NOT NULL DEFAULT 'local',
                    title TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL,
                    sync_state TEXT NOT NULL DEFAULT 'local',
                    revision INTEGER NOT NULL DEFAULT 0,
                    deleted_at TEXT
                );
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    owner_id TEXT NOT NULL DEFAULT 'local',
                    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    title TEXT NOT NULL,
                    doc_type TEXT NOT NULL DEFAULT 'note',
                    content_html TEXT NOT NULL DEFAULT '',
                    content_plain TEXT NOT NULL DEFAULT '',
                    tags TEXT NOT NULL DEFAULT '',
                    category TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL,
                    sync_state TEXT NOT NULL DEFAULT 'local',
                    revision INTEGER NOT NULL DEFAULT 0,
                    deleted_at TEXT
                );
                CREATE TABLE IF NOT EXISTS concepts (
                    id TEXT PRIMARY KEY,
                    owner_id TEXT NOT NULL DEFAULT 'local',
                    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    title TEXT NOT NULL,
                    content_html TEXT NOT NULL DEFAULT '',
                    content_plain TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'Idea',
                    updated_at TEXT NOT NULL,
                    sync_state TEXT NOT NULL DEFAULT 'local',
                    revision INTEGER NOT NULL DEFAULT 0,
                    deleted_at TEXT
                );
                CREATE TABLE IF NOT EXISTS commits (
                    id TEXT PRIMARY KEY,
                    owner_id TEXT NOT NULL DEFAULT 'local',
                    document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                    message TEXT NOT NULL,
                    content_html TEXT NOT NULL DEFAULT '',
                    content_plain TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    sync_state TEXT NOT NULL DEFAULT 'local',
                    revision INTEGER NOT NULL DEFAULT 0,
                    deleted_at TEXT
                );
                CREATE TABLE IF NOT EXISTS templates (
                    id TEXT PRIMARY KEY,
                    owner_id TEXT NOT NULL DEFAULT 'local',
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    content_html TEXT NOT NULL DEFAULT '',
                    content_plain TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL,
                    sync_state TEXT NOT NULL DEFAULT 'local',
                    revision INTEGER NOT NULL DEFAULT 0,
                    deleted_at TEXT
                );
                CREATE TABLE IF NOT EXISTS branches (
                    id TEXT PRIMARY KEY,
                    owner_id TEXT NOT NULL DEFAULT 'local',
                    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    content_html TEXT NOT NULL DEFAULT '',
                    content_plain TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    sync_state TEXT NOT NULL DEFAULT 'local',
                    revision INTEGER NOT NULL DEFAULT 0,
                    deleted_at TEXT
                );
                CREATE TABLE IF NOT EXISTS art_assets (
                    id TEXT PRIMARY KEY,
                    owner_id TEXT NOT NULL DEFAULT 'local',
                    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                    title TEXT NOT NULL,
                    art_type TEXT NOT NULL DEFAULT 'concept_art',
                    file_path TEXT NOT NULL DEFAULT '',
                    notes TEXT NOT NULL DEFAULT '',
                    width INTEGER NOT NULL DEFAULT 0,
                    height INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL,
                    sync_state TEXT NOT NULL DEFAULT 'local',
                    revision INTEGER NOT NULL DEFAULT 0,
                    deleted_at TEXT
                );
                CREATE INDEX IF NOT EXISTS ix_documents_project ON documents(project_id);
                CREATE INDEX IF NOT EXISTS ix_documents_search ON documents(title, tags, category);
                CREATE INDEX IF NOT EXISTS ix_concepts_project ON concepts(project_id);
                CREATE INDEX IF NOT EXISTS ix_commits_document ON commits(document_id);
                CREATE INDEX IF NOT EXISTS ix_branches_document ON branches(document_id);
                CREATE INDEX IF NOT EXISTS ix_art_assets_project ON art_assets(project_id, art_type);
                CREATE UNIQUE INDEX IF NOT EXISTS ux_templates_type_owner ON templates(owner_id, type);
                """
            )
            db.execute(
                "INSERT OR IGNORE INTO accounts(id, email, display_name, token, updated_at) VALUES (?, '', 'Автор', '', ?)",
                (DEFAULT_OWNER_ID, utc_now_iso()),
            )
            db.execute("INSERT OR REPLACE INTO app_meta(key, value) VALUES ('schema_version', '0.8.3')")

    def meta(self, key: str, default: str = "") -> str:
        with self.connect() as db:
            row = db.execute("SELECT value FROM app_meta WHERE key = ?", (key,)).fetchone()
            return str(row["value"]) if row else default

    def set_meta(self, key: str, value: str) -> None:
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO app_meta(key, value) VALUES (?, ?)", (key, value))

    def list_projects(self) -> list[Project]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT * FROM projects WHERE deleted_at IS NULL ORDER BY updated_at DESC, title COLLATE NOCASE"
            ).fetchall()
            return [self._project(row) for row in rows]

    def create_project(self, title: str, description: str = "") -> Project:
        project = Project(
            id=new_id(),
            owner_id=DEFAULT_OWNER_ID,
            title=title.strip() or "Новый проект",
            description=description.strip(),
            updated_at=utc_now_iso(),
        )
        self.upsert_project(project)
        return project

    def upsert_project(self, project: Project) -> None:
        now = project.updated_at or utc_now_iso()
        with self.connect() as db:
            values = (
                project.owner_id,
                project.title,
                project.description,
                now,
                project.sync_state,
                project.revision,
                project.deleted_at,
                project.id,
            )
            if db.execute("SELECT 1 FROM projects WHERE id = ?", (project.id,)).fetchone():
                db.execute(
                    """
                    UPDATE projects
                    SET owner_id = ?, title = ?, description = ?, updated_at = ?, sync_state = ?, revision = ?, deleted_at = ?
                    WHERE id = ?
                    """,
                    values,
                )
            else:
                db.execute(
                    """
                    INSERT INTO projects
                    (owner_id, title, description, updated_at, sync_state, revision, deleted_at, id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    values,
                )

    def list_documents(self, project_id: str) -> list[Document]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT * FROM documents WHERE project_id = ? AND deleted_at IS NULL ORDER BY updated_at DESC, title COLLATE NOCASE",
                (project_id,),
            ).fetchall()
            return [self._document(row) for row in rows]

    def first_document(self) -> Document | None:
        with self.connect() as db:
            row = db.execute(
                "SELECT * FROM documents WHERE deleted_at IS NULL ORDER BY updated_at DESC LIMIT 1"
            ).fetchone()
            return self._document(row) if row else None

    def get_document(self, document_id: str) -> Document | None:
        with self.connect() as db:
            row = db.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
            return self._document(row) if row else None

    def create_document(self, project_id: str, title: str, doc_type: str = "note") -> Document:
        doc = Document(
            id=new_id(),
            owner_id=DEFAULT_OWNER_ID,
            project_id=project_id,
            title=title.strip() or "Новый документ",
            doc_type=doc_type or "note",
            content_html="<h1>Новый документ</h1><p></p>",
            content_plain="Новый документ",
            updated_at=utc_now_iso(),
        )
        self.upsert_document(doc)
        return doc

    def upsert_document(self, document: Document) -> None:
        now = document.updated_at or utc_now_iso()
        with self.connect() as db:
            values = (
                document.owner_id,
                document.project_id,
                document.title.strip() or "Без названия",
                document.doc_type or "note",
                document.content_html,
                document.content_plain,
                document.tags,
                document.category,
                now,
                document.sync_state,
                document.revision,
                document.deleted_at,
                document.id,
            )
            if db.execute("SELECT 1 FROM documents WHERE id = ?", (document.id,)).fetchone():
                db.execute(
                    """
                    UPDATE documents
                    SET owner_id = ?, project_id = ?, title = ?, doc_type = ?, content_html = ?, content_plain = ?,
                        tags = ?, category = ?, updated_at = ?, sync_state = ?, revision = ?, deleted_at = ?
                    WHERE id = ?
                    """,
                    values,
                )
            else:
                db.execute(
                    """
                    INSERT INTO documents
                    (owner_id, project_id, title, doc_type, content_html, content_plain, tags, category,
                     updated_at, sync_state, revision, deleted_at, id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    values,
                )
            db.execute("UPDATE projects SET updated_at = ?, sync_state = 'local' WHERE id = ?", (now, document.project_id))

    def search_documents(self, query: str) -> list[Document]:
        like = f"%{query.strip()}%"
        with self.connect() as db:
            rows = db.execute(
                """
                SELECT * FROM documents
                WHERE deleted_at IS NULL
                  AND (title LIKE ? OR content_plain LIKE ? OR tags LIKE ? OR category LIKE ?)
                ORDER BY updated_at DESC
                """,
                (like, like, like, like),
            ).fetchall()
            return [self._document(row) for row in rows]

    def list_concepts(self, project_id: str) -> list[Concept]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT * FROM concepts WHERE project_id = ? AND deleted_at IS NULL ORDER BY updated_at DESC, title COLLATE NOCASE",
                (project_id,),
            ).fetchall()
            return [self._concept(row) for row in rows]

    def get_concept(self, concept_id: str) -> Concept | None:
        with self.connect() as db:
            row = db.execute("SELECT * FROM concepts WHERE id = ?", (concept_id,)).fetchone()
            return self._concept(row) if row else None

    def create_concept(self, project_id: str, title: str, status: str = "Idea") -> Concept:
        concept = Concept(
            id=new_id(),
            owner_id=DEFAULT_OWNER_ID,
            project_id=project_id,
            title=title.strip() or "Новый концепт",
            content_html="<h2>Новый концепт</h2><p></p>",
            content_plain="Новый концепт",
            status=status.strip() or "Idea",
            updated_at=utc_now_iso(),
        )
        self.upsert_concept(concept)
        return concept

    def upsert_concept(self, concept: Concept) -> None:
        with self.connect() as db:
            values = (
                concept.owner_id,
                concept.project_id,
                concept.title,
                concept.content_html,
                concept.content_plain,
                concept.status,
                concept.updated_at or utc_now_iso(),
                concept.sync_state,
                concept.revision,
                concept.deleted_at,
                concept.id,
            )
            if db.execute("SELECT 1 FROM concepts WHERE id = ?", (concept.id,)).fetchone():
                db.execute(
                    """
                    UPDATE concepts
                    SET owner_id = ?, project_id = ?, title = ?, content_html = ?, content_plain = ?, status = ?,
                        updated_at = ?, sync_state = ?, revision = ?, deleted_at = ?
                    WHERE id = ?
                    """,
                    values,
                )
            else:
                db.execute(
                    """
                    INSERT INTO concepts
                    (owner_id, project_id, title, content_html, content_plain, status, updated_at, sync_state, revision, deleted_at, id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    values,
                )

    def delete_concept(self, concept_id: str) -> None:
        with self.connect() as db:
            db.execute(
                "UPDATE concepts SET deleted_at = ?, sync_state = 'local' WHERE id = ?",
                (utc_now_iso(), concept_id),
            )

    def list_commits(self, document_id: str) -> list[Commit]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT * FROM commits WHERE document_id = ? AND deleted_at IS NULL ORDER BY created_at DESC",
                (document_id,),
            ).fetchall()
            return [self._commit(row) for row in rows]

    def get_commit(self, commit_id: str) -> Commit | None:
        with self.connect() as db:
            row = db.execute("SELECT * FROM commits WHERE id = ?", (commit_id,)).fetchone()
            return self._commit(row) if row else None

    def create_commit(self, document: Document, message: str) -> Commit:
        commit = Commit(
            id=new_id(),
            owner_id=document.owner_id,
            document_id=document.id,
            message=message.strip() or "Snapshot",
            content_html=document.content_html,
            content_plain=document.content_plain,
            created_at=utc_now_iso(),
        )
        self.upsert_commit(commit)
        return commit

    def upsert_commit(self, commit: Commit) -> None:
        with self.connect() as db:
            values = (
                commit.owner_id,
                commit.document_id,
                commit.message,
                commit.content_html,
                commit.content_plain,
                commit.created_at,
                commit.sync_state,
                commit.revision,
                commit.deleted_at,
                commit.id,
            )
            if db.execute("SELECT 1 FROM commits WHERE id = ?", (commit.id,)).fetchone():
                db.execute(
                    """
                    UPDATE commits
                    SET owner_id = ?, document_id = ?, message = ?, content_html = ?, content_plain = ?, created_at = ?,
                        sync_state = ?, revision = ?, deleted_at = ?
                    WHERE id = ?
                    """,
                    values,
                )
            else:
                db.execute(
                    """
                    INSERT INTO commits
                    (owner_id, document_id, message, content_html, content_plain, created_at, sync_state, revision, deleted_at, id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    values,
                )

    def rename_commit(self, commit_id: str, message: str) -> None:
        with self.connect() as db:
            db.execute(
                "UPDATE commits SET message = ?, sync_state = 'local', revision = revision + 1 WHERE id = ?",
                (message.strip() or "Snapshot", commit_id),
            )

    def delete_commit(self, commit_id: str) -> None:
        with self.connect() as db:
            db.execute(
                "UPDATE commits SET deleted_at = ?, sync_state = 'local' WHERE id = ?",
                (utc_now_iso(), commit_id),
            )

    def rollback_commit(self, commit_id: str) -> Document | None:
        commit = self.get_commit(commit_id)
        if not commit:
            return None
        document = self.get_document(commit.document_id)
        if not document:
            return None
        restored = Document(
            id=document.id,
            owner_id=document.owner_id,
            project_id=document.project_id,
            title=document.title,
            doc_type=document.doc_type,
            content_html=commit.content_html,
            content_plain=commit.content_plain,
            tags=document.tags,
            category=document.category,
            updated_at=utc_now_iso(),
            sync_state="local",
            revision=document.revision + 1,
        )
        self.upsert_document(restored)
        return restored

    def list_branches(self, document_id: str) -> list[Branch]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT * FROM branches WHERE document_id = ? AND deleted_at IS NULL ORDER BY updated_at DESC, name COLLATE NOCASE",
                (document_id,),
            ).fetchall()
            return [self._branch(row) for row in rows]

    def get_branch(self, branch_id: str) -> Branch | None:
        with self.connect() as db:
            row = db.execute("SELECT * FROM branches WHERE id = ?", (branch_id,)).fetchone()
            return self._branch(row) if row else None

    def create_branch(self, document: Document, name: str, description: str = "") -> Branch:
        now = utc_now_iso()
        branch = Branch(
            id=new_id(),
            owner_id=document.owner_id,
            project_id=document.project_id,
            document_id=document.id,
            name=name.strip() or "new-branch",
            description=description.strip(),
            content_html=document.content_html,
            content_plain=document.content_plain,
            created_at=now,
            updated_at=now,
        )
        self.upsert_branch(branch)
        return branch

    def upsert_branch(self, branch: Branch) -> None:
        now = branch.updated_at or utc_now_iso()
        with self.connect() as db:
            values = (
                branch.owner_id,
                branch.project_id,
                branch.document_id,
                branch.name,
                branch.description,
                branch.content_html,
                branch.content_plain,
                branch.created_at or now,
                now,
                branch.sync_state,
                branch.revision,
                branch.deleted_at,
                branch.id,
            )
            if db.execute("SELECT 1 FROM branches WHERE id = ?", (branch.id,)).fetchone():
                db.execute(
                    """
                    UPDATE branches
                    SET owner_id = ?, project_id = ?, document_id = ?, name = ?, description = ?, content_html = ?,
                        content_plain = ?, created_at = ?, updated_at = ?, sync_state = ?, revision = ?, deleted_at = ?
                    WHERE id = ?
                    """,
                    values,
                )
            else:
                db.execute(
                    """
                    INSERT INTO branches
                    (owner_id, project_id, document_id, name, description, content_html, content_plain,
                     created_at, updated_at, sync_state, revision, deleted_at, id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    values,
                )

    def save_document_to_branch(self, branch_id: str, document: Document) -> Branch | None:
        branch = self.get_branch(branch_id)
        if not branch:
            return None
        updated = Branch(
            id=branch.id,
            owner_id=branch.owner_id,
            project_id=document.project_id,
            document_id=document.id,
            name=branch.name,
            description=branch.description,
            content_html=document.content_html,
            content_plain=document.content_plain,
            created_at=branch.created_at,
            updated_at=utc_now_iso(),
            sync_state="local",
            revision=branch.revision + 1,
        )
        self.upsert_branch(updated)
        return updated

    def checkout_branch(self, branch_id: str) -> Document | None:
        branch = self.get_branch(branch_id)
        if not branch:
            return None
        document = self.get_document(branch.document_id)
        if not document:
            return None
        restored = Document(
            id=document.id,
            owner_id=document.owner_id,
            project_id=document.project_id,
            title=document.title,
            doc_type=document.doc_type,
            content_html=branch.content_html,
            content_plain=branch.content_plain,
            tags=document.tags,
            category=document.category,
            updated_at=utc_now_iso(),
            sync_state="local",
            revision=document.revision + 1,
        )
        self.upsert_document(restored)
        return restored

    def delete_branch(self, branch_id: str) -> None:
        with self.connect() as db:
            db.execute(
                "UPDATE branches SET deleted_at = ?, sync_state = 'local' WHERE id = ?",
                (utc_now_iso(), branch_id),
            )

    def list_templates(self) -> list[Template]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT * FROM templates WHERE deleted_at IS NULL ORDER BY type COLLATE NOCASE"
            ).fetchall()
            return [self._template(row) for row in rows]

    def get_template_by_type(self, template_type: str) -> Template | None:
        with self.connect() as db:
            row = db.execute(
                "SELECT * FROM templates WHERE owner_id = ? AND type = ? AND deleted_at IS NULL",
                (DEFAULT_OWNER_ID, template_type),
            ).fetchone()
            return self._template(row) if row else None

    def upsert_template(self, template: Template) -> None:
        with self.connect() as db:
            values = (
                template.owner_id,
                template.name,
                template.type,
                template.content_html,
                template.content_plain,
                template.updated_at or utc_now_iso(),
                template.sync_state,
                template.revision,
                template.deleted_at,
                template.id,
            )
            if db.execute("SELECT 1 FROM templates WHERE id = ?", (template.id,)).fetchone():
                db.execute(
                    """
                    UPDATE templates
                    SET owner_id = ?, name = ?, type = ?, content_html = ?, content_plain = ?, updated_at = ?,
                        sync_state = ?, revision = ?, deleted_at = ?
                    WHERE id = ?
                    """,
                    values,
                )
            else:
                db.execute(
                    """
                    INSERT INTO templates
                    (owner_id, name, type, content_html, content_plain, updated_at, sync_state, revision, deleted_at, id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    values,
                )

    def create_or_update_template(self, template_type: str, name: str, content_html: str, content_plain: str) -> Template:
        clean_type = template_type.strip().lower().replace(" ", "_") or "custom"
        current = self.get_template_by_type(clean_type)
        template = Template(
            id=current.id if current else new_id(),
            owner_id=DEFAULT_OWNER_ID,
            name=name.strip() or clean_type,
            type=clean_type,
            content_html=content_html,
            content_plain=content_plain,
            updated_at=utc_now_iso(),
            sync_state="local",
            revision=(current.revision + 1) if current else 0,
        )
        self.upsert_template(template)
        return template

    def delete_template(self, template_type: str) -> None:
        with self.connect() as db:
            db.execute(
                "UPDATE templates SET deleted_at = ?, sync_state = 'local' WHERE owner_id = ? AND type = ?",
                (utc_now_iso(), DEFAULT_OWNER_ID, template_type),
            )

    def list_art_assets(self, project_id: str, art_type: str | None = None) -> list[ArtAsset]:
        with self.connect() as db:
            if art_type:
                rows = db.execute(
                    """
                    SELECT * FROM art_assets
                    WHERE project_id = ? AND art_type = ? AND deleted_at IS NULL
                    ORDER BY updated_at DESC, title COLLATE NOCASE
                    """,
                    (project_id, art_type),
                ).fetchall()
            else:
                rows = db.execute(
                    """
                    SELECT * FROM art_assets
                    WHERE project_id = ? AND deleted_at IS NULL
                    ORDER BY updated_at DESC, title COLLATE NOCASE
                    """,
                    (project_id,),
                ).fetchall()
            return [self._art_asset(row) for row in rows]

    def get_art_asset(self, asset_id: str) -> ArtAsset | None:
        with self.connect() as db:
            row = db.execute("SELECT * FROM art_assets WHERE id = ?", (asset_id,)).fetchone()
            return self._art_asset(row) if row else None

    def upsert_art_asset(self, asset: ArtAsset) -> None:
        now = asset.updated_at or utc_now_iso()
        with self.connect() as db:
            values = (
                asset.owner_id,
                asset.project_id,
                asset.title.strip() or "Untitled art",
                asset.art_type or "concept_art",
                asset.file_path,
                asset.notes,
                int(asset.width),
                int(asset.height),
                now,
                asset.sync_state,
                asset.revision,
                asset.deleted_at,
                asset.id,
            )
            if db.execute("SELECT 1 FROM art_assets WHERE id = ?", (asset.id,)).fetchone():
                db.execute(
                    """
                    UPDATE art_assets
                    SET owner_id = ?, project_id = ?, title = ?, art_type = ?, file_path = ?, notes = ?,
                        width = ?, height = ?, updated_at = ?, sync_state = ?, revision = ?, deleted_at = ?
                    WHERE id = ?
                    """,
                    values,
                )
            else:
                db.execute(
                    """
                    INSERT INTO art_assets
                    (owner_id, project_id, title, art_type, file_path, notes, width, height,
                     updated_at, sync_state, revision, deleted_at, id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    values,
                )

    def delete_art_asset(self, asset_id: str) -> None:
        with self.connect() as db:
            db.execute(
                "UPDATE art_assets SET deleted_at = ?, sync_state = 'local' WHERE id = ?",
                (utc_now_iso(), asset_id),
            )

    def active_account(self) -> UserAccount:
        with self.connect() as db:
            row = db.execute(
                """
                SELECT * FROM accounts
                ORDER BY CASE WHEN email = '' THEN 1 ELSE 0 END, updated_at DESC
                LIMIT 1
                """
            ).fetchone()
            if row:
                return UserAccount(
                    id=row["id"],
                    email=row["email"],
                    display_name=row["display_name"],
                    token=row["token"],
                    updated_at=row["updated_at"],
                )
        return UserAccount(DEFAULT_OWNER_ID, "", "Автор", "", utc_now_iso())

    def save_account(self, email: str, token: str, display_name: str = "") -> UserAccount:
        account = UserAccount(new_id(), email.strip(), display_name.strip() or email.strip(), token, utc_now_iso())
        self.upsert_account(account)
        return account

    def upsert_account(self, account: UserAccount) -> None:
        with self.connect() as db:
            db.execute(
                """
                INSERT INTO accounts(id, email, display_name, token, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    email = excluded.email,
                    display_name = excluded.display_name,
                    token = excluded.token,
                    updated_at = excluded.updated_at
                """,
                (
                    account.id,
                    account.email,
                    account.display_name,
                    account.token,
                    account.updated_at or utc_now_iso(),
                ),
            )

    def create_document_conflict_copy(self, document_id: str, reason: str = "Sync conflict") -> Document | None:
        document = self.get_document(document_id)
        if not document:
            return None
        copy = Document(
            id=create_conflict_copy_id(document.id),
            owner_id=document.owner_id,
            project_id=document.project_id,
            title=f"{document.title} (conflict copy)",
            doc_type=document.doc_type,
            content_html=f"<p><b>Conflict copy:</b> {reason}</p><hr>{document.content_html}",
            content_plain=f"Conflict copy: {reason}\n\n{document.content_plain}",
            tags=document.tags,
            category=document.category,
            updated_at=utc_now_iso(),
            sync_state="conflict",
            revision=document.revision,
        )
        self.upsert_document(copy)
        return copy

    def outgoing_changes(self) -> dict[str, list[dict[str, object]]]:
        result: dict[str, list[dict[str, object]]] = {}
        with self.connect() as db:
            for table in ["projects", "documents", "concepts", "commits", "templates", "branches", "art_assets"]:
                rows = db.execute(f"SELECT * FROM {table} WHERE sync_state IN ('local', 'conflict')").fetchall()
                result[table] = [dict(row) for row in rows]
        return result

    def _project(self, row: sqlite3.Row) -> Project:
        return Project(**dict(row))

    def _document(self, row: sqlite3.Row) -> Document:
        return Document(**dict(row))

    def _concept(self, row: sqlite3.Row) -> Concept:
        return Concept(**dict(row))

    def _commit(self, row: sqlite3.Row) -> Commit:
        return Commit(**dict(row))

    def _branch(self, row: sqlite3.Row) -> Branch:
        return Branch(**dict(row))

    def _template(self, row: sqlite3.Row) -> Template:
        return Template(**dict(row))

    def _art_asset(self, row: sqlite3.Row) -> ArtAsset:
        return ArtAsset(**dict(row))
