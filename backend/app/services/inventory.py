"""Inventory calculation service."""
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
    remaining_weight_grams
    = total_weight_grams
    - SUM(completed & valid roasting batch actual_input_weight_grams)
    + SUM(inventory adjustment amount_grams)
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

    # Sum of inventory adjustments
    result = await db.execute(
        select(func.coalesce(func.sum(InventoryAdjustment.amount_grams), 0))
        .where(InventoryAdjustment.purchase_batch_id == purchase_batch_id)
    )
    adjustment_sum = result.scalar_one()

    remaining = pb.total_weight_grams - roast_consumed + adjustment_sum
    return max(0, remaining)


async def check_and_record_inventory(
    db: AsyncSession,
    purchase_batch_id: str,
    required_grams: int,
    event_type: str,
    related_entity_type: str,
    related_entity_id: str,
) -> int:
    """
    Validate inventory sufficiency, record a ledger entry,
    and return the new resulting balance.
    Raises InsufficientInventoryException if not enough.
    """
    from ..core.exceptions import InsufficientInventoryException

    current = await calculate_remaining_stock(db, purchase_batch_id)

    if event_type == "roast_consumption" and required_grams > current:
        raise InsufficientInventoryException(
            available_grams=current, required_grams=required_grams
        )

    new_balance = current - required_grams if event_type == "roast_consumption" else current + required_grams

    # Record ledger entry
    entry = InventoryLedger(
        purchase_batch_id=purchase_batch_id,
        event_type=event_type,
        change_grams=-required_grams if event_type == "roast_consumption" else required_grams,
        resulting_grams=new_balance,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
    )
    db.add(entry)

    return new_balance
