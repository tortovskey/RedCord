from abc import ABC, abstractmethod


class BaseAssistantProvider(ABC):
    @abstractmethod
    def complete(self, prompt: str, content: str) -> str:
        raise NotImplementedError


class MockAssistantProvider(BaseAssistantProvider):
    def complete(self, prompt: str, content: str) -> str:
        trimmed = content.strip()[:200]
        return (
            f"[Mock AI] Action: {prompt}\n"
            "1) Усильте конфликт в середине текста.\n"
            "2) Добавьте сенсорные детали окружения.\n"
            "3) Уточните мотивацию персонажа в 1-2 абзацах.\n"
            f"Краткий анализ исходника: {trimmed}"
        )


class AIAssistantService:
    def __init__(self, provider: BaseAssistantProvider | None = None):
        self.provider = provider or MockAssistantProvider()

    def improve_text(self, content: str) -> str:
        return self.provider.complete("Improve text", content)

    def suggest_ideas(self, content: str) -> str:
        return self.provider.complete("Suggest ideas", content)

    def find_contradictions(self, content: str) -> str:
        return self.provider.complete("Find contradictions", content)

    def summarize(self, content: str) -> str:
        return self.provider.complete("Summarize", content)
