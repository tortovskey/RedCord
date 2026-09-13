from __future__ import annotations

import logging
import time
from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

logger = logging.getLogger(__name__)

_engine: Engine | None = None
SessionLocal: sessionmaker[Session] | None = None


class Base(DeclarativeBase):
    pass


def init_engine(database_url: str) -> Engine:
    global _engine, SessionLocal
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    _engine = create_engine(database_url, pool_pre_ping=True, future=True, connect_args=connect_args)
    SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, expire_on_commit=False)
    return _engine


def get_engine() -> Engine:
    if _engine is None:
        raise RuntimeError("Database engine is not initialized")
    return _engine


def create_local_schema() -> None:
    """Create tables for local SQLite mode.

    PostgreSQL mode should normally use Alembic migrations.
    """
    if _engine is None:
        raise RuntimeError("Database engine is not initialized")

    from redcord.db import models  # noqa: F401

    Base.metadata.create_all(bind=_engine)


def get_session() -> Generator[Session, None, None]:
    if SessionLocal is None:
        raise RuntimeError("Database session factory is not initialized")
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def new_session() -> Session:
    if SessionLocal is None:
        raise RuntimeError("Database session factory is not initialized")
    return SessionLocal()


def check_database_connection(retries: int = 3, delay_seconds: float = 1.0) -> tuple[bool, str]:
    if _engine is None:
        return False, "Database engine is not initialized"

    last_error = ""
    for attempt in range(1, retries + 1):
        try:
            with _engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return True, "ok"
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            logger.warning("Database connection attempt %s/%s failed: %s", attempt, retries, exc)
            time.sleep(delay_seconds)

    return False, f"Не удалось подключиться к базе после {retries} попыток. Ошибка: {last_error}"
