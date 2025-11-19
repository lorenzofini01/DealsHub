"""
Infrastructure - Price History Repository
"""
from typing import Optional
from decimal import Decimal
from datetime import datetime, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from ...domain import PriceHistory, IPriceHistoryRepository
from .sqlalchemy_models import PriceHistoryModel


class SQLAlchemyPriceHistoryRepository(IPriceHistoryRepository):
    """Repository per storico prezzi"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_entry(self, history: PriceHistory) -> PriceHistory:
        """Aggiungi entry allo storico"""
        model = PriceHistoryModel(
            asin=history.asin,
            price=history.price,
            source=history.source
        )
        self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)

        history.id = model.id
        history.recorded_at = model.recorded_at
        return history

    async def get_average_price(self, asin: str, days: int = 30) -> Optional[Decimal]:
        """Ritorna prezzo medio negli ultimi N giorni"""
        cutoff = datetime.now() - timedelta(days=days)
        stmt = select(func.avg(PriceHistoryModel.price)).where(
            PriceHistoryModel.asin == asin,
            PriceHistoryModel.recorded_at >= cutoff
        )
        result = await self.session.execute(stmt)
        avg = result.scalar_one_or_none()
        return Decimal(str(avg)) if avg else None

    async def get_lowest_price(self, asin: str, days: int = 30) -> Optional[Decimal]:
        """Ritorna prezzo minimo negli ultimi N giorni"""
        cutoff = datetime.now() - timedelta(days=days)
        stmt = select(func.min(PriceHistoryModel.price)).where(
            PriceHistoryModel.asin == asin,
            PriceHistoryModel.recorded_at >= cutoff
        )
        result = await self.session.execute(stmt)
        min_price = result.scalar_one_or_none()
        return Decimal(str(min_price)) if min_price else None
