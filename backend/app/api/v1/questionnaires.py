"""Questionnaire API — creation, management, and public access."""
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter
from sqlalchemy import select

from ..dependencies import DBSessionDep, CurrentUserDep
from ...core.exceptions import (
    NotFoundException, ValidationException, ConflictException,
    RoastingBatchNotCompletedException, QuestionnaireClosedException,
    QuestionnaireExpiredException,
)
from ...models.all_models import RoastingBatch, Questionnaire
from ...repositories.questionnaires import QuestionnaireRepository
from ...schemas.all_schemas import (
    QuestionnaireResponse, QuestionnaireCreateResponse,
)

router = APIRouter(prefix="/questionnaires", tags=["questionnaires"])


@router.post("/roasting-batches/{batch_id}/questionnaires", status_code=201)
async def create_questionnaire(
    batch_id: str,
    db: DBSessionDep = None,
    _user: CurrentUserDep = None,
):
    """Create a new evaluation questionnaire for a completed batch."""
    # Validate batch is completed
    result = await db.execute(select(RoastingBatch).where(RoastingBatch.id == batch_id))
    batch = result.scalar_one_or_none()
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


@router.get("")
async def list_questionnaires(
    db: DBSessionDep = None,
    _user: CurrentUserDep = None,
):
    """List all questionnaires."""
    q_repo = QuestionnaireRepository(db)
    items = await q_repo.get_all()
    return [
        QuestionnaireResponse(
            id=q.id,
            roasting_batch_id=q.roasting_batch_id,
            status=q.status,
            share_code=q.share_code,
            share_url=q.share_url,
            created_at=q.created_at.isoformat() if q.created_at else "",
            expires_at=q.expires_at.isoformat() if q.expires_at else None,
            closed_at=q.closed_at.isoformat() if q.closed_at else None,
            submission_count=q.submission_count,
        )
        for q in items
    ]


@router.get("/{questionnaire_id}")
async def get_questionnaire(
    questionnaire_id: str,
    db: DBSessionDep = None,
    _user: CurrentUserDep = None,
):
    """Get questionnaire detail."""
    q_repo = QuestionnaireRepository(db)
    q = await q_repo.get_by_id(questionnaire_id)
    if not q:
        raise NotFoundException("Questionnaire", questionnaire_id)

    return QuestionnaireResponse(
        id=q.id,
        roasting_batch_id=q.roasting_batch_id,
        status=q.status,
        share_code=q.share_code,
        share_url=q.share_url,
        created_at=q.created_at.isoformat() if q.created_at else "",
        expires_at=q.expires_at.isoformat() if q.expires_at else None,
        closed_at=q.closed_at.isoformat() if q.closed_at else None,
        submission_count=q.submission_count,
    )


@router.post("/{questionnaire_id}/close")
async def close_questionnaire(
    questionnaire_id: str,
    db: DBSessionDep = None,
    _user: CurrentUserDep = None,
):
    """Close a questionnaire."""
    q_repo = QuestionnaireRepository(db)
    q = await q_repo.get_by_id(questionnaire_id)
    if not q:
        raise NotFoundException("Questionnaire", questionnaire_id)

    if q.status != "open":
        raise ConflictException(
            code="QUESTIONNAIRE_NOT_OPEN",
            message="问卷已关闭或已过期",
        )

    q.status = "closed"
    q.closed_at = datetime.now(timezone.utc)
    await db.flush()

    return QuestionnaireResponse(
        id=q.id,
        roasting_batch_id=q.roasting_batch_id,
        status=q.status,
        share_code=q.share_code,
        share_url=q.share_url,
        created_at=q.created_at.isoformat() if q.created_at else "",
        expires_at=q.expires_at.isoformat() if q.expires_at else None,
        closed_at=q.closed_at.isoformat() if q.closed_at else None,
        submission_count=q.submission_count,
    )


# -- Public endpoints (no auth) --
public_router = APIRouter(prefix="/public/questionnaires", tags=["public"])


@public_router.get("/{share_code}")
async def get_public_questionnaire(
    share_code: str,
    db: DBSessionDep = None,
):
    """Get questionnaire for public evaluation page (no auth required)."""
    q_repo = QuestionnaireRepository(db)
    q = await q_repo.get_by_share_code(share_code)
    if not q:
        raise NotFoundException("Questionnaire")

    from ...services.questionnaire import is_expired

    if q.status == "closed":
        raise QuestionnaireClosedException()

    if is_expired(q):
        raise QuestionnaireExpiredException()

    # Load batch with green bean info for public form
    from ...repositories.roasting_batches import RoastingBatchRepository
    batch_repo = RoastingBatchRepository(db)
    batch = await batch_repo.get_detail(q.roasting_batch_id)

    green_bean_name = None
    if batch and hasattr(batch, "purchase_batch") and batch.purchase_batch:
        if hasattr(batch.purchase_batch, "green_bean") and batch.purchase_batch.green_bean:
            green_bean_name = batch.purchase_batch.green_bean.name

    return {
        "share_code": q.share_code,
        "roast_date": batch.roasted_at.isoformat() if batch and batch.roasted_at else None,
        "green_bean_name": green_bean_name,
        "status": q.status,
        "expires_at": q.expires_at.isoformat() if q.expires_at else None,
    }
