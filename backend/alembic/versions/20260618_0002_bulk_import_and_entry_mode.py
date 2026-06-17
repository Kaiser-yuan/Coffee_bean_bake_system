"""bulk import and entry mode

Revision ID: 0002_bulk_import_and_entry_mode
Revises: 0001_initial_schema
Create Date: 2026-06-18

Adds backfill / bulk-import metadata to roasting_batches and introduces
the bulk_import_jobs + bulk_import_items tables used by the multi-CSV
roast generation and historical backfill features.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "0002_bulk_import_and_entry_mode"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -- roasting_batches: entry / backfill metadata --
    op.add_column(
        "roasting_batches",
        sa.Column(
            "entry_mode", sa.String(32), nullable=False, server_default="manual_plan",
        ),
    )
    op.add_column(
        "roasting_batches",
        sa.Column(
            "inventory_effective", sa.Boolean, nullable=False, server_default=sa.true(),
        ),
    )
    op.add_column("roasting_batches", sa.Column("roasted_at_source", sa.String(32)))
    op.add_column("roasting_batches", sa.Column("bulk_import_group_id", UUID(as_uuid=False)))
    op.add_column("roasting_batches", sa.Column("source_note", sa.Text))

    # -- bulk_import_jobs --
    op.create_table(
        "bulk_import_jobs",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "purchase_batch_id", UUID(as_uuid=False),
            sa.ForeignKey("purchase_batches.id"), nullable=True,
        ),
        sa.Column("mode", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="previewed"),
        sa.Column("file_count", sa.Integer, nullable=False),
        sa.Column("success_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("default_input_weight_grams", sa.Integer),
        sa.Column(
            "inventory_effective_default", sa.Boolean, nullable=False, server_default=sa.true(),
        ),
        sa.Column("created_by", UUID(as_uuid=False)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("committed_at", sa.DateTime(timezone=True)),
        sa.Column("notes", sa.Text),
    )
    op.create_index("ix_bulk_import_jobs_purchase_batch_id", "bulk_import_jobs", ["purchase_batch_id"])

    # -- bulk_import_items --
    op.create_table(
        "bulk_import_items",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "job_id", UUID(as_uuid=False),
            sa.ForeignKey("bulk_import_jobs.id"), nullable=False,
        ),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("file_hash", sa.String(64), nullable=False),
        sa.Column("file_size_bytes", sa.Integer, nullable=False),
        sa.Column("client_last_modified_at", sa.DateTime(timezone=True)),
        sa.Column("inferred_roasted_at", sa.DateTime(timezone=True)),
        sa.Column("roasted_at_source", sa.String(32)),
        sa.Column("display_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("parse_status", sa.String(16), nullable=False, server_default="parsed"),
        sa.Column("parse_error_message", sa.Text),
        sa.Column("warnings", sa.JSON),
        sa.Column("preview_summary", sa.JSON),
        sa.Column(
            "roasting_batch_id", UUID(as_uuid=False),
            sa.ForeignKey("roasting_batches.id"), nullable=True,
        ),
        sa.Column(
            "curve_file_id", UUID(as_uuid=False),
            sa.ForeignKey("curve_files.id"), nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_bulk_import_items_job_id", "bulk_import_items", ["job_id"])


def downgrade() -> None:
    op.drop_table("bulk_import_items")
    op.drop_table("bulk_import_jobs")
    op.drop_column("roasting_batches", "source_note")
    op.drop_column("roasting_batches", "bulk_import_group_id")
    op.drop_column("roasting_batches", "roasted_at_source")
    op.drop_column("roasting_batches", "inventory_effective")
    op.drop_column("roasting_batches", "entry_mode")
