"""Review repository."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.all_models import BatchReview, ReviewReminder, BatchReminder
from .base import BaseRepository


class ReviewRepository(BaseRepository[BatchReview]):
    model = BatchReview

    async def get_by_batch(self, roasting_batch_id: str) -> BatchReview | None:
        result = await self.db.execute(
            select(BatchReview)
            .options(selectinload(BatchReview.source_reminders))
            .where(BatchReview.roasting_batch_id == roasting_batch_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create(self, roasting_batch_id: str) -> BatchReview:
        existing = await self.get_by_batch(roasting_batch_id)
        if existing:
            return existing
        review = BatchReview(roasting_batch_id=roasting_batch_id)
        self.db.add(review)
        await self.db.flush()
        return review


class BatchReminderRepository(BaseRepository[BatchReminder]):
    model = BatchReminder

    async def get_by_batch(self, roasting_batch_id: str) -> list[BatchReminder]:
        result = await self.db.execute(
            select(BatchReminder)
            .options(selectinload(BatchReminder.source_reminder))
            .where(BatchReminder.roasting_batch_id == roasting_batch_id)
            .order_by(BatchReminder.priority)
        )
        return list(result.scalars().all())
