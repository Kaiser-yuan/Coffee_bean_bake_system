"""purchase batch inventory tracking mode and opening stock

Revision ID: 0004_purchase_batch_inventory_opening
Revises: 0003_widen_curve_version
Create Date: 2026-06-22

Adds ``inventory_tracking_mode`` and ``opening_stock_grams`` to
purchase_batches so historical-archive purchases do not create
phantom stock.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004_pb_inventory_opening"
down_revision: Union[str, None] = "0003_widen_curve_version"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "purchase_batches",
        sa.Column(
            "inventory_tracking_mode",
            sa.String(32),
            nullable=False,
            server_default="normal",
        ),
    )
    op.add_column(
        "purchase_batches",
        sa.Column("opening_stock_grams", sa.Integer, nullable=True),
    )
    # Backfill existing batches: opening_stock = total_weight
    op.execute(
        "UPDATE purchase_batches SET opening_stock_grams = total_weight_grams"
    )


def downgrade() -> None:
    op.drop_column("purchase_batches", "opening_stock_grams")
    op.drop_column("purchase_batches", "inventory_tracking_mode")
