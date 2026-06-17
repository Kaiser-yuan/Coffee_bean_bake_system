"""Green beans API endpoints."""
from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..dependencies import CurrentUserDep, DBSessionDep
from ...core.exceptions import NotFoundException, ValidationException
from ...models.all_models import GreenBean, PurchaseBatch, RoastingBatch, StandardTerm
from ...repositories.green_beans import GreenBeanRepository
from ...repositories.purchase_batches import PurchaseBatchRepository
from ...repositories.terms import TermRepository
from ...services.inventory import calculate_remaining_stock, append_inventory_ledger
from ...schemas.all_schemas import (
    GreenBeanMatchResponse, GreenBeanResponse,
    GreenBeanWithFirstPurchaseRequest, PurchaseBatchCreateRequest,
    PurchaseBatchResponse,
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
    db: DBSessionDep = None,
    _user: CurrentUserDep = None,
):
    """Get full tree with stock summary."""
    repo = GreenBeanRepository(db)

    # 1. Load green beans with eager-loaded relationships
    beans = await repo.get_tree(search=search, variety=variety, process=process, region=region)

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

    # 4. Build tree response with stock calculation
    tree: list[GreenBeanTreeResponse] = []
    for bean in beans:
        pb_list: list[PurchaseBatchTreeResponse] = []
        for pb in bean.purchase_batches:
            remaining = await calculate_remaining_stock(db, pb.id)
            supplier_name = pb.supplier.value if pb.supplier is not None else None
            rbs = rb_by_pb.get(pb.id, [])
            pb_list.append(PurchaseBatchTreeResponse(
                id=pb.id,
                green_bean_id=pb.green_bean_id,
                purchase_date=pb.purchase_date.isoformat() if pb.purchase_date else None,
                total_weight_grams=pb.total_weight_grams,
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
    pb = PurchaseBatch(
        green_bean_id=gb.id,
        purchase_date=datetime.fromisoformat(body.purchase_date) if body.purchase_date else datetime.now(timezone.utc),
        total_weight_grams=body.total_weight_grams,
        unit_price_fen_per_kg=body.unit_price_fen_per_kg,
        moisture_content_percent=body.moisture_content_percent,
        supplier_term_id=supplier_term.id if supplier_term else None,
        lot_number=body.lot_number,
        notes=body.notes,
    )
    db.add(pb)
    await db.flush()

    # Record initial inventory: change = total_weight, resulting = total_weight
    await append_inventory_ledger(
        db=db,
        purchase_batch_id=pb.id,
        change_grams=body.total_weight_grams,
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

    pb = PurchaseBatch(
        green_bean_id=green_bean_id,
        purchase_date=datetime.fromisoformat(body.purchase_date),
        total_weight_grams=body.total_weight_grams,
        unit_price_fen_per_kg=body.unit_price_fen_per_kg,
        moisture_content_percent=body.moisture_content_percent,
        supplier_term_id=supplier_term.id if supplier_term else None,
        lot_number=body.lot_number,
        notes=body.notes,
    )
    db.add(pb)
    await db.flush()

    # Record initial inventory: change = total_weight, resulting = total_weight
    await append_inventory_ledger(
        db=db,
        purchase_batch_id=pb.id,
        change_grams=body.total_weight_grams,
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
        moisture_content_percent=pb.moisture_content_percent,
        unit_price_fen_per_kg=pb.unit_price_fen_per_kg,
        total_price_fen=pb.total_price_fen,
        supplier=supplier_term.value if supplier_term else None,
        lot_number=pb.lot_number,
        notes=pb.notes,
        remaining_weight_grams=remaining,
    )
