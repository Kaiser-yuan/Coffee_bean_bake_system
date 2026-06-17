"""Repositories for bulk import jobs and items."""
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..models.all_models import (
    BulkImportJob, BulkImportItem, CurveFile, RoastingBatch,
)
from .base import BaseRepository


class BulkImportJobRepository(BaseRepository[BulkImportJob]):
    model = BulkImportJob

    async def get_with_items(self, job_id: str) -> BulkImportJob | None:
        result = await self.db.execute(
            select(BulkImportJob)
            .options(selectinload(BulkImportJob.items))
            .where(BulkImportJob.id == job_id)
        )
        return result.scalar_one_or_none()


class BulkImportItemRepository(BaseRepository[BulkImportItem]):
    model = BulkImportItem

    async def list_by_job(self, job_id: str) -> list[BulkImportItem]:
        result = await self.db.execute(
            select(BulkImportItem)
            .where(BulkImportItem.job_id == job_id)
            .order_by(BulkImportItem.display_order.asc())
        )
        return list(result.scalars().all())


async def find_duplicate_hashes(
    db, purchase_batch_id: str | None, hashes: list[str]
) -> set[str]:
    """Return the subset of `hashes` already stored as curve files under a
    purchase batch (roasting_batch -> purchase_batch). Used to detect
    duplicate uploads across the (purchase_batch_id, file_hash) dimension.
    """
    if not hashes:
        return set()
    if purchase_batch_id is None:
        return set()
    result = await db.execute(
        select(CurveFile.file_hash)
        .join(RoastingBatch, RoastingBatch.id == CurveFile.roasting_batch_id)
        .where(
            RoastingBatch.purchase_batch_id == purchase_batch_id,
            CurveFile.file_hash.in_(hashes),
        )
    )
    return set(result.scalars().all())
