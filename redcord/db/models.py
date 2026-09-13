from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from redcord.db.database import Base
from redcord.db.types import GUID


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)

    documents: Mapped[list["Document"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", passive_deletes=True
    )
    concepts: Mapped[list["Concept"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", passive_deletes=True
    )


class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    tags: Mapped[str] = mapped_column(String(500), default="", nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(120), default="", nullable=False, index=True)

    project: Mapped[Project] = relationship(back_populates="documents")
    commits: Mapped[list["Commit"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", passive_deletes=True
    )


class Template(Base):
    __tablename__ = "templates"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    content: Mapped[str] = mapped_column(Text, default="", nullable=False)


class Commit(Base):
    __tablename__ = "commits"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    content_snapshot: Mapped[str] = mapped_column(Text, default="", nullable=False)
    commit_file_path: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    document: Mapped[Document] = relationship(back_populates="commits")


class Concept(Base, TimestampMixin):
    __tablename__ = "concepts"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(80), default="Идея", nullable=False, index=True)

    project: Mapped[Project] = relationship(back_populates="concepts")


Index("ix_documents_search_basic", Document.title, Document.tags, Document.category)
