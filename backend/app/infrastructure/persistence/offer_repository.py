"""
Infrastructure - Offer Repository Implementation
"""
from typing import List, Optional
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from ...domain import Offer, OfferStatus, IOfferRepository
from .sqlalchemy_models import OfferModel
from decimal import Decimal


class SQLAlchemyOfferRepository(IOfferRepository):
    """
    Implementazione concreta del repository usando SQLAlchemy.
    Responsabile solo di persistenza, zero business logic.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, offer: Offer) -> Offer:
        """Crea nuova offerta"""
        model = self._to_model(offer)
        self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        return self._to_entity(model)

    async def update(self, offer: Offer) -> Offer:
        """Aggiorna offerta esistente"""
        model = await self.session.get(OfferModel, offer.id)
        if not model:
            raise ValueError(f"Offer {offer.id} not found")

        # Aggiorna tutti i campi
        model.product_url = offer.product_url
        model.title = offer.title
        model.text = offer.text
        model.image_url = offer.image_url
        model.price = offer.price
        model.original_price = offer.original_price
        model.discount_percentage = offer.discount_percentage
        model.currency = offer.currency
        model.shop = offer.shop
        model.category = offer.category
        model.status = offer.status.value
        model.deal_score = offer.deal_score
        model.view_count = offer.view_count
        model.click_count = offer.click_count
        model.save_count = offer.save_count
        model.asin = offer.asin
        model.verified_at = offer.verified_at

        await self.session.commit()
        await self.session.refresh(model)
        return self._to_entity(model)

    async def get_by_id(self, offer_id: int) -> Optional[Offer]:
        """Recupera per ID"""
        model = await self.session.get(OfferModel, offer_id)
        return self._to_entity(model) if model else None

    async def get_by_url(self, url: str) -> Optional[Offer]:
        """Recupera per URL"""
        stmt = select(OfferModel).where(OfferModel.product_url == url)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_asin(self, asin: str) -> Optional[Offer]:
        """Recupera per ASIN"""
        stmt = select(OfferModel).where(OfferModel.asin == asin)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def find_active(
        self,
        limit: int = 50,
        offset: int = 0,
        category: Optional[str] = None,
        search: Optional[str] = None,
        min_score: Optional[int] = None
    ) -> List[Offer]:
        """
        Trova offerte attive con filtri.
        Query ottimizzata con indici composti.
        """
        stmt = select(OfferModel).where(OfferModel.status == "active")

        # Filtro categoria
        if category and category != "Tutte":
            stmt = stmt.where(OfferModel.category == category)

        # Filtro ricerca (full-text search simulato)
        if search:
            search_term = f"%{search}%"
            stmt = stmt.where(
                or_(
                    OfferModel.title.ilike(search_term),
                    OfferModel.text.ilike(search_term)
                )
            )

        # Filtro score minimo
        if min_score is not None:
            stmt = stmt.where(OfferModel.deal_score >= min_score)

        # Ordina per deal_score DESC poi created_at DESC
        # Usa l'indice idx_status_score
        stmt = stmt.order_by(
            OfferModel.deal_score.desc(),
            OfferModel.created_at.desc()
        ).limit(limit).offset(offset)

        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def find_needs_verification(self, limit: int) -> List[Offer]:
        """
        Trova offerte che necessitano verifica.
        Priorità: senza titolo > senza immagine > più vecchie
        """
        stmt = select(OfferModel).where(
            OfferModel.status != "expired"
        ).order_by(
            OfferModel.title.is_(None).desc(),
            OfferModel.image_url.is_(None).desc(),
            OfferModel.updated_at.asc()
        ).limit(limit)

        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [self._to_entity(m) for m in models]

    async def delete(self, offer_id: int) -> bool:
        """Elimina offerta"""
        model = await self.session.get(OfferModel, offer_id)
        if not model:
            return False

        await self.session.delete(model)
        await self.session.commit()
        return True

    # ===== Mapper Methods =====

    def _to_entity(self, model: OfferModel) -> Offer:
        """Converte ORM Model -> Domain Entity"""
        return Offer(
            id=model.id,
            product_url=model.product_url,
            title=model.title,
            text=model.text,
            image_url=model.image_url,
            price=model.price,
            original_price=model.original_price,
            discount_percentage=model.discount_percentage,
            currency=model.currency,
            shop=model.shop,
            category=model.category,
            status=OfferStatus(model.status),
            deal_score=model.deal_score,
            view_count=model.view_count,
            click_count=model.click_count,
            save_count=model.save_count,
            asin=model.asin,
            created_at=model.created_at,
            updated_at=model.updated_at,
            verified_at=model.verified_at
        )

    def _to_model(self, entity: Offer) -> OfferModel:
        """Converte Domain Entity -> ORM Model"""
        return OfferModel(
            id=entity.id,
            product_url=entity.product_url,
            title=entity.title,
            text=entity.text,
            image_url=entity.image_url,
            price=entity.price,
            original_price=entity.original_price,
            discount_percentage=entity.discount_percentage,
            currency=entity.currency,
            shop=entity.shop,
            category=entity.category,
            status=entity.status.value,
            deal_score=entity.deal_score,
            view_count=entity.view_count,
            click_count=entity.click_count,
            save_count=entity.save_count,
            asin=entity.asin,
            verified_at=entity.verified_at
        )
