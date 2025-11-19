"""
Use Case: Search Offers
Workflow per ricerca offerte con caching intelligente
"""
from typing import List
from ...domain import Offer, IOfferRepository, ICacheService
from ..dtos import SearchOffersDTO, OfferDTO, OfferListDTO
import json
import logging

logger = logging.getLogger(__name__)


class SearchOffersUseCase:
    """
    Use Case per ricerca offerte.
    Workflow:
    1. Controlla cache
    2. Se miss, query DB
    3. Salva in cache
    4. Ritorna lista
    """

    def __init__(self, offer_repo: IOfferRepository, cache: ICacheService):
        self.offer_repo = offer_repo
        self.cache = cache

    async def execute(self, dto: SearchOffersDTO) -> OfferListDTO:
        """Esegue ricerca con caching multi-livello"""

        # 1. Genera cache key
        cache_key = self._generate_cache_key(dto)

        # 2. Controlla cache
        cached = await self.cache.get(cache_key)
        if cached:
            logger.debug(f"Cache HIT: {cache_key}")
            return OfferListDTO(**json.loads(cached))

        logger.debug(f"Cache MISS: {cache_key}")

        # 3. Query DB
        offers = await self.offer_repo.find_active(
            limit=dto.limit,
            offset=dto.offset,
            category=dto.category,
            search=dto.search,
            min_score=dto.min_score
        )

        # 4. Converti a DTO
        offer_dtos = [self._to_dto(o) for o in offers]

        result = OfferListDTO(
            total=len(offer_dtos),  # TODO: implement proper count query
            limit=dto.limit,
            offset=dto.offset,
            offers=offer_dtos
        )

        # 5. Salva in cache (TTL 5 minuti)
        await self.cache.set(cache_key, result.model_dump_json(), ttl=300)

        return result

    def _generate_cache_key(self, dto: SearchOffersDTO) -> str:
        """Genera chiave cache univoca per questa query"""
        parts = [
            f"offers:search",
            f"limit:{dto.limit}",
            f"offset:{dto.offset}",
            f"cat:{dto.category or 'all'}",
            f"q:{dto.search or 'none'}",
            f"score:{dto.min_score or '0'}",
            f"sort:{dto.sort_by}:{dto.sort_order}"
        ]
        return ":".join(parts)

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
