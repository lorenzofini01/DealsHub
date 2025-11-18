# backend/app/crud.py
from .database import async_session
from .models import Offer
from .schemas import OfferIn
from sqlalchemy import select, or_

async def create_or_update_offer(payload: OfferIn):
    async with async_session() as session:
        # semplice dedup per url + price — migliorabile
        q = select(Offer).where(Offer.product_url == str(payload.url))
        res = await session.execute(q)
        obj = res.scalars().first()
        if obj:
            obj.text = payload.text
            obj.updated_at = None
            session.add(obj)
            await session.commit()
            await session.refresh(obj)
            return obj.__dict__
        else:
            new = Offer(product_url=str(payload.url), text=payload.text, status="verifying")
            session.add(new)
            await session.commit()
            await session.refresh(new)
            return new.__dict__


async def get_offers(status="active", limit=50, offset=0, category=None, search=None):
    async with async_session() as session:
        q = select(Offer).where(Offer.status == status)

        # Filtro Categoria
        if category and category != "Tutte":
            q = q.where(Offer.category == category)

        # Filtro Ricerca (cerca nel titolo o nel testo)
        if search:
            search_term = f"%{search}%"
            q = q.where(or_(Offer.title.ilike(search_term), Offer.text.ilike(search_term)))

        # Ordina per più recenti
        q = q.order_by(Offer.created_at.desc()).limit(limit).offset(offset)

        res = await session.execute(q)
        rows = res.scalars().all()
        return [r.__dict__ for r in rows]