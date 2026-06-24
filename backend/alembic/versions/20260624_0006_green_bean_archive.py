"""green bean archive / soft-delete + audit timestamp

Revision ID: 0006_green_bean_archive
Revises: 0005_eval_purchase_cnstr
Create Date: 2026-06-24
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006_green_bean_archive"
down_revision: Union[str, None] = "0005_eval_purchase_cnstr"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "green_beans",
        sa.Column("is_archived", sa.Boolean, nullable=False, server_default="false"),
    )
    op.add_column(
        "green_beans", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "green_beans", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("green_beans", "updated_at")
    op.drop_column("green_beans", "archived_at")
    op.drop_column("green_beans", "is_archived")
