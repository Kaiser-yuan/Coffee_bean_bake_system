"""Bulk CSV import service — multi-CSV roast generation & historical backfill.

Two entry points (purchase-batch bulk import, historical backfill) share the
same preview/commit pipeline:

    CSV parse → time inference → preview (persist job+items) →
    commit (create completed roasting_batches + curve_files + curves,
    optional inventory deduction)

Inventory and curve handling reuse the existing services
(lock_purchase_batch / calculate_remaining_stock / append_inventory_ledger
and parse_kaleido_m1 / parse_and_activate_curve).
"""
import logging
import random
import re
from datetime import datetime, timezone, timedelta, date, time

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.exceptions import (
    NotFoundException, ValidationException, ConflictException,
    InsufficientInventoryException,
)
from ..core.timezone_utils import naive_to_utc, combine_naive, now_utc, get_app_zone
from ..models.all_models import (
    BulkImportJob, BulkImportItem, RoastingBatch, CurveFile,
)
from ..parsers.kaleido_m1 import parse_kaleido_m1, compute_auc
from ..repositories.bulk_imports import (
    BulkImportJobRepository, find_duplicate_hashes,
)
from ..repositories.purchase_batches import PurchaseBatchRepository
from ..services.inventory import (
    calculate_remaining_stock, append_inventory_ledger, lock_purchase_batch,
)
from ..services.curve import parse_and_activate_curve

logger = logging.getLogger("coffee-roast.bulk_import")

BATCH_COLORS = ["#df5b45", "#3478d4", "#1f9d68", "#8b5cc7", "#e5a029", "#d94b4b"]
# Default spacing between consecutive roasts when assigning times by upload order.
ROAST_SPACING_MINUTES = 45

_FILENAME_DATE_RE = re.compile(r"(\d{2})(\d{2})(\d{2})")


# ============================================================
# Time inference
# ============================================================
def parse_client_last_modified(raw: str | None) -> datetime | None:
    """Parse browser File.lastModified, which is epoch milliseconds.

    File.lastModified is *already* an absolute epoch timestamp — it doesn't
    need timezone reinterpretation. We preserve it as-is in UTC.
    """
    if not raw:
        return None
    try:
        return datetime.fromtimestamp(float(raw) / 1000.0, tz=timezone.utc)
    except (ValueError, TypeError, OSError):
        return None


def is_duplicate_file_hash(
    file_hash: str, existing_hashes: set[str], seen_hashes: set[str],
) -> bool:
    """Mark duplicates found in the database or earlier in the same upload."""
    duplicate = file_hash in existing_hashes or file_hash in seen_hashes
    seen_hashes.add(file_hash)
    return duplicate


def _parse_date_str(s: str | None) -> date | None:
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _parse_time_str(s: str | None) -> time | None:
    if not s:
        return None
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(s.strip(), fmt).time()
        except ValueError:
            continue
    return None


def _parse_csv_cooked_at(raw: str | None) -> datetime | None:
    """Best-effort parse of the Kaleido CookDate parameter into UTC.

    CookDate is a local-time string. We parse it as naive, then attach
    the application timezone and convert to UTC.
    """
    if not raw:
        return None
    raw = raw.strip()
    candidates = (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%m/%d/%Y %H:%M",
    )
    for fmt in candidates:
        try:
            parsed = datetime.strptime(raw, fmt)
            return naive_to_utc(parsed)
        except ValueError:
            continue
    return None


def _from_filename(filename: str) -> datetime | None:
    """Parse a date out of a filename like ``260530_9.csv`` -> 2026-05-30.

    The date is a local calendar date — interpret in app timezone, yield UTC.
    """
    m = _FILENAME_DATE_RE.search(filename)
    if not m:
        return None
    yy, mm, dd = int(m.group(1)), int(m.group(2)), int(m.group(3))
    year = 2000 + yy if yy < 70 else 1900 + yy
    try:
        d = date(year, mm, dd)
        return combine_naive(d, time(0, 0))
    except ValueError:
        return None


