"""Green beans API endpoints."""
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..dependencies import CurrentUserDep, DBSessionDep
from ...core.exceptions import NotFoundException, ValidationException
from ...models.all_models import GreenBean, PurchaseBatch, RoastingBatch, StandardTerm
from ...repositories.green_beans import GreenBeanRepository
from ...repositories.purchase_batches import PurchaseBatchRepository
from ...repositories.terms import TermRepository
from ...services.inventory import calculate_remaining_stock, calculate_remaining_stocks, append_inventory_ledger
from ...schemas.all_schemas import (
    GreenBeanMatchResponse, GreenBeanResponse,
    GreenBeanWithFirstPurchaseRequest, PurchaseBatchCreateRequest,
    PurchaseBatchResponse, GreenBeanUpdateRequest,
    GreenBeanTreeResponse, PurchaseBatchTreeResponse, RoastingBatchTreeResponse,
)

router = APIRouter(prefix="/green-beans", tags=["green-beans"])


def _gb_to_response(gb: GreenBean) -> GreenBeanResponse:
    return GreenBeanResponse(
        id=gb.id,
        name=gb.name,
        variety=gb.variety.value if gb.variety is not None else None,
        process=gb.process.value if gb.process is not None else None,
        region=gb.region,
        country=gb.country,
        farm=gb.farm,
        elevation=gb.elevation,
        brand=gb.brand,
        harvest_season=gb.harvest_season,
        vendor_flavor_description=gb.vendor_flavor_description,
        first_created_at=gb.first_created_at.isoformat() if gb.first_created_at else None,
        is_archived=gb.is_archived,
        archived_at=gb.archived_at.isoformat() if gb.archived_at else None,
    )


def _rb_to_tree_response(rb: RoastingBatch) -> RoastingBatchTreeResponse:
    return RoastingBatchTreeResponse(
        id=rb.id,
        purchase_batch_id=rb.purchase_batch_id,
        status=rb.status,
        planned_at=rb.planned_at.isoformat() if rb.planned_at else None,
        roasted_at=rb.roasted_at.isoformat() if rb.roasted_at else None,
        planned_input_weight_grams=rb.planned_input_weight_grams,
        actual_input_weight_grams=rb.actual_input_weight_grams,
        output_weight_grams=rb.output_weight_grams,
        weight_loss_percent=rb.weight_loss_percent,
        total_time_seconds=rb.total_time_seconds,
        development_time_seconds=rb.development_time_seconds,
        development_ratio_percent=rb.development_ratio_percent,
        target_description=rb.target_description,
        color_tag=rb.color_tag,
        entry_mode=rb.entry_mode,
        inventory_effective=rb.inventory_effective,
        source_note=rb.source_note,
    )


# -- Name matching (search before creating) --
@router.get("/matches")
async def match_green_beans(
    name: str,
    db: DBSessionDep = None,
    _user: CurrentUserDep = None,
):
    """Search existing green beans by name for dedup before creation."""
    repo = GreenBeanRepository(db)
    matches = await repo.search_by_name(name, limit=5)
    return [
        GreenBeanMatchResponse(
            id=m.id,
            name=m.name,
            brand=m.brand,
            harvest_season=m.harvest_season,
            processing_method=m.process.value if m.process else None,
            region=m.region,
        )
        for m in matches
    ]


# -- Tree view: beans -> purchase batches -> roasting batches --
@router.get("/tree")
async def get_green_bean_tree(
    search: str | None = None,
    variety: str | None = None,
    process: str | None = None,
    region: str | None = None,
    archive_status: Literal["active", "archived", "all"] = "active",
    db: DBSessionDep = None,
    _user: CurrentUserDep = None,
):
    """Get full tree with stock summary."""
    repo = GreenBeanRepository(db)

    # 1. Load green beans with eager-loaded relationships
    beans = await repo.get_tree(
        search=search,
        variety=variety,
        process=process,
        region=region,
        archive_status=archive_status,
    )

    # 2. Collect all purchase batch IDs
    all_pbs = [pb for bean in beans for pb in bean.purchase_batches]
    pb_ids = [pb.id for pb in all_pbs]

    # 3. Batch-load all roasting batches for these purchase batches
    rb_by_pb: dict[str, list[RoastingBatch]] = {}
    if pb_ids:
        rb_result = await db.execute(
            select(RoastingBatch)
            .where(RoastingBatch.purchase_batch_id.in_(pb_ids))
            .order_by(RoastingBatch.created_at.desc())
        )
        for rb in rb_result.scalars().all():
            rb_by_pb.setdefault(rb.purchase_batch_id, []).append(rb)

    # 4. Batch-calculate all remaining stocks in one query (P1-2: eliminate N+1).
    remaining_by_pb = await calculate_remaining_stocks(db, pb_ids)

    # 5. Build tree response with pre-computed stock values.
    tree: list[GreenBeanTreeResponse] = []
    for bean in beans:
        pb_list: list[PurchaseBatchTreeResponse] = []
        for pb in bean.purchase_batches:
            remaining = remaining_by_pb.get(pb.id, 0)
            supplier_name = pb.supplier.value if pb.supplier is not None else None
            rbs = rb_by_pb.get(pb.id, [])
            pb_list.append(PurchaseBatchTreeResponse(
                id=pb.id,
                green_bean_id=pb.green_bean_id,
                purchase_date=pb.purchase_date.isoformat() if pb.purchase_date else None,
                total_weight_grams=pb.total_weight_grams,
                inventory_tracking_mode=pb.inventory_tracking_mode,
                opening_stock_grams=pb.opening_stock_grams,
                moisture_content_percent=pb.moisture_content_percent,
                unit_price_fen_per_kg=pb.unit_price_fen_per_kg,
                total_price_fen=pb.total_price_fen,
                supplier=supplier_name,
                lot_number=pb.lot_number,
                notes=pb.notes,
                remaining_weight_grams=remaining,
                roasting_batches=[_rb_to_tree_response(rb) for rb in rbs],
            ))

        tree.append(GreenBeanTreeResponse(
            id=bean.id,
            name=bean.name,
            variety=bean.variety.value if bean.variety is not None else None,
            process=bean.process.value if bean.process is not None else None,
            region=bean.region,
            country=bean.country,
            farm=bean.farm,
            elevation=bean.elevation,
            brand=bean.brand,
            harvest_season=bean.harvest_season,
            vendor_flavor_description=bean.vendor_flavor_description,
            first_created_at=bean.first_created_at.isoformat() if bean.first_created_at else None,
            is_archived=bean.is_archived,
            archived_at=bean.archived_at.isoformat() if bean.archived_at else None,
            purchase_batches=pb_list,
        ))

    return tree


