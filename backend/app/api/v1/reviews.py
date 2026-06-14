"""Review and next-batch API."""
from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy import select

from ..dependencies import CurrentUserDep, DBSessionDep
from ...core.exceptions import NotFoundException, ValidationException
from ...models.all_models import RoastingBatch, ReviewReminder, BatchReminder
from ...repositories.reviews import ReviewRepository, BatchReminderRepository
from ...repositories.roasting_batches import RoastingBatchRepository
from ...repositories.questionnaires import QuestionnaireRepository
from ...repositories.evaluations import EvaluationRepository
from ...schemas.all_schemas import (
    ReviewOverviewResponse, ReminderResponse,
    PersonalReviewUpdateRequest, ComprehensiveReviewUpdateRequest,
    SuggestionUpdateRequest, RemindersPutRequest,
    NextRoastPlanRequest, NextRoastPlanResponse,
)

router = APIRouter(prefix="/reviews", tags=["reviews"])


def _to_reminder_response(r) -> ReminderResponse:
    return ReminderResponse(
        id=r.id,
        priority=r.priority,
        content=r.content,
    )


@router.get("/roasting-batches/{batch_id}/review-overview")
async def get_review_overview(
    batch_id: str,
    db: DBSessionDep = None,
    _user: CurrentUserDep = None,
):
    """Get full review overview for a batch."""
    batch_repo = RoastingBatchRepository(db)
    batch = await batch_repo.get_detail(batch_id)
    if not batch:
        raise NotFoundException("RoastingBatch", batch_id)

    review_repo = ReviewRepository(db)
    review = await review_repo.get_by_batch(batch_id)

    # Get questionnaires and evaluations
    q_repo = QuestionnaireRepository(db)
    questionnaires = await q_repo.get_by_batch(batch_id)

    eval_repo = EvaluationRepository(db)
    evaluations = await eval_repo.get_by_batch(batch_id)

    return ReviewOverviewResponse(
        batch={
            "id": batch.id,
            "status": batch.status,
            "roasted_at": batch.roasted_at.isoformat() if batch.roasted_at else None,
            "planned_input_weight_grams": batch.planned_input_weight_grams,
            "actual_input_weight_grams": batch.actual_input_weight_grams,
            "output_weight_grams": batch.output_weight_grams,
            "weight_loss_percent": batch.weight_loss_percent,
            "total_time_seconds": batch.total_time_seconds,
            "development_ratio_percent": batch.development_ratio_percent,
        },
        review={
            "id": review.id,
            "personal_review": review.personal_review,
            "personal_review_at": review.personal_review_at.isoformat() if review and review.personal_review_at else None,
            "comprehensive_review": review.comprehensive_review,
            "comprehensive_review_at": review.comprehensive_review_at.isoformat() if review and review.comprehensive_review_at else None,
            "next_batch_suggestion": review.next_batch_suggestion,
        } if review else None,
        reminders=[
            _to_reminder_response(r) for r in (review.source_reminders if review else [])
        ],
        evaluation_summary=review.evaluation_summary if review else None,
        evaluations=[{
            "id": e.id,
            "evaluator_name": e.evaluator_name,
            "overall_preference_score": e.overall_preference_score,
            "bean_age_days": e.bean_age_days,
            "submitted_at": e.submitted_at.isoformat() if e.submitted_at else None,
        } for e in evaluations[:10]],
        questionnaires=[{
            "id": q.id,
            "status": q.status,
            "submission_count": q.submission_count,
        } for q in questionnaires],
    )


@router.patch("/roasting-batches/{batch_id}/review/personal")
async def update_personal_review(
    batch_id: str,
    body: PersonalReviewUpdateRequest,
    db: DBSessionDep = None,
    _user: CurrentUserDep = None,
):
    """Save personal initial review."""
    review_repo = ReviewRepository(db)
    review = await review_repo.get_or_create(batch_id)
    review.personal_review = body.personal_review
    review.personal_review_at = datetime.now(timezone.utc)
    await db.flush()

    return {
        "personal_review": review.personal_review,
        "personal_review_at": review.personal_review_at.isoformat(),
    }


@router.patch("/roasting-batches/{batch_id}/review/comprehensive")
async def update_comprehensive_review(
    batch_id: str,
    body: ComprehensiveReviewUpdateRequest,
    db: DBSessionDep = None,
    _user: CurrentUserDep = None,
):
    """Save comprehensive review."""
    review_repo = ReviewRepository(db)
    review = await review_repo.get_or_create(batch_id)
    review.comprehensive_review = body.comprehensive_review
    review.comprehensive_review_at = datetime.now(timezone.utc)
    await db.flush()

    return {
        "comprehensive_review": review.comprehensive_review,
        "comprehensive_review_at": review.comprehensive_review_at.isoformat(),
    }


