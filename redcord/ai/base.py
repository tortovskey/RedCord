from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


SUPPORTED_PROVIDERS = ("mock", "openai_compatible")


@dataclass
class AISettings:
    provider: str = "mock"
    api_key: str = ""
    base_url: str = ""
    model: str = ""
    temperature: float = 0.7
    max_tokens: int = 1200


@dataclass(frozen=True)
class AIResponse:
    action: str
    title: str
    text: str
    provider: str


class AIProviderError(RuntimeError):
    """Safe provider error for UI display."""


class AIProvider(Protocol):
    name: str

    def generate(self, action: str, text: str, settings: AISettings) -> AIResponse:
        """Generate an editorial response."""

    def test_connection(self, settings: AISettings) -> str:
        """Return a short human readable connection status."""
