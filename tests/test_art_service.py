from __future__ import annotations

import shutil
import unittest
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from PyQt6.QtGui import QColor, QImage

from redcord.services.art_service import ArtSaveRequest, ArtService
from redcord.storage.sqlite_store import SQLiteStore


TMP_ROOT = Path(__file__).resolve().parents[1] / ".redcord_test_tmp"


@contextmanager
def _temp_dir():
    TMP_ROOT.mkdir(exist_ok=True)
    path = TMP_ROOT / f"case_{uuid4().hex}"
    path.mkdir()
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


class ArtServiceTests(unittest.TestCase):
    def test_save_asset_writes_png_and_metadata(self):
        with _temp_dir() as tmp:
            store = SQLiteStore(tmp / "redcord_08.db")
            store.initialize()
            project = store.create_project("Novel")
            image = QImage(320, 200, QImage.Format.Format_ARGB32)
            image.fill(QColor("#b93649"))
            service = ArtService(store, tmp / "art_assets")

            asset = service.save_asset(
                ArtSaveRequest(
                    project_id=project.id,
                    title="Book cover",
                    art_type="book_cover",
                    notes="crimson cover idea",
                    image=image,
                )
            )

            self.assertTrue(Path(asset.file_path).exists())
            self.assertEqual(asset.width, 320)
            self.assertEqual(asset.height, 200)
            self.assertEqual(store.list_art_assets(project.id)[0].title, "Book cover")

    def test_unique_export_name_sanitizes_title(self):
        with _temp_dir() as tmp:
            store = SQLiteStore(tmp / "redcord_08.db")
            store.initialize()
            service = ArtService(store, tmp / "art_assets")

            self.assertEqual(service.unique_export_name("Cover: test / 01"), "Cover_test_01")
            self.assertEqual(service.unique_export_name("   "), "redcord_art")


if __name__ == "__main__":
    unittest.main()
