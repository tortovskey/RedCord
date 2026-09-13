from __future__ import annotations

from dataclasses import dataclass

from redcord.ai.ai_settings_service import AISettingsService
from redcord.ai.base import AIResponse
from redcord.ai.provider_factory import create_provider


@dataclass(frozen=True)
class AIEditResult:
    action: str
    title: str
    text: str


class AIEditorService:
    """Compatibility facade for the old AI editor API.

    The provider architecture lives in redcord.ai. This class keeps older
    callers working while routing requests through the configured provider.
    """

    def __init__(self, settings_service: AISettingsService | None = None) -> None:
        self.settings_service = settings_service or AISettingsService()

    def run_action(self, action: str, text: str) -> AIEditResult:
        settings = self.settings_service.load()
        provider = create_provider(settings)
        response = provider.generate(action, text, settings)
        return self._to_legacy(response)

    def improve_text(self, text: str) -> AIEditResult:
        return self.run_action("improve_text", text)

    def summarize(self, text: str) -> AIEditResult:
        return self.run_action("summarize", text)

    def expand_scene(self, text: str) -> AIEditResult:
        return self.run_action("scene_development", text)

    def find_contradictions(self, text: str) -> AIEditResult:
        return self.run_action("contradictions", text)

    def character_questions(self, text: str) -> AIEditResult:
        return self.run_action("character_questions", text)

    def title_ideas(self, text: str) -> AIEditResult:
        return self.run_action("chapter_title", text)

    def fix_dialogue(self, text: str) -> AIEditResult:
        return self.run_action("check_dialogues", text)

    def _to_legacy(self, response: AIResponse) -> AIEditResult:
        return AIEditResult(action=response.action, title=response.title, text=response.text)
