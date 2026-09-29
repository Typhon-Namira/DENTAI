"""Sales manager operations, reporting, attribution, commissions and withdrawals.

Revision ID: 0015_sales_manager
Revises: 0014_admin_control
"""

import os

import sqlalchemy as sa
from alembic import op

revision = "0015_sales_manager"
down_revision = "0014_admin_control"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if os.getenv("MIGRATION_PLANE", "clinic") != "control":
        return

    inspector = sa.inspect(op.get_bind())

    if not inspector.has_table("platform_sales_managers"):
        op.create_table(
            "platform_sales_managers",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("username", sa.String(80), nullable=False),
            sa.Column("email", sa.String(320), nullable=False),
            sa.Column("password_hash", sa.Text(), nullable=False),
            sa.Column("full_name", sa.String(180), nullable=False),
            sa.Column("title", sa.String(160), nullable=False, server_default="Sales Manager"),
            sa.Column("phone", sa.String(50)),
            sa.Column("territory", sa.String(160)),
            sa.Column("bio", sa.Text()),
            sa.Column("photo_storage_key", sa.String(500)),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("public_verified", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("commission_rate_bps", sa.Integer(), nullable=False, server_default="3000"),
            sa.Column("bank_card_ciphertext", sa.Text()),
            sa.Column("bank_card_last4", sa.String(4)),
            sa.Column("bank_card_holder", sa.String(180)),
            sa.Column("bank_card_updated_at", sa.DateTime(timezone=True)),
            sa.Column("last_login_at", sa.DateTime(timezone=True)),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True)),
            sa.UniqueConstraint("username"),
            sa.UniqueConstraint("email"),
        )
        for column in ("username", "email", "full_name", "is_active", "public_verified", "last_login_at", "created_at", "deleted_at"):
            op.create_index(f"ix_platform_sales_managers_{column}", "platform_sales_managers", [column])

    if not inspector.has_table("platform_sales_manager_sessions"):
        op.create_table(
            "platform_sales_manager_sessions",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("manager_id", sa.Uuid(), sa.ForeignKey("platform_sales_managers.id", ondelete="CASCADE"), nullable=False),
            sa.Column("token_hash", sa.String(64), nullable=False),
            sa.Column("ip_address", sa.String(80)),
            sa.Column("user_agent", sa.String(500)),
            sa.Column("login_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("logout_at", sa.DateTime(timezone=True)),
            sa.Column("logout_reason", sa.String(80)),
            sa.UniqueConstraint("token_hash"),
        )
        for column in ("manager_id", "token_hash", "login_at", "expires_at", "logout_at"):
            op.create_index(f"ix_platform_sales_manager_sessions_{column}", "platform_sales_manager_sessions", [column])

    if not inspector.has_table("platform_sales_manager_activity"):
        op.create_table(
            "platform_sales_manager_activity",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("manager_id", sa.Uuid(), sa.ForeignKey("platform_sales_managers.id", ondelete="CASCADE"), nullable=False),
            sa.Column("session_id", sa.Uuid(), sa.ForeignKey("platform_sales_manager_sessions.id", ondelete="SET NULL")),
            sa.Column("action", sa.String(100), nullable=False),
            sa.Column("details", sa.JSON(), nullable=False),
            sa.Column("ip_address", sa.String(80)),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        for column in ("manager_id", "session_id", "action", "created_at"):
            op.create_index(f"ix_platform_sales_manager_activity_{column}", "platform_sales_manager_activity", [column])

    if not inspector.has_table("platform_sales_daily_reports"):
        op.create_table(
            "platform_sales_daily_reports",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("manager_id", sa.Uuid(), sa.ForeignKey("platform_sales_managers.id", ondelete="CASCADE"), nullable=False),
            sa.Column("report_date", sa.Date(), nullable=False),
            sa.Column("summary", sa.Text()),
            sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("manager_id", "report_date"),
        )
        for column in ("manager_id", "report_date", "submitted_at"):
            op.create_index(f"ix_platform_sales_daily_reports_{column}", "platform_sales_daily_reports", [column])

    if not inspector.has_table("platform_sales_clinic_contacts"):
        op.create_table(
            "platform_sales_clinic_contacts",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("report_id", sa.Uuid(), sa.ForeignKey("platform_sales_daily_reports.id", ondelete="CASCADE"), nullable=False),
            sa.Column("manager_id", sa.Uuid(), sa.ForeignKey("platform_sales_managers.id", ondelete="CASCADE"), nullable=False),
            sa.Column("clinic_name", sa.String(200), nullable=False),
            sa.Column("country", sa.String(80)),
            sa.Column("city", sa.String(100)),
            sa.Column("address", sa.String(300)),
            sa.Column("website", sa.String(300)),
            sa.Column("contact_name", sa.String(160)),
            sa.Column("contact_role", sa.String(120)),
            sa.Column("email", sa.String(320)),
            sa.Column("phone", sa.String(50)),
            sa.Column("negotiation_result", sa.Text(), nullable=False),
            sa.Column("outcome", sa.String(60), nullable=False),
            sa.Column("next_step", sa.Text()),
            sa.Column("follow_up_date", sa.Date()),
            sa.Column("clinic_name_norm", sa.String(220), nullable=False),
            sa.Column("email_norm", sa.String(320)),
            sa.Column("phone_norm", sa.String(60)),
            sa.Column("website_norm", sa.String(220)),
            sa.Column("city_norm", sa.String(120)),
            sa.Column("address_norm", sa.String(320)),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        for column in ("report_id", "manager_id", "clinic_name", "email", "phone", "outcome", "follow_up_date", "clinic_name_norm", "email_norm", "phone_norm", "website_norm", "city_norm", "created_at"):
            op.create_index(f"ix_platform_sales_clinic_contacts_{column}", "platform_sales_clinic_contacts", [column])

    if not inspector.has_table("platform_sales_clinic_attributions"):
        op.create_table(
            "platform_sales_clinic_attributions",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("manager_id", sa.Uuid(), sa.ForeignKey("platform_sales_managers.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("clinic_id", sa.Uuid(), nullable=False),
            sa.Column("access_request_id", sa.Uuid()),
            sa.Column("clinic_contact_id", sa.Uuid(), sa.ForeignKey("platform_sales_clinic_contacts.id", ondelete="SET NULL")),
            sa.Column("match_score", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("matched_signals", sa.JSON(), nullable=False),
            sa.Column("status", sa.String(40), nullable=False, server_default="AUTO_CONFIRMED"),
            sa.Column("attributed_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("clinic_id"),
            sa.UniqueConstraint("access_request_id"),
        )
        for column in ("manager_id", "clinic_id", "access_request_id", "clinic_contact_id", "status", "attributed_at"):
            op.create_index(f"ix_platform_sales_clinic_attributions_{column}", "platform_sales_clinic_attributions", [column])

    if not inspector.has_table("platform_subscription_payments"):
        op.create_table(
            "platform_subscription_payments",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("clinic_id", sa.Uuid(), nullable=False),
            sa.Column("access_request_id", sa.Uuid()),
            sa.Column("kind", sa.String(30), nullable=False),
            sa.Column("amount", sa.Integer(), nullable=False),
            sa.Column("currency", sa.String(12), nullable=False),
            sa.Column("reference", sa.String(200)),
            sa.Column("note", sa.Text()),
            sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("access_request_id"),
        )
        for column in ("clinic_id", "access_request_id", "kind", "verified_at"):
            op.create_index(f"ix_platform_subscription_payments_{column}", "platform_subscription_payments", [column])

    if not inspector.has_table("platform_sales_commissions"):
        op.create_table(
            "platform_sales_commissions",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("manager_id", sa.Uuid(), sa.ForeignKey("platform_sales_managers.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("clinic_id", sa.Uuid(), nullable=False),
            sa.Column("payment_id", sa.Uuid(), sa.ForeignKey("platform_subscription_payments.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("attribution_id", sa.Uuid(), sa.ForeignKey("platform_sales_clinic_attributions.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("rate_bps", sa.Integer(), nullable=False, server_default="3000"),
            sa.Column("gross_amount", sa.Integer(), nullable=False),
            sa.Column("commission_amount", sa.Integer(), nullable=False),
            sa.Column("currency", sa.String(12), nullable=False),
            sa.Column("status", sa.String(30), nullable=False, server_default="AVAILABLE"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("payment_id"),
        )
        for column in ("manager_id", "clinic_id", "payment_id", "attribution_id", "currency", "status", "created_at"):
            op.create_index(f"ix_platform_sales_commissions_{column}", "platform_sales_commissions", [column])

    if not inspector.has_table("platform_sales_withdrawals"):
        op.create_table(
            "platform_sales_withdrawals",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("manager_id", sa.Uuid(), sa.ForeignKey("platform_sales_managers.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("currency", sa.String(12), nullable=False),
            sa.Column("amount", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(30), nullable=False, server_default="REQUESTED"),
            sa.Column("bank_card_ciphertext", sa.Text(), nullable=False),
            sa.Column("bank_card_last4", sa.String(4), nullable=False),
            sa.Column("bank_card_holder", sa.String(180)),
            sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("processed_at", sa.DateTime(timezone=True)),
            sa.Column("payment_reference", sa.String(200)),
            sa.Column("admin_note", sa.Text()),
        )
        for column in ("manager_id", "currency", "status", "requested_at", "processed_at"):
            op.create_index(f"ix_platform_sales_withdrawals_{column}", "platform_sales_withdrawals", [column])


def downgrade() -> None:
    if os.getenv("MIGRATION_PLANE", "clinic") != "control":
        return
    for table in (
        "platform_sales_withdrawals",
        "platform_sales_commissions",
        "platform_subscription_payments",
        "platform_sales_clinic_attributions",
        "platform_sales_clinic_contacts",
        "platform_sales_daily_reports",
        "platform_sales_manager_activity",
        "platform_sales_manager_sessions",
        "platform_sales_managers",
    ):
        op.drop_table(table)