@router.patch("/roasting-batches/{batch_id}/review/suggestion")
async def update_suggestion(
    batch_id: str,
    body: SuggestionUpdateRequest,
    db: DBSessionDep = None,
    _user: CurrentUserDep = None,
):
    """Save next batch suggestion."""
    review_repo = ReviewRepository(db)
    review = await review_repo.get_or_create(batch_id)
    review.next_batch_suggestion = body.next_batch_suggestion
    await db.flush()

    return {"next_batch_suggestion": review.next_batch_suggestion}


@router.put("/roasting-batches/{batch_id}/review/reminders")
async def replace_reminders(
    batch_id: str,
    body: RemindersPutRequest,
    db: DBSessionDep = None,
    _user: CurrentUserDep = None,
):
    """Replace all reminders (max 3)."""
    from ...services.review import validate_reminders

    try:
        validate_reminders(body.reminders)
    except ValueError as e:
        raise ValidationException(str(e))

    review_repo = ReviewRepository(db)
    review = await review_repo.get_or_create(batch_id)

    # Delete existing source reminders
    for existing_rem in review.source_reminders:
        await db.delete(existing_rem)

    # Create new
    new_reminders = []
    for r in body.reminders:
        rem = ReviewReminder(
            batch_review_id=review.id,
            priority=r.get("priority", 1),
            content=r.get("content", ""),
        )
        db.add(rem)
        new_reminders.append(rem)

    await db.flush()
    return [_to_reminder_response(r) for r in new_reminders]


@router.post("/roasting-batches/{batch_id}/next-roast-plan")
async def create_next_roast_plan(
    batch_id: str,
    body: NextRoastPlanRequest,
    db: DBSessionDep = None,
    _user: CurrentUserDep = None,
):
    """Create next roast plan with reminder snapshots."""
    batch_repo = RoastingBatchRepository(db)
    batch = await batch_repo.get_detail(batch_id)
    if not batch:
        raise NotFoundException("RoastingBatch", batch_id)

    # Validate purchase batch
    from ...repositories.purchase_batches import PurchaseBatchRepository
    pb_repo = PurchaseBatchRepository(db)
    pb = await pb_repo.get_by_id(body.purchase_batch_id)
    if not pb:
        raise NotFoundException("PurchaseBatch", body.purchase_batch_id)

    # Check inventory
    from ...services.inventory import calculate_remaining_stock
    remaining = await calculate_remaining_stock(db, body.purchase_batch_id)
    if body.planned_input_weight_grams > remaining:
        from ...core.exceptions import InsufficientInventoryException
        raise InsufficientInventoryException(
            available_grams=remaining,
            required_grams=body.planned_input_weight_grams,
        )

    # Create roasting batch
    import random
    BATCH_COLORS = ["#df5b45", "#3478d4", "#1f9d68", "#8b5cc7", "#e5a029", "#d94b4b"]
    new_batch = RoastingBatch(
        purchase_batch_id=body.purchase_batch_id,
        status="planned",
        planned_at=datetime.fromisoformat(body.planned_at) if body.planned_at else None,
        planned_input_weight_grams=body.planned_input_weight_grams,
        target_description=body.target_description,
        color_tag=random.choice(BATCH_COLORS),
    )
    db.add(new_batch)
    await db.flush()

    # Copy selected reminders as immutable snapshots
    review_repo = ReviewRepository(db)
    review = await review_repo.get_by_batch(batch_id)
    copied_count = 0

    if review and body.review_reminder_ids:
        for rem_id in body.review_reminder_ids:
            # Find in source reminders
            source_rem = next(
                (r for r in review.source_reminders if r.id == rem_id),
                None
            )
            if source_rem:
                snapshot = BatchReminder(
                    roasting_batch_id=new_batch.id,
                    source_review_reminder_id=source_rem.id,
                    priority=source_rem.priority,
                    content=source_rem.content,
                )
                db.add(snapshot)
                copied_count += 1

    await db.flush()

    from ...api.v1.roasting_batches import _to_batch_response

    return NextRoastPlanResponse(
        roasting_batch=_to_batch_response(new_batch),
        copied_reminders=copied_count,
    )
