"""API v1 router aggregation."""
from fastapi import APIRouter

router = APIRouter()

from .auth import router as auth_router
from .terms import router as terms_router, admin_router as terms_admin_router
from .green_beans import router as green_beans_router
from .purchase_batches import router as purchase_batches_router
from .roasting_batches import router as roasting_batches_router
from .curves import router as curves_router
from .questionnaires import router as questionnaires_router, public_router as public_questionnaires_router
from .evaluations import router as public_evals_router, admin_router as evals_admin_router
from .reviews import router as reviews_router
from .dashboard import router as dashboard_router

router.include_router(auth_router)
router.include_router(terms_router)
router.include_router(terms_admin_router)
router.include_router(green_beans_router)
router.include_router(purchase_batches_router)
router.include_router(roasting_batches_router)
router.include_router(curves_router)
router.include_router(questionnaires_router)
router.include_router(public_questionnaires_router)
router.include_router(public_evals_router)
router.include_router(evals_admin_router)
router.include_router(reviews_router)
router.include_router(dashboard_router)
