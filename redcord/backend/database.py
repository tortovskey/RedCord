from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


DATABASE_URL = os.getenv("REDCORD_BACKEND_DATABASE_URL", "postgresql+psycopg://redcord:redcord@localhost:5432/redcord")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def create_schema() -> None:
    Base.metadata.create_all(engine)
