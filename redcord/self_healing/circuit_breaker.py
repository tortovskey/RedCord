from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from redcord.app.config import get_settings


class CircuitOpenError(RuntimeError):
    pass


@dataclass
class CircuitState:
    name: str
    failure_count: int = 0
    opened_at: float | None = None
    last_error: str = ""


class CircuitBreaker:
    """Persistent circuit breaker for external dependencies, e.g. AI/backends."""

    def __init__(self, name: str, failure_threshold: int = 3, reset_timeout_seconds: int = 60) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.reset_timeout_seconds = reset_timeout_seconds
        settings = get_settings()
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        self.path = settings.data_dir / "circuit_breakers.json"
        self.state = self._load()

    def is_open(self) -> bool:
        if self.state.opened_at is None:
            return False
        if time.time() - self.state.opened_at >= self.reset_timeout_seconds:
            self.reset()
            return False
        return True

    def before_call(self) -> None:
        if self.is_open():
            raise CircuitOpenError(f"Circuit '{self.name}' is open")

    def record_success(self) -> None:
        self.state.failure_count = 0
        self.state.opened_at = None
        self.state.last_error = ""
        self._save()

    def record_failure(self, error: BaseException | str) -> None:
        self.state.failure_count += 1
        self.state.last_error = str(error)
        if self.state.failure_count >= self.failure_threshold:
            self.state.opened_at = time.time()
        self._save()

    def reset(self) -> None:
        self.state = CircuitState(name=self.name)
        self._save()

    def _load_all(self) -> dict[str, dict]:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _load(self) -> CircuitState:
        data = self._load_all().get(self.name)
        if not data:
            return CircuitState(name=self.name)
        return CircuitState(**data)

    def _save(self) -> None:
        data = self._load_all()
        data[self.name] = asdict(self.state)
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
