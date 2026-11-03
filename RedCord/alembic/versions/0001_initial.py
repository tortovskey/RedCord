"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-04-25
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("projects",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(255), unique=True),
        sa.Column("description", sa.Text),
        sa.Column("created_at", sa.DateTime),
        sa.Column("updated_at", sa.DateTime),
    )
    op.create_table("documents",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id")),
        sa.Column("title", sa.String(255)),
        sa.Column("document_type", sa.String(50)),
        sa.Column("content", sa.Text),
        sa.Column("content_hash", sa.String(128)),
        sa.Column("status", sa.String(50)),
        sa.Column("tags", sa.Text),
        sa.Column("created_at", sa.DateTime),
        sa.Column("updated_at", sa.DateTime),
        sa.Column("deleted_at", sa.DateTime, nullable=True),
    )
    op.create_table("document_versions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("document_id", sa.Integer, sa.ForeignKey("documents.id")),
        sa.Column("version_number", sa.Integer),
        sa.Column("commit_message", sa.String(255)),
        sa.Column("content_snapshot", sa.Text),
        sa.Column("content_hash", sa.String(128)),
        sa.Column("diff_text", sa.Text),
        sa.Column("is_stable", sa.Boolean),
        sa.Column("created_at", sa.DateTime),
    )
    op.create_table("concepts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id")),
        sa.Column("title", sa.String(255)),
        sa.Column("body", sa.Text),
        sa.Column("status", sa.String(50)),
        sa.Column("tags", sa.Text),
        sa.Column("linked_document_id", sa.Integer, sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("created_at", sa.DateTime),
        sa.Column("updated_at", sa.DateTime),
    )
    op.create_table("templates",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(100), unique=True),
        sa.Column("document_type", sa.String(50)),
        sa.Column("body", sa.Text),
        sa.Column("created_at", sa.DateTime),
    )
    op.create_table("autosaves",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("document_id", sa.Integer, sa.ForeignKey("documents.id")),
        sa.Column("content_snapshot", sa.Text),
        sa.Column("content_hash", sa.String(128)),
        sa.Column("created_at", sa.DateTime),
        sa.Column("recovered", sa.Boolean),
        sa.Column("recovered_at", sa.DateTime, nullable=True),
    )
    op.create_table("backups",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id")),
        sa.Column("path", sa.Text),
        sa.Column("backup_type", sa.String(50)),
        sa.Column("created_at", sa.DateTime),
        sa.Column("verified", sa.Boolean),
        sa.Column("notes", sa.Text),
    )
    op.create_table("recovery_events",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("project_id", sa.Integer, sa.ForeignKey("projects.id")),
        sa.Column("document_id", sa.Integer, sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("event_type", sa.String(100)),
        sa.Column("message", sa.Text),
        sa.Column("source", sa.String(100)),
        sa.Column("created_at", sa.DateTime),
    )
    op.create_table("ai_requests",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("document_id", sa.Integer, sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("prompt", sa.Text),
        sa.Column("response", sa.Text),
        sa.Column("provider", sa.String(100)),
        sa.Column("status", sa.String(50)),
        sa.Column("created_at", sa.DateTime),
    )
    op.create_table("app_settings",
        sa.Column("key", sa.String(120), primary_key=True),
        sa.Column("value", sa.Text),
    )


def downgrade() -> None:
    for table in [
        "app_settings", "ai_requests", "recovery_events", "backups", "autosaves",
        "templates", "concepts", "document_versions", "documents", "projects",
    ]:
        op.drop_table(table)
