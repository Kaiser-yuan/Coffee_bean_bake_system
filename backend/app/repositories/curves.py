"""Curves repository."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.all_models import CurveFile, RoastingCurve, RoastingBatch, GreenBean, PurchaseBatch
from .base import BaseRepository


class CurveFileRepository(BaseRepository[CurveFile]):
    model = CurveFile

    async def get_by_hash(self, roasting_batch_id: str, file_hash: str) -> CurveFile | None:
        result = await self.db.execute(
            select(CurveFile)
            .where(
                CurveFile.roasting_batch_id == roasting_batch_id,
                CurveFile.file_hash == file_hash,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_batch(self, roasting_batch_id: str) -> list[CurveFile]:
        result = await self.db.execute(
            select(CurveFile)
            .where(CurveFile.roasting_batch_id == roasting_batch_id)
            .order_by(CurveFile.uploaded_at.desc())
        )
        return list(result.scalars().all())


class RoastingCurveRepository(BaseRepository[RoastingCurve]):
    model = RoastingCurve

    async def get_by_batch(self, roasting_batch_id: str) -> RoastingCurve | None:
        result = await self.db.execute(
            select(RoastingCurve)
            .options(selectinload(RoastingCurve.curve_file))
            .where(RoastingCurve.roasting_batch_id == roasting_batch_id)
        )
        return result.scalar_one_or_none()

    async def get_by_batch_ids(self, batch_ids: list[str]) -> list[RoastingCurve]:
        result = await self.db.execute(
            select(RoastingCurve)
            .options(selectinload(RoastingCurve.curve_file))
            .where(RoastingCurve.roasting_batch_id.in_(batch_ids))
        )
        return list(result.scalars().all())
