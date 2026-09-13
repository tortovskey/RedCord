from __future__ import annotations

import shutil
import unittest
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from redcord.sync.conflicts import create_conflict_copy_id
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


class SyncConflictTests(unittest.TestCase):
    def test_conflict_copy_id_keeps_original_id_visible(self):
        conflict_id = create_conflict_copy_id("doc-1")

        self.assertTrue(conflict_id.startswith("doc-1__conflict__"))
        self.assertGreater(len(conflict_id), len("doc-1__conflict__"))

    def test_store_creates_document_conflict_copy(self):
        with _temp_dir() as tmp:
            store = SQLiteStore(tmp / "redcord_08.db")
            store.initialize()
            project = store.create_project("Novel")
            document = store.create_document(project.id, "Chapter")

            copy = store.create_document_conflict_copy(document.id, "server is newer")

            self.assertIsNotNone(copy)
            self.assertTrue(copy.id.startswith(f"{document.id}__conflict__"))
            self.assertEqual(copy.sync_state, "conflict")
            self.assertIn("server is newer", copy.content_plain)
            self.assertEqual(len(store.list_documents(project.id)), 2)


if __name__ == "__main__":
    unittest.main()