def infer_roasted_at(
    *,
    filename: str,
    parsed,
    client_last_modified: datetime | None,
    default_roast_date: str | None,
    first_roast_time: str | None,
    order: int,
    strategy: str | None,
) -> tuple[datetime | None, str | None]:
    """Infer the roasted_at timestamp for one CSV.

    Priority (when strategy is None/'auto'):
      1. csv_content   — Kaleido CookDate parameter
      2. filename      — leading YYMMDD in the filename
      3. file_last_modified — browser-supplied lastModified (already UTC)
      4. manual        — default_roast_date + first_roast_time
      5. upload_order  — default_roast_date + first_roast_time + order spacing

    All local-time sources (csv_content, filename, manual, upload_order) are
    interpreted in the app timezone and returned as UTC.

    Returns (datetime|None, source_label|None).
    """
    base_date = _parse_date_str(default_roast_date)
    base_time = _parse_time_str(first_roast_time) or time(0, 0)

    def _manual_dt() -> datetime | None:
        if base_date is None:
            return None
        return combine_naive(base_date, base_time)

    def _upload_order_dt() -> datetime | None:
        if base_date is None:
            return None
        offset = (order - 1) * ROAST_SPACING_MINUTES if order > 0 else 0
        dt = combine_naive(base_date, base_time)
        return dt + timedelta(minutes=offset)

    sources = {
        "csv_content": lambda: _parse_csv_cooked_at(
            parsed.parameters.cooked_at if parsed else None
        ),
        "filename": lambda: _from_filename(filename),
        "file_last_modified": lambda: (
            client_last_modified.astimezone(timezone.utc)
            if client_last_modified else None
        ),
        "manual": _manual_dt,
        "upload_order": _upload_order_dt,
    }

    if strategy and strategy != "auto" and strategy in sources:
        val = sources[strategy]()
        return val, (strategy if val else None)

    # Auto priority
    for key in ("csv_content", "filename", "file_last_modified", "manual", "upload_order"):
        val = sources[key]()
        if val is not None:
            return val, key
    return None, None


# ============================================================
# Curve summary
# ============================================================
def _build_preview_summary(parsed) -> dict:
    events_by_type = {e.event_type: e for e in parsed.events}
    charge = events_by_type.get("charge")
    fc_start = events_by_type.get("first_crack_start")
    drop = events_by_type.get("drop")
    dev_ratio = None
    if fc_start and drop and charge and drop.time_seconds > charge.time_seconds:
        total = drop.time_seconds - charge.time_seconds
        dev_time = drop.time_seconds - fc_start.time_seconds
        dev_ratio = round(dev_time / total * 100, 2) if total > 0 else None
    auc = compute_auc(parsed.points)
    return {
        "total_time_seconds": round(parsed.total_time_seconds, 2),
        "turning_point_seconds": round(events_by_type["turning_point"].time_seconds, 2)
        if "turning_point" in events_by_type else None,
        "yellowing_seconds": round(events_by_type["yellowing"].time_seconds, 2)
        if "yellowing" in events_by_type else None,
        "first_crack_start_seconds": round(fc_start.time_seconds, 2) if fc_start else None,
        "development_ratio_percent": dev_ratio,
        "auc_bt_above_100": auc,
    }


def _save_curve_file(content: bytes, roasting_batch_id: str, file_id: str) -> str:
    now = datetime.now(timezone.utc)
    rel_path = f"roast-curves/{now.year}/{now.month:02d}/{roasting_batch_id}/{file_id}.csv"
    full_path = settings.upload_path / rel_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_bytes(content)
    return rel_path


# ============================================================
# Preview
# ============================================================
class UploadedCsv:
    """Lightweight container for one uploaded CSV in a preview request."""
    __slots__ = ("filename", "content", "client_last_modified")

    def __init__(self, filename: str, content: bytes, client_last_modified: datetime | None):
        self.filename = filename
        self.content = content
        self.client_last_modified = client_last_modified


