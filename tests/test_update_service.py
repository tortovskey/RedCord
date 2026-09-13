from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
import unittest
from uuid import uuid4

from redcord.services.update_service import UpdateErrorForUser, UpdateService


TMP_ROOT = Path(__file__).resolve().parents[1] / ".redcord_test_tmp"


@contextmanager
def _temp_dir():
    TMP_ROOT.mkdir(exist_ok=True)
    path = TMP_ROOT / f"case_{uuid4().hex}"
    path.mkdir()
    try:
        yield str(path)
    finally:
        shutil.rmtree(path, ignore_errors=True)


def _make_archive(tmp_path, version: str | None = "0.7.9"):
    source = tmp_path / "source"
    package = source / "redcord"
    package.mkdir(parents=True)
    if version is None:
        (package / "__init__.py").write_text("", encoding="utf-8")
    else:
        (package / "__init__.py").write_text(f'__version__ = "{version}"\n', encoding="utf-8")
    (source / "README.md").write_text("# RedCord test update\n", encoding="utf-8")

    archive = tmp_path / "update.zip"
    with zipfile.ZipFile(archive, "w") as zip_file:
        for path in source.rglob("*"):
            if path.is_file():
                zip_file.write(path, path.relative_to(source))
    return archive


def _make_manifest_archive(tmp_path):
    source = tmp_path / "manifest_source"
    package = source / "redcord"
    package.mkdir(parents=True)
    init_file = package / "__init__.py"
    readme = source / "README.md"
    init_file.write_text('__version__ = "0.8.3"\n', encoding="utf-8")
    readme.write_text("# RedCord 0.8.3\n", encoding="utf-8")
    manifest = {
        "version": "0.8.3",
        "min_version": "0.8.2",
        "migration_required": True,
        "files": [
            {
                "path": "redcord/__init__.py",
                "sha256": hashlib.sha256(init_file.read_bytes()).hexdigest(),
            },
            "README.md",
        ],
        "sha256": {"README.md": hashlib.sha256(readme.read_bytes()).hexdigest()},
    }
    (source / "redcord_update_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    archive = tmp_path / "manifest_update.zip"
    with zipfile.ZipFile(archive, "w") as zip_file:
        for path in source.rglob("*"):
            if path.is_file():
                zip_file.write(path, path.relative_to(source))
    return archive


def _service_for_target(target):
    service = UpdateService()
    service.settings = SimpleNamespace(
        app_dir=target,
        data_dir=target / "data",
        commit_dir=target / "commits",
    )
    return service


class UpdateServiceTests(unittest.TestCase):
    def test_update_service_preserves_user_data_and_writes_log(self):
        with _temp_dir() as raw:
            tmp_path = Path(raw)
            target = tmp_path / "app"
            (target / "redcord").mkdir(parents=True)
            (target / "redcord" / "__init__.py").write_text('__version__ = "0.7.3"\n', encoding="utf-8")
            (target / "data").mkdir()
            (target / "commits").mkdir()
            (target / "data" / "settings.json").write_text("{}", encoding="utf-8")
            (target / "commits" / "keep.md").write_text("keep", encoding="utf-8")
            (target / ".env").write_text("SECRET=1", encoding="utf-8")

            result = _service_for_target(target).apply_update_from_archive(_make_archive(tmp_path))

            self.assertEqual(result.mode, "direct")
            self.assertEqual(result.detected_version, "0.7.9")
            self.assertEqual((target / "data" / "settings.json").read_text(encoding="utf-8"), "{}")
            self.assertEqual((target / "commits" / "keep.md").read_text(encoding="utf-8"), "keep")
            self.assertEqual((target / ".env").read_text(encoding="utf-8"), "SECRET=1")
            self.assertTrue((target / "data" / "update.log").exists())
            self.assertTrue((target / "data" / "last_update.json").exists())

    def test_update_service_rejects_archive_without_version(self):
        with _temp_dir() as raw:
            tmp_path = Path(raw)
            target = tmp_path / "app"
            target.mkdir()
            (target / "data").mkdir()
            (target / "commits").mkdir()

            with self.assertRaises(UpdateErrorForUser):
                _service_for_target(target).apply_update_from_archive(_make_archive(tmp_path, version=None))

    def test_update_service_validates_manifest_archive(self):
        with _temp_dir() as raw:
            tmp_path = Path(raw)
            target = tmp_path / "app"
            (target / "redcord").mkdir(parents=True)
            (target / "redcord" / "__init__.py").write_text('__version__ = "0.8.0"\n', encoding="utf-8")
            (target / "data").mkdir()
            (target / "commits").mkdir()

            result = _service_for_target(target).apply_update_from_archive(_make_manifest_archive(tmp_path))
            manifest = json.loads((target / "data" / "last_update.json").read_text(encoding="utf-8"))

            self.assertEqual(result.detected_version, "0.8.3")
            self.assertTrue(result.migration_required)
            self.assertTrue(manifest["migration_required"])
            self.assertEqual(manifest["archive_manifest"]["version"], "0.8.3")
