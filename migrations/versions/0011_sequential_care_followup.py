"""Sequential tooth follow-up scheduling and visit outcomes.

Revision ID: 0011_sequential_care_followup
Revises: 0010_care_lifecycle_availability
"""

import os

import sqlalchemy as sa
from alembic import op

revision = "0011_sequential_care_followup"
down_revision = "0010_care_lifecycle_availability"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if os.getenv("MIGRATION_PLANE", "clinic") == "control":
        return

    with op.batch_alter_table("care_plan_items") as batch:
        batch.add_column(
            sa.Column("sequence_order", sa.Integer(), nullable=False, server_default="0")
        )
        batch.add_column(
            sa.Column("priority_score", sa.Float(), nullable=False, server_default="0")
        )
        batch.add_column(
            sa.Column("priority_level", sa.String(24), nullable=False, server_default="ROUTINE")
        )
        batch.add_column(sa.Column("conversation_start_at", sa.DateTime(timezone=True)))
        batch.add_column(sa.Column("outcome", sa.String(40)))
        batch.add_column(sa.Column("outcome_at", sa.DateTime(timezone=True)))
        batch.create_index("ix_care_plan_items_sequence_order", ["sequence_order"])
        batch.create_index("ix_care_plan_items_conversation_start_at", ["conversation_start_at"])

    with op.batch_alter_table("care_appointments") as batch:
        batch.add_column(sa.Column("visit_outcome", sa.String(40)))
        batch.add_column(sa.Column("outcome_recorded_at", sa.DateTime(timezone=True)))
        batch.create_index("ix_care_appointments_visit_outcome", ["visit_outcome"])


def downgrade() -> None:
    if os.getenv("MIGRATION_PLANE", "clinic") == "control":
        return

    with op.batch_alter_table("care_appointments") as batch:
        batch.drop_index("ix_care_appointments_visit_outcome")
        batch.drop_column("outcome_recorded_at")
        batch.drop_column("visit_outcome")

    with op.batch_alter_table("care_plan_items") as batch:
        batch.drop_index("ix_care_plan_items_conversation_start_at")
        batch.drop_index("ix_care_plan_items_sequence_order")
        for column in (
            "outcome_at",
            "outcome",
            "conversation_start_at",
            "priority_level",
            "priority_score",
            "sequence_order",
        ):
            batch.drop_column(column)
