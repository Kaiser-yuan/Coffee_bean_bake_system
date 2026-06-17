"""Initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-06-16

Explicit op.create_table / op.create_index / op.create_foreign_key
instead of Base.metadata.create_all/drop_all, so the migration is a
frozen, reviewable history of the schema and downgrade only drops the
tables that belong to this project (in reverse dependency order).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. users
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("hashed_password", sa.String(256), nullable=False),
        sa.Column("display_name", sa.String(128)),
        sa.Column("is_admin", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    # 2. standard_terms
    op.create_table(
        "standard_terms",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("value", sa.String(128), nullable=False),
        sa.Column("display_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("usage_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("category", "value", name="uq_term_category_value"),
    )
    op.create_index("ix_standard_terms_category", "standard_terms", ["category"])

    # 3. green_beans
    op.create_table(
        "green_beans",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("variety_term_id", UUID(as_uuid=False), sa.ForeignKey("standard_terms.id")),
        sa.Column("process_term_id", UUID(as_uuid=False), sa.ForeignKey("standard_terms.id")),
        sa.Column("region", sa.String(128)),
        sa.Column("country", sa.String(128)),
        sa.Column("farm", sa.String(256)),
        sa.Column("elevation", sa.String(64)),
        sa.Column("brand", sa.String(128)),
        sa.Column("harvest_season", sa.String(64)),
        sa.Column("vendor_flavor_description", sa.Text),
        sa.Column("first_created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_green_beans_name", "green_beans", ["name"])

    # 4. purchase_batches
    op.create_table(
        "purchase_batches",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("green_bean_id", UUID(as_uuid=False), sa.ForeignKey("green_beans.id"), nullable=False),
        sa.Column("purchase_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total_weight_grams", sa.Integer, nullable=False),
        sa.Column("moisture_content_percent", sa.Float),
        sa.Column("unit_price_fen_per_kg", sa.BigInteger),
        sa.Column("total_price_fen", sa.BigInteger),
        sa.Column("supplier_term_id", UUID(as_uuid=False), sa.ForeignKey("standard_terms.id")),
        sa.Column("lot_number", sa.String(64)),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("total_weight_grams > 0", name="ck_pb_weight_positive"),
    )
    op.create_index("ix_purchase_batches_green_bean_id", "purchase_batches", ["green_bean_id"])

    # 5. inventory_adjustments
    op.create_table(
        "inventory_adjustments",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("purchase_batch_id", UUID(as_uuid=False), sa.ForeignKey("purchase_batches.id"), nullable=False),
        sa.Column("adjustment_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("amount_grams", sa.Integer, nullable=False),
        sa.Column("reason", sa.String(256), nullable=False),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_inventory_adjustments_purchase_batch_id", "inventory_adjustments", ["purchase_batch_id"])

    # 6. roasting_batches
    op.create_table(
        "roasting_batches",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("purchase_batch_id", UUID(as_uuid=False), sa.ForeignKey("purchase_batches.id"), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="planned"),
        sa.Column("planned_at", sa.DateTime(timezone=True)),
        sa.Column("roasted_at", sa.DateTime(timezone=True)),
        sa.Column("planned_input_weight_grams", sa.Integer, nullable=False),
        sa.Column("actual_input_weight_grams", sa.Integer),
        sa.Column("output_weight_grams", sa.Integer),
        sa.Column("weight_loss_percent", sa.Float),
        sa.Column("total_time_seconds", sa.Integer),
        sa.Column("development_time_seconds", sa.Integer),
        sa.Column("development_ratio_percent", sa.Float),
        sa.Column("roast_level_term_id", UUID(as_uuid=False), sa.ForeignKey("standard_terms.id")),
        sa.Column("target_description", sa.Text),
        sa.Column("color_tag", sa.String(7)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("planned_input_weight_grams > 0", name="ck_rb_weight_positive"),
    )
    op.create_index("ix_roasting_batches_purchase_batch_id", "roasting_batches", ["purchase_batch_id"])
    op.create_index("ix_roasting_batches_status", "roasting_batches", ["status"])

    # 7. curve_files
    op.create_table(
        "curve_files",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("roasting_batch_id", UUID(as_uuid=False), sa.ForeignKey("roasting_batches.id"), nullable=False),
        sa.Column("original_filename", sa.String(512), nullable=False),
        sa.Column("storage_path", sa.String(1024), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger, nullable=False),
        sa.Column("file_hash", sa.String(64), nullable=False),
        sa.Column("source_type", sa.String(32), nullable=False, server_default="kaleido_m1"),
        sa.Column("format_type", sa.String(32), nullable=False, server_default="kaleido_kldo_v101"),
        sa.Column("parse_status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("parse_error_code", sa.String(64)),
        sa.Column("parse_error_message", sa.Text),
        sa.Column("parser_version", sa.String(16)),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("parsed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_curve_files_roasting_batch_id", "curve_files", ["roasting_batch_id"])

    # 8. roasting_curves
    op.create_table(
        "roasting_curves",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("roasting_batch_id", UUID(as_uuid=False), sa.ForeignKey("roasting_batches.id"), nullable=False),
        sa.Column("curve_file_id", UUID(as_uuid=False), sa.ForeignKey("curve_files.id"), nullable=False),
        sa.Column("preheat_temp_celsius", sa.Float),
        sa.Column("total_time_seconds", sa.Float),
        sa.Column("charge_seconds", sa.Float, server_default="0.0"),
        sa.Column("turning_point_seconds", sa.Float),
        sa.Column("yellowing_seconds", sa.Float),
        sa.Column("first_crack_start_seconds", sa.Float),
        sa.Column("first_crack_end_seconds", sa.Float),
        sa.Column("second_crack_start_seconds", sa.Float),
        sa.Column("second_crack_end_seconds", sa.Float),
        sa.Column("drop_seconds", sa.Float),
        sa.Column("drying_time_seconds", sa.Float),
        sa.Column("drying_ratio_percent", sa.Float),
        sa.Column("maillard_time_seconds", sa.Float),
        sa.Column("maillard_ratio_percent", sa.Float),
        sa.Column("development_time_seconds", sa.Float),
        sa.Column("development_ratio_percent", sa.Float),
        sa.Column("points", sa.JSON),
        sa.Column("events", sa.JSON),
        sa.Column("stages", sa.JSON),
        sa.Column("control_changes", sa.JSON),
        sa.Column("calculation_version", sa.String(16)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_roasting_curves_roasting_batch_id", "roasting_curves", ["roasting_batch_id"], unique=True)

    # 9. questionnaires
    op.create_table(
        "questionnaires",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("roasting_batch_id", UUID(as_uuid=False), sa.ForeignKey("roasting_batches.id"), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="open"),
        sa.Column("share_code", sa.String(32), nullable=False),
        sa.Column("share_url", sa.String(512)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.Column("submission_count", sa.Integer, nullable=False, server_default="0"),
    )
    op.create_index("ix_questionnaires_roasting_batch_id", "questionnaires", ["roasting_batch_id"])
    op.create_index("ix_questionnaires_share_code", "questionnaires", ["share_code"], unique=True)

    # 10. cupping_evaluations
    op.create_table(
        "cupping_evaluations",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("questionnaire_id", UUID(as_uuid=False), sa.ForeignKey("questionnaires.id"), nullable=False),
        sa.Column("roasting_batch_id", UUID(as_uuid=False), sa.ForeignKey("roasting_batches.id"), nullable=False),
        sa.Column("evaluator_name", sa.String(64)),
        sa.Column("evaluator_type", sa.String(16)),
        sa.Column("brew_method_term_id", UUID(as_uuid=False), sa.ForeignKey("standard_terms.id")),
        sa.Column("drink_temperature", sa.String(8)),
        sa.Column("drink_form", sa.String(16)),
        sa.Column("dry_fragrance_score", sa.Integer),
        sa.Column("wet_aroma_score", sa.Integer),
        sa.Column("acidity_intensity_score", sa.Integer),
        sa.Column("sweetness_score", sa.Integer),
        sa.Column("bitterness_intensity_score", sa.Integer),
        sa.Column("aftertaste_score", sa.Integer),
        sa.Column("overall_preference_score", sa.Integer, nullable=False),
        sa.Column("flavor_term_ids", sa.JSON),
        sa.Column("free_notes", sa.Text),
        sa.Column("bean_age_days", sa.Integer),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_cupping_evaluations_questionnaire_id", "cupping_evaluations", ["questionnaire_id"])
    op.create_index("ix_cupping_evaluations_roasting_batch_id", "cupping_evaluations", ["roasting_batch_id"])

    # 11. batch_reviews
    op.create_table(
        "batch_reviews",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("roasting_batch_id", UUID(as_uuid=False), sa.ForeignKey("roasting_batches.id"), nullable=False),
        sa.Column("personal_review", sa.Text),
        sa.Column("personal_review_at", sa.DateTime(timezone=True)),
        sa.Column("evaluation_summary", sa.Text),
        sa.Column("comprehensive_review", sa.Text),
        sa.Column("comprehensive_review_at", sa.DateTime(timezone=True)),
        sa.Column("next_batch_suggestion", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_batch_reviews_roasting_batch_id", "batch_reviews", ["roasting_batch_id"], unique=True)

    # 12. review_reminders
    op.create_table(
        "review_reminders",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("batch_review_id", UUID(as_uuid=False), sa.ForeignKey("batch_reviews.id"), nullable=False),
        sa.Column("priority", sa.Integer, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.CheckConstraint("priority BETWEEN 1 AND 3", name="ck_reminder_priority"),
    )
    op.create_index("ix_review_reminders_batch_review_id", "review_reminders", ["batch_review_id"])

    # 13. batch_reminders
    op.create_table(
        "batch_reminders",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("roasting_batch_id", UUID(as_uuid=False), sa.ForeignKey("roasting_batches.id"), nullable=False),
        # source_* fields are intentionally plain UUIDs without FK constraints
        sa.Column("source_review_id", UUID(as_uuid=False)),
        sa.Column("source_roasting_batch_id", UUID(as_uuid=False)),
        sa.Column("source_review_reminder_id", UUID(as_uuid=False)),
        sa.Column("priority", sa.Integer, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("is_completed", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("priority BETWEEN 1 AND 3", name="ck_batch_rem_priority"),
    )
    op.create_index("ix_batch_reminders_roasting_batch_id", "batch_reminders", ["roasting_batch_id"])

    # 14. inventory_ledger
    op.create_table(
        "inventory_ledger",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("purchase_batch_id", UUID(as_uuid=False), sa.ForeignKey("purchase_batches.id"), nullable=False),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("related_entity_type", sa.String(32)),
        sa.Column("related_entity_id", UUID(as_uuid=False)),
        sa.Column("change_grams", sa.Integer, nullable=False),
        sa.Column("resulting_grams", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_inventory_ledger_purchase_batch_id", "inventory_ledger", ["purchase_batch_id"])


def downgrade() -> None:
    # Reverse dependency order — only drops tables that belong to this project.
    op.drop_table("inventory_ledger")
    op.drop_table("batch_reminders")
    op.drop_table("review_reminders")
    op.drop_table("batch_reviews")
    op.drop_table("cupping_evaluations")
    op.drop_table("questionnaires")
    op.drop_table("roasting_curves")
    op.drop_table("curve_files")
    op.drop_table("roasting_batches")
    op.drop_table("inventory_adjustments")
    op.drop_table("purchase_batches")
    op.drop_table("green_beans")
    op.drop_table("standard_terms")
    op.drop_table("users")
