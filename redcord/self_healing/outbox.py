from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from redcord.app.config import get_settings
from redcord.self_healing.event_log import SystemEventLog


@dataclass
class OutboxEvent:
    id: str
    type: str
    payload: dict[str, Any]
    status: str
    created_at: str
    attempts: int = 0
    last_error: str = ""


class OutboxStore:
    """JSON-backed outbox for future sync/backend mode."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.settings.data_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.settings.data_dir / "outbox_events.json"
        self.log = SystemEventLog()

    def enqueue(self, event_type: str, payload: dict[str, Any]) -> OutboxEvent:
        events = self.list_events()
        event = OutboxEvent(
            id=str(uuid.uuid4()),
            type=event_type,
            payload=payload,
            status="pending",
            created_at=datetime.now().isoformat(timespec="seconds"),
        )
        events.append(event)
        self._write(events)
        self.log.write("INFO", "outbox", f"Outbox event queued: {event_type}", event_id=event.id)
        return event

    def list_events(self) -> list[OutboxEvent]:
        if not self.path.exists():
            return []
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            return [OutboxEvent(**item) for item in raw]
        except Exception:
            return []

    def pending(self) -> list[OutboxEvent]:
        return [event for event in self.list_events() if event.status == "pending"]

    def mark_done(self, event_id: str) -> None:
        events = self.list_events()
        for event in events:
            if event.id == event_id:
                event.status = "done"
        self._write(events)

    def mark_failed(self, event_id: str, error: str) -> None:
        events = self.list_events()
        for event in events:
            if event.id == event_id:
                event.attempts += 1
                event.last_error = error
                if event.attempts >= 3:
                    event.status = "failed"
        self._write(events)

    def _write(self, events: list[OutboxEvent]) -> None:
        self.path.write_text(
            json.dumps([asdict(event) for event in events], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
