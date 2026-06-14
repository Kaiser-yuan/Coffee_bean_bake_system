"""Standard terms repository."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.all_models import StandardTerm
from .base import BaseRepository


class TermRepository(BaseRepository[StandardTerm]):
    model = StandardTerm

    async def get_by_category(
        self, category: str | None = None, active_only: bool = False
    ) -> list[StandardTerm]:
        stmt = select(StandardTerm).order_by(StandardTerm.display_order)
        if category:
            stmt = stmt.where(StandardTerm.category == category)
        if active_only:
            stmt = stmt.where(StandardTerm.is_active == True)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_category_and_value(
        self, category: str, value: str
    ) -> StandardTerm | None:
        result = await self.db.execute(
            select(StandardTerm).where(
                StandardTerm.category == category,
                StandardTerm.value == value
            )
        )
        return result.scalar_one_or_none()

    async def get_active_for_forms(self, category: str) -> list[StandardTerm]:
        return await self.get_by_category(category=category, active_only=True)

    async def get_or_create_value(self, category: str, value: str) -> StandardTerm:
        """Find existing term or create a new active one."""
        existing = await self.get_by_category_and_value(category, value)
        if existing:
            return existing
        term = StandardTerm(category=category, value=value)
        return await self.save(term)
