"""Add durable AI analysis queue state."""

import os

import sqlalchemy as sa
from alembic import op

revision = "0003_ai_job_queue"
down_revision = "0002_opg_provenance"
branch_labels = None
depends_on = None


def has_column(table: str, column: str) -> bool:
    return column in {item["name"] for item in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade():
    if os.getenv("MIGRATION_PLANE", "clinic") == "control":
        return
    columns = (
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("worker_id", sa.String(160)),
        sa.Column("claimed_at", sa.DateTime(timezone=True)),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True)),
        sa.Column("retry_at", sa.DateTime(timezone=True)),
    )
    for column in columns:
        if not has_column("ai_analyses", column.name):
            op.add_column("ai_analyses", column)
    op.create_index("ix_ai_analyses_retry_at", "ai_analyses", ["retry_at"], unique=False)


def downgrade():
    if os.getenv("MIGRATION_PLANE", "clinic") == "control":
        return
    op.drop_index("ix_ai_analyses_retry_at", table_name="ai_analyses")
    for name in (
        "retry_at",
        "heartbeat_at",
        "claimed_at",
        "worker_id",
        "max_attempts",
        "attempt_count",
    ):
        if has_column("ai_analyses", name):
            op.drop_column("ai_analyses", name)
