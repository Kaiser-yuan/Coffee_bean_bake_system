"""Green beans API endpoints."""
from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..dependencies import CurrentUserDep, DBSessionDep
from ...core.exceptions import NotFoundException, ValidationException
from ...models.all_models import GreenBean, PurchaseBatch, StandardTerm
from ...repositories.green_beans import GreenBeanRepository
from ...repositories.purchase_batches import PurchaseBatchRepository
from ...repositories.terms import TermRepository
from ...services.inventory import check_and_record_inventory
from ...schemas.all_schemas import (
    GreenBeanMatchResponse, GreenBeanResponse,
    GreenBeanWithFirstPurchaseRequest, PurchaseBatchCreateRequest,
    PurchaseBatchResponse,
)

router = APIRouter(prefix="/green-beans", tags=["green-beans"])


def _gb_to_response(gb: GreenBean) -> dict:
    return GreenBeanResponse(
        id=gb.id,
        name=gb.name,
        variety=gb.variety.value if gb.variety else None,
        process=gb.process.value if gb.process else None,
        region=gb.region,
        country=gb.country,
        farm=gb.farm,
        elevation=gb.elevation,
        brand=gb.brand,
        harvest_season=gb.harvest_season,
        vendor_flavor_description=gb.vendor_flavor_description,
        first_created_at=gb.first_created_at.isoformat() if gb.first_created_at else None,
    )


# -- Name matching (search before creating) --
@router.get("/matches")
async def match_green_beans(
    name: str,
    db: DBSessionDep = None,
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
):
    """Get full tree with stock summary."""
    repo = GreenBeanRepository(db)
    beans = await repo.get_tree(search=search, variety=variety, process=process, region=region)
    return [_gb_to_response(b) for b in beans]


# -- Create with first purchase (transactional) --
@router.post("/with-first-purchase", status_code=201)
async def create_green_bean_with_first_purchase(
    body: GreenBeanWithFirstPurchaseRequest,
    db: DBSessionDep = None,
    _user: CurrentUserDep = None,
):
    """Atomically create a green bean + its first purchase batch."""
    term_repo = TermRepository(db)

    # Resolve terms
    variety_term_id = None
    process_term_id = None
    if body.variety:
        t = await term_repo.get_or_create_value("variety", body.variety)
        variety_term_id = t.id
    if body.process:
        t = await term_repo.get_or_create_value("process", body.process)
        process_term_id = t.id

    # Create green bean
    gb = GreenBean(
        name=body.name,
        variety_term_id=variety_term_id,
        process_term_id=process_term_id,
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
        lot_number=body.lot_number,
        notes=body.notes,
    )
    db.add(pb)
    await db.flush()

    # Record initial inventory
    await check_and_record_inventory(
        db=db,
        purchase_batch_id=pb.id,
        required_grams=body.total_weight_grams,
        event_type="purchase_in",
        related_entity_type="purchase_batch",
        related_entity_id=pb.id,
    )

    return {
        "green_bean": _gb_to_response(gb),
        "purchase_batch": {
            "id": pb.id,
            "green_bean_id": pb.green_bean_id,
            "total_weight_grams": pb.total_weight_grams,
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

    pb = PurchaseBatch(
        green_bean_id=green_bean_id,
        purchase_date=datetime.fromisoformat(body.purchase_date),
        total_weight_grams=body.total_weight_grams,
        unit_price_fen_per_kg=body.unit_price_fen_per_kg,
        moisture_content_percent=body.moisture_content_percent,
        lot_number=body.lot_number,
        notes=body.notes,
    )
    db.add(pb)
    await db.flush()

    await check_and_record_inventory(
        db=db,
        purchase_batch_id=pb.id,
        required_grams=body.total_weight_grams,
        event_type="purchase_in",
        related_entity_type="purchase_batch",
        related_entity_id=pb.id,
    )

    from ...services.inventory import calculate_remaining_stock
    remaining = await calculate_remaining_stock(db, pb.id)

    return PurchaseBatchResponse(
        id=pb.id,
        green_bean_id=pb.green_bean_id,
        purchase_date=pb.purchase_date.isoformat() if pb.purchase_date else None,
        total_weight_grams=pb.total_weight_grams,
        moisture_content_percent=pb.moisture_content_percent,
        unit_price_fen_per_kg=pb.unit_price_fen_per_kg,
        total_price_fen=pb.total_price_fen,
        lot_number=pb.lot_number,
        notes=pb.notes,
        remaining_weight_grams=remaining,
    )
