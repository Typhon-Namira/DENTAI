"""Platform access requests, billing terms, and admin audit.

Revision ID: 0012_platform_access_control
Revises: 0011_sequential_care_followup
"""

import os

import sqlalchemy as sa
from alembic import op

revision = "0012_platform_access_control"
down_revision = "0011_sequential_care_followup"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if os.getenv("MIGRATION_PLANE", "clinic") != "control":
        return

    op.add_column(
        "clinic_registry",
        sa.Column(
            "subscription_enforced",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "clinic_registry",
        sa.Column("access_expires_at", sa.DateTime(timezone=True)),
    )
    op.create_index(
        "ix_clinic_registry_access_expires_at",
        "clinic_registry",
        ["access_expires_at"],
    )

    op.create_table(
        "platform_commercial_config",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("plan_name", sa.String(80), nullable=False, server_default="Teta2 Care"),
        sa.Column("price_amount", sa.Numeric(12, 2), nullable=False, server_default="99000"),
        sa.Column("currency", sa.String(12), nullable=False, server_default="AMD"),
        sa.Column("bank_name", sa.String(160)),
        sa.Column("card_holder", sa.String(200)),
        sa.Column("card_number", sa.String(64)),
        sa.Column("payment_instructions", sa.Text()),
        sa.Column("support_email", sa.String(320)),
        sa.Column("sender_name", sa.String(120), nullable=False, server_default="Teta2 Care"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "platform_access_requests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("status", sa.String(40), nullable=False, server_default="SUBMITTED"),
        sa.Column("plan_name", sa.String(80), nullable=False, server_default="Teta2 Care"),
        sa.Column("clinic_name", sa.String(200), nullable=False),
        sa.Column("legal_name", sa.String(240)),
        sa.Column("country", sa.String(100), nullable=False),
        sa.Column("city", sa.String(120), nullable=False),
        sa.Column("address", sa.Text()),
        sa.Column("website", sa.String(500)),
        sa.Column("contact_name", sa.String(200), nullable=False),
        sa.Column("contact_role", sa.String(160)),
        sa.Column("contact_email", sa.String(320), nullable=False),
        sa.Column("contact_phone", sa.String(50), nullable=False),
        sa.Column("dentist_count", sa.Integer()),
        sa.Column("monthly_patient_volume", sa.Integer()),
        sa.Column("preferred_language", sa.String(16), nullable=False, server_default="en"),
        sa.Column("notes", sa.Text()),
        sa.Column("quoted_price_amount", sa.Numeric(12, 2)),
        sa.Column("quoted_currency", sa.String(12)),
        sa.Column("payment_reference", sa.String(120), unique=True),
        sa.Column("payment_notes", sa.Text()),
        sa.Column("receipt_reference", sa.String(500)),
        sa.Column("review_note", sa.Text()),
        sa.Column("payment_email_sent_at", sa.DateTime(timezone=True)),
        sa.Column("payment_confirmed_at", sa.DateTime(timezone=True)),
        sa.Column("rejected_at", sa.DateTime(timezone=True)),
        sa.Column("activated_at", sa.DateTime(timezone=True)),
        sa.Column(
            "clinic_registry_id",
            sa.Uuid(),
            sa.ForeignKey("clinic_registry.id", ondelete="SET NULL"),
        ),
        sa.Column("issued_username", sa.String(80)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_platform_access_requests_status",
        "platform_access_requests",
        ["status"],
    )
    op.create_index(
        "ix_platform_access_requests_contact_email",
        "platform_access_requests",
        ["contact_email"],
    )
    op.create_index(
        "ix_platform_access_requests_payment_reference",
        "platform_access_requests",
        ["payment_reference"],
    )
    op.create_index(
        "ix_platform_access_requests_clinic_registry_id",
        "platform_access_requests",
        ["clinic_registry_id"],
    )
    op.create_index(
        "ix_platform_access_requests_created_at",
        "platform_access_requests",
        ["created_at"],
    )

    op.create_table(
        "platform_subscription_terms",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "clinic_id",
            sa.Uuid(),
            sa.ForeignKey("clinic_registry.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "access_request_id",
            sa.Uuid(),
            sa.ForeignKey("platform_access_requests.id", ondelete="SET NULL"),
        ),
        sa.Column("plan_name", sa.String(80), nullable=False, server_default="Teta2 Care"),
        sa.Column("price_amount", sa.Numeric(12, 2)),
        sa.Column("currency", sa.String(12)),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"),
        sa.Column("kind", sa.String(30), nullable=False, server_default="INITIAL"),
        sa.Column("payment_reference", sa.String(120)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_platform_subscription_terms_clinic_id",
        "platform_subscription_terms",
        ["clinic_id"],
    )
    op.create_index(
        "ix_platform_subscription_terms_access_request_id",
        "platform_subscription_terms",
        ["access_request_id"],
    )
    op.create_index(
        "ix_platform_subscription_terms_starts_at",
        "platform_subscription_terms",
        ["starts_at"],
    )
    op.create_index(
        "ix_platform_subscription_terms_ends_at",
        "platform_subscription_terms",
        ["ends_at"],
    )
    op.create_index(
        "ix_platform_subscription_terms_status",
        "platform_subscription_terms",
        ["status"],
    )

    op.create_table(
        "platform_email_logs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "access_request_id",
            sa.Uuid(),
            sa.ForeignKey("platform_access_requests.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "clinic_id",
            sa.Uuid(),
            sa.ForeignKey("clinic_registry.id", ondelete="SET NULL"),
        ),
        sa.Column("kind", sa.String(60), nullable=False),
        sa.Column("recipient", sa.String(320), nullable=False),
        sa.Column("subject", sa.String(240), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="QUEUED"),
        sa.Column("safe_error", sa.String(200)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
    )
    op.create_index(
        "ix_platform_email_logs_access_request_id",
        "platform_email_logs",
        ["access_request_id"],
    )
    op.create_index(
        "ix_platform_email_logs_clinic_id",
        "platform_email_logs",
        ["clinic_id"],
    )
    op.create_index(
        "ix_platform_email_logs_kind",
        "platform_email_logs",
        ["kind"],
    )
    op.create_index(
        "ix_platform_email_logs_status",
        "platform_email_logs",
        ["status"],
    )

    op.create_table(
        "platform_admin_audit",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("access_request_id", sa.Uuid()),
        sa.Column("clinic_id", sa.Uuid()),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_platform_admin_audit_action",
        "platform_admin_audit",
        ["action"],
    )
    op.create_index(
        "ix_platform_admin_audit_access_request_id",
        "platform_admin_audit",
        ["access_request_id"],
    )
    op.create_index(
        "ix_platform_admin_audit_clinic_id",
        "platform_admin_audit",
        ["clinic_id"],
    )
    op.create_index(
        "ix_platform_admin_audit_created_at",
        "platform_admin_audit",
        ["created_at"],
    )


def downgrade() -> None:
    if os.getenv("MIGRATION_PLANE", "clinic") != "control":
        return
    op.drop_table("platform_admin_audit")
    op.drop_table("platform_email_logs")
    op.drop_table("platform_subscription_terms")
    op.drop_table("platform_access_requests")
    op.drop_table("platform_commercial_config")
    op.drop_index("ix_clinic_registry_access_expires_at", table_name="clinic_registry")
    op.drop_column("clinic_registry", "access_expires_at")
    op.drop_column("clinic_registry", "subscription_enforced")
