from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from redcord.ai.base import SUPPORTED_PROVIDERS, AISettings
from redcord.app.config import get_settings


class AISettingsService:
    def __init__(self, path: str | Path | None = None) -> None:
        if path is not None:
            self.path = Path(path)
        else:
            settings = get_settings()
            settings.data_dir.mkdir(parents=True, exist_ok=True)
            self.path = settings.data_dir / "ai_settings.json"

    def load(self) -> AISettings:
        if not self.path.exists():
            value = AISettings()
            self.save(value)
            return value
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return self._from_mapping(data)
        except Exception:
            value = AISettings()
            self.save(value)
            return value

    def save(self, value: AISettings) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        sanitized = self._sanitize(value)
        self.path.write_text(
            json.dumps(asdict(sanitized), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _from_mapping(self, data: dict[str, object]) -> AISettings:
        return self._sanitize(
            AISettings(
                provider=str(data.get("provider") or "mock"),
                api_key=str(data.get("api_key") or ""),
                base_url=str(data.get("base_url") or ""),
                model=str(data.get("model") or ""),
                temperature=float(data.get("temperature", 0.7)),
                max_tokens=int(data.get("max_tokens", 1200)),
            )
        )

    def _sanitize(self, value: AISettings) -> AISettings:
        provider = value.provider if value.provider in SUPPORTED_PROVIDERS else "mock"
        temperature = min(2.0, max(0.0, float(value.temperature)))
        max_tokens = min(64000, max(128, int(value.max_tokens)))
        return AISettings(
            provider=provider,
            api_key=value.api_key,
            base_url=value.base_url.strip(),
            model=value.model.strip(),
            temperature=temperature,
            max_tokens=max_tokens,
        )
