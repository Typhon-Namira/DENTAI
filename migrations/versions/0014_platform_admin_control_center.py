"""Platform admin accounting, gift provenance, and audit metadata.

Revision ID: 0014_admin_control
Revises: 0013_freemium_subscriptions
"""

import os

import sqlalchemy as sa
from alembic import op

revision = "0014_admin_control"
down_revision = "0013_freemium_subscriptions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if os.getenv("MIGRATION_PLANE", "clinic") != "control":
        return

    inspector = sa.inspect(op.get_bind())

    clinic_columns = {column["name"] for column in inspector.get_columns("clinic_registry")}
    clinic_indexes = {index["name"] for index in inspector.get_indexes("clinic_registry")}
    with op.batch_alter_table("clinic_registry") as batch:
        if "subscription_source" not in clinic_columns:
            batch.add_column(
                sa.Column(
                    "subscription_source",
                    sa.String(24),
                    nullable=False,
                    server_default="LEGACY",
                )
            )
        if "gift_granted_at" not in clinic_columns:
            batch.add_column(sa.Column("gift_granted_at", sa.DateTime(timezone=True)))
        if "gift_note" not in clinic_columns:
            batch.add_column(sa.Column("gift_note", sa.Text()))
        if "ix_clinic_registry_subscription_source" not in clinic_indexes:
            batch.create_index("ix_clinic_registry_subscription_source", ["subscription_source"])

    request_columns = {
        column["name"] for column in inspector.get_columns("platform_access_requests")
    }
    request_indexes = {index["name"] for index in inspector.get_indexes("platform_access_requests")}
    with op.batch_alter_table("platform_access_requests") as batch:
        if "payment_amount" not in request_columns:
            batch.add_column(sa.Column("payment_amount", sa.Integer()))
        if "payment_currency" not in request_columns:
            batch.add_column(sa.Column("payment_currency", sa.String(12)))
        if "ix_platform_access_requests_payment_verified_at" not in request_indexes:
            batch.create_index(
                "ix_platform_access_requests_payment_verified_at",
                ["payment_verified_at"],
            )

    if not inspector.has_table("platform_admin_audit"):
        op.create_table(
            "platform_admin_audit",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("action", sa.String(100), nullable=False),
            sa.Column("target_type", sa.String(60), nullable=False),
            sa.Column("target_id", sa.String(100)),
            sa.Column("details", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_platform_admin_audit_action", "platform_admin_audit", ["action"])
        op.create_index(
            "ix_platform_admin_audit_target_type",
            "platform_admin_audit",
            ["target_type"],
        )
        op.create_index(
            "ix_platform_admin_audit_target_id",
            "platform_admin_audit",
            ["target_id"],
        )
        op.create_index(
            "ix_platform_admin_audit_created_at",
            "platform_admin_audit",
            ["created_at"],
        )

    op.execute(
        sa.text(
            "UPDATE clinic_registry SET subscription_source = CASE "
            "WHEN UPPER(COALESCE(subscription_plan, '')) = 'FREE' THEN 'FREE' "
            "WHEN UPPER(COALESCE(subscription_plan, '')) IN ('PREMIUM', 'TETA2_CARE') THEN 'PAID' "
            "ELSE 'LEGACY' END "
            "WHERE subscription_source IS NULL OR subscription_source = '' OR subscription_source = 'LEGACY'"
        )
    )


def downgrade() -> None:
    if os.getenv("MIGRATION_PLANE", "clinic") != "control":
        return

    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("platform_admin_audit"):
        op.drop_table("platform_admin_audit")

    request_columns = {
        column["name"] for column in inspector.get_columns("platform_access_requests")
    }
    request_indexes = {index["name"] for index in inspector.get_indexes("platform_access_requests")}
    with op.batch_alter_table("platform_access_requests") as batch:
        if "ix_platform_access_requests_payment_verified_at" in request_indexes:
            batch.drop_index("ix_platform_access_requests_payment_verified_at")
        for column in ("payment_currency", "payment_amount"):
            if column in request_columns:
                batch.drop_column(column)

    clinic_columns = {column["name"] for column in inspector.get_columns("clinic_registry")}
    clinic_indexes = {index["name"] for index in inspector.get_indexes("clinic_registry")}
    with op.batch_alter_table("clinic_registry") as batch:
        if "ix_clinic_registry_subscription_source" in clinic_indexes:
            batch.drop_index("ix_clinic_registry_subscription_source")
        for column in ("gift_note", "gift_granted_at", "subscription_source"):
            if column in clinic_columns:
                batch.drop_column(column)
