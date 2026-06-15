"""Curve file upload, parse, and query API."""
import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Query
from fastapi.responses import Response

from ..dependencies import CurrentUserDep, DBSessionDep
from ...core.config import settings
from ...core.exceptions import (
    NotFoundException, ConflictException,
    CurveParseFailedException, DuplicateCurveFileException,
    ValidationException,
)
from ...models.all_models import RoastingBatch, CurveFile, RoastingCurve
from ...repositories.curves import CurveFileRepository, RoastingCurveRepository
from ...repositories.roasting_batches import RoastingBatchRepository
from ...parsers.kaleido_m1 import parse_kaleido_m1
from ...services.curve import build_curve_response, parse_and_activate_curve, compute_curve_comparison
from ...schemas.all_schemas import (
    CurveFileResponse, CurveResponse, CurveComparisonResponse,
)

router = APIRouter(tags=["curves"])
logger = logging.getLogger("coffee-roast.curves")


def _save_uploaded_file(content: bytes, roasting_batch_id: str, file_id: str) -> str:
    """Save file to disk and return relative storage path."""
    now = datetime.now(timezone.utc)
    rel_path = f"roast-curves/{now.year}/{now.month:02d}/{roasting_batch_id}/{file_id}.csv"
    full_path = settings.upload_path / rel_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_bytes(content)
    return rel_path


@router.post("/roasting-batches/{batch_id}/curve-files", status_code=201)
async def upload_curve_file(
    batch_id: str,
    file: UploadFile = File(...),
    db: DBSessionDep = None,
    _user: CurrentUserDep = None,
):
    """Upload a Kaleido M1 CSV file and trigger parsing."""
    # Validate batch exists
    batch_repo = RoastingBatchRepository(db)
    batch = await batch_repo.get_by_id(batch_id)
    if not batch:
        raise NotFoundException("RoastingBatch", batch_id)

    # Read file
    content = await file.read()
    if len(content) > settings.upload_max_size_bytes:
        raise ValidationException(f"文件大小超过限制 ({settings.upload_max_size_bytes // 1024 // 1024}MB)")

    # Pre-parse to get hash
    try:
        parsed = parse_kaleido_m1(content, file.filename or "unknown.csv")
    except ValueError as e:
        raise CurveParseFailedException(str(e))

    # Check for duplicate
    repo = CurveFileRepository(db)
    existing = await repo.get_by_hash(batch_id, parsed.file_hash)
    if existing:
        raise DuplicateCurveFileException()

    # Create curve file record
    cf = CurveFile(
        roasting_batch_id=batch_id,
        original_filename=file.filename or "unknown.csv",
        storage_path="",  # Will be updated
        file_size_bytes=len(content),
        file_hash=parsed.file_hash,
        source_type="kaleido_m1",
        format_type="kaleido_kldo_v101",
        parse_status="parsing",
        parser_version="kl_v1.0",
        uploaded_at=datetime.now(timezone.utc),
    )
    db.add(cf)
    await db.flush()

    # Save to disk
    storage_path = _save_uploaded_file(content, batch_id, cf.id)
    cf.storage_path = storage_path

    # Parse and activate curve via unified service
    try:
        curve = await parse_and_activate_curve(db, cf, content)
    except Exception as e:
        logger.exception("Curve processing failed")
        cf.parse_status = "failed"
        cf.parse_error_code = "PARSE_ERROR"
        cf.parse_error_message = str(e)
        await db.flush()
        return {
            "id": cf.id,
            "parse_status": cf.parse_status,
            "parse_error_message": cf.parse_error_message,
        }

    cf.parsed_at = datetime.now(timezone.utc)
    await db.flush()

    return {
        "id": cf.id,
        "parse_status": cf.parse_status,
        "data_points": parsed.point_count,
        "total_time_seconds": round(parsed.total_time_seconds, 2),
        "events_found": len(parsed.events),
        "warnings": parsed.warnings,
    }


@router.get("/curve-files/{file_id}")
async def get_curve_file(
    file_id: str,
    db: DBSessionDep = None,
    _user: CurrentUserDep = None,
):
    """Get a single curve file metadata."""
    repo = CurveFileRepository(db)
    cf = await repo.get_by_id(file_id)
    if not cf:
        raise NotFoundException("CurveFile", file_id)

    return CurveFileResponse(
        id=cf.id,
        roasting_batch_id=cf.roasting_batch_id,
        original_filename=cf.original_filename,
        file_size_bytes=cf.file_size_bytes,
        source_type=cf.source_type,
        format_type=cf.format_type,
        parse_status=cf.parse_status,
        parse_error_code=cf.parse_error_code,
        parse_error_message=cf.parse_error_message,
        uploaded_at=cf.uploaded_at.isoformat() if cf.uploaded_at else None,
        parsed_at=cf.parsed_at.isoformat() if cf.parsed_at else None,
    )


