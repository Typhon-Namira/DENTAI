"""Platform access requests and fixed 30-day subscriptions.

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

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    clinic_columns = {column["name"] for column in inspector.get_columns("clinic_registry")}
    clinic_indexes = {index["name"] for index in inspector.get_indexes("clinic_registry")}

    missing_columns = []
    if "subscription_plan" not in clinic_columns:
        missing_columns.append(
            sa.Column(
                "subscription_plan",
                sa.String(40),
                nullable=False,
                server_default="TETA2_CARE",
            )
        )
    if "subscription_status" not in clinic_columns:
        missing_columns.append(
            sa.Column(
                "subscription_status",
                sa.String(32),
                nullable=False,
                server_default="ACTIVE",
            )
        )
    if "subscription_started_at" not in clinic_columns:
        missing_columns.append(sa.Column("subscription_started_at", sa.DateTime(timezone=True)))
    if "subscription_ends_at" not in clinic_columns:
        missing_columns.append(sa.Column("subscription_ends_at", sa.DateTime(timezone=True)))
    if "renewal_count" not in clinic_columns:
        missing_columns.append(
            sa.Column("renewal_count", sa.Integer(), nullable=False, server_default="0")
        )

    if missing_columns:
        with op.batch_alter_table("clinic_registry") as batch:
            for column in missing_columns:
                batch.add_column(column)

    if "ix_clinic_registry_subscription_status" not in clinic_indexes:
        op.create_index(
            "ix_clinic_registry_subscription_status",
            "clinic_registry",
            ["subscription_status"],
        )
    if "ix_clinic_registry_subscription_ends_at" not in clinic_indexes:
        op.create_index(
            "ix_clinic_registry_subscription_ends_at",
            "clinic_registry",
            ["subscription_ends_at"],
        )

    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "platform_access_requests" not in existing_tables:
        op.create_table(
            "platform_access_requests",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("clinic_name", sa.String(200), nullable=False),
            sa.Column("requested_slug", sa.String(80), nullable=False),
            sa.Column("country", sa.String(120), nullable=False),
            sa.Column("city", sa.String(120), nullable=False),
            sa.Column("address", sa.String(300)),
            sa.Column("website", sa.String(300)),
            sa.Column("director_name", sa.String(200), nullable=False),
            sa.Column("work_email", sa.String(320), nullable=False),
            sa.Column("phone", sa.String(80), nullable=False),
            sa.Column("branch_count", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("dentist_count", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("notes", sa.Text()),
            sa.Column("plan", sa.String(40), nullable=False, server_default="TETA2_CARE"),
            sa.Column("status", sa.String(40), nullable=False, server_default="SUBMITTED"),
            sa.Column("admin_note", sa.Text()),
            sa.Column("payment_reference", sa.String(300)),
            sa.Column("payment_proof_note", sa.Text()),
            sa.Column("payment_instructions_sent_at", sa.DateTime(timezone=True)),
            sa.Column("payment_reported_at", sa.DateTime(timezone=True)),
            sa.Column("payment_verified_at", sa.DateTime(timezone=True)),
            sa.Column("activated_at", sa.DateTime(timezone=True)),
            sa.Column("rejected_at", sa.DateTime(timezone=True)),
            sa.Column("clinic_id", sa.Uuid()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index(
            "ix_platform_access_requests_clinic_name",
            "platform_access_requests",
            ["clinic_name"],
        )
        op.create_index(
            "ix_platform_access_requests_requested_slug",
            "platform_access_requests",
            ["requested_slug"],
        )
        op.create_index(
            "ix_platform_access_requests_work_email",
            "platform_access_requests",
            ["work_email"],
        )
        op.create_index(
            "ix_platform_access_requests_status",
            "platform_access_requests",
            ["status"],
        )
        op.create_index(
            "ix_platform_access_requests_clinic_id",
            "platform_access_requests",
            ["clinic_id"],
        )
        op.create_index(
            "ix_platform_access_requests_created_at",
            "platform_access_requests",
            ["created_at"],
        )

    if "platform_billing_settings" not in existing_tables:
        op.create_table(
            "platform_billing_settings",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("plan_name", sa.String(40), nullable=False, server_default="Teta2 Care"),
            sa.Column("price", sa.Numeric(12, 2), nullable=False, server_default="0"),
            sa.Column("currency", sa.String(12), nullable=False, server_default="AMD"),
            sa.Column("bank_name", sa.String(200), nullable=False, server_default=""),
            sa.Column("cardholder_name", sa.String(200), nullable=False, server_default=""),
            sa.Column("card_number", sa.String(100), nullable=False, server_default=""),
            sa.Column("payment_note", sa.Text(), nullable=False, server_default=""),
            sa.Column("support_email", sa.String(320), nullable=False, server_default=""),
            sa.Column(
                "login_url",
                sa.String(500),
                nullable=False,
                server_default="https://www.teta2.com",
            ),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )

    if "platform_admin_events" not in existing_tables:
        op.create_table(
            "platform_admin_events",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("action", sa.String(100), nullable=False),
            sa.Column("entity_type", sa.String(80), nullable=False),
            sa.Column("entity_id", sa.String(120)),
            sa.Column("details", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index(
            "ix_platform_admin_events_action", "platform_admin_events", ["action"]
        )
        op.create_index(
            "ix_platform_admin_events_created_at",
            "platform_admin_events",
            ["created_at"],
        )


def downgrade() -> None:
    if os.getenv("MIGRATION_PLANE", "clinic") != "control":
        return

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "platform_admin_events" in tables:
        op.drop_table("platform_admin_events")
    if "platform_billing_settings" in tables:
        op.drop_table("platform_billing_settings")
    if "platform_access_requests" in tables:
        op.drop_table("platform_access_requests")

    inspector = sa.inspect(bind)
    clinic_columns = {column["name"] for column in inspector.get_columns("clinic_registry")}
    clinic_indexes = {index["name"] for index in inspector.get_indexes("clinic_registry")}
    with op.batch_alter_table("clinic_registry") as batch:
        if "ix_clinic_registry_subscription_ends_at" in clinic_indexes:
            batch.drop_index("ix_clinic_registry_subscription_ends_at")
        if "ix_clinic_registry_subscription_status" in clinic_indexes:
            batch.drop_index("ix_clinic_registry_subscription_status")
        for column in (
            "renewal_count",
            "subscription_ends_at",
            "subscription_started_at",
            "subscription_status",
            "subscription_plan",
        ):
            if column in clinic_columns:
                batch.drop_column(column)
