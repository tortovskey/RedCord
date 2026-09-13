"""initial RedCord schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-04-25
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from redcord.db.types import GUID

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_index("ix_projects_title", "projects", ["title"])

    op.create_table(
        "templates",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("type", sa.String(length=80), nullable=False),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
    )
    op.create_index("ix_templates_type", "templates", ["type"], unique=True)

    op.create_table(
        "documents",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("project_id", GUID(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("type", sa.String(length=80), nullable=False),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column("tags", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("category", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_index("ix_documents_project_id", "documents", ["project_id"])
    op.create_index("ix_documents_title", "documents", ["title"])
    op.create_index("ix_documents_type", "documents", ["type"])
    op.create_index("ix_documents_tags", "documents", ["tags"])
    op.create_index("ix_documents_category", "documents", ["category"])
    op.create_index("ix_documents_search_basic", "documents", ["title", "tags", "category"])

    op.create_table(
        "commits",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("document_id", GUID(), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("message", sa.String(length=500), nullable=False),
        sa.Column("content_snapshot", sa.Text(), nullable=False, server_default=""),
        sa.Column("commit_file_path", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_index("ix_commits_document_id", "commits", ["document_id"])
    op.create_index("ix_commits_created_at", "commits", ["created_at"])

    op.create_table(
        "concepts",
        sa.Column("id", GUID(), primary_key=True),
        sa.Column("project_id", GUID(), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=80), nullable=False, server_default="Идея"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_index("ix_concepts_project_id", "concepts", ["project_id"])
    op.create_index("ix_concepts_title", "concepts", ["title"])
    op.create_index("ix_concepts_status", "concepts", ["status"])


def downgrade() -> None:
    op.drop_table("concepts")
    op.drop_table("commits")
    op.drop_table("documents")
    op.drop_table("templates")
    op.drop_table("projects")
