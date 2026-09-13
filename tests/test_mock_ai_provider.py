from __future__ import annotations

import unittest

from redcord.ai.base import AISettings
from redcord.ai.mock_provider import MockAIProvider


class MockAIProviderTests(unittest.TestCase):
    def test_mock_provider_summarize_works_offline(self):
        provider = MockAIProvider()

        response = provider.generate(
            "summarize",
            "Герой вошел в комнату. Он увидел письмо. Дверь захлопнулась. Началась сцена.",
            AISettings(),
        )

        self.assertEqual(response.provider, "mock")
        self.assertEqual(response.title, "Краткое содержание")
        self.assertIn("Герой вошел", response.text)

    def test_mock_provider_has_required_writer_actions(self):
        provider = MockAIProvider()

        for action in ["improve_text", "fix_style", "vivid", "shorten", "expand", "chapter_plan", "beat_sheet"]:
            response = provider.generate(action, "Тестовый текст для сцены.", AISettings())
            self.assertTrue(response.text.strip())
            self.assertEqual(response.action, action)