async def preview_roast_csv_import(
    *,
    db: AsyncSession,
    purchase_batch_id: str,
    mode: str,
    files: list[UploadedCsv],
    default_input_weight_grams: int | None,
    inventory_effective_default: bool,
    default_roast_date: str | None = None,
    first_roast_time: str | None = None,
    time_inference_strategy: str | None = None,
    created_by: str | None = None,
) -> dict:
    """Parse uploaded CSVs, persist a preview job + items, return preview payload.

    Does NOT create roasting_batches or deduct inventory.
    """
    if not files:
        raise ValidationException("未上传任何 CSV 文件")
    if mode not in ("csv_bulk_import", "historical_backfill"):
        raise ValidationException(f"未知的导入模式: {mode}")

    purchase_batch = await PurchaseBatchRepository(db).get_by_id(purchase_batch_id)
    if not purchase_batch:
        raise NotFoundException("PurchaseBatch", purchase_batch_id)

    # Persist job first so items can reference it
    job = BulkImportJob(
        purchase_batch_id=purchase_batch_id,
        mode=mode,
        status="previewed",
        file_count=len(files),
        default_input_weight_grams=default_input_weight_grams,
        inventory_effective_default=inventory_effective_default,
        created_by=created_by,
        created_at=datetime.now(timezone.utc),
    )
    db.add(job)
    await db.flush()

    # Pre-parse to collect hashes for duplicate detection
    parsed_files: list[tuple[UploadedCsv, object]] = []
    hashes: list[str] = []
    for uf in files:
        try:
            parsed = parse_kaleido_m1(uf.content, uf.filename)
            parsed_files.append((uf, parsed))
            hashes.append(parsed.file_hash)
        except ValueError:
            parsed_files.append((uf, None))

    duplicate_hashes = await find_duplicate_hashes(db, purchase_batch_id, hashes)

    items_payload: list[dict] = []
    seen_hashes: set[str] = set()
    for order, (uf, parsed) in enumerate(parsed_files, start=1):
        if parsed is None:
            try:
                reparsed = parse_kaleido_m1(uf.content, uf.filename)
                file_hash = reparsed.file_hash
            except ValueError as e:
                file_hash = ""
                item = BulkImportItem(
                    job_id=job.id,
                    original_filename=uf.filename,
                    file_hash=file_hash,
                    file_size_bytes=len(uf.content),
                    client_last_modified_at=uf.client_last_modified,
                    display_order=order,
                    parse_status="failed",
                    parse_error_message=str(e),
                    warnings=None,
                    preview_summary=None,
                )
                db.add(item)
                await db.flush()
                items_payload.append({
                    "item_id": item.id,
                    "filename": uf.filename,
                    "file_hash": file_hash,
                    "file_size_bytes": len(uf.content),
                    "inferred_roasted_at": None,
                    "roasted_at_source": None,
                    "input_weight_grams": default_input_weight_grams,
                    "output_weight_grams": None,
                    "inventory_effective": inventory_effective_default,
                    "parse_status": "failed",
                    "parse_error_message": str(e),
                    "summary": {},
                    "warnings": [],
                    "is_duplicate": False,
                })
                continue
            parsed = reparsed

        inferred_dt, source = infer_roasted_at(
            filename=uf.filename,
            parsed=parsed,
            client_last_modified=uf.client_last_modified,
            default_roast_date=default_roast_date,
            first_roast_time=first_roast_time,
            order=order,
            strategy=time_inference_strategy,
        )
        summary = _build_preview_summary(parsed)
        warnings = [str(w) if not isinstance(w, str) else w for w in parsed.warnings]
        is_dup = is_duplicate_file_hash(parsed.file_hash, duplicate_hashes, seen_hashes)

        item = BulkImportItem(
            job_id=job.id,
            original_filename=uf.filename,
            file_hash=parsed.file_hash,
            file_size_bytes=len(uf.content),
            client_last_modified_at=uf.client_last_modified,
            inferred_roasted_at=inferred_dt,
            roasted_at_source=source,
            display_order=order,
            parse_status="parsed",
            parse_error_message=None,
            warnings={"items": warnings} if warnings else None,
            preview_summary=summary,
        )
        db.add(item)
        await db.flush()

        items_payload.append({
            "item_id": item.id,
            "filename": uf.filename,
            "file_hash": parsed.file_hash,
            "file_size_bytes": len(uf.content),
            "inferred_roasted_at": inferred_dt.isoformat() if inferred_dt else None,
            "roasted_at_source": source,
            "input_weight_grams": default_input_weight_grams,
            "output_weight_grams": None,
            "inventory_effective": inventory_effective_default,
            "parse_status": "parsed",
            "parse_error_message": None,
            "summary": summary,
            "warnings": warnings,
            "is_duplicate": is_dup,
        })

    available = await calculate_remaining_stock(db, purchase_batch_id)
    total_planned = sum(
        (it["input_weight_grams"] or 0) for it in items_payload
        if it["parse_status"] == "parsed" and not it["is_duplicate"]
    )

    blocking_errors: list[str] = []
    if mode == "csv_bulk_import" and total_planned > available:
        blocking_errors.append(
            f"预计投豆量 {total_planned}g 超过当前库存 {available}g，提交时将被拒绝"
        )

    return {
        "job_id": job.id,
        "purchase_batch_id": purchase_batch_id,
        "mode": mode,
        "inventory_effective_default": inventory_effective_default,
        "available_stock_grams": available,
        "total_planned_input_grams": total_planned,
        "items": items_payload,
        "blocking_errors": blocking_errors,
    }


