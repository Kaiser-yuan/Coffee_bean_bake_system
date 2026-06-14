"""Public evaluation submission API."""
from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy import select

from ..dependencies import DBSessionDep
from ...core.exceptions import (
    NotFoundException, ValidationException,
    QuestionnaireClosedException, QuestionnaireExpiredException,
)
from ...models.all_models import CuppingEvaluation, Questionnaire, RoastingBatch
from ...repositories.evaluations import EvaluationRepository
from ...repositories.questionnaires import QuestionnaireRepository
from ...services.questionnaire import compute_bean_age_days, is_expired
from ...schemas.all_schemas import (
    EvaluationSubmitRequest, EvaluationResponse,
    EvaluationStatsResponse, DimensionSummary, FlavorFrequency,
)

router = APIRouter(prefix="/public/questionnaires", tags=["public-evaluations"])


@router.post("/{share_code}/evaluations", status_code=201)
async def submit_evaluation(
    share_code: str,
    body: EvaluationSubmitRequest,
    db: DBSessionDep = None,
):
    """Submit a public evaluation (no auth required)."""
    q_repo = QuestionnaireRepository(db)
    q = await q_repo.get_by_share_code(share_code)
    if not q:
        raise NotFoundException("Questionnaire")

    if q.status == "closed":
        raise QuestionnaireClosedException()

    if is_expired(q):
        raise QuestionnaireExpiredException()

    # Validate overall_preference_score is required
    if body.overall_preference_score < 1 or body.overall_preference_score > 5:
        raise ValidationException("综合喜好评分必须在 1-5 之间")

    # Calculate bean age
    result = await db.execute(
        select(RoastingBatch).where(RoastingBatch.id == q.roasting_batch_id)
    )
    batch = result.scalar_one_or_none()

    bean_age = None
    if batch and batch.roasted_at:
        bean_age = compute_bean_age_days(batch.roasted_at, datetime.now(timezone.utc))

    eval_ = CuppingEvaluation(
        questionnaire_id=q.id,
        roasting_batch_id=q.roasting_batch_id,
        evaluator_name=body.evaluator_name,
        evaluator_type=body.evaluator_type,
        drink_temperature=body.drink_temperature,
        drink_form=body.drink_form,
        dry_fragrance_score=body.dry_fragrance_score,
        wet_aroma_score=body.wet_aroma_score,
        acidity_intensity_score=body.acidity_intensity_score,
        sweetness_score=body.sweetness_score,
        bitterness_intensity_score=body.bitterness_intensity_score,
        aftertaste_score=body.aftertaste_score,
        overall_preference_score=body.overall_preference_score,
        flavor_term_ids=body.flavor_notes,  # Store as simple list for now
        free_notes=body.free_notes,
        bean_age_days=bean_age,
        submitted_at=datetime.now(timezone.utc),
    )
    db.add(eval_)
    await db.flush()

    # Increment submission count
    q.submission_count += 1
    await db.flush()

    return {
        "id": eval_.id,
        "status": "submitted",
        "bean_age_days": bean_age,
    }


# -- Admin evaluations API --
admin_router = APIRouter(prefix="/evaluations", tags=["evaluations"])


@admin_router.get("/questionnaires/{questionnaire_id}")
async def get_evaluations_for_questionnaire(
    questionnaire_id: str,
    db: DBSessionDep = None,
    _user=None,  # Auth required via router
):
    """Get all evaluations and stats for a questionnaire."""
    eval_repo = EvaluationRepository(db)
    evaluations = await eval_repo.get_by_questionnaire(questionnaire_id)

    # Compute dimensions
    dim_labels = {
        "dry_fragrance_score": "干香",
        "wet_aroma_score": "湿香",
        "acidity_intensity_score": "酸感（强度）",
        "sweetness_score": "甜感",
        "bitterness_intensity_score": "苦感（强度）",
        "aftertaste_score": "回味",
        "overall_preference_score": "综合喜好",
    }
    dim_colors = {
        "dry_fragrance_score": "#e5a029",
        "wet_aroma_score": "#20a184",
        "acidity_intensity_score": "#3478d4",
        "sweetness_score": "#df5b45",
        "bitterness_intensity_score": "#8b5cc7",
        "aftertaste_score": "#1f9d68",
        "overall_preference_score": "#2f6bff",
    }
    dimensions = []

    for key, label in dim_labels.items():
        vals = [getattr(e, key) for e in evaluations
                if getattr(e, key) is not None and getattr(e, key) > 0]
        avg = sum(vals) / len(vals) if vals else None
        dimensions.append(DimensionSummary(
            label=label,
            average=round(avg, 1) if avg else None,
            valid_count=len(vals),
        ))

    # Flavor frequencies
    flavor_map: dict[str, int] = {}
    for e in evaluations:
        if e.flavor_term_ids:
            for f in e.flavor_term_ids:
                flavor_map[f] = flavor_map.get(f, 0) + 1
    top_flavors = sorted(flavor_map.items(), key=lambda x: x[1], reverse=True)[:8]
    flavors = [FlavorFrequency(name=name, count=count) for name, count in top_flavors]

    return {
        "evaluations": [
            EvaluationResponse(
                id=e.id,
                questionnaire_id=e.questionnaire_id,
                evaluator_name=e.evaluator_name,
                evaluator_type=e.evaluator_type,
                brew_method=e.brew_method_term_id,
                drink_temperature=e.drink_temperature,
                drink_form=e.drink_form,
                dry_fragrance_score=e.dry_fragrance_score,
                wet_aroma_score=e.wet_aroma_score,
                acidity_intensity_score=e.acidity_intensity_score,
                sweetness_score=e.sweetness_score,
                bitterness_intensity_score=e.bitterness_intensity_score,
                aftertaste_score=e.aftertaste_score,
                overall_preference_score=e.overall_preference_score,
                flavor_notes=e.flavor_term_ids or [],
                free_notes=e.free_notes,
                bean_age_days=e.bean_age_days,
                submitted_at=e.submitted_at.isoformat() if e.submitted_at else None,
            )
            for e in evaluations
        ],
        "stats": EvaluationStatsResponse(
            dimensions=dimensions,
            top_flavors=flavors,
            total_submissions=len(evaluations),
        ),
    }
