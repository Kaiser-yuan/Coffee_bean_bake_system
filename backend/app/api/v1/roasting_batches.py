"""Roasting batches API."""
import random
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter

from ..dependencies import CurrentUserDep, DBSessionDep
from ...core.exceptions import (
    NotFoundException, ValidationException, InvalidBatchStatusException,
    ConflictException, RoastingBatchNotCompletedException,
)
from ...models.all_models import RoastingBatch, Questionnaire
from ...repositories.roasting_batches import RoastingBatchRepository
from ...repositories.purchase_batches import PurchaseBatchRepository
from ...repositories.questionnaires import QuestionnaireRepository
from ...services.inventory import (
    calculate_remaining_stock, append_inventory_ledger, lock_purchase_batch,
)
from ...services.roasting import compute_batch_completeness, compute_allowed_actions
from ...schemas.all_schemas import (
    RoastingBatchCreateRequest, BatchCompleteRequest, OutputWeightUpdateRequest,
    RoastingBatchResponse, BatchCompleteness, QuestionnaireCreateResponse,
)

router = APIRouter(prefix="/roasting-batches", tags=["roasting-batches"])

BATCH_COLORS = ["#df5b45", "#3478d4", "#1f9d68", "#8b5cc7", "#e5a029", "#d94b4b"]


def _to_batch_response(batch: RoastingBatch) -> RoastingBatchResponse:
    gb_name = None
    pb_label = None
    if batch.purchase_batch is not None:
        pb_label = f"PB-{batch.purchase_batch.id[:8]}"
        if batch.purchase_batch.green_bean is not None:
            gb_name = batch.purchase_batch.green_bean.name

    return RoastingBatchResponse(
        id=batch.id,
        purchase_batch_id=batch.purchase_batch_id,
        status=batch.status,
        planned_at=batch.planned_at.isoformat() if batch.planned_at else None,
        roasted_at=batch.roasted_at.isoformat() if batch.roasted_at else None,
        planned_input_weight_grams=batch.planned_input_weight_grams,
        actual_input_weight_grams=batch.actual_input_weight_grams,
        output_weight_grams=batch.output_weight_grams,
        weight_loss_percent=batch.weight_loss_percent,
        total_time_seconds=batch.total_time_seconds,
        development_time_seconds=batch.development_time_seconds,
        development_ratio_percent=batch.development_ratio_percent,
        roast_level=batch.roast_level.value if batch.roast_level is not None else None,
        target_description=batch.target_description,
        color_tag=batch.color_tag,
        completeness=BatchCompleteness(**compute_batch_completeness(batch)),
        allowed_actions=compute_allowed_actions(batch),
        green_bean_name=gb_name,
        purchase_batch_label=pb_label,
    )


