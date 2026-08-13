"""Add OPG schema version and finding provenance."""

import os

import sqlalchemy as sa
from alembic import op

revision = "0002_opg_provenance"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def has_column(table: str, column: str) -> bool:
    return column in {item["name"] for item in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade():
    if os.getenv("MIGRATION_PLANE", "clinic") == "control":
        return
    if not has_column("ai_analyses", "analysis_schema_version"):
        op.add_column(
            "ai_analyses",
            sa.Column(
                "analysis_schema_version",
                sa.String(40),
                nullable=False,
                server_default="legacy-1.0",
            ),
        )
    if not has_column("dental_findings", "provenance"):
        op.add_column(
            "dental_findings",
            sa.Column("provenance", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        )


def downgrade():
    if os.getenv("MIGRATION_PLANE", "clinic") == "control":
        return
    if has_column("dental_findings", "provenance"):
        op.drop_column("dental_findings", "provenance")
    if has_column("ai_analyses", "analysis_schema_version"):
        op.drop_column("ai_analyses", "analysis_schema_version")
