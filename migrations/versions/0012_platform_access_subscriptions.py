"""Platform access requests and renewable Teta2 Care subscriptions.

Revision ID: 0012_platform_access_subscriptions
Revises: 0011_sequential_care_followup
"""

import os

import sqlalchemy as sa
from alembic import op

revision = "0012_platform_access_subscriptions"
down_revision = "0011_sequential_care_followup"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if os.getenv("MIGRATION_PLANE", "clinic") != "control":
        return

    with op.batch_alter_table("clinic_registry") as batch:
        batch.add_column(sa.Column("subscription_plan", sa.String(40)))
        batch.add_column(sa.Column("subscription_starts_at", sa.DateTime(timezone=True)))
        batch.add_column(sa.Column("subscription_expires_at", sa.DateTime(timezone=True)))
        batch.create_index("ix_clinic_registry_subscription_expires_at", ["subscription_expires_at"])

    op.create_table(
        "platform_access_requests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("clinic_name", sa.String(200), nullable=False),
        sa.Column("country", sa.String(80), nullable=False),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("address", sa.String(300)),
        sa.Column("website", sa.String(300)),
        sa.Column("contact_name", sa.String(160), nullable=False),
        sa.Column("contact_role", sa.String(120), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("phone", sa.String(50), nullable=False),
        sa.Column("dentists_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("branches_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("notes", sa.Text()),
        sa.Column("status", sa.String(40), nullable=False, server_default="SUBMITTED"),
        sa.Column("admin_note", sa.Text()),
        sa.Column("payment_reference", sa.String(200)),
        sa.Column("payment_proof_note", sa.Text()),
        sa.Column("payment_instructions_sent_at", sa.DateTime(timezone=True)),
        sa.Column("payment_verified_at", sa.DateTime(timezone=True)),
        sa.Column("activated_clinic_id", sa.Uuid()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    for name, cols in (
        ("ix_platform_access_requests_clinic_name", ["clinic_name"]),
        ("ix_platform_access_requests_email", ["email"]),
        ("ix_platform_access_requests_status", ["status"]),
        ("ix_platform_access_requests_created_at", ["created_at"]),
        ("ix_platform_access_requests_activated_clinic_id", ["activated_clinic_id"]),
    ):
        op.create_index(name, "platform_access_requests", cols)

    op.create_table(
        "platform_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("plan_name", sa.String(80), nullable=False, server_default="Teta2 Care"),
        sa.Column("subscription_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("price_amount", sa.Integer(), nullable=False, server_default="99000"),
        sa.Column("price_currency", sa.String(12), nullable=False, server_default="AMD"),
        sa.Column("payment_recipient", sa.String(200), nullable=False, server_default="Teta2"),
        sa.Column("payment_card", sa.String(100), nullable=False, server_default=""),
        sa.Column("payment_bank_details", sa.Text(), nullable=False, server_default=""),
        sa.Column("payment_email_subject", sa.String(240), nullable=False, server_default="Teta2 Care access request — payment instructions"),
        sa.Column("payment_email_intro", sa.Text(), nullable=False, server_default="Your Teta2 Care access request has been approved. Please complete the subscription payment using the details below and reply to this email with your payment receipt."),
        sa.Column("activation_email_subject", sa.String(240), nullable=False, server_default="Your Teta2 Care dashboard is ready"),
        sa.Column("activation_email_intro", sa.Text(), nullable=False, server_default="Your payment has been verified and your Teta2 Care dashboard has been activated for 30 days."),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "platform_email_log",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("access_request_id", sa.Uuid()),
        sa.Column("clinic_id", sa.Uuid()),
        sa.Column("kind", sa.String(50), nullable=False),
        sa.Column("recipient", sa.String(320), nullable=False),
        sa.Column("subject", sa.String(240), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="QUEUED"),
        sa.Column("provider_message_id", sa.String(200)),
        sa.Column("error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    for name, cols in (
        ("ix_platform_email_log_access_request_id", ["access_request_id"]),
        ("ix_platform_email_log_clinic_id", ["clinic_id"]),
        ("ix_platform_email_log_kind", ["kind"]),
        ("ix_platform_email_log_created_at", ["created_at"]),
    ):
        op.create_index(name, "platform_email_log", cols)

    op.create_table(
        "platform_visits",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("path", sa.String(300), nullable=False),
        sa.Column("method", sa.String(12), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("visitor_hash", sa.String(80)),
        sa.Column("user_agent", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    for name, cols in (
        ("ix_platform_visits_path", ["path"]),
        ("ix_platform_visits_visitor_hash", ["visitor_hash"]),
        ("ix_platform_visits_created_at", ["created_at"]),
    ):
        op.create_index(name, "platform_visits", cols)


def downgrade() -> None:
    if os.getenv("MIGRATION_PLANE", "clinic") != "control":
        return
    op.drop_table("platform_visits")
    op.drop_table("platform_email_log")
    op.drop_table("platform_settings")
    op.drop_table("platform_access_requests")
    with op.batch_alter_table("clinic_registry") as batch:
        batch.drop_index("ix_clinic_registry_subscription_expires_at")
        batch.drop_column("subscription_expires_at")
        batch.drop_column("subscription_starts_at")
        batch.drop_column("subscription_plan")
