from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from redcord.app.config import get_settings


@dataclass
class SystemEvent:
    level: str
    source: str
    message: str
    created_at: str
    details: dict[str, Any]


class SystemEventLog:
    """Small JSONL event log for desktop self-healing diagnostics."""

    def __init__(self) -> None:
        settings = get_settings()
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        self.path = settings.data_dir / "system_events.jsonl"

    def write(self, level: str, source: str, message: str, **details: Any) -> None:
        event = SystemEvent(
            level=level,
            source=source,
            message=message,
            created_at=datetime.now().isoformat(timespec="seconds"),
            details=details,
        )
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")

    def tail(self, limit: int = 50) -> list[SystemEvent]:
        if not self.path.exists():
            return []
        lines = self.path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]
        events: list[SystemEvent] = []
        for line in lines:
            try:
                data = json.loads(line)
                events.append(SystemEvent(**data))
            except Exception:
                continue
        return events
