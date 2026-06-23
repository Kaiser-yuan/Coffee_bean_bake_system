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
        self, category: str, value: str, active_only: bool = False
    ) -> StandardTerm | None:
        stmt = select(StandardTerm).where(
            StandardTerm.category == category,
            StandardTerm.value == value,
        )
        if active_only:
            stmt = stmt.where(StandardTerm.is_active == True)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_for_forms(self, category: str) -> list[StandardTerm]:
        return await self.get_by_category(category=category, active_only=True)

    async def get_or_create_value(self, category: str, value: str) -> StandardTerm:
        """Find an existing term or insert a new active one — admin only.

        Uses PostgreSQL ``INSERT ... ON CONFLICT DO NOTHING`` so concurrent
        admin inserts of the same (category, value) never raise a unique-
        violation 500. On conflict the caller simply re-queries — the shared
        session is never rolled back (which would abort the whole request
        transaction).
        """
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        existing = await self.get_by_category_and_value(category, value)
        if existing:
            return existing

        stmt = (
            pg_insert(StandardTerm)
            .values(category=category, value=value, is_active=True)
            .on_conflict_do_nothing(index_elements=["category", "value"])
            .returning(StandardTerm)
        )
        result = await self.db.execute(stmt)
        term = result.scalar_one_or_none()
        if term is not None:
            return term
        # Lost the race — another request inserted and committed it.
        return await self.get_by_category_and_value(category, value)
