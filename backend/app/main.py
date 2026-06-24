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
        try:
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
        finally:
            await engine.dispose()

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
    version=settings.app_version,
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
    return {"service": settings.app_name, "version": settings.app_version, "docs": "/api/v1/docs"}


# Meta endpoint — version probe for frontend mismatch detection (P0).
@app.get("/api/v1/meta")
async def meta():
    from .core.config import settings
    return {
        "service": settings.app_name,
        "app_version": settings.app_version,
        "git_sha": settings.app_git_sha,
        "api_contract_version": "2026-06-24.2",
        "features": [
            "bean_archive_status",
            "batch_stock_aggregation",
            "curve_aligned_seconds",
        ],
    }


# Health readiness check — DB + migration + storage (P1).
@app.get("/api/v1/health/ready")
async def health_ready():
    from sqlalchemy import text
    from pathlib import Path
    errors: list[str] = []
    migration_version = "unknown"

    # Check DB connectivity using a fresh async session.
    try:
        from .core.database import async_session_factory
        async with async_session_factory() as db:
            await db.execute(text("SELECT 1"))
    except Exception as e:
        errors.append(f"database: {e}")

    # Check migration head vs current.
    try:
        from alembic.config import Config
        from alembic.script import ScriptDirectory
        alembic_cfg = Config(str(Path(__file__).resolve().parent.parent / "alembic.ini"))
        script = ScriptDirectory.from_config(alembic_cfg)
        head_rev = script.get_current_head()

        async with async_session_factory() as db2:
            result = await db2.execute(text("SELECT version_num FROM alembic_version"))
            row = result.scalar_one_or_none()
            current_rev = row if isinstance(row, str) else (row[0] if row else None)
            if current_rev and (current_rev != head_rev):
                errors.append(f"migration behind: current={current_rev}, head={head_rev}")
            migration_version = current_rev or "none"
    except Exception as e:
        errors.append(f"migration: {e}")

    # Check upload storage writable.
    try:
        test_path = settings.upload_path / ".health_check"
        test_path.write_text("health")
        test_path.unlink(missing_ok=True)
    except Exception as e:
        errors.append(f"upload_storage: {e}")

    if errors:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "errors": errors,
                "git_sha": settings.app_git_sha,
            },
        )

    return {
        "status": "ready",
        "database": "ok",
        "migration": migration_version,
        "upload_storage": "ok",
        "git_sha": settings.app_git_sha,
    }


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
