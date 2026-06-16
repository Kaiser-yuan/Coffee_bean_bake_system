"""Dashboard aggregation API."""
from fastapi import APIRouter, Query
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from ..dependencies import DBSessionDep, CurrentUserDep
from ...models.all_models import (
    RoastingBatch, PurchaseBatch, GreenBean, StandardTerm,
    RoastingCurve, Questionnaire, BatchReview,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
async def get_dashboard(
    year: int = Query(..., description="Target year"),
    db: DBSessionDep = None,
    _user: CurrentUserDep = None,
):
    """Get annual dashboard data."""
    # All completed batches in the year — eager load all needed relationships
    result = await db.execute(
        select(RoastingBatch)
        .options(
            selectinload(RoastingBatch.purchase_batch).selectinload(PurchaseBatch.green_bean).selectinload(GreenBean.variety),
            selectinload(RoastingBatch.purchase_batch).selectinload(PurchaseBatch.green_bean).selectinload(GreenBean.process),
            selectinload(RoastingBatch.active_curve),
            selectinload(RoastingBatch.questionnaires),
            selectinload(RoastingBatch.review),
        )
        .where(
            RoastingBatch.status == "completed",
            func.extract("year", RoastingBatch.roasted_at) == year,
        )
        .order_by(RoastingBatch.roasted_at.desc())
    )
    completed_batches = list(result.unique().scalars().all())

    # Counts
    total_roasts = len(completed_batches)
    total_input_weight = sum(
        (b.actual_input_weight_grams or b.planned_input_weight_grams)
        for b in completed_batches
    )

    # Bean profiles (distinct green beans)
    bean_profile_ids = set()
    for b in completed_batches:
        if b.purchase_batch and b.purchase_batch.green_bean_id:
            bean_profile_ids.add(b.purchase_batch.green_bean_id)
    total_bean_profiles = len(bean_profile_ids)

    # Average weight loss
    batches_with_loss = [
        b for b in completed_batches
        if b.weight_loss_percent is not None
    ]
    avg_loss = (
        round(sum(b.weight_loss_percent for b in batches_with_loss) / len(batches_with_loss), 1)
        if batches_with_loss else None
    )

    # Monthly roasts
    monthly = []
    for month in range(1, 13):
        count = sum(
            1 for b in completed_batches
            if b.roasted_at and b.roasted_at.month == month
        )
        monthly.append({"month": month, "count": count})

    # Variety distribution
    variety_map: dict[str, int] = {}
    for b in completed_batches:
        variety = "其他"
        if (b.purchase_batch is not None and b.purchase_batch.green_bean is not None
                and b.purchase_batch.green_bean.variety is not None):
            variety = b.purchase_batch.green_bean.variety.value
        variety_map[variety] = variety_map.get(variety, 0) + 1
    variety_dist = [{"name": k, "count": v} for k, v in variety_map.items()]

    # Region distribution
    region_map: dict[str, int] = {}
    for b in completed_batches:
        region = "其他"
        if (b.purchase_batch is not None and b.purchase_batch.green_bean is not None
                and b.purchase_batch.green_bean.region):
            region = b.purchase_batch.green_bean.region
        region_map[region] = region_map.get(region, 0) + 1
    region_dist = [{"name": k, "count": v} for k, v in region_map.items()]

    # Pending batches (grouped by bean)
    result = await db.execute(
        select(RoastingBatch)
        .options(
            selectinload(RoastingBatch.purchase_batch).selectinload(PurchaseBatch.green_bean).selectinload(GreenBean.variety),
            selectinload(RoastingBatch.purchase_batch).selectinload(PurchaseBatch.green_bean).selectinload(GreenBean.process),
        )
        .where(RoastingBatch.status == "planned")
        .order_by(RoastingBatch.created_at.desc())
    )
    pending_batches = list(result.unique().scalars().all())

    # Group pending by green bean
    pending_groups: dict[str, dict] = {}
    for b in pending_batches:
        gb = None
        if b.purchase_batch is not None and b.purchase_batch.green_bean is not None:
            gb = b.purchase_batch.green_bean
        bean_id = gb.id if gb else "unknown"
        if bean_id not in pending_groups:
            pending_groups[bean_id] = {
                "bean_id": bean_id,
                "bean_name": gb.name if gb else "未知",
                "variety": gb.variety.value if gb and gb.variety else None,
                "process": gb.process.value if gb and gb.process else None,
                "region": gb.region if gb else None,
                "batch_count": 0,
                "batches": [],
            }
        pending_groups[bean_id]["batch_count"] += 1
        pending_groups[bean_id]["batches"].append({
            "id": b.id,
            "planned_at": b.planned_at.isoformat() if b.planned_at else None,
            "planned_input_weight_grams": b.planned_input_weight_grams,
            "target_description": b.target_description,
            "purchase_batch_label": f"PB-{b.purchase_batch_id[:8]}",
        })

    # Recent batches
    recent_batches = [
        {
            "id": b.id,
            "roasted_at": b.roasted_at.isoformat() if b.roasted_at else None,
            "green_bean_name": b.purchase_batch.green_bean.name if b.purchase_batch is not None and b.purchase_batch.green_bean is not None else None,
            "variety": b.purchase_batch.green_bean.variety.value if b.purchase_batch is not None and b.purchase_batch.green_bean is not None and b.purchase_batch.green_bean.variety is not None else None,
            "actual_input_weight_grams": b.actual_input_weight_grams,
            "output_weight_grams": b.output_weight_grams,
            "weight_loss_percent": b.weight_loss_percent,
            "status": b.status,
        }
        for b in completed_batches[:8]
    ]

    # Pending actions count — use eager-loaded relationships directly
    pending_actions = {
        "missing_output_weight": sum(
            1 for b in completed_batches if b.output_weight_grams is None
        ),
        "missing_curve": sum(
            1 for b in completed_batches
            if b.active_curve is None
        ),
        "missing_evaluation": sum(
            1 for b in completed_batches
            if not b.questionnaires or all(q.submission_count == 0 for q in b.questionnaires)
        ),
        "missing_review": sum(
            1 for b in completed_batches
            if b.review is None or b.review.comprehensive_review is None
        ),
    }

    return {
        "year": year,
        "total_completed_roasts": total_roasts,
        "total_roasted_bean_profiles": total_bean_profiles,
        "total_input_weight_grams": total_input_weight,
        "average_weight_loss_percent": avg_loss,
        "monthly_roasts": monthly,
        "variety_distribution": variety_dist,
        "region_distribution": region_dist,
        "pending_groups": list(pending_groups.values()),
        "recent_batches": recent_batches,
        "pending_actions": pending_actions,
    }
