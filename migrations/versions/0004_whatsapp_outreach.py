"""Add tenant WhatsApp contact and scheduled DENTAI outreach."""

import os

import sqlalchemy as sa
from alembic import op

revision = "0004_whatsapp_outreach"
down_revision = "0003_ai_job_queue"
branch_labels = None
depends_on = None


def has_column(table: str, column: str) -> bool:
    return column in {item["name"] for item in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade():
    if os.getenv("MIGRATION_PLANE", "clinic") == "control":
        return
    if not has_column("patients", "whatsapp_phone"):
        op.add_column("patients", sa.Column("whatsapp_phone", sa.String(40)))
    status = sa.Enum(
        "QUEUED", "SCHEDULED", "SENDING", "SENT", "FAILED", "CANCELLED",
        name="whatsappoutreachstatus",
    )
    status.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "whatsapp_outreach",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("patient_id", sa.Uuid(), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("analysis_id", sa.Uuid(), sa.ForeignKey("ai_analyses.id"), nullable=False),
        sa.Column("finding_id", sa.Uuid(), sa.ForeignKey("dental_findings.id")),
        sa.Column("followup_id", sa.Uuid(), sa.ForeignKey("followups.id")),
        sa.Column("tooth_fdi", sa.String(20), nullable=False),
        sa.Column("finding_type", sa.String(100), nullable=False),
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
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("failed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_whatsapp_outreach_patient_id", "whatsapp_outreach", ["patient_id"])
    op.create_index("ix_whatsapp_outreach_due", "whatsapp_outreach", ["status", "scheduled_send_at", "retry_at"])


def downgrade():
    if os.getenv("MIGRATION_PLANE", "clinic") == "control":
        return
    op.drop_index("ix_whatsapp_outreach_due", table_name="whatsapp_outreach")
    op.drop_index("ix_whatsapp_outreach_patient_id", table_name="whatsapp_outreach")
    op.drop_table("whatsapp_outreach")
    sa.Enum(name="whatsappoutreachstatus").drop(op.get_bind(), checkfirst=True)
    if has_column("patients", "whatsapp_phone"):
        op.drop_column("patients", "whatsapp_phone")
