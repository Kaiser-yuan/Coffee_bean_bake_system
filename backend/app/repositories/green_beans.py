"""Green beans repository."""
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.all_models import GreenBean, PurchaseBatch, RoastingBatch, StandardTerm
from .base import BaseRepository


class GreenBeanRepository(BaseRepository[GreenBean]):
    model = GreenBean

    async def search_by_name(self, query: str, limit: int = 5) -> list[GreenBean]:
        stmt = (
            select(GreenBean)
            .options(selectinload(GreenBean.process))
            .where(
                GreenBean.name.ilike(f"%{query}%"),
                GreenBean.is_archived.is_(False),
            )
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_tree(
        self,
        search: str | None = None,
        variety: str | None = None,
        process: str | None = None,
        region: str | None = None,
        archive_status: str = "active",
    ) -> list[GreenBean]:
        stmt = (
            select(GreenBean)
            .options(
                selectinload(GreenBean.variety),
                selectinload(GreenBean.process),
                selectinload(GreenBean.purchase_batches).selectinload(PurchaseBatch.supplier),
            )
            .order_by(GreenBean.name)
        )

        if archive_status == "active":
            stmt = stmt.where(GreenBean.is_archived.is_(False))
        elif archive_status == "archived":
            stmt = stmt.where(GreenBean.is_archived.is_(True))

        if search:
            stmt = stmt.where(
                GreenBean.name.ilike(f"%{search}%") |
                GreenBean.brand.ilike(f"%{search}%") |
                GreenBean.region.ilike(f"%{search}%")
            )
        if variety:
            stmt = stmt.where(GreenBean.variety.has(StandardTerm.value == variety))
        if process:
            stmt = stmt.where(GreenBean.process.has(StandardTerm.value == process))
        if region:
            stmt = stmt.where(GreenBean.region == region)

        result = await self.db.execute(stmt)
        return list(result.unique().scalars().all())

    async def get_by_id_with_purchase_count(self, green_bean_id: str) -> GreenBean | None:
        """Get a green bean with count of its purchase batches (for delete/archive decision)."""
        from sqlalchemy import select as _sel
        row = await self.db.execute(
            _sel(GreenBean, func.count(PurchaseBatch.id).label("purchase_count"))
            .outerjoin(PurchaseBatch, PurchaseBatch.green_bean_id == GreenBean.id)
            .where(GreenBean.id == green_bean_id)
            .group_by(GreenBean.id)
        )
        result = row.first()
        if result is None:
            return None
        gb = result[0]
        gb.purchase_count = result[1]
        return gb
