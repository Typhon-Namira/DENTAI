"""Care lifecycle, delivery state, and availability exceptions.

Revision ID: 0010_care_lifecycle_availability
Revises: 0009_care_message_idempotency
"""

import os

import sqlalchemy as sa
from alembic import op

revision = "0010_care_lifecycle_availability"
down_revision = "0009_care_message_idempotency"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if os.getenv("MIGRATION_PLANE", "clinic") == "control":
        return
    with op.batch_alter_table("care_plans") as batch:
        batch.add_column(sa.Column("approved_by", sa.Uuid()))
        batch.add_column(sa.Column("approved_at", sa.DateTime(timezone=True)))
        batch.add_column(sa.Column("rejected_by", sa.Uuid()))
        batch.add_column(sa.Column("rejected_at", sa.DateTime(timezone=True)))
        batch.add_column(sa.Column("paused_at", sa.DateTime(timezone=True)))
        batch.create_foreign_key(
            "fk_care_plans_approved_by_users", "users", ["approved_by"], ["id"]
        )
        batch.create_foreign_key(
            "fk_care_plans_rejected_by_users", "users", ["rejected_by"], ["id"]
        )

    with op.batch_alter_table("care_conversation_messages") as batch:
        batch.add_column(sa.Column("sent_at", sa.DateTime(timezone=True)))
        batch.add_column(sa.Column("delivered_at", sa.DateTime(timezone=True)))
        batch.add_column(sa.Column("read_at", sa.DateTime(timezone=True)))
        batch.add_column(sa.Column("failed_at", sa.DateTime(timezone=True)))
        batch.add_column(sa.Column("last_error", sa.Text()))
        batch.add_column(
            sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0")
        )

    with op.batch_alter_table("care_appointments") as batch:
        batch.add_column(
            sa.Column(
                "notification_status", sa.String(32), nullable=False, server_default="NOT_REQUIRED"
            )
        )
        batch.add_column(
            sa.Column(
                "notification_attempt_count", sa.Integer(), nullable=False, server_default="0"
            )
        )
        batch.add_column(sa.Column("notification_provider_id", sa.String(200)))
        batch.add_column(sa.Column("notification_sent_at", sa.DateTime(timezone=True)))
        batch.add_column(sa.Column("notification_failed_at", sa.DateTime(timezone=True)))
        batch.add_column(sa.Column("notification_error", sa.Text()))
        batch.create_index("ix_care_appointments_notification_status", ["notification_status"])

    op.create_table(
        "care_availability_exceptions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("branch_id", sa.Uuid(), sa.ForeignKey("branches.id"), nullable=False),
        sa.Column("doctor_id", sa.Uuid(), sa.ForeignKey("users.id")),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False, server_default="UNAVAILABLE"),
        sa.Column("reason", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    for column in ("branch_id", "doctor_id", "starts_at", "ends_at", "kind"):
        op.create_index(
            f"ix_care_availability_exceptions_{column}", "care_availability_exceptions", [column]
        )


def downgrade() -> None:
    if os.getenv("MIGRATION_PLANE", "clinic") == "control":
        return
    op.drop_table("care_availability_exceptions")
    with op.batch_alter_table("care_appointments") as batch:
        batch.drop_index("ix_care_appointments_notification_status")
        for column in (
            "notification_error",
            "notification_failed_at",
            "notification_sent_at",
            "notification_provider_id",
            "notification_attempt_count",
            "notification_status",
        ):
            batch.drop_column(column)
    with op.batch_alter_table("care_conversation_messages") as batch:
        for column in (
            "attempt_count",
            "last_error",
            "failed_at",
            "read_at",
            "delivered_at",
            "sent_at",
        ):
            batch.drop_column(column)
    with op.batch_alter_table("care_plans") as batch:
        for column in ("paused_at", "rejected_at", "rejected_by", "approved_at", "approved_by"):
            batch.drop_column(column)
