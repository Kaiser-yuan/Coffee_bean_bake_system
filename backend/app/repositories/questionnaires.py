"""Questionnaire repository."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.all_models import Questionnaire
from .base import BaseRepository


class QuestionnaireRepository(BaseRepository[Questionnaire]):
    model = Questionnaire

    async def get_by_share_code(self, share_code: str) -> Questionnaire | None:
        result = await self.db.execute(
            select(Questionnaire).where(Questionnaire.share_code == share_code)
        )
        return result.scalar_one_or_none()

    async def get_by_batch(self, roasting_batch_id: str) -> list[Questionnaire]:
        result = await self.db.execute(
            select(Questionnaire)
            .where(Questionnaire.roasting_batch_id == roasting_batch_id)
            .order_by(Questionnaire.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_open_for_batch(self, roasting_batch_id: str) -> Questionnaire | None:
        """Get the currently open questionnaire for a batch (first edition: max 1)."""
        result = await self.db.execute(
            select(Questionnaire)
            .where(
                Questionnaire.roasting_batch_id == roasting_batch_id,
                Questionnaire.status == "open",
            )
            .limit(1)
        )
        return result.scalar_one_or_none()
