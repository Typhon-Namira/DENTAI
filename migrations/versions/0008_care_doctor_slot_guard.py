"""Prevent duplicate Teta2 Care bookings for the same dentist slot.

Revision ID: 0008_care_doctor_slot_guard
Revises: 0007_teta2_care_orchestration
"""

import os

from alembic import op

revision = "0008_care_doctor_slot_guard"
down_revision = "0007_teta2_care_orchestration"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if os.getenv("MIGRATION_PLANE", "clinic") == "control":
        return
    with op.batch_alter_table("care_appointments") as batch_op:
        batch_op.create_unique_constraint(
            "uq_care_appointment_doctor_slot",
            ["branch_id", "doctor_id", "starts_at"],
        )


def downgrade() -> None:
    if os.getenv("MIGRATION_PLANE", "clinic") == "control":
        return
    with op.batch_alter_table("care_appointments") as batch_op:
        batch_op.drop_constraint("uq_care_appointment_doctor_slot", type_="unique")
