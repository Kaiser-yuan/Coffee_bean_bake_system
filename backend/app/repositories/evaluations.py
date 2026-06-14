"""Evaluation repository."""
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.all_models import CuppingEvaluation
from .base import BaseRepository


class EvaluationRepository(BaseRepository[CuppingEvaluation]):
    model = CuppingEvaluation

    async def get_by_questionnaire(self, questionnaire_id: str) -> list[CuppingEvaluation]:
        result = await self.db.execute(
            select(CuppingEvaluation)
            .where(CuppingEvaluation.questionnaire_id == questionnaire_id)
            .order_by(CuppingEvaluation.submitted_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_batch(self, roasting_batch_id: str) -> list[CuppingEvaluation]:
        result = await self.db.execute(
            select(CuppingEvaluation)
            .where(CuppingEvaluation.roasting_batch_id == roasting_batch_id)
            .order_by(CuppingEvaluation.submitted_at.desc())
        )
        return list(result.scalars().all())

    async def get_count_by_questionnaire(self, questionnaire_id: str) -> int:
        result = await self.db.execute(
            select(func.count())
            .where(CuppingEvaluation.questionnaire_id == questionnaire_id)
        )
        return result.scalar_one()
