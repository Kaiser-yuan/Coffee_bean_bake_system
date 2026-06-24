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
    remaining = opening_stock
              - SUM(completed, inventory_effective roasting batches actual_input_weight_grams)
              + SUM(inventory adjustments amount_grams)

    ``opening_stock`` is ``opening_stock_grams`` if explicitly set, otherwise
    ``total_weight_grams``.  For ``inventory_tracking_mode = historical_archive``
    this defaults to 0, so the batch does not contribute phantom stock.

    Only batches that are both ``completed`` and ``inventory_effective=True``
    count as consumed — historical backfill / archive-only batches
    (inventory_effective=False) do not affect current stock.

    This is the *fact* calculation — the single source of truth.
    """
    # Get purchase batch
    result = await db.execute(
        select(PurchaseBatch).where(PurchaseBatch.id == purchase_batch_id)
    )
    pb = result.scalar_one_or_none()
    if not pb:
        return 0

    # Opening stock: explicit value or total_weight_grams
    opening = (
        pb.opening_stock_grams
        if pb.opening_stock_grams is not None
        else pb.total_weight_grams
    )

    # Sum of completed, inventory-effective roast batch inputs
    result = await db.execute(
        select(func.coalesce(func.sum(RoastingBatch.actual_input_weight_grams), 0))
        .where(
            RoastingBatch.purchase_batch_id == purchase_batch_id,
            RoastingBatch.status == "completed",
            RoastingBatch.inventory_effective.is_(True),
        )
    )
    roast_consumed = result.scalar_one()

    # Sum of inventory adjustments (can be negative)
    result = await db.execute(
        select(func.coalesce(func.sum(InventoryAdjustment.amount_grams), 0))
        .where(InventoryAdjustment.purchase_batch_id == purchase_batch_id)
    )
    adjustment_sum = result.scalar_one()

    remaining = opening - roast_consumed + adjustment_sum
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

    For a new purchase batch, ``change_grams`` should be the *opening stock*
    (``opening_stock_grams ?? total_weight_grams``), NOT blindly the full
    ``total_weight_grams``.
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


async def calculate_remaining_stocks(
    db: AsyncSession,
    purchase_batch_ids: list[str],
) -> dict[str, int]:
    """Batch version of ``calculate_remaining_stock`` — one round-trip for all IDs.

    Uses aggregate subqueries so the N+1 problem in the green-bean tree
    endpoint (one query per purchase batch) is eliminated.
    """
    if not purchase_batch_ids:
        return {}

    # Fetch purchase batches in bulk
    result = await db.execute(
        select(PurchaseBatch).where(PurchaseBatch.id.in_(purchase_batch_ids))
    )
    pbs = list(result.scalars().all())
    pb_map = {pb.id: pb for pb in pbs}

    # Sum completed, inventory-effective roast batch inputs per purchase batch
    consumed_subq = (
        select(
            RoastingBatch.purchase_batch_id,
            func.coalesce(func.sum(RoastingBatch.actual_input_weight_grams), 0).label("consumed"),
        )
        .where(
            RoastingBatch.purchase_batch_id.in_(purchase_batch_ids),
            RoastingBatch.status == "completed",
            RoastingBatch.inventory_effective.is_(True),
        )
        .group_by(RoastingBatch.purchase_batch_id)
    ).subquery()

    # Sum adjustment amounts per purchase batch
    adj_subq = (
        select(
            InventoryAdjustment.purchase_batch_id,
            func.coalesce(func.sum(InventoryAdjustment.amount_grams), 0).label("adjustments"),
        )
        .where(InventoryAdjustment.purchase_batch_id.in_(purchase_batch_ids))
        .group_by(InventoryAdjustment.purchase_batch_id)
    ).subquery()

    # One join to compute all remainders
    combined = (
        select(
            PurchaseBatch.id.label("pb_id"),
            (
                func.coalesce(PurchaseBatch.opening_stock_grams, PurchaseBatch.total_weight_grams)
                - func.coalesce(consumed_subq.c.consumed, 0)
                + func.coalesce(adj_subq.c.adjustments, 0)
            ).label("remaining"),
        )
        .outerjoin(consumed_subq, consumed_subq.c.purchase_batch_id == PurchaseBatch.id)
        .outerjoin(adj_subq, adj_subq.c.purchase_batch_id == PurchaseBatch.id)
        .where(PurchaseBatch.id.in_(purchase_batch_ids))
    )
    result2 = await db.execute(combined)
    rows = result2.all()

    result_dict: dict[str, int] = {}
    for row in rows:
        remaining = row.remaining or 0
        result_dict[row.pb_id] = max(0, remaining)

    # Ensure every requested ID has an entry (default to 0 if PB not found)
    for bid in purchase_batch_ids:
        if bid not in result_dict:
            result_dict[bid] = 0

    return result_dict
