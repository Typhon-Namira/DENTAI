"""Add Patient Radar production lifecycle tables."""

import os

import sqlalchemy as sa
from alembic import op

revision = "0006_radar_production"
down_revision = "0005_patient_radar"
branch_labels = None
depends_on = None


def inspector():
    return sa.inspect(op.get_bind())


def has_table(table: str) -> bool:
    return table in inspector().get_table_names()


def has_index(table: str, index: str) -> bool:
    return has_table(table) and index in {item["name"] for item in inspector().get_indexes(table)}


def upgrade():
    if os.getenv("MIGRATION_PLANE", "clinic") == "control":
        return

    if not has_table("radar_connections"):
        op.create_table(
            "radar_connections",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("platform", sa.String(24), nullable=False),
            sa.Column("provider", sa.String(40), nullable=False),
            sa.Column("status", sa.String(32), nullable=False, server_default="CONNECTING"),
            sa.Column("account_external_id", sa.String(300)),
            sa.Column("account_display", sa.String(300)),
            sa.Column("encrypted_credentials", sa.Text()),
            sa.Column("scopes", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
            sa.Column("expires_at", sa.DateTime(timezone=True)),
            sa.Column("last_health_at", sa.DateTime(timezone=True)),
            sa.Column("last_error_code", sa.String(100)),
            sa.Column("last_error", sa.String(500)),
            sa.Column("auth_nonce", sa.String(100)),
            sa.Column("connection_metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )

    if not has_table("radar_source_candidates"):
        op.create_table(
            "radar_source_candidates",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("platform", sa.String(24), nullable=False),
            sa.Column("external_source_id", sa.String(300), nullable=False),
            sa.Column("source_type", sa.String(40), nullable=False),
            sa.Column("name", sa.String(300), nullable=False),
            sa.Column("handle", sa.String(300)),
            sa.Column("source_url", sa.String(1000), nullable=False),
            sa.Column("location_hint", sa.String(160)),
            sa.Column("language_hints", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
            sa.Column("discovered_from_source_id", sa.Uuid(), sa.ForeignKey("radar_sources.id", ondelete="SET NULL")),
            sa.Column("state", sa.String(24), nullable=False, server_default="NEW"),
            sa.Column("candidate_score", sa.Integer(), nullable=False, server_default="50"),
            sa.Column("discovery_count", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("last_discovered_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("evidence", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("platform", "external_source_id"),
        )

    if not has_table("radar_outcomes"):
        op.create_table(
            "radar_outcomes",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("opportunity_id", sa.Uuid(), sa.ForeignKey("radar_opportunities.id", ondelete="CASCADE"), nullable=False),
            sa.Column("outcome", sa.String(32), nullable=False),
            sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("outcome_metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )

    if not has_table("radar_runtime_state"):
        op.create_table(
            "radar_runtime_state",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("key", sa.String(160), nullable=False, unique=True),
            sa.Column("value", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )

    indexes = {
        "radar_connections": [
            ("ix_radar_connections_platform", ["platform"]),
            ("ix_radar_connections_status", ["status"]),
            ("ix_radar_connections_account", ["account_external_id"]),
            ("ix_radar_connections_expires", ["expires_at"]),
            ("ix_radar_connections_nonce", ["auth_nonce"]),
        ],
        "radar_source_candidates": [
            ("ix_radar_source_candidates_state_score", ["state", "candidate_score"]),
            ("ix_radar_source_candidates_platform", ["platform"]),
            ("ix_radar_source_candidates_parent", ["discovered_from_source_id"]),
        ],
        "radar_outcomes": [
            ("ix_radar_outcomes_opportunity", ["opportunity_id"]),
            ("ix_radar_outcomes_outcome", ["outcome"]),
            ("ix_radar_outcomes_occurred", ["occurred_at"]),
        ],
        "radar_runtime_state": [("ix_radar_runtime_state_key", ["key"])],
    }
    for table, entries in indexes.items():
        for name, columns in entries:
            if not has_index(table, name):
                op.create_index(name, table, columns)


def downgrade():
    if os.getenv("MIGRATION_PLANE", "clinic") == "control":
        return
    for table in ("radar_runtime_state", "radar_outcomes", "radar_source_candidates", "radar_connections"):
        if has_table(table):
            op.drop_table(table)
