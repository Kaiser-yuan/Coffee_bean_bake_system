"""Widen roasting curve calculation version.

Revision ID: 0003_widen_curve_version
Revises: 0002_bulk_import_and_entry_mode
Create Date: 2026-06-21
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_widen_curve_version"
down_revision: Union[str, None] = "0002_bulk_import_and_entry_mode"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "roasting_curves",
        "calculation_version",
        existing_type=sa.String(16),
        type_=sa.String(32),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "roasting_curves",
        "calculation_version",
        existing_type=sa.String(32),
        type_=sa.String(16),
        existing_nullable=True,
    )