# ============================================================
# Commit
# ============================================================
async def commit_roast_csv_import(
    *,
    db: AsyncSession,
    job_id: str,
    submitted_items: list[dict],
    file_bytes_by_hash: dict[str, bytes],
    expected_purchase_batch_id: str | None = None,
    expected_mode: str | None = None,
) -> dict:
    """Commit a previewed job: create completed roasting batches + curves.

    The HTTP layer carries the original CSV bytes keyed by ``file_hash`` so
    commit is self-sufficient (preview does not persist large blobs).

    Inventory is checked globally — the sum of effective items' input weights
    must not exceed available stock, or the whole commit is rejected. Each
    item is then processed in the same transaction (the request commits
    atomically via the ``get_db`` dependency). A job can only be committed
    once (防重复提交).
    """
    job_repo = BulkImportJobRepository(db)
    job = await job_repo.get_with_items(job_id, for_update=True)
    if not job:
        raise NotFoundException("BulkImportJob", job_id)
    if expected_purchase_batch_id and job.purchase_batch_id != expected_purchase_batch_id:
        raise ConflictException(
            code="BULK_IMPORT_PURCHASE_BATCH_MISMATCH",
            message="导入任务与当前采购批次不匹配",
        )
    if expected_mode and job.mode != expected_mode:
        raise ConflictException(
            code="BULK_IMPORT_MODE_MISMATCH",
            message="导入任务类型与当前入口不匹配",
        )
    if job.status == "committed":
        raise ConflictException(
            code="BULK_IMPORT_ALREADY_COMMITTED",
            message="该导入任务已提交，不能重复生成批次",
        )
    if job.status in ("cancelled", "failed"):
        raise ConflictException(
            code="BULK_IMPORT_NOT_COMMITTABLE",
            message=f"导入任务状态为 {job.status}，无法提交",
        )

    items_by_id = {it.id: it for it in job.items}

    # Resolve a plan for every submitted, parsed item
    plan: list[dict] = []
    submitted_item_ids: set[str] = set()
    for sub in submitted_items:
        if sub["item_id"] in submitted_item_ids:
            raise ValidationException(f"条目 {sub['item_id']} 被重复提交")
        submitted_item_ids.add(sub["item_id"])
        item = items_by_id.get(sub["item_id"])
        if item is None:
            raise NotFoundException("BulkImportItem", sub["item_id"])
        if item.parse_status != "parsed":
            continue
        if item.roasting_batch_id or item.curve_file_id:
            raise ConflictException(
                code="BULK_IMPORT_ITEM_ALREADY_COMMITTED",
                message=f"文件 {item.original_filename} 已生成烘焙批次",
            )
        actual_input = sub.get("actual_input_weight_grams") or job.default_input_weight_grams
        if not actual_input or actual_input <= 0:
            raise ValidationException(
                f"文件 {item.original_filename} 缺少投豆量，无法提交"
            )
        inv_eff = sub.get("inventory_effective")
        if inv_eff is None:
            inv_eff = job.inventory_effective_default
        roasted_at = sub.get("roasted_at") or item.inferred_roasted_at
        if roasted_at is None:
            raise ValidationException(
                f"文件 {item.original_filename} 缺少烘焙时间，无法提交"
            )
        if item.file_hash not in file_bytes_by_hash:
            raise ValidationException(
                f"文件 {item.original_filename} 的原始内容缺失，无法提交"
            )
        output_weight = sub.get("output_weight_grams")
        # 0 means "not provided" — treat as None. Only validate when
        # the caller explicitly passes a positive or sentinel value.
        if output_weight is not None and output_weight != 0:
            if output_weight <= 0:
                raise ValidationException(
                    f"文件 {item.original_filename} 的出豆量必须大于零"
                )
            if output_weight > actual_input:
                raise ValidationException(
                    f"文件 {item.original_filename} 的出豆量 ({output_weight}g) "
                    f"超过投豆量 ({actual_input}g)"
                )
        else:
            output_weight = None
        plan.append({
            "item": item,
            "actual_input": actual_input,
            "inventory_effective": inv_eff,
            "roasted_at": roasted_at,
            "output_weight": output_weight,
            "source_note": sub.get("source_note"),
            "content": file_bytes_by_hash[item.file_hash],
        })

    if not plan:
        raise ValidationException("没有可提交的有效条目")

    # Global inventory check + lock
    total_effective_input = sum(p["actual_input"] for p in plan if p["inventory_effective"])
    if job.purchase_batch_id:
        _pb = await lock_purchase_batch(db, job.purchase_batch_id)
        if not _pb:
            raise NotFoundException("PurchaseBatch", job.purchase_batch_id)

        duplicate_hashes = await find_duplicate_hashes(
            db,
            job.purchase_batch_id,
            [p["item"].file_hash for p in plan],
        )
        if duplicate_hashes:
            raise ConflictException(
                code="DUPLICATE_CURVE_FILE",
                message="提交文件中存在已导入的重复 CSV",
                details={"file_hashes": sorted(duplicate_hashes)},
            )

    if job.purchase_batch_id and total_effective_input > 0:
        available = await calculate_remaining_stock(db, job.purchase_batch_id)
        if total_effective_input > available:
            raise InsufficientInventoryException(
                available_grams=available,
                required_grams=total_effective_input,
            )

    entry_mode = "csv_bulk_import" if job.mode == "csv_bulk_import" else "historical_backfill"

    success_count = 0
    failed_count = 0
    total_consumed = 0
    result_items: list[dict] = []

    for p in plan:
        item: BulkImportItem = p["item"]
        content: bytes = p["content"]
        storage_path: str | None = None
        try:
            async with db.begin_nested():
                # 1. Create the completed roasting batch
                batch = RoastingBatch(
                    purchase_batch_id=job.purchase_batch_id,
                    status="completed",
                    planned_at=p["roasted_at"],
                    roasted_at=p["roasted_at"],
                    planned_input_weight_grams=p["actual_input"],
                    actual_input_weight_grams=p["actual_input"],
                    output_weight_grams=p["output_weight"],
                    entry_mode=entry_mode,
                    inventory_effective=p["inventory_effective"],
                    roasted_at_source=item.roasted_at_source,
                    bulk_import_group_id=job.id,
                    source_note=p["source_note"],
                    color_tag=random.choice(BATCH_COLORS),
                )
                if p["output_weight"]:
                    batch.weight_loss_percent = round(
                        (1 - p["output_weight"] / p["actual_input"]) * 100, 1
                    )
                db.add(batch)
                await db.flush()

                # 2. Create curve file record + save bytes to disk
                cf = CurveFile(
                    roasting_batch_id=batch.id,
                    original_filename=item.original_filename,
                    storage_path="",
                    file_size_bytes=len(content),
                    file_hash=item.file_hash,
                    source_type="kaleido_m1",
                    format_type="kaleido_kldo_v101",
                    parse_status="parsing",
                    parser_version="kl_v1.0",
                    uploaded_at=datetime.now(timezone.utc),
                )
                db.add(cf)
                await db.flush()
                storage_path = _save_curve_file(content, batch.id, cf.id)
                cf.storage_path = storage_path

                # 3. Parse + activate curve (sets batch summary fields too)
                await parse_and_activate_curve(db, cf, content)
                cf.parse_status = "parsed"
                cf.parsed_at = datetime.now(timezone.utc)
                await db.flush()

                # 4. Optional inventory deduction
                if p["inventory_effective"]:
                    await append_inventory_ledger(
                        db=db,
                        purchase_batch_id=job.purchase_batch_id,
                        change_grams=-p["actual_input"],
                        event_type="roast_consumption",
                        related_entity_type="roasting_batch",
                        related_entity_id=batch.id,
                    )
                    await db.flush()

                # 5. Link item back to created entities
                item.roasting_batch_id = batch.id
                item.curve_file_id = cf.id
                await db.flush()

            success_count += 1
            if p["inventory_effective"]:
                total_consumed += p["actual_input"]
            result_items.append({
                "item_id": item.id,
                "filename": item.original_filename,
                "success": True,
                "roasting_batch_id": batch.id,
                "error_message": None,
            })
        except Exception as e:  # pragma: no cover - defensive
            logger.exception("Bulk import item failed: %s", item.original_filename)
            if storage_path:
                (settings.upload_path / storage_path).unlink(missing_ok=True)
            failed_count += 1
            result_items.append({
                "item_id": item.id,
                "filename": item.original_filename,
                "success": False,
                "roasting_batch_id": None,
                "error_message": str(e),
            })

    job.status = "committed" if success_count > 0 else "failed"
    job.success_count = success_count
    job.failed_count = failed_count
    job.committed_at = datetime.now(timezone.utc)
    await db.flush()

    return {
        "job_id": job.id,
        "status": job.status,
        "success_count": success_count,
        "failed_count": failed_count,
        "total_consumed_grams": total_consumed,
        "items": result_items,
    }


