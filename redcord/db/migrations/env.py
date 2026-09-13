from __future__ import annotations

from logging.config import fileConfig
from pathlib import Path
import sys

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

ROOT_DIR = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT_DIR))
load_dotenv(ROOT_DIR / ".env")

from redcord.app.config import get_settings  # noqa: E402
from redcord.db.database import Base  # noqa: E402
from redcord.db import models  # noqa: F401,E402

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    url = get_settings().database_url
    if not url:
        raise RuntimeError("DATABASE_URL is empty. Create .env from .env.example.")
    return url


def run_migrations_offline() -> None:
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(configuration, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