@router.get("/curve-files/{file_id}/download")
async def download_curve_file(
    file_id: str,
    db: DBSessionDep = None,
    _user: CurrentUserDep = None,
):
    """Download the original curve file."""
    repo = CurveFileRepository(db)
    cf = await repo.get_by_id(file_id)
    if not cf:
        raise NotFoundException("CurveFile", file_id)

    full_path = settings.upload_path / cf.storage_path
    if not full_path.exists():
        raise NotFoundException("File on disk")

    content = full_path.read_bytes()
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{cf.original_filename}"',
        },
    )


@router.get("/roasting-batches/{batch_id}/curve-files")
async def list_curve_files(
    batch_id: str,
    db: DBSessionDep = None,
    _user: CurrentUserDep = None,
):
    """List all curve files for a batch."""
    repo = CurveFileRepository(db)
    files = await repo.get_by_batch(batch_id)
    return [
        CurveFileResponse(
            id=f.id,
            roasting_batch_id=f.roasting_batch_id,
            original_filename=f.original_filename,
            file_size_bytes=f.file_size_bytes,
            source_type=f.source_type,
            format_type=f.format_type,
            parse_status=f.parse_status,
            parse_error_code=f.parse_error_code,
            parse_error_message=f.parse_error_message,
            uploaded_at=f.uploaded_at.isoformat() if f.uploaded_at else None,
            parsed_at=f.parsed_at.isoformat() if f.parsed_at else None,
        )
        for f in files
    ]


@router.get("/roasting-batches/{batch_id}/curve")
async def get_active_curve(
    batch_id: str,
    db: DBSessionDep = None,
    _user: CurrentUserDep = None,
):
    """Get the current active curve for a batch."""
    repo = RoastingCurveRepository(db)
    curve = await repo.get_by_batch(batch_id)
    if not curve:
        raise NotFoundException("RoastingCurve", batch_id)
    return build_curve_response(curve)


@router.post("/curve-files/{file_id}/reparse")
async def reparse_curve_file(
    file_id: str,
    db: DBSessionDep = None,
    _user: CurrentUserDep = None,
):
    """Re-parse a curve file — rebuilds derived metrics, events, and replaces active curve."""
    repo = CurveFileRepository(db)
    cf = await repo.get_by_id(file_id)
    if not cf:
        raise NotFoundException("CurveFile", file_id)

    # Read file from disk (don't trust storage_path for security)
    full_path = settings.upload_path / cf.storage_path
    if not full_path.exists():
        raise NotFoundException("File on disk")

    content = full_path.read_bytes()

    # Use the unified parse-and-activate service
    try:
        curve = await parse_and_activate_curve(db, cf, content)
    except ValueError as e:
        cf.parse_status = "failed"
        cf.parse_error_message = str(e)
        await db.flush()
        raise CurveParseFailedException(str(e))

    cf.parsed_at = datetime.now(timezone.utc)
    cf.parse_error_message = None
    cf.parse_error_code = None
    await db.flush()

    return {
        "status": "parsed",
        "data_points": len(curve.points.get("data", [])) if curve.points else 0,
    }


@router.get("/curve-comparisons")
async def compare_curves(
    batch_ids: str = Query(..., description="Comma-separated batch IDs"),
    align_by: str = Query("charge", description="charge|yellowing|first_crack_start|drop"),
    db: DBSessionDep = None,
    _user: CurrentUserDep = None,
):
    """Compare curves across multiple batches."""
    ids = [bid.strip() for bid in batch_ids.split(",") if bid.strip()]
    if len(ids) < 2:
        raise ValidationException("至少需要 2 个批次进行对比")
    if len(ids) > 5:
        raise ValidationException("最多支持 5 个批次同时对比")

    if align_by not in ("charge", "yellowing", "first_crack_start", "drop"):
        raise ValidationException(f"不支持的 align_by: {align_by}")

    repo = RoastingCurveRepository(db)
    curves = await repo.get_by_batch_ids(ids)

    if len(curves) < 2:
        raise ValidationException("部分批次没有有效曲线")

    # Order by input
    curve_map = {c.roasting_batch_id: c for c in curves}
    ordered = [curve_map[bid] for bid in ids if bid in curve_map]

    base = ordered[0]
    comparisons = ordered[1:]

    result = compute_curve_comparison(base, comparisons, align_by=align_by)
    return result
