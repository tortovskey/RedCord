from __future__ import annotations

import json
import urllib.error
import urllib.request

from redcord.ai.base import AIProviderError, AIResponse, AISettings
from redcord.ai.prompts import get_prompt


class OpenAICompatibleProvider:
    name = "openai_compatible"

    def generate(self, action: str, text: str, settings: AISettings) -> AIResponse:
        if not settings.base_url:
            raise AIProviderError("Укажите Base URL для OpenAI-compatible provider.")
        if not settings.model:
            raise AIProviderError("Укажите Model name для OpenAI-compatible provider.")

        prompt = get_prompt(action)
        url = settings.base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": settings.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Ты ИИ-агент RedCord для писателей. Отвечай по-русски, "
                        "практично, структурно и без лишней воды."
                    ),
                },
                {
                    "role": "user",
                    "content": f"{prompt.instruction}\n\nТекст:\n{text}",
                },
            ],
            "temperature": settings.temperature,
            "max_tokens": settings.max_tokens,
        }
        headers = {"Content-Type": "application/json"}
        if settings.api_key:
            headers["Authorization"] = f"Bearer {settings.api_key}"

        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=90) as response:  # noqa: S310
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            message = exc.read().decode("utf-8", errors="replace")[:500]
            raise AIProviderError(f"Endpoint вернул HTTP {exc.code}: {message}") from exc
        except urllib.error.URLError as exc:
            raise AIProviderError(f"Не удалось подключиться к endpoint: {exc.reason}") from exc
        except TimeoutError as exc:
            raise AIProviderError("Endpoint не ответил вовремя.") from exc

        try:
            data = json.loads(raw)
            content = data["choices"][0]["message"]["content"]
        except Exception as exc:  # noqa: BLE001
            raise AIProviderError("Endpoint вернул неожиданный формат ответа.") from exc

        return AIResponse(action=action, title=prompt.title, text=str(content).strip(), provider=self.name)

    def test_connection(self, settings: AISettings) -> str:
        response = self.generate("summarize", "Тестовое подключение RedCord.", settings)
        preview = response.text.replace("\n", " ")[:120]
        return f"Подключение работает. Ответ модели: {preview}"