# ============================================================
# Cancel
# ============================================================
async def cancel_bulk_import_job(
    *,
    db: AsyncSession,
    job_id: str,
) -> dict:
    """Cancel a previewed bulk-import job.

    Only jobs in ``previewed`` status can be cancelled. Committed or
    already-cancelled jobs are rejected with an appropriate error.
    """
    job_repo = BulkImportJobRepository(db)
    job = await job_repo.get_with_items(job_id)
    if not job:
        raise NotFoundException("BulkImportJob", job_id)
    if job.status == "committed":
        raise ConflictException(
            code="BULK_IMPORT_ALREADY_COMMITTED",
            message="已提交的导入任务不能取消",
        )
    if job.status == "cancelled":
        raise ConflictException(
            code="BULK_IMPORT_ALREADY_CANCELLED",
            message="导入任务已取消",
        )
    if job.status == "failed":
        raise ConflictException(
            code="BULK_IMPORT_FAILED",
            message="导入任务已失败，不能取消",
        )
    job.status = "cancelled"
    await db.flush()
    return {"job_id": job.id, "status": "cancelled"}


async def expire_stale_bulk_jobs(db: AsyncSession) -> int:
    """Cancel all previewed jobs older than ``settings.bulk_job_expiry_seconds``.

    Returns the number of jobs expired. Call this from a periodic task
    (cron / background scheduler) or from a dedicated admin endpoint.
    """
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(
        seconds=settings.bulk_job_expiry_seconds
    )
    result = await db.execute(
        select(BulkImportJob)
        .where(
            BulkImportJob.status == "previewed",
            BulkImportJob.created_at < cutoff,
        )
        .with_for_update()
    )
    stale_jobs = list(result.scalars().all())
    for job in stale_jobs:
        job.status = "cancelled"
    if stale_jobs:
        await db.flush()
        logger.info(
            "Expired %d stale previewed bulk-import jobs (cutoff %s)",
            len(stale_jobs),
            cutoff.isoformat(),
        )
    return len(stale_jobs)
