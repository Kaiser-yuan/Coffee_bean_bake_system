"""Purchase batches repository."""
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.all_models import (
    PurchaseBatch, InventoryLedger, InventoryAdjustment,
    RoastingBatch, GreenBean,
)
from .base import BaseRepository


class PurchaseBatchRepository(BaseRepository[PurchaseBatch]):
    model = PurchaseBatch

    async def get_by_green_bean_id(self, green_bean_id: str) -> list[PurchaseBatch]:
        result = await self.db.execute(
            select(PurchaseBatch).where(PurchaseBatch.green_bean_id == green_bean_id)
        )
        return list(result.scalars().all())

    async def get_detail(self, purchase_batch_id: str) -> PurchaseBatch | None:
        result = await self.db.execute(
            select(PurchaseBatch)
            .options(
                selectinload(PurchaseBatch.green_bean),
                selectinload(PurchaseBatch.adjustments),
            )
            .where(PurchaseBatch.id == purchase_batch_id)
        )
        return result.scalar_one_or_none()


class InventoryLedgerRepository(BaseRepository[InventoryLedger]):
    model = InventoryLedger

    async def get_ledger_by_purchase_batch(
        self, purchase_batch_id: str, limit: int = 100
    ) -> list[InventoryLedger]:
        result = await self.db.execute(
            select(InventoryLedger)
            .where(InventoryLedger.purchase_batch_id == purchase_batch_id)
            .order_by(InventoryLedger.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_latest_result(self, purchase_batch_id: str) -> int:
        """Get the latest resulting_grams, or 0."""
        result = await self.db.execute(
            select(InventoryLedger.resulting_grams)
            .where(InventoryLedger.purchase_batch_id == purchase_batch_id)
            .order_by(InventoryLedger.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none() or 0

    async def add_entry(
        self,
        purchase_batch_id: str,
        event_type: str,
        change_grams: int,
        resulting_grams: int,
        related_entity_type: str | None = None,
        related_entity_id: str | None = None,
    ) -> InventoryLedger:
        entry = InventoryLedger(
            purchase_batch_id=purchase_batch_id,
            event_type=event_type,
            change_grams=change_grams,
            resulting_grams=resulting_grams,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
        )
        self.db.add(entry)
        return entry
