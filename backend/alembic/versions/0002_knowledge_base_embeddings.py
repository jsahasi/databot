"""Add knowledge_base_articles table with embeddings

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-13
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "knowledge_base_articles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("article_id", sa.String(64), nullable=False),
        sa.Column("title", sa.Text(), nullable=False, server_default=""),
        sa.Column("url", sa.Text(), nullable=False, server_default=""),
        sa.Column("chunk_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", postgresql.ARRAY(sa.Float(precision=24)), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_kb_article_id", "knowledge_base_articles", ["article_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_kb_article_id", table_name="knowledge_base_articles")
    op.drop_table("knowledge_base_articles")
