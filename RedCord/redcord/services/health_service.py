from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from redcord.core.config import HealthStatus


class HealthService:
    def __init__(self, session: Session):
        self.session = session
        self.db_disabled_mock = False

    def set_db_disabled_mock(self, disabled: bool) -> None:
        self.db_disabled_mock = disabled

    def database_status(self) -> str:
        if self.db_disabled_mock:
            return "unhealthy (mock)"
        try:
            self.session.execute(text("SELECT 1"))
            return "healthy"
        except Exception:
            return "unhealthy"

    def build_health_status(self, autosave_active: bool, backup_last_run: str, integrity_ok: bool, watchdog_active: bool) -> HealthStatus:
        return HealthStatus(
            database=self.database_status(),
            autosave="active" if autosave_active else "inactive",
            backup_last_run=backup_last_run or "never",
            integrity="ok" if integrity_ok else "issues",
            ai_assistant="healthy/mock",
            watchdog="active" if watchdog_active else "inactive",
        )

    @staticmethod
    def now_str() -> str:
        return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
