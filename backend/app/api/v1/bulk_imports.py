"""Bulk CSV roast generation API — multi-CSV batches under a purchase batch.

Preview persists a job + items (no roasting batches, no inventory change).
Commit creates completed roasting batches + curves and (by default) deducts
inventory. The original CSV bytes are re-sent at commit time, keyed by the
file_hash returned from preview.
"""
import json

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from ..dependencies import CurrentUserDep, DBSessionDep
from ...core.exceptions import ValidationException
from ...schemas.all_schemas import (
    BulkImportCommitItem, BulkImportCommitResponse, BulkImportPreviewResponse,
)
from ...services.bulk_import import (
    preview_roast_csv_import, commit_roast_csv_import, UploadedCsv,
    parse_client_last_modified,
)

router = APIRouter(tags=["bulk-imports"])

_ALLOWED_STRATEGIES = {
    "auto", "csv_content", "filename", "file_last_modified", "manual", "upload_order",
}


@router.post(
    "/purchase-batches/{purchase_batch_id}/roasting-batches/bulk-preview",
    response_model=BulkImportPreviewResponse,
)
async def bulk_preview(
    purchase_batch_id: str,
    db: DBSessionDep = None,
    _user: CurrentUserDep = None,
    files: list[UploadFile] = File(...),
    default_input_weight_grams: int | None = Form(None),
    inventory_effective_default: bool = Form(True),
    default_roast_date: str | None = Form(None),
    first_roast_time: str | None = Form(None),
    time_inference_strategy: str | None = Form(None),
    client_last_modified: list[str] = Form(default=[]),
):
    """Preview a multi-CSV roast generation for a purchase batch."""
    if time_inference_strategy and time_inference_strategy not in _ALLOWED_STRATEGIES:
        raise ValidationException(f"不支持的时间推断策略: {time_inference_strategy}")

    # -- Upload limits from settings --
    from ...core.config import settings
    if len(files) > settings.bulk_upload_max_files:
        raise ValidationException(
            f"单次最多上传 {settings.bulk_upload_max_files} 个文件，本次收到 {len(files)} 个"
        )
    total_bytes = 0
    for f in files:
        # Peek size before reading fully — FastAPI UploadFile doesn't expose
        # size natively, so we read and track.
        content = await f.read()
        total_bytes += len(content)
        if len(content) > settings.upload_max_size_bytes:
            raise ValidationException(
                f"文件 {f.filename} 超过 {settings.upload_max_size_bytes // 1024 // 1024}MB 限制"
            )
    if total_bytes > settings.bulk_upload_max_total_bytes:
        raise ValidationException(
            f"上传总大小 {total_bytes / 1024 / 1024:.1f}MB "
            f"超过 {settings.bulk_upload_max_total_bytes // 1024 // 1024}MB 限制"
        )
    # Re-seek for downstream — we've already consumed the stream.
    # Since FastAPI's UploadFile is SpooledTemporaryFile under the hood,
    # re-seek to start so the service layer can re-read.
    for f in files:
        await f.seek(0)

    uploaded: list[UploadedCsv] = []
    for index, f in enumerate(files):
        content = await f.read()
        if len(content) > 20 * 1024 * 1024:
            raise ValidationException(f"文件 {f.filename} 超过 20MB 限制")
        uploaded.append(UploadedCsv(
            filename=f.filename or "unknown.csv",
            content=content,
            client_last_modified=parse_client_last_modified(
                client_last_modified[index] if index < len(client_last_modified) else None
            ),
        ))

    return await preview_roast_csv_import(
        db=db,
        purchase_batch_id=purchase_batch_id,
        mode="csv_bulk_import",
        files=uploaded,
        default_input_weight_grams=default_input_weight_grams,
        inventory_effective_default=inventory_effective_default,
        default_roast_date=default_roast_date,
        first_roast_time=first_roast_time,
        time_inference_strategy=time_inference_strategy,
        created_by=_user.id if _user else None,
    )


@router.post(
    "/purchase-batches/{purchase_batch_id}/roasting-batches/bulk-commit",
    response_model=BulkImportCommitResponse,
)
async def bulk_commit(
    purchase_batch_id: str,
    job_id: str = Form(...),
    payload: str = Form(...),  # JSON: {"items": [BulkImportCommitItem, ...]}
    db: DBSessionDep = None,
    _user: CurrentUserDep = None,
    files: list[UploadFile] = File(default=[]),
):
    """Commit a previewed bulk-import job.

    The CSV files must be re-sent so their bytes are available for curve
    parsing; they are matched to preview items by file_hash. The commit
    metadata (items) is sent as a JSON ``payload`` form field so the request
    stays a single multipart/form-data submission.
    """
    try:
        parsed_payload = json.loads(payload)
    except (ValueError, TypeError) as e:
        raise HTTPException(status_code=422, detail=f"payload 解析失败: {e}")

    raw_items = parsed_payload.get("items", []) if isinstance(parsed_payload, dict) else []
    submitted: list[dict] = []
    for raw in raw_items:
        item = BulkImportCommitItem.model_validate(raw)
        submitted.append(item.model_dump(mode="python"))

    file_bytes_by_hash: dict[str, bytes] = {}
    for f in files:
        content = await f.read()
        from ...parsers.kaleido_m1 import parse_kaleido_m1
        try:
            parsed = parse_kaleido_m1(content, f.filename or "unknown.csv")
            file_bytes_by_hash[parsed.file_hash] = content
        except ValueError as e:
            raise HTTPException(status_code=422, detail=f"CSV 解析失败: {e}")

    return await commit_roast_csv_import(
        db=db,
        job_id=job_id,
        submitted_items=submitted,
        file_bytes_by_hash=file_bytes_by_hash,
        expected_purchase_batch_id=purchase_batch_id,
        expected_mode="csv_bulk_import",
    )


@router.post("/bulk-import-jobs/{job_id}/cancel", tags=["bulk-imports"])
async def cancel_bulk_job(
    job_id: str,
    db: DBSessionDep = None,
    _user: CurrentUserDep = None,
):
    """Cancel a previewed bulk-import job. Only jobs in 'previewed' status can
    be cancelled. Committed / failed / already-cancelled jobs are rejected."""
    from ...services.bulk_import import cancel_bulk_import_job
    return await cancel_bulk_import_job(db=db, job_id=job_id)
