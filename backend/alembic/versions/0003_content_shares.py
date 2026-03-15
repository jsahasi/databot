"""Add content_shares, share_recipients, share_comments tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-15
"""

from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "content_shares",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("content_html", sa.Text(), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("admin_id", sa.Integer(), nullable=False),
        sa.Column("admin_email", sa.String(255), nullable=False),
        sa.Column("session_id", sa.String(100), server_default=""),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "share_recipients",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "share_id",
            sa.String(36),
            sa.ForeignKey("content_shares.id"),
            nullable=False,
        ),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("token_hash", sa.String(128), nullable=False),
        sa.Column("approved", sa.Boolean(), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("viewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_share_recipients_share_id", "share_recipients", ["share_id"]
    )

    op.create_table(
        "share_comments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "share_id",
            sa.String(36),
            sa.ForeignKey("content_shares.id"),
            nullable=False,
        ),
        sa.Column("author_email", sa.String(255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_share_comments_share_id", "share_comments", ["share_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_share_comments_share_id", table_name="share_comments")
    op.drop_table("share_comments")
    op.drop_index("ix_share_recipients_share_id", table_name="share_recipients")
    op.drop_table("share_recipients")
    op.drop_table("content_shares")
