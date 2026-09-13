from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4


def new_id() -> str:
    return str(uuid4())


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Project:
    id: str
    owner_id: str
    title: str
    description: str = ""
    updated_at: str = ""
    sync_state: str = "local"
    revision: int = 0
    deleted_at: str | None = None


@dataclass
class Document:
    id: str
    owner_id: str
    project_id: str
    title: str
    doc_type: str
    content_html: str
    content_plain: str
    tags: str = ""
    category: str = ""
    updated_at: str = ""
    sync_state: str = "local"
    revision: int = 0
    deleted_at: str | None = None


@dataclass
class Concept:
    id: str
    owner_id: str
    project_id: str
    title: str
    content_html: str
    content_plain: str
    status: str = "Idea"
    updated_at: str = ""
    sync_state: str = "local"
    revision: int = 0
    deleted_at: str | None = None


@dataclass
class Commit:
    id: str
    owner_id: str
    document_id: str
    message: str
    content_html: str
    content_plain: str
    created_at: str
    sync_state: str = "local"
    revision: int = 0
    deleted_at: str | None = None


@dataclass
class Branch:
    id: str
    owner_id: str
    project_id: str
    document_id: str
    name: str
    description: str = ""
    content_html: str = ""
    content_plain: str = ""
    created_at: str = ""
    updated_at: str = ""
    sync_state: str = "local"
    revision: int = 0
    deleted_at: str | None = None


@dataclass
class Template:
    id: str
    owner_id: str
    name: str
    type: str
    content_html: str = ""
    content_plain: str = ""
    updated_at: str = ""
    sync_state: str = "local"
    revision: int = 0
    deleted_at: str | None = None


@dataclass
class ArtAsset:
    id: str
    owner_id: str
    project_id: str
    title: str
    art_type: str
    file_path: str
    notes: str = ""
    width: int = 0
    height: int = 0
    updated_at: str = ""
    sync_state: str = "local"
    revision: int = 0
    deleted_at: str | None = None


@dataclass
class UserAccount:
    id: str
    email: str
    display_name: str
    token: str = ""
    updated_at: str = ""


@dataclass
class SyncConflict:
    local_id: str
    remote_id: str
    entity_type: str
    reason: str
    conflict_copy_id: str