# -- Create with first purchase (transactional) --
@router.post("/with-first-purchase", status_code=201)
async def create_green_bean_with_first_purchase(
    body: GreenBeanWithFirstPurchaseRequest,
    db: DBSessionDep = None,
    _user: CurrentUserDep = None,
):
    """Atomically create a green bean + its first purchase batch."""
    term_repo = TermRepository(db)

    # Resolve terms — keep references for response to avoid MissingGreenlet
    variety_term = None
    process_term = None
    supplier_term = None
    if body.variety:
        variety_term = await term_repo.get_or_create_value("variety", body.variety)
    if body.process:
        process_term = await term_repo.get_or_create_value("process", body.process)
    if body.supplier:
        supplier_term = await term_repo.get_or_create_value("supplier", body.supplier)

    # Create green bean
    gb = GreenBean(
        name=body.name,
        variety_term_id=variety_term.id if variety_term else None,
        process_term_id=process_term.id if process_term else None,
        region=body.region,
        country=body.country,
        farm=body.farm,
        elevation=body.elevation,
        brand=body.brand,
        harvest_season=body.harvest_season,
        vendor_flavor_description=body.vendor_flavor_description,
        first_created_at=datetime.now(timezone.utc),
    )
    db.add(gb)
    await db.flush()

    # Create purchase batch
    tracking_mode = getattr(body, "inventory_tracking_mode", "normal") or "normal"
    opening_stock = getattr(body, "opening_stock_grams", None)
    if tracking_mode == "historical_archive":
        if opening_stock is None:
            opening_stock = 0  # historical archive defaults to zero opening stock
    else:
        if opening_stock is None:
            opening_stock = body.total_weight_grams

    pb = PurchaseBatch(
        green_bean_id=gb.id,
        purchase_date=datetime.fromisoformat(body.purchase_date) if body.purchase_date else datetime.now(timezone.utc),
        total_weight_grams=body.total_weight_grams,
        inventory_tracking_mode=tracking_mode,
        opening_stock_grams=opening_stock,
        unit_price_fen_per_kg=body.unit_price_fen_per_kg,
        moisture_content_percent=body.moisture_content_percent,
        supplier_term_id=supplier_term.id if supplier_term else None,
        lot_number=body.lot_number,
        notes=body.notes,
    )
    db.add(pb)
    await db.flush()

    # Record initial inventory: change = opening_stock
    await append_inventory_ledger(
        db=db,
        purchase_batch_id=pb.id,
        change_grams=opening_stock,
        event_type="purchase_in",
        related_entity_type="purchase_batch",
        related_entity_id=pb.id,
    )

    return {
        "green_bean": {
            "id": gb.id,
            "name": gb.name,
            "variety": variety_term.value if variety_term else None,
            "process": process_term.value if process_term else None,
            "region": gb.region,
            "country": gb.country,
            "farm": gb.farm,
            "elevation": gb.elevation,
            "brand": gb.brand,
            "harvest_season": gb.harvest_season,
            "vendor_flavor_description": gb.vendor_flavor_description,
            "first_created_at": gb.first_created_at.isoformat() if gb.first_created_at else None,
        },
        "purchase_batch": {
            "id": pb.id,
            "green_bean_id": pb.green_bean_id,
            "total_weight_grams": pb.total_weight_grams,
            "supplier": supplier_term.value if supplier_term else None,
        },
    }


