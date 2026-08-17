"""Add tenant WhatsApp contact and scheduled DENTAI outreach."""

import os

import sqlalchemy as sa
from alembic import op

revision = "0004_whatsapp_outreach"
down_revision = "0003_ai_job_queue"
branch_labels = None
depends_on = None


STATUS_VALUES = (
    "QUEUED",
    "SCHEDULED",
    "CLAIMED",
    "SENDING",
    "SEND_UNKNOWN",
    "SENT",
    "FAILED",
    "CANCELLED",
)


def inspector():
    return sa.inspect(op.get_bind())


def has_table(table: str) -> bool:
    return table in inspector().get_table_names()


def has_column(table: str, column: str) -> bool:
    return has_table(table) and column in {item["name"] for item in inspector().get_columns(table)}


def has_index(table: str, index: str) -> bool:
    return has_table(table) and index in {item["name"] for item in inspector().get_indexes(table)}


def ensure_postgres_status_values() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    for value in ("CLAIMED", "SEND_UNKNOWN"):
        op.execute(
            sa.text(
                f"ALTER TYPE whatsappoutreachstatus ADD VALUE IF NOT EXISTS '{value}'"
            )
        )


def outreach_status_enum() -> sa.Enum:
    return sa.Enum(*STATUS_VALUES, name="whatsappoutreachstatus")


def create_outreach_table() -> None:
    status = outreach_status_enum()
    status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "whatsapp_outreach",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("patient_id", sa.Uuid(), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("analysis_id", sa.Uuid(), sa.ForeignKey("ai_analyses.id"), nullable=False),
        sa.Column("finding_id", sa.Uuid(), sa.ForeignKey("dental_findings.id")),
        sa.Column("source_finding_ids", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("followup_id", sa.Uuid(), sa.ForeignKey("followups.id")),
        sa.Column("tooth_fdi", sa.String(20), nullable=False),
        sa.Column("finding_type", sa.String(500), nullable=False),
        sa.Column("recommended_window", sa.String(80), nullable=False),
        sa.Column("target_followup_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scheduled_send_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("language", sa.String(16), nullable=False, server_default="hy-AM"),
        sa.Column("status", status, nullable=False, server_default="SCHEDULED"),
        sa.Column("provider_message_id", sa.String(200)),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("retry_at", sa.DateTime(timezone=True)),
        sa.Column("timing_reason", sa.Text(), nullable=False),
        sa.Column("timing_policy_rule_id", sa.String(500), nullable=False),
        sa.Column("timing_policy_version", sa.String(40), nullable=False),
        sa.Column("clinic_timezone", sa.String(80), nullable=False),
        sa.Column("include_image", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("safe_error", sa.String(120)),
        sa.Column("worker_id", sa.String(160)),
        sa.Column("claimed_at", sa.DateTime(timezone=True)),
        sa.Column("dispatch_started_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("failed_at", sa.DateTime(timezone=True)),
    )


def ensure_outreach_columns() -> None:
    if not has_column("whatsapp_outreach", "source_finding_ids"):
        op.add_column(
            "whatsapp_outreach",
            sa.Column("source_finding_ids", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        )
    if not has_column("whatsapp_outreach", "dispatch_started_at"):
        op.add_column(
            "whatsapp_outreach",
            sa.Column("dispatch_started_at", sa.DateTime(timezone=True)),
        )


def upgrade():
    if os.getenv("MIGRATION_PLANE", "clinic") == "control":
        return
    if not has_column("patients", "whatsapp_phone"):
        op.add_column("patients", sa.Column("whatsapp_phone", sa.String(40)))

    if not has_table("whatsapp_outreach"):
        create_outreach_table()
    else:
        ensure_postgres_status_values()
        ensure_outreach_columns()

    if not has_index("whatsapp_outreach", "ix_whatsapp_outreach_patient_id"):
        op.create_index("ix_whatsapp_outreach_patient_id", "whatsapp_outreach", ["patient_id"])
    if not has_index("whatsapp_outreach", "ix_whatsapp_outreach_due"):
        op.create_index(
            "ix_whatsapp_outreach_due",
            "whatsapp_outreach",
            ["status", "scheduled_send_at", "retry_at"],
        )


def downgrade():
    if os.getenv("MIGRATION_PLANE", "clinic") == "control":
        return
    if has_table("whatsapp_outreach"):
        if has_index("whatsapp_outreach", "ix_whatsapp_outreach_due"):
            op.drop_index("ix_whatsapp_outreach_due", table_name="whatsapp_outreach")
        if has_index("whatsapp_outreach", "ix_whatsapp_outreach_patient_id"):
            op.drop_index("ix_whatsapp_outreach_patient_id", table_name="whatsapp_outreach")
        op.drop_table("whatsapp_outreach")
    outreach_status_enum().drop(op.get_bind(), checkfirst=True)
    if has_column("patients", "whatsapp_phone"):
        op.drop_column("patients", "whatsapp_phone")
