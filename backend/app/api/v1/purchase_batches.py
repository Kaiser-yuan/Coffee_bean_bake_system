"""Purchase batches API."""
from datetime import datetime, timezone

from fastapi import APIRouter

from ..dependencies import CurrentUserDep, DBSessionDep
from ...core.exceptions import NotFoundException, ValidationException
from ...models.all_models import InventoryAdjustment
from ...repositories.purchase_batches import PurchaseBatchRepository, InventoryLedgerRepository
from ...services.inventory import calculate_remaining_stock, append_inventory_ledger, lock_purchase_batch
from ...schemas.all_schemas import (
    PurchaseBatchResponse, InventoryLedgerResponse, InventoryAdjustmentRequest,
)

router = APIRouter(prefix="/purchase-batches", tags=["purchase-batches"])


@router.get("/{purchase_batch_id}")
async def get_purchase_batch(
    purchase_batch_id: str,
    db: DBSessionDep = None,
    _user: CurrentUserDep = None,
):
    """Get purchase batch detail with remaining stock."""
    repo = PurchaseBatchRepository(db)
    pb = await repo.get_detail(purchase_batch_id)
    if not pb:
        raise NotFoundException("PurchaseBatch", purchase_batch_id)

    remaining = await calculate_remaining_stock(db, purchase_batch_id)

    return PurchaseBatchResponse(
        id=pb.id,
        green_bean_id=pb.green_bean_id,
        purchase_date=pb.purchase_date.isoformat() if pb.purchase_date else None,
        total_weight_grams=pb.total_weight_grams,
        inventory_tracking_mode=pb.inventory_tracking_mode,
        opening_stock_grams=pb.opening_stock_grams,
        moisture_content_percent=pb.moisture_content_percent,
        unit_price_fen_per_kg=pb.unit_price_fen_per_kg,
        total_price_fen=pb.total_price_fen,
        supplier=pb.supplier.value if pb.supplier else None,
        lot_number=pb.lot_number,
        notes=pb.notes,
        remaining_weight_grams=remaining,
        allowed_actions=["create_roast_plan", "create_inventory_adjustment"],
    )


@router.get("/{purchase_batch_id}/inventory-ledger")
async def get_inventory_ledger(
    purchase_batch_id: str,
    db: DBSessionDep = None,
    _user: CurrentUserDep = None,
):
    """Get inventory change history for a purchase batch."""
    ledger_repo = InventoryLedgerRepository(db)
    entries = await ledger_repo.get_ledger_by_purchase_batch(purchase_batch_id)
    return [
        InventoryLedgerResponse(
            id=e.id,
            event_type=e.event_type,
            related_entity_type=e.related_entity_type,
            related_entity_id=e.related_entity_id,
            change_grams=e.change_grams,
            resulting_grams=e.resulting_grams,
            created_at=e.created_at.isoformat() if e.created_at else "",
        )
        for e in entries
    ]


@router.post("/{purchase_batch_id}/inventory-adjustments", status_code=201)
async def create_inventory_adjustment(
    purchase_batch_id: str,
    body: InventoryAdjustmentRequest,
    db: DBSessionDep = None,
    _user: CurrentUserDep = None,
):
    """Create a manual inventory adjustment.

    Uses pessimistic locking on the purchase batch row.
    amount_grams can be positive (increase) or negative (decrease).
    """
    # Pessimistic lock
    pb = await lock_purchase_batch(db, purchase_batch_id)
    if not pb:
        raise NotFoundException("PurchaseBatch", purchase_batch_id)

    # amount_grams must not be zero
    if body.amount_grams == 0:
        raise ValidationException("库存调整金额不能为 0")

    # Check that negative adjustment doesn't exceed inventory
    if body.amount_grams < 0:
        remaining = await calculate_remaining_stock(db, purchase_batch_id)
        if abs(body.amount_grams) > remaining:
            from ...core.exceptions import InsufficientInventoryException
            raise InsufficientInventoryException(
                available_grams=remaining,
                required_grams=abs(body.amount_grams),
            )

    adjustment = InventoryAdjustment(
        purchase_batch_id=purchase_batch_id,
        adjustment_date=datetime.now(timezone.utc),
        amount_grams=body.amount_grams,
        reason=body.reason,
        notes=body.notes,
    )
    db.add(adjustment)
    await db.flush()

    # Record ledger with actual change (can be negative)
    await append_inventory_ledger(
        db=db,
        purchase_batch_id=purchase_batch_id,
        change_grams=body.amount_grams,
        event_type="adjustment",
        related_entity_type="inventory_adjustment",
        related_entity_id=adjustment.id,
    )

    return {"id": adjustment.id, "status": "created"}
