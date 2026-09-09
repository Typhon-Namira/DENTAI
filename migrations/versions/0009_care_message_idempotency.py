"""Make inbound Care messages idempotent.

Revision ID: 0009_care_message_idempotency
Revises: 0008_care_doctor_slot_guard
"""

import os

from alembic import op

revision = "0009_care_message_idempotency"
down_revision = "0008_care_doctor_slot_guard"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if os.getenv("MIGRATION_PLANE", "clinic") == "control":
        return
    with op.batch_alter_table("care_conversation_messages") as batch_op:
        batch_op.create_unique_constraint(
            "uq_care_message_provider_id",
            ["conversation_id", "provider_message_id"],
        )


def downgrade() -> None:
    if os.getenv("MIGRATION_PLANE", "clinic") == "control":
        return
    with op.batch_alter_table("care_conversation_messages") as batch_op:
        batch_op.drop_constraint("uq_care_message_provider_id", type_="unique")
