"""Standard terms API."""
from fastapi import APIRouter

from ..dependencies import CurrentUserDep, DBSessionDep
from ...core.exceptions import NotFoundException, ValidationException
from ...repositories.terms import TermRepository
from ...schemas.all_schemas import (
    TermResponse, TermCreateRequest, TermUpdateRequest,
)

router = APIRouter(prefix="/terms", tags=["terms"])


def _to_term_response(term) -> dict:
    return TermResponse(
        id=term.id,
        category=term.category,
        value=term.value,
        display_order=term.display_order,
        is_active=term.is_active,
        usage_count=term.usage_count,
    )


# -- Public (used by frontend forms) --
@router.get("")
async def list_active_terms(
    category: str | None = None,
    active: bool = True,
    db: DBSessionDep = None,
):
    """Get terms for frontend form dropdowns."""
    repo = TermRepository(db)
    terms = await repo.get_by_category(category=category, active_only=active)
    return [_to_term_response(t) for t in terms]


# -- Admin (full CRUD) --
admin_router = APIRouter(prefix="/admin/terms", tags=["admin-terms"])


@admin_router.get("")
async def list_all_terms(
    category: str | None = None,
    db: DBSessionDep = None,
    _user: CurrentUserDep = None,
):
    """Get all terms including inactive ones."""
    repo = TermRepository(db)
    terms = await repo.get_by_category(category=category)
    return [_to_term_response(t) for t in terms]


@admin_router.post("", status_code=201)
async def create_term(
    body: TermCreateRequest,
    db: DBSessionDep = None,
    _user: CurrentUserDep = None,
):
    """Create a new standard term."""
    repo = TermRepository(db)
    existing = await repo.get_by_category_and_value(body.category, body.value)
    if existing:
        raise ValidationException(
            f"词条 '{body.value}' 在分类 '{body.category}' 中已存在",
            details={"existing_id": existing.id},
        )
    term = await repo.get_or_create_value(body.category, body.value)
    term.display_order = body.display_order
    return _to_term_response(term)


@admin_router.patch("/{term_id}")
async def update_term(
    term_id: str,
    body: TermUpdateRequest,
    db: DBSessionDep = None,
    _user: CurrentUserDep = None,
):
    """Update a term — enable, disable, rename, reorder."""
    repo = TermRepository(db)
    term = await repo.get_by_id(term_id)
    if not term:
        raise NotFoundException("Term", term_id)

    if body.value is not None:
        term.value = body.value
    if body.display_order is not None:
        term.display_order = body.display_order
    if body.is_active is not None:
        # Disallow deactivating used terms? Design guide says they CAN be deactivated
        term.is_active = body.is_active

    await db.flush()
    return _to_term_response(term)
