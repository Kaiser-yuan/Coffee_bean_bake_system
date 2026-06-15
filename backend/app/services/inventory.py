"""Inventory calculation service.

Separates "inventory fact calculation" from "ledger recording".
The fact calculation is the source of truth. The ledger records
what happened — its resulting_grams comes from the fact calculation,
not from ledger arithmetic.
"""
import logging

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.all_models import (
    PurchaseBatch, RoastingBatch, InventoryAdjustment, InventoryLedger,
)

logger = logging.getLogger("coffee-roast.inventory")


async def calculate_remaining_stock(
    db: AsyncSession, purchase_batch_id: str
) -> int:
    """
    remaining = total_weight_grams
              - SUM(completed roasting batches actual_input_weight_grams)
              + SUM(inventory adjustments amount_grams)

    This is the *fact* calculation — the single source of truth.
    """
    # Get purchase batch
    result = await db.execute(
        select(PurchaseBatch).where(PurchaseBatch.id == purchase_batch_id)
    )
    pb = result.scalar_one_or_none()
    if not pb:
        return 0

    # Sum of completed, non-voided roast batch inputs
    result = await db.execute(
        select(func.coalesce(func.sum(RoastingBatch.actual_input_weight_grams), 0))
        .where(
            RoastingBatch.purchase_batch_id == purchase_batch_id,
            RoastingBatch.status == "completed",
        )
    )
    roast_consumed = result.scalar_one()

    # Sum of inventory adjustments (can be negative)
    result = await db.execute(
        select(func.coalesce(func.sum(InventoryAdjustment.amount_grams), 0))
        .where(InventoryAdjustment.purchase_batch_id == purchase_batch_id)
    )
    adjustment_sum = result.scalar_one()

    remaining = pb.total_weight_grams - roast_consumed + adjustment_sum
    return max(0, remaining)


async def append_inventory_ledger(
    db: AsyncSession,
    purchase_batch_id: str,
    change_grams: int,
    event_type: str,
    related_entity_type: str | None = None,
    related_entity_id: str | None = None,
) -> InventoryLedger:
    """Append a ledger entry.

    change_grams: negative for consumption, positive for returns/adjustments.
    resulting_grams is computed from the fact calculation AFTER the change
    has been applied to the DB, so it always reflects reality.
    """
    resulting = await calculate_remaining_stock(db, purchase_batch_id)

    entry = InventoryLedger(
        purchase_batch_id=purchase_batch_id,
        event_type=event_type,
        change_grams=change_grams,
        resulting_grams=resulting,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
    )
    db.add(entry)
    return entry


async def lock_purchase_batch(
    db: AsyncSession, purchase_batch_id: str
) -> PurchaseBatch | None:
    """Pessimistic lock on a purchase batch row for inventory mutations."""
    result = await db.execute(
        select(PurchaseBatch)
        .where(PurchaseBatch.id == purchase_batch_id)
        .with_for_update()
    )
    return result.scalar_one_or_none()
