"""Add tenant Armenia Patient Radar intelligence tables."""

import os

import sqlalchemy as sa
from alembic import op

revision = "0005_patient_radar"
down_revision = "0004_whatsapp_outreach"
branch_labels = None
depends_on = None


def inspector():
    return sa.inspect(op.get_bind())


def has_table(table: str) -> bool:
    return table in inspector().get_table_names()


def has_index(table: str, index: str) -> bool:
    return has_table(table) and index in {item["name"] for item in inspector().get_indexes(table)}


def create_sources() -> None:
    op.create_table(
        "radar_sources",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("platform", sa.String(24), nullable=False),
        sa.Column("external_source_id", sa.String(300), nullable=False),
        sa.Column("source_type", sa.String(40), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("handle", sa.String(300)),
        sa.Column("source_url", sa.String(1000), nullable=False),
        sa.Column("language_hints", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("location_hint", sa.String(160)),
        sa.Column("armenia_relevance", sa.Float(), nullable=False, server_default="50"),
        sa.Column("engagement_score", sa.Float(), nullable=False, server_default="50"),
        sa.Column("dental_signal_probability", sa.Float(), nullable=False, server_default="50"),
        sa.Column("source_score", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("priority", sa.String(20), nullable=False, server_default="MEDIUM"),
        sa.Column("monitoring_interval_minutes", sa.Integer(), nullable=False, server_default="45"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_polled_at", sa.DateTime(timezone=True)),
        sa.Column("last_content_at", sa.DateTime(timezone=True)),
        sa.Column("next_check_at", sa.DateTime(timezone=True)),
        sa.Column("source_metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("platform", "external_source_id"),
    )


def create_opportunities() -> None:
    op.create_table(
        "radar_opportunities",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("platform", sa.String(24), nullable=False),
        sa.Column("person_key", sa.String(64), nullable=False),
        sa.Column("author_display", sa.String(300)),
        sa.Column("author_profile_url", sa.String(1000)),
        sa.Column("language", sa.String(20), nullable=False, server_default="unknown"),
        sa.Column("location", sa.String(160)),
        sa.Column("treatment", sa.String(80)),
        sa.Column("intent", sa.String(80), nullable=False),
        sa.Column("urgency", sa.String(30), nullable=False),
        sa.Column("opportunity_score", sa.Integer(), nullable=False),
        sa.Column("tier", sa.String(20), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="NEW"),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("signal_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("evidence_summary", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("scoring_rule_set", sa.String(100), nullable=False),
        sa.Column("scoring_rule_version", sa.String(40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("platform", "person_key"),
    )


def create_signals() -> None:
    op.create_table(
        "radar_signals",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "source_id",
            sa.Uuid(),
            sa.ForeignKey("radar_sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "opportunity_id",
            sa.Uuid(),
            sa.ForeignKey("radar_opportunities.id", ondelete="SET NULL"),
        ),
        sa.Column("platform", sa.String(24), nullable=False),
        sa.Column("external_signal_id", sa.String(400)),
        sa.Column("dedupe_key", sa.String(64), nullable=False),
        sa.Column("signal_type", sa.String(40), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("context_text", sa.Text()),
        sa.Column("source_url", sa.String(1500), nullable=False),
        sa.Column("author_display", sa.String(300)),
        sa.Column("person_key", sa.String(64), nullable=False),
        sa.Column("language", sa.String(20), nullable=False),
        sa.Column("location", sa.String(160)),
        sa.Column("treatment", sa.String(80)),
        sa.Column("intent", sa.String(80), nullable=False),
        sa.Column("urgency_label", sa.String(30), nullable=False),
        sa.Column("dental_relevance", sa.Float(), nullable=False),
        sa.Column("treatment_intent", sa.Float(), nullable=False),
        sa.Column("location_match", sa.Float(), nullable=False),
        sa.Column("urgency_score", sa.Float(), nullable=False),
        sa.Column("recency_score", sa.Float(), nullable=False),
        sa.Column("recommendation_intent", sa.Float(), nullable=False),
        sa.Column("classifier_confidence", sa.Float(), nullable=False),
        sa.Column("opportunity_score", sa.Integer(), nullable=False),
        sa.Column("tier", sa.String(20), nullable=False),
        sa.Column("is_candidate", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("evidence", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("source_id", "dedupe_key"),
    )


INDEXES = {
    "radar_sources": (
        ("ix_radar_sources_platform", ["platform"]),
        ("ix_radar_sources_priority", ["priority"]),
        ("ix_radar_sources_active_due", ["is_active", "next_check_at"]),
    ),
    "radar_opportunities": (
        ("ix_radar_opportunities_platform", ["platform"]),
        ("ix_radar_opportunities_person_key", ["person_key"]),
        ("ix_radar_opportunities_score", ["opportunity_score"]),
        ("ix_radar_opportunities_tier_status", ["tier", "status"]),
        ("ix_radar_opportunities_last_seen", ["last_seen_at"]),
        ("ix_radar_opportunities_filters", ["language", "location", "treatment"]),
    ),
    "radar_signals": (
        ("ix_radar_signals_source_id", ["source_id"]),
        ("ix_radar_signals_opportunity_id", ["opportunity_id"]),
        ("ix_radar_signals_person_key", ["person_key"]),
        ("ix_radar_signals_platform", ["platform"]),
        ("ix_radar_signals_observed_at", ["observed_at"]),
        ("ix_radar_signals_candidate_score", ["is_candidate", "opportunity_score"]),
    ),
}


def ensure_indexes() -> None:
    for table, indexes in INDEXES.items():
        if not has_table(table):
            continue
        for name, columns in indexes:
            if not has_index(table, name):
                op.create_index(name, table, columns)


def upgrade():
    if os.getenv("MIGRATION_PLANE", "clinic") == "control":
        return
    if not has_table("radar_sources"):
        create_sources()
    if not has_table("radar_opportunities"):
        create_opportunities()
    if not has_table("radar_signals"):
        create_signals()
    ensure_indexes()


def downgrade():
    if os.getenv("MIGRATION_PLANE", "clinic") == "control":
        return
    for table in ("radar_signals", "radar_opportunities", "radar_sources"):
        if not has_table(table):
            continue
        for name, _ in reversed(INDEXES.get(table, ())):
            if has_index(table, name):
                op.drop_index(name, table_name=table)
        op.drop_table(table)
