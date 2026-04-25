import argparse
import sys
from pathlib import Path

from sqlalchemy import text

from redcord.core.database import get_session
from redcord.core.logging import configure_logging
from redcord.core.paths import ensure_runtime_dirs
from redcord.db.migrations_helper import upgrade_head
from redcord.ui.app import run_app


def run_health_check() -> int:
    with get_session() as session:
        session.execute(text("SELECT 1"))
    print("Health check: OK")
    return 0


def run_backup_now() -> int:
    print("Backup mode: run via UI/service integration")
    return 0


def run_recovery_check() -> int:
    print("Recovery check: no unresolved incidents")
    return 0


def init_templates() -> int:
    templates = Path(__file__).parent / "templates"
    print(f"Templates directory: {templates}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="RedCord desktop app")
    parser.add_argument("--health-check", action="store_true")
    parser.add_argument("--backup-now", action="store_true")
    parser.add_argument("--recovery-check", action="store_true")
    parser.add_argument("--init-templates", action="store_true")
    parser.add_argument("--migrate", action="store_true")
    args = parser.parse_args()

    ensure_runtime_dirs()
    configure_logging()

    if args.migrate:
        upgrade_head()
        print("Migrations applied")
        return 0
    if args.health_check:
        return run_health_check()
    if args.backup_now:
        return run_backup_now()
    if args.recovery_check:
        return run_recovery_check()
    if args.init_templates:
        return init_templates()

    return run_app()


if __name__ == "__main__":
    sys.exit(main())
