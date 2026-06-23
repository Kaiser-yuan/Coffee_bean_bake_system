"""public evaluation free_flavor_description, purchase batch constraints, seed form vocab

Revision ID: 0005_eval_and_purchase_constraints
Revises: 0004_pb_inventory_opening
Create Date: 2026-06-23

1. Add ``free_flavor_description`` to ``cupping_evaluations`` — free-text
   flavor descriptions are stored here and never enter ``standard_terms``
   (P1-2: public evaluations may only reference active standard terms).

2. Add CHECK constraints to ``purchase_batches`` so the inventory-tracking
   mode and opening stock are valid at the DB level (P1-3):
   - mode IN ('normal', 'historical_archive')
   - opening_stock_grams >= 0
   - opening_stock_grams <= total_weight_grams  (NULL opening still allowed)

3. Seed the brew_method / flavor standard terms that the public evaluation
   form's chips submit, so valid submissions resolve instead of 422-ing.
   Idempotent via ON CONFLICT DO NOTHING.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import insert as pg_insert

# revision identifiers, used by Alembic.
revision: str = "0005_eval_purchase_cnstr"
down_revision: Union[str, None] = "0004_pb_inventory_opening"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Standard terms the public evaluation form submits (must already exist &
# be active for a submission to resolve, otherwise 422 — never auto-created).
_FORM_VOCAB: dict[str, list[str]] = {
    "brew_method": ["杯测", "手冲", "意式", "奶咖", "其他"],
    "flavor": [
        "花香", "柑橘", "莓果", "核果", "巧克力", "坚果", "焦糖",
        "香料", "草本", "发酵", "酒香", "烟熏", "茶感", "热带水果",
    ],
}


def upgrade() -> None:
    # 1. free_flavor_description column
    op.add_column(
        "cupping_evaluations",
        sa.Column(
            "free_flavor_description",
            sa.Text,
            nullable=True,
            comment="自由风味描述（不进入标准词表）",
        ),
    )

    # 2. purchase_batches constraints
    op.create_check_constraint(
        "ck_pb_inventory_mode_valid",
        "purchase_batches",
        "inventory_tracking_mode IN ('normal', 'historical_archive')",
    )
    op.create_check_constraint(
        "ck_pb_opening_nonneg",
        "purchase_batches",
        "opening_stock_grams IS NULL OR opening_stock_grams >= 0",
    )
    op.create_check_constraint(
        "ck_pb_opening_le_total",
        "purchase_batches",
        "opening_stock_grams IS NULL OR opening_stock_grams <= total_weight_grams",
    )

    # 3. seed form vocab (idempotent)
    terms_table = sa.table(
        "standard_terms",
        sa.column("id"),
        sa.column("category"),
        sa.column("value"),
        sa.column("display_order"),
        sa.column("is_active"),
        sa.column("usage_count"),
        sa.column("created_at"),
    )
    for category, values in _FORM_VOCAB.items():
        for display_order, value in enumerate(values):
            op.execute(
                pg_insert(terms_table)
                .values(
                    id=sa.func.gen_random_uuid(),
                    category=category,
                    value=value,
                    display_order=display_order,
                    is_active=True,
                    usage_count=0,
                    created_at=sa.func.now(),
                )
                .on_conflict_do_nothing(index_elements=["category", "value"])
            )


def downgrade() -> None:
    op.drop_column("cupping_evaluations", "free_flavor_description")
    op.drop_constraint("ck_pb_opening_le_total", "purchase_batches", type_="check")
    op.drop_constraint("ck_pb_opening_nonneg", "purchase_batches", type_="check")
    op.drop_constraint("ck_pb_inventory_mode_valid", "purchase_batches", type_="check")
    # Seeded terms are not removed on downgrade — they may have been created
    # independently by the admin seed script.
