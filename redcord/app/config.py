from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


SOURCE_ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2])).resolve()
APP_DIR = Path(sys.executable).resolve().parent if _is_frozen() else SOURCE_ROOT

# Load external .env first. In EXE mode this is next to RedCord.exe.
load_dotenv(APP_DIR / ".env")
# In development mode this is the same path; in bundled mode this is only a fallback.
load_dotenv(SOURCE_ROOT / ".env", override=False)


@dataclass(frozen=True)
class Settings:
    """Runtime settings loaded from .env or generated local defaults."""

    database_url: str
    app_env: str
    log_level: str
    default_theme: str
    app_dir: Path
    data_dir: Path
    commit_dir: Path
    assets_dir: Path
    settings_file: Path
    log_file: Path
    client_db_file: Path
    uses_local_sqlite: bool


def _path_from_env(name: str, default: Path) -> Path:
    raw = os.getenv(name, "").strip()
    path = Path(raw) if raw else default
    if not path.is_absolute():
        path = APP_DIR / path
    return path


def _build_database_url(data_dir: Path) -> tuple[str, bool]:
    raw = os.getenv("DATABASE_URL", "").strip()
    if raw:
        return raw, False

    # EXE-friendly fallback: local SQLite database in the data folder.
    # PostgreSQL is still supported through DATABASE_URL.
    sqlite_path = data_dir / "redcord_08.db"
    return f"sqlite:///{sqlite_path.as_posix()}", True


def get_settings() -> Settings:
    data_dir = _path_from_env("DATA_DIR", APP_DIR / "data")
    commit_dir = _path_from_env("COMMIT_DIR", APP_DIR / "commits")
    assets_dir_default = (SOURCE_ROOT / "redcord" / "assets") if _is_frozen() else (APP_DIR / "redcord" / "assets")
    assets_dir = _path_from_env("ASSETS_DIR", assets_dir_default)
    database_url, uses_local_sqlite = _build_database_url(data_dir)

    return Settings(
        database_url=database_url,
        app_env=os.getenv("APP_ENV", "development"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        default_theme=os.getenv("REDCORD_THEME", "dark_crimson"),
        app_dir=APP_DIR,
        data_dir=data_dir,
        commit_dir=commit_dir,
        assets_dir=assets_dir,
        settings_file=data_dir / "settings.json",
        log_file=data_dir / "redcord.log",
        client_db_file=data_dir / "redcord_08.db",
        uses_local_sqlite=uses_local_sqlite,
    )
