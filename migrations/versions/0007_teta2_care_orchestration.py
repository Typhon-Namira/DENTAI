"""Teta2 Care orchestration, conversations and appointments.

Revision ID: 0007_teta2_care_orchestration
Revises: 0006_radar_production
"""

import os

import sqlalchemy as sa
from alembic import op

revision = "0007_teta2_care_orchestration"
down_revision = "0006_radar_production"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if os.getenv("MIGRATION_PLANE", "clinic") == "control":
        return
    op.create_table(
        "clinic_care_settings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "branch_id",
            sa.Uuid(),
            sa.ForeignKey("branches.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("timezone", sa.String(80), nullable=False, server_default="Asia/Yerevan"),
        sa.Column("working_days", sa.JSON(), nullable=False),
        sa.Column("day_start", sa.String(5), nullable=False, server_default="09:00"),
        sa.Column("day_end", sa.String(5), nullable=False, server_default="18:00"),
        sa.Column("appointment_minutes", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("slot_interval_minutes", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("min_booking_notice_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("booking_horizon_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("buffer_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("preferred_times", sa.JSON(), nullable=False),
        sa.Column("blocked_windows", sa.JSON(), nullable=False),
        sa.Column("auto_followup_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "auto_outreach_after_review", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column("attach_tooth_image", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("default_language", sa.String(16), nullable=False, server_default="en"),
        sa.Column("booking_instructions", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_clinic_care_settings_branch_id", "clinic_care_settings", ["branch_id"])

    op.create_table(
        "care_plans",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("patient_id", sa.Uuid(), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column(
            "analysis_id",
            sa.Uuid(),
            sa.ForeignKey("ai_analyses.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("branch_id", sa.Uuid(), sa.ForeignKey("branches.id"), nullable=False),
        sa.Column("doctor_id", sa.Uuid(), sa.ForeignKey("users.id")),
        sa.Column("status", sa.String(40), nullable=False, server_default="READY_FOR_REVIEW"),
        sa.Column("language", sa.String(16), nullable=False, server_default="en"),
        sa.Column("summary", sa.Text()),
        sa.Column("activated_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    for name in ("patient_id", "analysis_id", "branch_id", "doctor_id", "status"):
        op.create_index(f"ix_care_plans_{name}", "care_plans", [name])

    op.create_table(
        "care_plan_items",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "care_plan_id",
            sa.Uuid(),
            sa.ForeignKey("care_plans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "finding_id",
            sa.Uuid(),
            sa.ForeignKey("dental_findings.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("tooth_fdi", sa.String(20), nullable=False),
        sa.Column("finding_type", sa.String(120), nullable=False),
        sa.Column("confidence", sa.Float()),
        sa.Column("recommended_window", sa.String(80), nullable=False),
        sa.Column("target_followup_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="AWAITING_REVIEW"),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("message_preview", sa.Text()),
        sa.Column("appointment_required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("image_required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    for name in ("care_plan_id", "finding_id", "tooth_fdi", "target_followup_at", "status"):
        op.create_index(f"ix_care_plan_items_{name}", "care_plan_items", [name])

    op.create_table(
        "care_conversations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("patient_id", sa.Uuid(), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("care_plan_id", sa.Uuid(), sa.ForeignKey("care_plans.id", ondelete="SET NULL")),
        sa.Column("branch_id", sa.Uuid(), sa.ForeignKey("branches.id"), nullable=False),
        sa.Column("whatsapp_phone", sa.String(40), nullable=False),
        sa.Column("language", sa.String(16), nullable=False, server_default="en"),
        sa.Column("status", sa.String(40), nullable=False, server_default="ACTIVE"),
        sa.Column("summary", sa.Text()),
        sa.Column("booking_context", sa.JSON(), nullable=False),
        sa.Column("last_message_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    for name in (
        "patient_id",
        "care_plan_id",
        "branch_id",
        "whatsapp_phone",
        "status",
        "last_message_at",
    ):
        op.create_index(f"ix_care_conversations_{name}", "care_conversations", [name])

    op.create_table(
        "care_conversation_messages",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "conversation_id",
            sa.Uuid(),
            sa.ForeignKey("care_conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "care_plan_item_id", sa.Uuid(), sa.ForeignKey("care_plan_items.id", ondelete="SET NULL")
        ),
        sa.Column("direction", sa.String(16), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False, server_default="WHATSAPP"),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("language", sa.String(16), nullable=False, server_default="en"),
        sa.Column("status", sa.String(32), nullable=False, server_default="RECORDED"),
        sa.Column("provider_message_id", sa.String(200)),
        sa.Column("message_metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    for name in (
        "conversation_id",
        "care_plan_item_id",
        "direction",
        "status",
        "provider_message_id",
        "created_at",
    ):
        op.create_index(
            f"ix_care_conversation_messages_{name}", "care_conversation_messages", [name]
        )

    op.create_table(
        "care_appointments",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("patient_id", sa.Uuid(), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("branch_id", sa.Uuid(), sa.ForeignKey("branches.id"), nullable=False),
        sa.Column("doctor_id", sa.Uuid(), sa.ForeignKey("users.id")),
        sa.Column(
            "conversation_id",
            sa.Uuid(),
            sa.ForeignKey("care_conversations.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "care_plan_item_id", sa.Uuid(), sa.ForeignKey("care_plan_items.id", ondelete="SET NULL")
        ),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("timezone", sa.String(80), nullable=False, server_default="Asia/Yerevan"),
        sa.Column("status", sa.String(40), nullable=False, server_default="PROPOSED"),
        sa.Column("source", sa.String(20), nullable=False, server_default="AI"),
        sa.Column("tooth_fdi", sa.String(20)),
        sa.Column("finding_type", sa.String(120)),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("doctor_note", sa.Text()),
        sa.Column("patient_confirmed_at", sa.DateTime(timezone=True)),
        sa.Column("reschedule_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "branch_id", "starts_at", "patient_id", name="uq_care_appointment_patient_slot"
        ),
    )
    for name in (
        "patient_id",
        "branch_id",
        "doctor_id",
        "conversation_id",
        "care_plan_item_id",
        "starts_at",
        "ends_at",
        "status",
    ):
        op.create_index(f"ix_care_appointments_{name}", "care_appointments", [name])


def downgrade() -> None:
    if os.getenv("MIGRATION_PLANE", "clinic") == "control":
        return
    op.drop_table("care_appointments")
    op.drop_table("care_conversation_messages")
    op.drop_table("care_conversations")
    op.drop_table("care_plan_items")
    op.drop_table("care_plans")
    op.drop_table("clinic_care_settings")
