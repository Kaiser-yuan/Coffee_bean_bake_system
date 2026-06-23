"""Historical data backfill API — archive old roast CSVs.

Shares the preview/commit pipeline with the bulk-import feature but defaults
to ``inventory_effective=False`` (archive-only, does not affect current stock)
and ``entry_mode=historical_backfill``.

P2-2: Upload limits are enforced by the shared ``read_uploads_with_limits``
helper — no double-read, no hardcoded 20 MB, no re-seek.
"""
import json

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from ..dependencies import CurrentUserDep, DBSessionDep
from ...core.exceptions import ValidationException
from ...schemas.all_schemas import (
    BulkImportCommitItem, BulkImportCommitResponse, BulkImportPreviewResponse,
)
from ...services.bulk_import import (
    preview_roast_csv_import, commit_roast_csv_import,
)
from ..upload_helpers import read_uploads_with_limits

router = APIRouter(prefix="/backfills", tags=["backfills"])

_ALLOWED_STRATEGIES = {
    "auto", "csv_content", "filename", "file_last_modified", "manual", "upload_order",
}


@router.post(
    "/roasting-csv/preview",
    response_model=BulkImportPreviewResponse,
)
async def backfill_preview(
    db: DBSessionDep = None,
    _user: CurrentUserDep = None,
    purchase_batch_id: str = Form(...),
    files: list[UploadFile] = File(...),
    default_input_weight_grams: int | None = Form(None),
    inventory_effective_default: bool = Form(False),
    default_roast_date: str | None = Form(None),
    first_roast_time: str | None = Form(None),
    time_inference_strategy: str | None = Form(None),
    client_last_modified: list[str] = Form(default=[]),
):
    """Preview a historical backfill. Defaults to archive-only (no stock effect)."""
    if time_inference_strategy and time_inference_strategy not in _ALLOWED_STRATEGIES:
        raise ValidationException(f"不支持的时间推断策略: {time_inference_strategy}")

    uploaded = await read_uploads_with_limits(
        files, client_last_modified=client_last_modified,
    )

    return await preview_roast_csv_import(
        db=db,
        purchase_batch_id=purchase_batch_id,
        mode="historical_backfill",
        files=uploaded,
        default_input_weight_grams=default_input_weight_grams,
        inventory_effective_default=inventory_effective_default,
        default_roast_date=default_roast_date,
        first_roast_time=first_roast_time,
        time_inference_strategy=time_inference_strategy,
        created_by=_user.id if _user else None,
    )


@router.post(
    "/roasting-csv/commit",
    response_model=BulkImportCommitResponse,
)
async def backfill_commit(
    job_id: str = Form(...),
    payload: str = Form(...),  # JSON: {"items": [BulkImportCommitItem, ...]}
    db: DBSessionDep = None,
    _user: CurrentUserDep = None,
    files: list[UploadFile] = File(default=[]),
):
    """Commit a historical backfill job. Re-send CSV files matched by hash."""
    try:
        parsed_payload = json.loads(payload)
    except (ValueError, TypeError) as e:
        raise HTTPException(status_code=422, detail=f"payload 解析失败: {e}")

    raw_items = parsed_payload.get("items", []) if isinstance(parsed_payload, dict) else []
    submitted: list[dict] = []
    for raw in raw_items:
        item = BulkImportCommitItem.model_validate(raw)
        submitted.append(item.model_dump(mode="python"))

    from ...core.config import settings
    if len(files) > settings.bulk_upload_max_files * 2:
        raise HTTPException(status_code=422, detail="文件数量超过限制")

    file_bytes_by_hash: dict[str, bytes] = {}
    for f in files:
        content = await f.read()
        if len(content) > settings.upload_max_size_bytes:
            raise HTTPException(status_code=422, detail=f"文件 {f.filename} 超过限制")
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
        expected_mode="historical_backfill",
    )
