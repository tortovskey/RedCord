from __future__ import annotations

import json
from pathlib import Path

from redcord.app.config import get_settings
from redcord.self_healing.backup_service import BackupService
from redcord.self_healing.event_log import SystemEventLog
from redcord.self_healing.health_checks import HealthCheckService, HealthStatus


class RecoveryManager:
    """Basic self-healing manager for desktop/offline mode."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.log = SystemEventLog()
        self.health = HealthCheckService()
        self.backup = BackupService()

    def ensure_runtime_state(self) -> list[str]:
        actions: list[str] = []
        for path in [self.settings.data_dir, self.settings.commit_dir, self.settings.assets_dir]:
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)
                actions.append(f"Создана папка: {path}")
        if not self.settings.settings_file.exists():
            self.settings.settings_file.write_text(
                json.dumps({"profile_name": "Автор", "theme": self.settings.default_theme, "autosave_enabled": True}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            actions.append("Создан settings.json")
        if actions:
            self.log.write("INFO", "recovery", "Runtime state repaired", actions=actions)
        return actions

    def run_recovery(self) -> tuple[list[HealthStatus], list[str]]:
        actions = self.ensure_runtime_state()
        statuses = self.health.run_all()
        if any(not status.ok for status in statuses):
            backup_path = self.backup.create_backup(reason="pre-recovery")
            actions.append(f"Создан safety backup: {backup_path}")
            self.log.write("WARNING", "recovery", "Recovery detected unhealthy statuses")
        else:
            self.log.write("INFO", "recovery", "Health checks passed")
        return statuses, actions
