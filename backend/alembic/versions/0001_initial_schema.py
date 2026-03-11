"""Initial schema

Revision ID: 0001
Revises:
Create Date: 2026-03-11
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # sync_logs — no foreign keys, create first                           #
    # ------------------------------------------------------------------ #
    op.create_table(
        "sync_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("on24_event_id", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("records_synced", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
    )
    op.create_index("ix_sync_logs_entity_type", "sync_logs", ["entity_type"])
    op.create_index("ix_sync_logs_on24_event_id", "sync_logs", ["on24_event_id"])
    op.create_index("ix_sync_logs_status", "sync_logs", ["status"])

    # ------------------------------------------------------------------ #
    # events — no foreign keys                                            #
    # ------------------------------------------------------------------ #
    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("on24_event_id", sa.BigInteger(), nullable=False),
        sa.Column("client_id", sa.BigInteger(), nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("event_type", sa.String(100), nullable=True),
        sa.Column("content_type", sa.String(50), nullable=True),
        sa.Column("language", sa.String(10), nullable=True),
        sa.Column("timezone", sa.String(50), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "registration_required", sa.Boolean(), nullable=False, server_default="true"
        ),
        sa.Column("live_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("live_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archive_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archive_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("on24_created", sa.DateTime(timezone=True), nullable=True),
        sa.Column("on24_last_modified", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_registrants", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_attendees", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("live_attendees", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "on_demand_attendees", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("no_show_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("engagement_score", sa.Numeric(8, 2), nullable=True),
        sa.Column("audience_url", sa.Text(), nullable=True),
        sa.Column("report_url", sa.Text(), nullable=True),
        sa.Column("tags", postgresql.JSONB(), nullable=True),
        sa.Column("raw_json", postgresql.JSONB(), nullable=True),
        # TimestampMixin
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # SyncedMixin
        sa.Column(
            "synced_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_events_on24_event_id", "events", ["on24_event_id"], unique=True
    )
    op.create_index("ix_events_live_start", "events", ["live_start"])

    # ------------------------------------------------------------------ #
    # registrants — FK → events.on24_event_id                            #
    # ------------------------------------------------------------------ #
    op.create_table(
        "registrants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("on24_registrant_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "on24_event_id",
            sa.BigInteger(),
            sa.ForeignKey("events.on24_event_id"),
            nullable=False,
        ),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=True),
        sa.Column("last_name", sa.String(100), nullable=True),
        sa.Column("company", sa.String(255), nullable=True),
        sa.Column("job_title", sa.String(255), nullable=True),
        sa.Column("job_function", sa.String(100), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("state", sa.String(100), nullable=True),
        sa.Column("country", sa.String(100), nullable=True),
        sa.Column("zip_code", sa.String(20), nullable=True),
        sa.Column("work_phone", sa.String(100), nullable=True),
        sa.Column("company_industry", sa.String(100), nullable=True),
        sa.Column("company_size", sa.String(100), nullable=True),
        sa.Column("partner_ref", sa.String(100), nullable=True),
        sa.Column("registration_status", sa.String(30), nullable=True),
        sa.Column("registration_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_activity", sa.DateTime(timezone=True), nullable=True),
        sa.Column("utm_source", sa.String(255), nullable=True),
        sa.Column("utm_medium", sa.String(255), nullable=True),
        sa.Column("utm_campaign", sa.String(255), nullable=True),
        sa.Column("custom_fields", postgresql.JSONB(), nullable=True),
        sa.Column("raw_json", postgresql.JSONB(), nullable=True),
        # TimestampMixin
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # SyncedMixin
        sa.Column(
            "synced_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "on24_registrant_id", "on24_event_id", name="uq_registrant_event"
        ),
    )
    op.create_index(
        "ix_registrants_on24_registrant_id", "registrants", ["on24_registrant_id"]
    )
    op.create_index(
        "ix_registrants_on24_event_id", "registrants", ["on24_event_id"]
    )
    op.create_index("ix_registrants_email", "registrants", ["email"])

    # ------------------------------------------------------------------ #
    # attendees — FK → events.on24_event_id                              #
    # ------------------------------------------------------------------ #
    op.create_table(
        "attendees",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("on24_attendee_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "on24_event_id",
            sa.BigInteger(),
            sa.ForeignKey("events.on24_event_id"),
            nullable=False,
        ),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=True),
        sa.Column("last_name", sa.String(100), nullable=True),
        sa.Column("company", sa.String(255), nullable=True),
        sa.Column("join_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("leave_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("live_minutes", sa.Integer(), nullable=True),
        sa.Column("archive_minutes", sa.Integer(), nullable=True),
        sa.Column("cumulative_live_minutes", sa.Integer(), nullable=True),
        sa.Column("cumulative_archive_minutes", sa.Integer(), nullable=True),
        sa.Column("engagement_score", sa.Numeric(8, 2), nullable=True),
        sa.Column("asked_questions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "resources_downloaded", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("answered_polls", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("answered_surveys", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("launch_mode", sa.String(30), nullable=True),
        sa.Column("questions", postgresql.JSONB(), nullable=True),
        sa.Column("polls", postgresql.JSONB(), nullable=True),
        sa.Column("resources", postgresql.JSONB(), nullable=True),
        sa.Column("surveys", postgresql.JSONB(), nullable=True),
        sa.Column("call_to_actions", postgresql.JSONB(), nullable=True),
        sa.Column("raw_json", postgresql.JSONB(), nullable=True),
        # TimestampMixin
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # SyncedMixin
        sa.Column(
            "synced_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "on24_attendee_id", "on24_event_id", name="uq_attendee_event"
        ),
    )
    op.create_index(
        "ix_attendees_on24_attendee_id", "attendees", ["on24_attendee_id"]
    )
    op.create_index("ix_attendees_on24_event_id", "attendees", ["on24_event_id"])
    op.create_index("ix_attendees_email", "attendees", ["email"])

    # ------------------------------------------------------------------ #
    # poll_responses — FK → events.on24_event_id                         #
    # ------------------------------------------------------------------ #
    op.create_table(
        "poll_responses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "on24_event_id",
            sa.BigInteger(),
            sa.ForeignKey("events.on24_event_id"),
            nullable=False,
        ),
        sa.Column("poll_id", sa.BigInteger(), nullable=True),
        sa.Column("attendee_email", sa.String(255), nullable=False),
        sa.Column("question", sa.Text(), nullable=True),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_json", postgresql.JSONB(), nullable=True),
        # TimestampMixin
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # SyncedMixin
        sa.Column(
            "synced_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_poll_responses_on24_event_id", "poll_responses", ["on24_event_id"]
    )
    op.create_index(
        "ix_poll_responses_attendee_email", "poll_responses", ["attendee_email"]
    )

    # ------------------------------------------------------------------ #
    # survey_responses — FK → events.on24_event_id                       #
    # ------------------------------------------------------------------ #
    op.create_table(
        "survey_responses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "on24_event_id",
            sa.BigInteger(),
            sa.ForeignKey("events.on24_event_id"),
            nullable=False,
        ),
        sa.Column("survey_id", sa.BigInteger(), nullable=True),
        sa.Column("attendee_email", sa.String(255), nullable=False),
        sa.Column("question", sa.Text(), nullable=True),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_json", postgresql.JSONB(), nullable=True),
        # TimestampMixin
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # SyncedMixin
        sa.Column(
            "synced_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_survey_responses_on24_event_id", "survey_responses", ["on24_event_id"]
    )
    op.create_index(
        "ix_survey_responses_attendee_email", "survey_responses", ["attendee_email"]
    )

    # ------------------------------------------------------------------ #
    # viewing_sessions — FK → events.on24_event_id, attendees.id         #
    # ------------------------------------------------------------------ #
    op.create_table(
        "viewing_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "attendee_id",
            sa.Integer(),
            sa.ForeignKey("attendees.id"),
            nullable=True,
        ),
        sa.Column(
            "on24_event_id",
            sa.BigInteger(),
            sa.ForeignKey("events.on24_event_id"),
            nullable=False,
        ),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("session_type", sa.String(30), nullable=True),
        sa.Column("session_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("session_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("raw_json", postgresql.JSONB(), nullable=True),
        # TimestampMixin
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # SyncedMixin
        sa.Column(
            "synced_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_viewing_sessions_attendee_id", "viewing_sessions", ["attendee_id"]
    )
    op.create_index(
        "ix_viewing_sessions_on24_event_id", "viewing_sessions", ["on24_event_id"]
    )
    op.create_index("ix_viewing_sessions_email", "viewing_sessions", ["email"])

    # ------------------------------------------------------------------ #
    # resources_viewed — FK → events.on24_event_id                       #
    # ------------------------------------------------------------------ #
    op.create_table(
        "resources_viewed",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "on24_event_id",
            sa.BigInteger(),
            sa.ForeignKey("events.on24_event_id"),
            nullable=False,
        ),
        sa.Column("attendee_email", sa.String(255), nullable=False),
        sa.Column("resource_name", sa.Text(), nullable=True),
        sa.Column("resource_type", sa.String(50), nullable=True),
        sa.Column("viewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_json", postgresql.JSONB(), nullable=True),
        # TimestampMixin
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # SyncedMixin
        sa.Column(
            "synced_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_resources_viewed_on24_event_id", "resources_viewed", ["on24_event_id"]
    )
    op.create_index(
        "ix_resources_viewed_attendee_email", "resources_viewed", ["attendee_email"]
    )

    # ------------------------------------------------------------------ #
    # cta_clicks — FK → events.on24_event_id                             #
    # ------------------------------------------------------------------ #
    op.create_table(
        "cta_clicks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "on24_event_id",
            sa.BigInteger(),
            sa.ForeignKey("events.on24_event_id"),
            nullable=False,
        ),
        sa.Column("attendee_email", sa.String(255), nullable=False),
        sa.Column("cta_name", sa.String(500), nullable=True),
        sa.Column("cta_url", sa.Text(), nullable=True),
        sa.Column("clicked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("raw_json", postgresql.JSONB(), nullable=True),
        # TimestampMixin
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # SyncedMixin
        sa.Column(
            "synced_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_cta_clicks_on24_event_id", "cta_clicks", ["on24_event_id"]
    )
    op.create_index("ix_cta_clicks_attendee_email", "cta_clicks", ["attendee_email"])

    # ------------------------------------------------------------------ #
    # engagement_profiles — no foreign keys                               #
    # ------------------------------------------------------------------ #
    op.create_table(
        "engagement_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("company", sa.String(255), nullable=True),
        sa.Column(
            "total_events_attended", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("total_engagement_score", sa.Numeric(10, 2), nullable=True),
        sa.Column("last_event_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pep_data", postgresql.JSONB(), nullable=True),
        # TimestampMixin
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # SyncedMixin
        sa.Column(
            "synced_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_engagement_profiles_email", "engagement_profiles", ["email"], unique=True
    )
    op.create_index(
        "ix_engagement_profiles_company", "engagement_profiles", ["company"]
    )

    # ------------------------------------------------------------------ #
    # agent_audit_logs — no foreign keys                                  #
    # ------------------------------------------------------------------ #
    op.create_table(
        "agent_audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.String(100), nullable=False),
        sa.Column("agent_name", sa.String(50), nullable=False),
        sa.Column("tool_name", sa.String(100), nullable=False),
        sa.Column("tool_input", postgresql.JSONB(), nullable=True),
        sa.Column("tool_result", postgresql.JSONB(), nullable=True),
        sa.Column(
            "confirmed", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column("error", sa.Text(), nullable=True),
        # TimestampMixin
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_agent_audit_logs_session_id", "agent_audit_logs", ["session_id"]
    )


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_table("agent_audit_logs")
    op.drop_table("engagement_profiles")
    op.drop_table("cta_clicks")
    op.drop_table("resources_viewed")
    op.drop_table("viewing_sessions")
    op.drop_table("survey_responses")
    op.drop_table("poll_responses")
    op.drop_table("attendees")
    op.drop_table("registrants")
    op.drop_table("events")
    op.drop_table("sync_logs")
