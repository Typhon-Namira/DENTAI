"""Sales manager score system and first-1000 equity award.

Revision ID: 0016_sales_scores
Revises: 0015_sales_managers
"""

import os

import sqlalchemy as sa
from alembic import op

revision = "0016_sales_scores"
down_revision = "0015_sales_managers"
branch_labels = None
depends_on = None


def _index(table: str, name: str) -> None:
    op.create_index(f"ix_{table}_{name}", table, [name])


def upgrade() -> None:
    if os.getenv("MIGRATION_PLANE", "clinic") != "control":
        return

    inspector = sa.inspect(op.get_bind())

    if not inspector.has_table("platform_sales_growth_ideas"):
        op.create_table(
            "platform_sales_growth_ideas",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("manager_id", sa.Uuid(), nullable=False),
            sa.Column("title", sa.String(180), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("expected_impact", sa.Text()),
            sa.Column("status", sa.String(24), nullable=False, server_default="PENDING"),
            sa.Column("admin_note", sa.Text()),
            sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("reviewed_at", sa.DateTime(timezone=True)),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(
                ["manager_id"], ["platform_sales_managers.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        for name in ("manager_id", "status", "submitted_at", "reviewed_at"):
            _index("platform_sales_growth_ideas", name)

    if not inspector.has_table("platform_sales_score_events"):
        op.create_table(
            "platform_sales_score_events",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("manager_id", sa.Uuid(), nullable=False),
            sa.Column("category", sa.String(32), nullable=False),
            sa.Column("points", sa.Integer(), nullable=False),
            sa.Column("source_type", sa.String(40), nullable=False),
            sa.Column("source_id", sa.String(100), nullable=False),
            sa.Column("description", sa.String(300), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(
                ["manager_id"], ["platform_sales_managers.id"], ondelete="RESTRICT"
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "source_type",
                "source_id",
                "category",
                name="uq_sales_score_event_source_category",
            ),
        )
        for name in (
            "manager_id",
            "category",
            "source_type",
            "source_id",
            "created_at",
        ):
            _index("platform_sales_score_events", name)

    if not inspector.has_table("platform_sales_equity_awards"):
        op.create_table(
            "platform_sales_equity_awards",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("award_key", sa.String(40), nullable=False),
            sa.Column("manager_id", sa.Uuid(), nullable=False),
            sa.Column("points_at_award", sa.Integer(), nullable=False, server_default="1000"),
            sa.Column("equity_percent_bps", sa.Integer(), nullable=False, server_default="300"),
            sa.Column(
                "status",
                sa.String(32),
                nullable=False,
                server_default="PENDING_ADMIN_REVIEW",
            ),
            sa.Column("reached_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("reviewed_at", sa.DateTime(timezone=True)),
            sa.Column("admin_note", sa.Text()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(
                ["manager_id"], ["platform_sales_managers.id"], ondelete="RESTRICT"
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("award_key"),
        )
        for name in ("award_key", "manager_id", "status", "reached_at"):
            _index("platform_sales_equity_awards", name)


def downgrade() -> None:
    if os.getenv("MIGRATION_PLANE", "clinic") != "control":
        return
    for table in (
        "platform_sales_equity_awards",
        "platform_sales_score_events",
        "platform_sales_growth_ideas",
    ):
        op.drop_table(table)
