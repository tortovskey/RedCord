from __future__ import annotations

import shutil
import zipfile
from datetime import datetime
from pathlib import Path

from redcord.app.config import get_settings
from redcord.self_healing.event_log import SystemEventLog


class BackupService:
    """Creates compact local backups of user data."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.log = SystemEventLog()

    def create_backup(self, reason: str = "manual") -> Path:
        backup_root = self.settings.data_dir / "backups"
        backup_root.mkdir(parents=True, exist_ok=True)
        backup_path = backup_root / f"redcord_backup_{datetime.now():%Y-%m-%d_%H-%M-%S}.zip"
        with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for base in [self.settings.data_dir, self.settings.commit_dir]:
                if not base.exists():
                    continue
                for path in base.rglob("*"):
                    if path.is_file() and "backups" not in path.parts:
                        try:
                            zf.write(path, path.relative_to(self.settings.app_dir))
                        except ValueError:
                            zf.write(path, path.name)
            env_path = self.settings.app_dir / ".env"
            if env_path.exists():
                zf.write(env_path, ".env")
        self.log.write("INFO", "backup", "Backup created", path=str(backup_path), reason=reason)
        return backup_path

    def cleanup_old_backups(self, keep: int = 10) -> int:
        backup_root = self.settings.data_dir / "backups"
        if not backup_root.exists():
            return 0
        backups = sorted(backup_root.glob("redcord_backup_*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
        removed = 0
        for backup in backups[keep:]:
            backup.unlink(missing_ok=True)
            removed += 1
        return removed
