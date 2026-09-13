from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import text

from redcord.app.config import get_settings
from redcord.db.database import get_engine
from redcord.self_healing.outbox import OutboxStore


@dataclass
class HealthStatus:
    name: str
    ok: bool
    message: str


class HealthCheckService:
    def __init__(self) -> None:
        self.settings = get_settings()

    def run_all(self) -> list[HealthStatus]:
        return [
            self.check_database(),
            self.check_data_dir(),
            self.check_commit_dir(),
            self.check_settings_json(),
            self.check_outbox(),
        ]

    def check_database(self) -> HealthStatus:
        try:
            with get_engine().connect() as connection:
                connection.execute(text("SELECT 1"))
            return HealthStatus("Database", True, "Подключение работает")
        except Exception as exc:
            return HealthStatus("Database", False, str(exc))

    def check_data_dir(self) -> HealthStatus:
        path = self.settings.data_dir
        return HealthStatus("Data directory", path.exists() and path.is_dir(), str(path))

    def check_commit_dir(self) -> HealthStatus:
        path = self.settings.commit_dir
        return HealthStatus("Commits directory", path.exists() and path.is_dir(), str(path))

    def check_settings_json(self) -> HealthStatus:
        path = self.settings.settings_file
        if not path.exists():
            return HealthStatus("Settings", True, "settings.json ещё не создан, будет создан автоматически")
        try:
            json.loads(path.read_text(encoding="utf-8"))
            return HealthStatus("Settings", True, "settings.json валиден")
        except Exception as exc:
            return HealthStatus("Settings", False, f"settings.json повреждён: {exc}")

    def check_outbox(self) -> HealthStatus:
        pending = len(OutboxStore().pending())
        return HealthStatus("Outbox", True, f"Ожидают синхронизации: {pending}")
