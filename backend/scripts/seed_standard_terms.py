"""Seed standard terms.

Idempotent: existing category/value pairs are skipped, so this script is safe
to run repeatedly during local integration.
"""
import asyncio
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.models.all_models import StandardTerm

SEED_DATA = {
    "variety": [
        "铁皮卡", "波旁", "卡杜拉", "卡杜艾", "瑰夏",
        "SL28", "SL34", "帕卡马拉", "埃塞俄比亚原生种", "卡蒂姆",
    ],
    "process": ["水洗", "日晒", "蜜处理", "厌氧发酵", "半水洗", "湿刨法"],
    "region": ["非洲", "中美洲", "南美洲", "亚洲", "大洋洲"],
    "flavor": [
        "花香", "柑橘", "莓果", "巧克力", "坚果", "焦糖", "蜂蜜", "红酒",
        "核果", "香料", "烟草", "草本", "发酵", "奶油", "烤面包", "黑莓",
        "柠檬", "橙子", "葡萄柚", "百香果", "芒果", "桃子", "杏子", "椰子",
        "杏仁", "核桃", "榛子", "黑巧克力", "牛奶巧克力", "太妃糖",
        "茉莉花", "玫瑰花", "薰衣草", "伯爵茶", "绿茶",
    ],
    "roast_level": [
        "极浅烘焙", "浅烘焙", "中浅烘焙", "中度烘焙",
        "中深烘焙", "深度烘焙", "极深烘焙",
    ],
    "brew_method": ["手冲", "法压壶", "爱乐压", "虹吸壶", "摩卡壶", "意式浓缩", "冷萃", "冰滴"],
    "drink_temperature": ["热", "冷"],
    "drink_form": ["黑咖啡", "加奶", "其他"],
    "evaluator_type": ["烘焙师", "同事", "顾客"],
    "supplier": ["供应商A", "供应商B", "淘宝", "微批次直采"],
}


async def seed(db: AsyncSession) -> tuple[int, int]:
    created = 0
    skipped = 0
    for category, values in SEED_DATA.items():
        for display_order, value in enumerate(values):
            result = await db.execute(
                select(StandardTerm).where(
                    StandardTerm.category == category,
                    StandardTerm.value == value,
                )
            )
            if result.scalar_one_or_none():
                skipped += 1
                print(f"[SKIP] {category}/{value}")
                continue

            db.add(
                StandardTerm(
                    category=category,
                    value=value,
                    display_order=display_order,
                    is_active=True,
                )
            )
            created += 1
            print(f"[OK]   {category}/{value}")

    await db.flush()
    return created, skipped


async def main() -> None:
    engine = create_async_engine(settings.database_url)
    async with AsyncSession(engine) as db:
        created, skipped = await seed(db)
        await db.commit()
    await engine.dispose()
    print(f"\nSeed complete: created={created}, skipped={skipped}")


if __name__ == "__main__":
    asyncio.run(main())
