"""Freemium subscription state for clinic access.

Revision ID: 0013_freemium_subscriptions
Revises: 0012_platform_access
"""

import os

import sqlalchemy as sa
from alembic import op

revision = "0013_freemium_subscriptions"
down_revision = "0012_platform_access"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if os.getenv("MIGRATION_PLANE", "clinic") != "control":
        return

    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("clinic_registry")}
    indexes = {index["name"] for index in inspector.get_indexes("clinic_registry")}
    with op.batch_alter_table("clinic_registry") as batch:
        if "subscription_state" not in columns:
            batch.add_column(
                sa.Column(
                    "subscription_state",
                    sa.String(40),
                    nullable=False,
                    server_default="ACTIVE",
                )
            )
        if "free_trial_started_at" not in columns:
            batch.add_column(sa.Column("free_trial_started_at", sa.DateTime(timezone=True)))
        if "upgrade_requested_at" not in columns:
            batch.add_column(sa.Column("upgrade_requested_at", sa.DateTime(timezone=True)))
        if "ix_clinic_registry_subscription_state" not in indexes:
            batch.create_index("ix_clinic_registry_subscription_state", ["subscription_state"])

    op.execute(
        sa.text(
            "UPDATE clinic_registry SET subscription_state = 'ACTIVE' "
            "WHERE subscription_state IS NULL OR subscription_state = ''"
        )
    )


def downgrade() -> None:
    if os.getenv("MIGRATION_PLANE", "clinic") != "control":
        return

    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("clinic_registry")}
    indexes = {index["name"] for index in inspector.get_indexes("clinic_registry")}
    with op.batch_alter_table("clinic_registry") as batch:
        if "ix_clinic_registry_subscription_state" in indexes:
            batch.drop_index("ix_clinic_registry_subscription_state")
        for column in ("upgrade_requested_at", "free_trial_started_at", "subscription_state"):
            if column in columns:
                batch.drop_column(column)