# -- Add purchase to existing bean --
@router.post("/{green_bean_id}/purchase-batches", status_code=201)
async def add_purchase_batch(
    green_bean_id: str,
    body: PurchaseBatchCreateRequest,
    db: DBSessionDep = None,
    _user: CurrentUserDep = None,
):
    """Add a new purchase batch to an existing green bean."""
    gb_repo = GreenBeanRepository(db)
    gb = await gb_repo.get_by_id(green_bean_id)
    if not gb:
        raise NotFoundException("GreenBean", green_bean_id)

    term_repo = TermRepository(db)
    supplier_term = None
    if body.supplier:
        supplier_term = await term_repo.get_or_create_value("supplier", body.supplier)

    tracking_mode = getattr(body, "inventory_tracking_mode", "normal") or "normal"
    opening_stock = getattr(body, "opening_stock_grams", None)
    if tracking_mode == "historical_archive":
        if opening_stock is None:
            opening_stock = 0
    else:
        if opening_stock is None:
            opening_stock = body.total_weight_grams

    pb = PurchaseBatch(
        green_bean_id=green_bean_id,
        purchase_date=datetime.fromisoformat(body.purchase_date),
        total_weight_grams=body.total_weight_grams,
        inventory_tracking_mode=tracking_mode,
        opening_stock_grams=opening_stock,
        unit_price_fen_per_kg=body.unit_price_fen_per_kg,
        moisture_content_percent=body.moisture_content_percent,
        supplier_term_id=supplier_term.id if supplier_term else None,
        lot_number=body.lot_number,
        notes=body.notes,
    )
    db.add(pb)
    await db.flush()

    # Record initial inventory: change = opening_stock
    await append_inventory_ledger(
        db=db,
        purchase_batch_id=pb.id,
        change_grams=opening_stock,
        event_type="purchase_in",
        related_entity_type="purchase_batch",
        related_entity_id=pb.id,
    )

    remaining = await calculate_remaining_stock(db, pb.id)

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
        supplier=supplier_term.value if supplier_term else None,
        lot_number=pb.lot_number,
        notes=pb.notes,
        remaining_weight_grams=remaining,
    )


# -- Edit green bean --
@router.patch("/{green_bean_id}")
async def update_green_bean(
    green_bean_id: str,
    body: GreenBeanUpdateRequest,
    db: DBSessionDep = None,
    _user: CurrentUserDep = None,
):
    """P1-2: Update green bean metadata fields. All fields optional, at least one required."""
    repo = GreenBeanRepository(db)
    gb = await repo.get_by_id(green_bean_id)
    if not gb:
        raise NotFoundException("GreenBean", green_bean_id)

    fields_set = body.model_fields_set
    if "name" in fields_set:
        gb.name = body.name
    if "variety" in fields_set:
        if body.variety is None:
            gb.variety_term_id = None
        else:
            term_repo = TermRepository(db)
            vt = await term_repo.get_or_create_value("variety", body.variety)
            gb.variety_term_id = vt.id
    if "process" in fields_set:
        if body.process is None:
            gb.process_term_id = None
        else:
            term_repo = TermRepository(db)
            pt = await term_repo.get_or_create_value("process", body.process)
            gb.process_term_id = pt.id
    for field in (
        "region", "country", "farm", "elevation", "brand",
        "harvest_season", "vendor_flavor_description",
    ):
        if field in fields_set:
            setattr(gb, field, getattr(body, field))
    gb.updated_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(gb, attribute_names=["variety", "process"])
    return _gb_to_response(gb)


# -- Delete / archive green bean --
@router.delete("/{green_bean_id}")
async def delete_green_bean(
    green_bean_id: str,
    db: DBSessionDep = None,
    _user: CurrentUserDep = None,
):
    """P1-2: Delete empty bean; archive bean with purchase data."""
    repo = GreenBeanRepository(db)
    gb = await repo.get_by_id_with_purchase_count(green_bean_id)
    if not gb:
        raise NotFoundException("GreenBean", green_bean_id)

    purchase_count = gb.purchase_count if hasattr(gb, 'purchase_count') else 0
    if purchase_count == 0:
        # Physical delete for beans with no purchase batches.
        await db.delete(gb)
        await db.flush()
        return {"status": "deleted", "green_bean_id": green_bean_id}

    # Bean has purchase batches — archive instead of physical delete.
    gb.is_archived = True
    gb.archived_at = datetime.now(timezone.utc)
    gb.updated_at = gb.archived_at
    await db.flush()
    return {"status": "archived", "green_bean_id": green_bean_id}


# -- Restore archived green bean --
@router.post("/{green_bean_id}/restore")
async def restore_green_bean(
    green_bean_id: str,
    db: DBSessionDep = None,
    _user: CurrentUserDep = None,
):
    """P1-2: Restore an archived green bean."""
    repo = GreenBeanRepository(db)
    gb = await repo.get_by_id(green_bean_id)
    if not gb:
        raise NotFoundException("GreenBean", green_bean_id)
    if not gb.is_archived:
        raise ValidationException("该生豆未被归档")
    gb.is_archived = False
    gb.archived_at = None
    gb.updated_at = datetime.now(timezone.utc)
    await db.flush()
    return {"status": "restored", "green_bean_id": green_bean_id}
