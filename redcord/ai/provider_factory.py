from __future__ import annotations

from redcord.ai.base import AIProvider, AISettings
from redcord.ai.mock_provider import MockAIProvider
from redcord.ai.openai_compatible_provider import OpenAICompatibleProvider


def create_provider(settings: AISettings | str | None = None) -> AIProvider:
    provider_name = "mock"
    if isinstance(settings, AISettings):
        provider_name = settings.provider
    elif isinstance(settings, str):
        provider_name = settings

    if provider_name == "openai_compatible":
        return OpenAICompatibleProvider()
    return MockAIProvider()
