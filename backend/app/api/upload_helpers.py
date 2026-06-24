"""Shared upload helpers — size limits and chunked reads.

P2-2: A single read path for preview & commit, bulk-import & backfill.
Files are read once into ``UploadedCsv`` tuples so the content is never
re-read / re-seeked.
"""
from fastapi import UploadFile

from ..core.config import settings
from ..core.exceptions import ValidationException
from ..services.bulk_import import UploadedCsv, parse_client_last_modified


async def read_uploads_with_limits(
    files: list[UploadFile],
    client_last_modified: list[str] | None = None,
    max_files: int | None = None,
    max_single_bytes: int | None = None,
    max_total_bytes: int | None = None,
) -> list[UploadedCsv]:
    """Read uploaded CSVs once, enforcing file-count / single-file / total-size
    limits.

    Raises ``ValidationException(422)`` before creating any job or changing
    any state.

    All users (preview & commit, bulk-import & backfill) funnel through this
    so limits are applied consistently and the hard-coded 20 MB constants are
    eliminated.
    """
    max_files = max_files if max_files is not None else settings.bulk_upload_max_files
    max_single = max_single_bytes if max_single_bytes is not None else settings.upload_max_size_bytes
    max_total = max_total_bytes if max_total_bytes is not None else settings.bulk_upload_max_total_bytes

    if not files:
        raise ValidationException("未上传任何 CSV 文件")

    if len(files) > max_files:
        raise ValidationException(
            f"单次最多上传 {max_files} 个文件，本次收到 {len(files)} 个"
        )

    results: list[UploadedCsv] = []
    total_bytes = 0
    lastmod = client_last_modified or []

    for i, f in enumerate(files):
        chunks: list[bytes] = []
        file_bytes = 0
        while chunk := await f.read(1024 * 1024):
            file_bytes += len(chunk)
            total_bytes += len(chunk)
            if file_bytes > max_single:
                raise ValidationException(
                    f"文件 {f.filename} 超过 {max_single // 1024 // 1024} MB 限制"
                )
            if total_bytes > max_total:
                raise ValidationException(
                    f"上传总大小超过 {max_total // 1024 // 1024} MB 限制"
                )
            chunks.append(chunk)

        content = b"".join(chunks)

        results.append(UploadedCsv(
            filename=f.filename or "unknown.csv",
            content=content,
            client_last_modified=parse_client_last_modified(
                lastmod[i] if i < len(lastmod) else None
            ),
        ))

    return results
