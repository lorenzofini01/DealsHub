"""
Use Case: Ingest Offer
Workflow completo per ingestione di una nuova offerta dal collector
"""
from typing import Optional
from ...domain import (
    Offer, OfferStatus, IOfferRepository, ICacheService,
    DuplicateDetectionService, CategoryDetectionService, DealScoringService
)
from ..dtos import IngestOfferDTO, OfferDTO
import logging

logger = logging.getLogger(__name__)


class IngestOfferUseCase:
    """
    Use Case per ingestione offerta.
    Workflow:
    1. Controlla duplicati
    2. Crea/aggiorna offerta
    3. Invalida cache
    4. Trigghera scraping asincrono
    """

    def __init__(
        self,
        offer_repo: IOfferRepository,
        cache: ICacheService,
        duplicate_service: DuplicateDetectionService,
        category_service: CategoryDetectionService,
        scoring_service: DealScoringService
    ):
        self.offer_repo = offer_repo
        self.cache = cache
        self.duplicate_service = duplicate_service
        self.category_service = category_service
        self.scoring_service = scoring_service

    async def execute(self, dto: IngestOfferDTO) -> OfferDTO:
        """Esegue il workflow completo"""
        url = str(dto.url)

        # 1. Check duplicati
        existing = await self._find_duplicate(url)
        if existing:
            logger.info(f"Offerta duplicata trovata: {existing.id}, aggiorno timestamp")
            return await self._update_existing(existing, dto)

        # 2. Crea nuova offerta
        logger.info(f"Nuova offerta: {url[:50]}...")
        return await self._create_new(dto)

    async def _find_duplicate(self, url: str) -> Optional[Offer]:
        """Cerca duplicati intelligenti"""
        # Prima prova exact URL match
        offer = await self.offer_repo.get_by_url(url)
        if offer:
            return offer

        # Poi prova ASIN per Amazon
        asin = self.duplicate_service.extract_asin(url)
        if asin:
            offer = await self.offer_repo.get_by_asin(asin)
            if offer:
                return offer

        return None

    async def _update_existing(self, offer: Offer, dto: IngestOfferDTO) -> OfferDTO:
        """Aggiorna offerta esistente (refresh timestamp)"""
        offer.text = dto.text  # Potrebbe essere cambiato il messaggio

        # Se era expired, riportala a verifying
        if offer.status == OfferStatus.EXPIRED:
            offer.status = OfferStatus.VERIFYING
            logger.info(f"Offerta {offer.id} riattivata")

        updated = await self.offer_repo.update(offer)

        # Invalida cache
        await self._invalidate_cache()

        return self._to_dto(updated)

    async def _create_new(self, dto: IngestOfferDTO) -> OfferDTO:
        """Crea nuova offerta"""
        # Estrai ASIN se Amazon
        asin = self.duplicate_service.extract_asin(str(dto.url))

        # Rileva categoria preliminare (poi verrà affinata dallo scraper)
        category_score = self.category_service.detect(dto.text)

        # Crea entità
        offer = Offer(
            product_url=str(dto.url),
            text=dto.text,
            category=category_score.category_name if category_score.is_confident() else None,
            status=OfferStatus.VERIFYING,
            asin=asin
        )

        # Salva
        created = await self.offer_repo.create(offer)

        # Invalida cache
        await self._invalidate_cache()

        logger.info(f"Offerta creata: ID {created.id}")
        return self._to_dto(created)

    async def _invalidate_cache(self) -> None:
        """Invalida cache delle liste offerte"""
        await self.cache.clear_pattern("offers:*")

    def _to_dto(self, offer: Offer) -> OfferDTO:
        """Converte Entity -> DTO"""
        return OfferDTO(
            id=offer.id,
            title=offer.title,
            product_url=offer.product_url,
            image_url=offer.image_url,
            price=offer.price,
            original_price=offer.original_price,
            discount_percentage=offer.discount_percentage,
            currency=offer.currency,
            shop=offer.shop,
            category=offer.category,
            status=offer.status.value,
            deal_score=offer.deal_score,
            deal_quality=offer.get_quality().value,
            view_count=offer.view_count,
            click_count=offer.click_count,
            ctr=offer.get_ctr(),
            is_hot=offer.is_hot_deal(),
            created_at=offer.created_at,
            updated_at=offer.updated_at
        )
