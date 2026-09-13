from __future__ import annotations

import shutil
import unittest
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from redcord.domain.entities import ArtAsset, new_id, utc_now_iso
from redcord.storage.sqlite_store import DEFAULT_OWNER_ID, SQLiteStore


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


class SQLiteStore081Tests(unittest.TestCase):
    def test_schema_version_and_concept_crud(self):
        with _temp_dir() as tmp:
            store = SQLiteStore(tmp / "redcord_08.db")
            store.initialize()
            project = store.create_project("Novel")
            concept = store.create_concept(project.id, "Magic", "Draft")

            loaded = store.get_concept(concept.id)
            self.assertEqual(store.meta("schema_version"), "0.8.3")
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.title, "Magic")

            store.delete_concept(concept.id)
            self.assertEqual(store.list_concepts(project.id), [])

    def test_commit_rollback_branch_and_template_crud(self):
        with _temp_dir() as tmp:
            store = SQLiteStore(tmp / "redcord_08.db")
            store.initialize()
            project = store.create_project("Novel")
            document = store.create_document(project.id, "Chapter")
            document.content_plain = "First"
            document.content_html = "<p>First</p>"
            store.upsert_document(document)
            commit = store.create_commit(document, "First snapshot")

            document.content_plain = "Second"
            document.content_html = "<p>Second</p>"
            store.upsert_document(document)
            restored = store.rollback_commit(commit.id)
            self.assertIsNotNone(restored)
            self.assertEqual(store.get_document(document.id).content_plain, "First")

            branch = store.create_branch(store.get_document(document.id), "alt")
            self.assertEqual(store.list_branches(document.id)[0].name, "alt")
            store.delete_branch(branch.id)
            self.assertEqual(store.list_branches(document.id), [])

            template = store.create_or_update_template("scene", "Scene", "<p>Scene</p>", "Scene")
            self.assertEqual(store.get_template_by_type("scene").id, template.id)
            store.delete_template("scene")
            self.assertEqual(store.list_templates(), [])

    def test_art_asset_crud(self):
        with _temp_dir() as tmp:
            store = SQLiteStore(tmp / "redcord_08.db")
            store.initialize()
            project = store.create_project("Novel")
            asset = ArtAsset(
                id=new_id(),
                owner_id=DEFAULT_OWNER_ID,
                project_id=project.id,
                title="Cover sketch",
                art_type="book_cover",
                file_path=str(tmp / "cover.png"),
                notes="red dress, black sky",
                width=1280,
                height=800,
                updated_at=utc_now_iso(),
            )

            store.upsert_art_asset(asset)
            loaded = store.list_art_assets(project.id, "book_cover")

            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0].title, "Cover sketch")
            self.assertIn("art_assets", store.outgoing_changes())

            store.delete_art_asset(asset.id)
            self.assertEqual(store.list_art_assets(project.id), [])


if __name__ == "__main__":
    unittest.main()
