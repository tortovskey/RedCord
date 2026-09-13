from __future__ import annotations

import shutil
import sqlite3
import json
import unittest
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

from redcord.services.importer_07 import Legacy07Importer
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


def _legacy_db(path: Path) -> None:
    with sqlite3.connect(path) as db:
        db.executescript(
            """
            CREATE TABLE projects(id TEXT, title TEXT, description TEXT, updated_at TEXT);
            CREATE TABLE documents(id TEXT, project_id TEXT, title TEXT, type TEXT, content TEXT, tags TEXT, category TEXT, updated_at TEXT);
            CREATE TABLE concepts(id TEXT, project_id TEXT, title TEXT, content TEXT, status TEXT, updated_at TEXT);
            CREATE TABLE commits(id TEXT, document_id TEXT, message TEXT, content_snapshot TEXT, created_at TEXT);
            CREATE TABLE templates(id TEXT, name TEXT, type TEXT, content TEXT, updated_at TEXT);
            CREATE TABLE accounts(id TEXT, email TEXT, display_name TEXT, token TEXT, updated_at TEXT);
            """
        )
        db.execute("INSERT INTO projects VALUES ('p1', 'Novel', 'Desc', '2026-01-01T00:00:00')")
        db.execute(
            "INSERT INTO documents VALUES ('d1', 'p1', 'Chapter', 'chapter', 'Line one', 'tag', 'draft', '2026-01-02T00:00:00')"
        )
        db.execute(
            "INSERT INTO concepts VALUES ('c1', 'p1', 'Magic', 'Rules', 'Idea', '2026-01-03T00:00:00')"
        )
        db.execute("INSERT INTO commits VALUES ('k1', 'd1', 'Initial', 'Line one', '2026-01-04T00:00:00')")
        db.execute("INSERT INTO templates VALUES ('t1', 'Scene', 'scene', 'Template text', '2026-01-05T00:00:00')")
        db.execute("INSERT INTO accounts VALUES ('a1', 'writer@example.com', 'Writer', '', '2026-01-06T00:00:00')")


class Legacy07ImporterTests(unittest.TestCase):
    def test_imports_legacy_sqlite_without_mutating_old_database(self):
        with _temp_dir() as tmp:
            legacy_path = tmp / "redcord.db"
            _legacy_db(legacy_path)
            (tmp / "branches.json").write_text(
                json.dumps(
                    {
                        "branches": [
                            {
                                "id": "b1",
                                "document_id": "d1",
                                "name": "alt",
                                "content_snapshot": "Branch text",
                                "created_at": "2026-01-07T00:00:00",
                                "updated_at": "2026-01-07T00:00:00",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            original_bytes = legacy_path.read_bytes()

            store = SQLiteStore(tmp / "redcord_08.db")
            store.initialize()
            report = Legacy07Importer(store, legacy_path, tmp / "backups").import_once()

            self.assertEqual(report.projects, 1)
            self.assertEqual(report.documents, 1)
            self.assertEqual(report.concepts, 1)
            self.assertEqual(report.commits, 1)
            self.assertEqual(report.templates, 1)
            self.assertEqual(report.branches, 1)
            self.assertEqual(report.accounts, 1)
            self.assertEqual(legacy_path.read_bytes(), original_bytes)
            self.assertTrue(report.backup_path and report.backup_path.exists())

            projects = store.list_projects()
            docs = store.list_documents("p1")
            self.assertEqual(projects[0].title, "Novel")
            self.assertEqual(docs[0].title, "Chapter")
            self.assertIn("<p>Line one</p>", docs[0].content_html)
            self.assertEqual(store.list_branches("d1")[0].name, "alt")
            self.assertEqual(store.get_template_by_type("scene").name, "Scene")
            self.assertEqual(store.active_account().email, "writer@example.com")

    def test_import_runs_once(self):
        with _temp_dir() as tmp:
            legacy_path = tmp / "redcord.db"
            _legacy_db(legacy_path)
            store = SQLiteStore(tmp / "redcord_08.db")
            store.initialize()

            importer = Legacy07Importer(store, legacy_path, tmp / "backups")
            importer.import_once()
            second = importer.import_once()

            self.assertTrue(second.skipped)


if __name__ == "__main__":
    unittest.main()
