from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtGui import QImage

from redcord.app.config import get_settings
from redcord.domain.entities import ArtAsset, new_id, utc_now_iso
from redcord.storage.sqlite_store import DEFAULT_OWNER_ID, SQLiteStore


ART_TYPES = [
    ("concept_art", "Concept Art"),
    ("book_cover", "Обложка книги"),
    ("comic_cover", "Обложка комикса"),
    ("manga_cover", "Обложка манги"),
]

CANVAS_PRESETS = [
    ("concept_landscape", "Concept 16:10", 1280, 800),
    ("book_cover", "Book cover", 1600, 2560),
    ("comic_cover", "Comic cover", 1800, 2700),
    ("manga_cover", "Manga cover", 1600, 2400),
    ("square", "Square", 1600, 1600),
]


@dataclass(frozen=True)
class ArtSaveRequest:
    project_id: str
    title: str
    art_type: str
    notes: str
    image: QImage
    asset_id: str | None = None


class ArtService:
    def __init__(self, store: SQLiteStore, art_dir: str | Path | None = None) -> None:
        self.store = store
        self.art_dir = Path(art_dir) if art_dir else get_settings().data_dir / "art_assets"
        self.art_dir.mkdir(parents=True, exist_ok=True)

    def save_asset(self, request: ArtSaveRequest) -> ArtAsset:
        asset_id = request.asset_id or new_id()
        target = self.art_dir / f"{asset_id}.png"
        target.parent.mkdir(parents=True, exist_ok=True)
        if not request.image.save(str(target), "PNG"):
            raise OSError(f"Could not save PNG: {target}")
        existing = self.store.get_art_asset(asset_id)
        asset = ArtAsset(
            id=asset_id,
            owner_id=DEFAULT_OWNER_ID,
            project_id=request.project_id,
            title=request.title.strip() or "Untitled art",
            art_type=request.art_type or "concept_art",
            file_path=str(target),
            notes=request.notes.strip(),
            width=request.image.width(),
            height=request.image.height(),
            updated_at=utc_now_iso(),
            sync_state="local",
            revision=(existing.revision + 1) if existing else 0,
        )
        self.store.upsert_art_asset(asset)
        return asset

    def export_png(self, image: QImage, path: str | Path) -> Path:
        target = Path(path)
        if target.suffix.lower() != ".png":
            target = target.with_suffix(".png")
        target.parent.mkdir(parents=True, exist_ok=True)
        if not image.save(str(target), "PNG"):
            raise OSError(f"Could not export PNG: {target}")
        return target

    def unique_export_name(self, title: str) -> str:
        value = re.sub(r"[^a-zA-Z0-9а-яА-Я_-]+", "_", title.strip()).strip("_")
        return value or "redcord_art"
