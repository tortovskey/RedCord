from __future__ import annotations

import json
import shutil
import unittest
from pathlib import Path
from contextlib import contextmanager
from uuid import uuid4

from redcord.ai.ai_settings_service import AISettingsService
from redcord.ai.base import AISettings


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


class AISettingsTests(unittest.TestCase):
    def test_ai_settings_roundtrip(self):
        with _temp_dir() as raw:
            path = Path(raw) / "ai_settings.json"
            service = AISettingsService(path)

            value = AISettings(
                provider="openai_compatible",
                api_key="secret",
                base_url="http://localhost:1234/v1",
                model="local-model",
                temperature=0.8,
                max_tokens=1600,
            )
            service.save(value)

            loaded = service.load()
            self.assertEqual(loaded.provider, "openai_compatible")
            self.assertEqual(loaded.api_key, "secret")
            self.assertEqual(loaded.base_url, "http://localhost:1234/v1")
            self.assertEqual(loaded.model, "local-model")
            self.assertEqual(loaded.temperature, 0.8)
            self.assertEqual(loaded.max_tokens, 1600)

            raw_json = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(raw_json["api_key"], "secret")

    def test_ai_settings_invalid_provider_falls_back_to_mock(self):
        with _temp_dir() as raw:
            path = Path(raw) / "ai_settings.json"
            path.write_text('{"provider": "unknown"}', encoding="utf-8")

            loaded = AISettingsService(path).load()

            self.assertEqual(loaded.provider, "mock")
