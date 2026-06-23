"""FastAPI application entry point."""
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .core.config import settings
from .core.exceptions import AppException
from .core.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()

    # Periodic stale-job expiry task (P2-1).
    async def _expire_loop():
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        engine = create_async_engine(settings.database_url, echo=False)
        while True:
            try:
                async with AsyncSession(engine) as db:
                    from .services.bulk_import import expire_stale_bulk_jobs
                    expired = await expire_stale_bulk_jobs(db)
                    if expired:
                        import logging
                        logging.getLogger("coffee-roast.bulk_import").info(
                            "Background: expired %d stale previewed jobs", expired
                        )
                    await db.commit()
            except Exception:
                import logging
                logging.getLogger("coffee-roast.bulk_import").warning(
                    "Background expiry task failed, will retry", exc_info=True
                )
            await asyncio.sleep(1200)  # every 20 minutes

    task = asyncio.create_task(_expire_loop())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="Coffee Roast API",
    description="咖啡烘焙分析系统后端 API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/v1/docs",
    openapi_url="/api/v1/openapi.json",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code,
            "message": exc.message,
            "details": exc.details,
            "request_id": exc.request_id,
        },
    )


# Root
@app.get("/")
async def root():
    return {"service": settings.app_name, "version": "0.1.0", "docs": "/api/v1/docs"}


# Import and mount routers
def register_routers() -> None:
    from .api.v1.auth import router as auth_router
    from .api.v1.backfills import router as backfills_router
    from .api.v1.bulk_imports import router as bulk_imports_router
    from .api.v1.curves import router as curves_router
    from .api.v1.dashboard import router as dashboard_router
    from .api.v1.evaluations import (
        admin_router as evaluations_admin_router,
        router as evaluations_public_router,
    )
    from .api.v1.green_beans import router as green_beans_router
    from .api.v1.purchase_batches import router as purchase_batches_router
    from .api.v1.questionnaires import (
        public_router as questionnaires_public_router,
        router as questionnaires_router,
    )
    from .api.v1.reviews import router as reviews_router
    from .api.v1.roasting_batches import router as roasting_batches_router
    from .api.v1.terms import admin_router as terms_admin_router
    from .api.v1.terms import router as terms_router

    for router in (
        auth_router,
        terms_router,
        terms_admin_router,
        green_beans_router,
        purchase_batches_router,
        roasting_batches_router,
        bulk_imports_router,
        backfills_router,
        curves_router,
        questionnaires_router,
        questionnaires_public_router,
        evaluations_public_router,
        evaluations_admin_router,
        reviews_router,
        dashboard_router,
    ):
        app.include_router(router, prefix="/api/v1")


register_routers()
