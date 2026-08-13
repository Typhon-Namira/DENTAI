"""Initial control or clinic schema selected by MIGRATION_PLANE."""

import os

from alembic import op

import app.database.control_models  # noqa: F401
import app.database.models  # noqa: F401
from app.database.base import Base

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def selected():
    control = os.getenv("MIGRATION_PLANE", "clinic") == "control"
    return [t for name, t in Base.metadata.tables.items() if (name == "clinic_registry") == control]


def upgrade():
    bind = op.get_bind()
    for table in selected():
        table.create(bind, checkfirst=True)


def downgrade():
    bind = op.get_bind()
    for table in reversed(selected()):
        table.drop(bind, checkfirst=True)
