"""Roasting batches repository."""
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.all_models import (
    RoastingBatch, PurchaseBatch, GreenBean, CurveFile, RoastingCurve,
    BatchReview, BatchReminder,
)
from .base import BaseRepository


class RoastingBatchRepository(BaseRepository[RoastingBatch]):
    model = RoastingBatch

    async def get_list(
        self,
        status: str | None = None,
        purchase_batch_id: str | None = None,
        search: str | None = None,
        has_curve: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[RoastingBatch], int]:
        stmt = (
            select(RoastingBatch)
            .options(
                selectinload(RoastingBatch.purchase_batch).selectinload(PurchaseBatch.green_bean),
                selectinload(RoastingBatch.active_curve),
            )
        )

        if status:
            stmt = stmt.where(RoastingBatch.status == status)
        if purchase_batch_id:
            stmt = stmt.where(RoastingBatch.purchase_batch_id == purchase_batch_id)

        # has_curve: check if active_curve exists
        if has_curve is True:
            stmt = stmt.where(RoastingBatch.active_curve.has())
        elif has_curve is False:
            stmt = stmt.where(~RoastingBatch.active_curve.has())

        # Count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        result = await self.db.execute(count_stmt)
        total = result.scalar_one()

        # Paginate
        stmt = stmt.order_by(RoastingBatch.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(stmt)
        items = list(result.unique().scalars().all())

        return items, total

    async def get_detail(self, batch_id: str) -> RoastingBatch | None:
        result = await self.db.execute(
            select(RoastingBatch)
            .options(
                selectinload(RoastingBatch.purchase_batch).selectinload(PurchaseBatch.green_bean),
                selectinload(RoastingBatch.active_curve),
                selectinload(RoastingBatch.reminders),
                selectinload(RoastingBatch.review),
                selectinload(RoastingBatch.questionnaires),
            )
            .where(RoastingBatch.id == batch_id)
        )
        return result.unique().scalar_one_or_none()

    async def get_by_purchase_batch(self, purchase_batch_id: str) -> list[RoastingBatch]:
        result = await self.db.execute(
            select(RoastingBatch)
            .where(RoastingBatch.purchase_batch_id == purchase_batch_id)
        )
        return list(result.scalars().all())
