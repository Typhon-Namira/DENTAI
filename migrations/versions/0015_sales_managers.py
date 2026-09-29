"""Sales manager operations, attribution, commissions and withdrawals.

Revision ID: 0015_sales_managers
Revises: 0014_admin_control
"""

import os

import sqlalchemy as sa
from alembic import op

revision = "0015_sales_managers"
down_revision = "0014_admin_control"
branch_labels = None
depends_on = None


def _index(table: str, name: str) -> None:
    op.create_index(f"ix_{table}_{name}", table, [name])


def upgrade() -> None:
    if os.getenv("MIGRATION_PLANE", "clinic") != "control":
        return

    inspector = sa.inspect(op.get_bind())

    if not inspector.has_table("platform_sales_managers"):
        op.create_table(
            "platform_sales_managers",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("username", sa.String(80), nullable=False),
            sa.Column("email", sa.String(320), nullable=False),
            sa.Column("password_hash", sa.Text(), nullable=False),
            sa.Column("first_name", sa.String(100), nullable=False),
            sa.Column("last_name", sa.String(100), nullable=False),
            sa.Column(
                "title",
                sa.String(120),
                nullable=False,
                server_default="Sales Manager",
            ),
            sa.Column("phone", sa.String(50)),
            sa.Column("photo_storage_key", sa.String(500)),
            sa.Column("photo_mime", sa.String(80)),
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            ),
            sa.Column(
                "is_public",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            ),
            sa.Column("verified_at", sa.DateTime(timezone=True)),
            sa.Column(
                "must_change_password",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            ),
            sa.Column(
                "token_version",
                sa.Integer(),
                nullable=False,
                server_default="1",
            ),
            sa.Column("encrypted_bank_card", sa.Text()),
            sa.Column("bank_card_last4", sa.String(4)),
            sa.Column("bank_account_holder", sa.String(160)),
            sa.Column("last_login_at", sa.DateTime(timezone=True)),
            sa.Column("last_logout_at", sa.DateTime(timezone=True)),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("username"),
            sa.UniqueConstraint("email"),
        )
        for name in (
            "username",
            "email",
            "is_active",
            "is_public",
            "verified_at",
            "created_at",
        ):
            _index("platform_sales_managers", name)

    if not inspector.has_table("platform_sales_manager_sessions"):
        op.create_table(
            "platform_sales_manager_sessions",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("manager_id", sa.Uuid(), nullable=False),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("ended_at", sa.DateTime(timezone=True)),
            sa.Column("ip_hash", sa.String(80)),
            sa.Column("user_agent", sa.String(500)),
            sa.ForeignKeyConstraint(
                ["manager_id"],
                ["platform_sales_managers.id"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        for name in ("manager_id", "started_at", "ended_at"):
            _index("platform_sales_manager_sessions", name)

    if not inspector.has_table("platform_sales_daily_reports"):
        op.create_table(
            "platform_sales_daily_reports",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("manager_id", sa.Uuid(), nullable=False),
            sa.Column("report_date", sa.Date(), nullable=False),
            sa.Column(
                "status",
                sa.String(24),
                nullable=False,
                server_default="DRAFT",
            ),
            sa.Column("summary", sa.Text()),
            sa.Column("submitted_at", sa.DateTime(timezone=True)),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(
                ["manager_id"],
                ["platform_sales_managers.id"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "manager_id",
                "report_date",
                name="uq_sales_report_manager_date",
            ),
        )
        for name in ("manager_id", "report_date", "status", "submitted_at"):
            _index("platform_sales_daily_reports", name)

    if not inspector.has_table("platform_sales_report_clinics"):
        op.create_table(
            "platform_sales_report_clinics",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("report_id", sa.Uuid(), nullable=False),
            sa.Column("manager_id", sa.Uuid(), nullable=False),
            sa.Column("clinic_name", sa.String(200), nullable=False),
            sa.Column("country", sa.String(80), nullable=False),
            sa.Column("city", sa.String(100), nullable=False),
            sa.Column("address", sa.String(300)),
            sa.Column("website", sa.String(300)),
            sa.Column("contact_name", sa.String(160)),
            sa.Column("contact_role", sa.String(120)),
            sa.Column("email", sa.String(320)),
            sa.Column("phone", sa.String(50)),
            sa.Column("negotiation_result", sa.Text(), nullable=False),
            sa.Column(
                "outcome_status",
                sa.String(40),
                nullable=False,
                server_default="CONTACTED",
            ),
            sa.Column("next_step", sa.Text()),
            sa.Column("notes", sa.Text()),
            sa.Column("contacted_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("normalized_name", sa.String(220), nullable=False),
            sa.Column("normalized_email", sa.String(320)),
            sa.Column("normalized_phone", sa.String(60)),
            sa.Column("normalized_website", sa.String(240)),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(
                ["report_id"],
                ["platform_sales_daily_reports.id"],
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["manager_id"],
                ["platform_sales_managers.id"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        for name in (
            "report_id",
            "manager_id",
            "clinic_name",
            "city",
            "email",
            "phone",
            "outcome_status",
            "contacted_at",
            "normalized_name",
            "normalized_email",
            "normalized_phone",
            "normalized_website",
        ):
            _index("platform_sales_report_clinics", name)

    if not inspector.has_table("platform_sales_manager_activity"):
        op.create_table(
            "platform_sales_manager_activity",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("manager_id", sa.Uuid(), nullable=False),
            sa.Column("session_id", sa.Uuid()),
            sa.Column("action", sa.String(100), nullable=False),
            sa.Column("entity_type", sa.String(60)),
            sa.Column("entity_id", sa.String(100)),
            sa.Column("details", sa.JSON(), nullable=False),
            sa.Column("ip_hash", sa.String(80)),
            sa.Column("user_agent", sa.String(500)),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(
                ["manager_id"],
                ["platform_sales_managers.id"],
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["session_id"],
                ["platform_sales_manager_sessions.id"],
                ondelete="SET NULL",
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        for name in (
            "manager_id",
            "session_id",
            "action",
            "entity_type",
            "entity_id",
            "created_at",
        ):
            _index("platform_sales_manager_activity", name)

    if not inspector.has_table("platform_sales_referral_attributions"):
        op.create_table(
            "platform_sales_referral_attributions",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("access_request_id", sa.Uuid(), nullable=False),
            sa.Column("clinic_id", sa.Uuid()),
            sa.Column("manager_id", sa.Uuid()),
            sa.Column("report_clinic_id", sa.Uuid()),
            sa.Column(
                "status",
                sa.String(30),
                nullable=False,
                server_default="UNMATCHED",
            ),
            sa.Column("match_method", sa.String(80)),
            sa.Column(
                "match_score",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
            sa.Column("match_details", sa.JSON(), nullable=False),
            sa.Column("matched_at", sa.DateTime(timezone=True)),
            sa.Column("confirmed_at", sa.DateTime(timezone=True)),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(
                ["manager_id"],
                ["platform_sales_managers.id"],
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["report_clinic_id"],
                ["platform_sales_report_clinics.id"],
                ondelete="SET NULL",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("access_request_id"),
        )
        for name in (
            "access_request_id",
            "clinic_id",
            "manager_id",
            "report_clinic_id",
            "status",
            "created_at",
        ):
            _index("platform_sales_referral_attributions", name)

    if not inspector.has_table("platform_sales_subscription_payments"):
        op.create_table(
            "platform_sales_subscription_payments",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("clinic_id", sa.Uuid(), nullable=False),
            sa.Column("access_request_id", sa.Uuid()),
            sa.Column(
                "kind",
                sa.String(24),
                nullable=False,
                server_default="INITIAL",
            ),
            sa.Column("amount", sa.Integer(), nullable=False),
            sa.Column("currency", sa.String(12), nullable=False),
            sa.Column("reference", sa.String(200)),
            sa.Column("subscription_days", sa.Integer()),
            sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("access_request_id"),
        )
        for name in (
            "clinic_id",
            "access_request_id",
            "kind",
            "currency",
            "verified_at",
        ):
            _index("platform_sales_subscription_payments", name)

    if not inspector.has_table("platform_sales_commissions"):
        op.create_table(
            "platform_sales_commissions",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("manager_id", sa.Uuid(), nullable=False),
            sa.Column("payment_id", sa.Uuid(), nullable=False),
            sa.Column("attribution_id", sa.Uuid()),
            sa.Column("clinic_id", sa.Uuid(), nullable=False),
            sa.Column("gross_amount", sa.Integer(), nullable=False),
            sa.Column(
                "commission_rate_bps",
                sa.Integer(),
                nullable=False,
                server_default="3000",
            ),
            sa.Column("commission_amount", sa.Integer(), nullable=False),
            sa.Column("currency", sa.String(12), nullable=False),
            sa.Column(
                "status",
                sa.String(24),
                nullable=False,
                server_default="AVAILABLE",
            ),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(
                ["manager_id"],
                ["platform_sales_managers.id"],
                ondelete="RESTRICT",
            ),
            sa.ForeignKeyConstraint(
                ["payment_id"],
                ["platform_sales_subscription_payments.id"],
                ondelete="RESTRICT",
            ),
            sa.ForeignKeyConstraint(
                ["attribution_id"],
                ["platform_sales_referral_attributions.id"],
                ondelete="SET NULL",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("payment_id"),
        )
        for name in (
            "manager_id",
            "payment_id",
            "attribution_id",
            "clinic_id",
            "currency",
            "status",
            "created_at",
        ):
            _index("platform_sales_commissions", name)

    if not inspector.has_table("platform_sales_withdrawals"):
        op.create_table(
            "platform_sales_withdrawals",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("manager_id", sa.Uuid(), nullable=False),
            sa.Column("amount", sa.Integer(), nullable=False),
            sa.Column("currency", sa.String(12), nullable=False),
            sa.Column(
                "status",
                sa.String(24),
                nullable=False,
                server_default="PENDING",
            ),
            sa.Column("bank_card_last4", sa.String(4), nullable=False),
            sa.Column(
                "encrypted_bank_card_snapshot",
                sa.Text(),
                nullable=False,
            ),
            sa.Column("bank_account_holder", sa.String(160)),
            sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("reviewed_at", sa.DateTime(timezone=True)),
            sa.Column("paid_at", sa.DateTime(timezone=True)),
            sa.Column("paid_reference", sa.String(200)),
            sa.Column("admin_note", sa.Text()),
            sa.ForeignKeyConstraint(
                ["manager_id"],
                ["platform_sales_managers.id"],
                ondelete="RESTRICT",
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        for name in (
            "manager_id",
            "currency",
            "status",
            "requested_at",
            "paid_at",
        ):
            _index("platform_sales_withdrawals", name)


def downgrade() -> None:
    if os.getenv("MIGRATION_PLANE", "clinic") != "control":
        return

    for table in (
        "platform_sales_withdrawals",
        "platform_sales_commissions",
        "platform_sales_subscription_payments",
        "platform_sales_referral_attributions",
        "platform_sales_manager_activity",
        "platform_sales_report_clinics",
        "platform_sales_daily_reports",
        "platform_sales_manager_sessions",
        "platform_sales_managers",
    ):
        op.drop_table(table)