@router.get("")
async def list_roasting_batches(
    status: str | None = None,
    purchase_batch_id: str | None = None,
    search: str | None = None,
    has_curve: bool | None = None,
    page: int = 1,
    page_size: int = 20,
    db: DBSessionDep = None,
    _user: CurrentUserDep = None,
):
    """List roasting batches with filters."""
    repo = RoastingBatchRepository(db)
    items, total = await repo.get_list(
        status=status,
        purchase_batch_id=purchase_batch_id,
        search=search,
        has_curve=has_curve,
        page=page,
        page_size=page_size,
    )
    return {
        "items": [_to_batch_response(b) for b in items],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


@router.post("", status_code=201)
async def create_roasting_batch(
    body: RoastingBatchCreateRequest,
    db: DBSessionDep = None,
    _user: CurrentUserDep = None,
):
    """Create a new roasting plan. Does NOT deduct inventory."""
    # Validate purchase batch exists
    pb_repo = PurchaseBatchRepository(db)
    pb = await pb_repo.get_by_id(body.purchase_batch_id)
    if not pb:
        raise NotFoundException("PurchaseBatch", body.purchase_batch_id)

    # Validate weight
    if body.planned_input_weight_grams <= 0:
        raise ValidationException("投豆量必须大于零")

    # Check available inventory (but don't deduct yet)
    remaining = await calculate_remaining_stock(db, body.purchase_batch_id)
    if body.planned_input_weight_grams > remaining:
        from ...core.exceptions import InsufficientInventoryException
        raise InsufficientInventoryException(
            available_grams=remaining,
            required_grams=body.planned_input_weight_grams,
        )

    batch = RoastingBatch(
        purchase_batch_id=body.purchase_batch_id,
        status="planned",
        planned_at=body.planned_at,
        planned_input_weight_grams=body.planned_input_weight_grams,
        target_description=body.target_description,
        color_tag=random.choice(BATCH_COLORS),
    )
    db.add(batch)
    await db.flush()

    # Re-fetch with eager-loaded relationships to avoid MissingGreenlet
    batch = await repo.get_detail(batch.id)
    return _to_batch_response(batch)


@router.post("/{batch_id}/questionnaires", status_code=201)
async def create_questionnaire(
    batch_id: str,
    db: DBSessionDep = None,
    _user: CurrentUserDep = None,
):
    """Create a new evaluation questionnaire for a completed batch."""
    repo = RoastingBatchRepository(db)
    batch = await repo.get_detail(batch_id)
    if not batch:
        raise NotFoundException("RoastingBatch", batch_id)

    if batch.status != "completed":
        raise RoastingBatchNotCompletedException()

    # Check if there's already an open questionnaire
    q_repo = QuestionnaireRepository(db)
    existing_open = await q_repo.get_open_for_batch(batch_id)
    if existing_open:
        raise ConflictException(
            code="QUESTIONNAIRE_ALREADY_OPEN",
            message="该批次已存在进行中的问卷",
            details={"existing_questionnaire_id": existing_open.id},
        )

    from ...services.questionnaire import generate_share_code, generate_share_url
    share_code = generate_share_code()

    q = Questionnaire(
        roasting_batch_id=batch_id,
        status="open",
        share_code=share_code,
        share_url=generate_share_url(share_code),
        created_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
    )
    db.add(q)
    await db.flush()

    return QuestionnaireCreateResponse(
        id=q.id,
        status=q.status,
        share_code=q.share_code,
        share_url=q.share_url or "",
        expires_at=q.expires_at.isoformat() if q.expires_at else None,
    )


@router.get("/{batch_id}")
async def get_roasting_batch(
    batch_id: str,
    db: DBSessionDep = None,
    _user: CurrentUserDep = None,
):
    """Get roasting batch detail."""
    repo = RoastingBatchRepository(db)
    batch = await repo.get_detail(batch_id)
    if not batch:
        raise NotFoundException("RoastingBatch", batch_id)
    return _to_batch_response(batch)


@router.post("/{batch_id}/complete")
async def complete_batch(
    batch_id: str,
    body: BatchCompleteRequest,
    db: DBSessionDep = None,
    _user: CurrentUserDep = None,
):
    """Mark a planned batch as completed. Deducts inventory.

    Uses pessimistic locking on the purchase batch row to prevent
    concurrent completion from driving inventory negative.
    """
    repo = RoastingBatchRepository(db)
    batch = await repo.get_by_id(batch_id)
    if not batch:
        raise NotFoundException("RoastingBatch", batch_id)

    if batch.status != "planned":
        raise InvalidBatchStatusException(batch.status, "planned")

    if body.actual_input_weight_grams <= 0:
        raise ValidationException("实际投豆量必须大于零")

    # Pessimistic lock on purchase batch
    _pb = await lock_purchase_batch(db, batch.purchase_batch_id)
    if not _pb:
        raise NotFoundException("PurchaseBatch", batch.purchase_batch_id)

    # Re-check inventory under lock
    remaining = await calculate_remaining_stock(db, batch.purchase_batch_id)
    if body.actual_input_weight_grams > remaining:
        from ...core.exceptions import InsufficientInventoryException
        raise InsufficientInventoryException(
            available_grams=remaining,
            required_grams=body.actual_input_weight_grams,
        )

    # Update batch
    batch.status = "completed"
    batch.roasted_at = body.roasted_at
    batch.actual_input_weight_grams = body.actual_input_weight_grams
    await db.flush()

    # Record ledger: consumption is negative
    await append_inventory_ledger(
        db=db,
        purchase_batch_id=batch.purchase_batch_id,
        change_grams=-body.actual_input_weight_grams,
        event_type="roast_consumption",
        related_entity_type="roasting_batch",
        related_entity_id=batch.id,
    )
    await db.flush()

    # Re-fetch with eager-loaded relationships to avoid MissingGreenlet
    batch = await repo.get_detail(batch.id)
    return _to_batch_response(batch)


@router.post("/{batch_id}/reopen")
async def reopen_batch(
    batch_id: str,
    db: DBSessionDep = None,
    _user: CurrentUserDep = None,
):
    """Reopen a completed batch. Restores inventory.

    Uses pessimistic locking to prevent race conditions.
    """
    repo = RoastingBatchRepository(db)
    batch = await repo.get_by_id(batch_id)
    if not batch:
        raise NotFoundException("RoastingBatch", batch_id)

    if batch.status != "completed":
        raise InvalidBatchStatusException(batch.status, "completed")

    consumed = batch.actual_input_weight_grams or batch.planned_input_weight_grams

    # Pessimistic lock
    _pb = await lock_purchase_batch(db, batch.purchase_batch_id)
    if not _pb:
        raise NotFoundException("PurchaseBatch", batch.purchase_batch_id)

    # Update batch
    batch.status = "planned"
    batch.roasted_at = None
    batch.actual_input_weight_grams = None
    batch.output_weight_grams = None
    batch.weight_loss_percent = None
    await db.flush()

    # Record ledger: return is positive (restoring inventory)
    await append_inventory_ledger(
        db=db,
        purchase_batch_id=batch.purchase_batch_id,
        change_grams=consumed,
        event_type="roast_return",
        related_entity_type="roasting_batch",
        related_entity_id=batch.id,
    )
    await db.flush()

    # Re-fetch with eager-loaded relationships to avoid MissingGreenlet
    batch = await repo.get_detail(batch.id)
    return _to_batch_response(batch)


@router.post("/{batch_id}/void")
async def void_batch(
    batch_id: str,
    db: DBSessionDep = None,
    _user: CurrentUserDep = None,
):
    """Void a batch. If completed, restores inventory.

    Uses pessimistic locking to prevent race conditions.
    """
    repo = RoastingBatchRepository(db)
    batch = await repo.get_by_id(batch_id)
    if not batch:
        raise NotFoundException("RoastingBatch", batch_id)

    if batch.status == "voided":
        raise InvalidBatchStatusException(batch.status, "planned or completed")

    # If completed, restore inventory under lock
    if batch.status == "completed":
        consumed = batch.actual_input_weight_grams or batch.planned_input_weight_grams

        _pb = await lock_purchase_batch(db, batch.purchase_batch_id)
        if not _pb:
            raise NotFoundException("PurchaseBatch", batch.purchase_batch_id)

        batch.status = "voided"
        await db.flush()

        await append_inventory_ledger(
            db=db,
            purchase_batch_id=batch.purchase_batch_id,
            change_grams=consumed,
            event_type="roast_return",
            related_entity_type="roasting_batch",
            related_entity_id=batch.id,
        )
        await db.flush()
    else:
        batch.status = "voided"
        await db.flush()

    # Re-fetch with eager-loaded relationships to avoid MissingGreenlet
    batch = await repo.get_detail(batch.id)
    return _to_batch_response(batch)


@router.patch("/{batch_id}/output-weight")
async def update_output_weight(
    batch_id: str,
    body: OutputWeightUpdateRequest,
    db: DBSessionDep = None,
    _user: CurrentUserDep = None,
):
    """Record or update the output weight (bean weight after roast)."""
    repo = RoastingBatchRepository(db)
    batch = await repo.get_by_id(batch_id)
    if not batch:
        raise NotFoundException("RoastingBatch", batch_id)

    if batch.status != "completed":
        raise InvalidBatchStatusException(batch.status, "completed")

    if body.output_weight_grams <= 0:
        raise ValidationException("出豆量必须大于零")

    input_weight = batch.actual_input_weight_grams or batch.planned_input_weight_grams
    if body.output_weight_grams > input_weight:
        raise ValidationException("出豆量不能大于投豆量")

    batch.output_weight_grams = body.output_weight_grams

    # Calculate weight loss
    if input_weight > 0:
        batch.weight_loss_percent = round(
            (1 - body.output_weight_grams / input_weight) * 100, 1
        )

    await db.flush()

    # Re-fetch with eager-loaded relationships to avoid MissingGreenlet
    batch = await repo.get_detail(batch.id)
    return _to_batch_response(batch)
