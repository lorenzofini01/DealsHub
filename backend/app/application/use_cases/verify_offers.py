"""
Use Case: Verify Offers
Workflow per verifica offerte (scraping + scoring)
"""
from typing import List
from ...domain import (
    Offer, OfferStatus, IOfferRepository, ICacheService, IScraperService,
    DealScoringService, CategoryDetectionService, DuplicateDetectionService,
    IPriceHistoryRepository, PriceHistory
)
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class VerifyOffersUseCase:
    """
    Use Case per verifica batch di offerte.
    Eseguito periodicamente da Celery Beat.
    """

    def __init__(
        self,
        offer_repo: IOfferRepository,
        price_history_repo: IPriceHistoryRepository,
        cache: ICacheService,
        scraper: IScraperService,
        scoring_service: DealScoringService,
        category_service: CategoryDetectionService,
        duplicate_service: DuplicateDetectionService
    ):
        self.offer_repo = offer_repo
        self.price_history_repo = price_history_repo
        self.cache = cache
        self.scraper = scraper
        self.scoring_service = scoring_service
        self.category_service = category_service
        self.duplicate_service = duplicate_service

    async def execute(self, batch_size: int = 40) -> dict:
        """
        Verifica batch di offerte.
        Priorità: senza titolo > senza immagine > più vecchie
        """
        logger.info(f"Starting verification batch (size: {batch_size})")

        # 1. Recupera offerte da verificare
        offers = await self.offer_repo.find_needs_verification(limit=batch_size)
        if not offers:
            logger.info("No offers to verify")
            return {"verified": 0, "expired": 0, "active": 0}

        stats = {"verified": 0, "expired": 0, "active": 0, "merged": 0}

        # 2. Processa ogni offerta
        for offer in offers:
            try:
                result = await self._verify_single_offer(offer)
                stats[result] += 1
            except Exception as e:
                logger.error(f"Error verifying offer {offer.id}: {e}")

        # 3. Invalida cache
        await self.cache.clear_pattern("offers:*")

        logger.info(f"Verification complete: {stats}")
        return stats

    async def _verify_single_offer(self, offer: Offer) -> str:
        """Verifica singola offerta"""
        logger.debug(f"Verifying offer {offer.id}: {offer.product_url[:50]}...")

        # 1. Scrape metadata
        metadata = await self.scraper.scrape_product(offer.product_url)

        # 2. Controlla se prodotto disponibile
        if not metadata.get("is_available"):
            logger.info(f"Offer {offer.id} expired (not available)")
            offer.mark_as_expired()
            await self.offer_repo.update(offer)
            return "expired"

        # 3. Controlla duplicati (merge se necessario)
        if await self._check_and_merge_duplicates(offer, metadata):
            return "merged"

        # 4. Aggiorna metadata
        if metadata.get("title"):
            offer.title = metadata["title"]
        elif not offer.title:
            # Fallback: estrai da testo Telegram
            offer.title = self._extract_title_from_text(offer.text, offer.product_url)

        if metadata.get("image_url"):
            offer.image_url = metadata["image_url"]

        if metadata.get("price"):
            new_price = Decimal(str(metadata["price"]))

            # Salva storico prezzi
            if offer.asin:
                await self._save_price_history(offer.asin, new_price)

            offer.price = new_price

        if metadata.get("original_price"):
            offer.original_price = Decimal(str(metadata["original_price"]))

        # Ricalcola discount
        if offer.price and offer.original_price:
            offer.discount_percentage = offer._calculate_discount()

        # 5. Rileva categoria (con ML se disponibile)
        category_score = self.category_service.detect(
            offer.text or "",
            offer.title
        )
        if category_score.is_confident():
            offer.category = category_score.category_name

        # 6. Calcola Deal Score
        avg_price = None
        if offer.asin:
            avg_price = await self.price_history_repo.get_average_price(offer.asin, days=30)

        offer.deal_score = self.scoring_service.calculate_base_score(offer)

        # 7. Marca come attiva
        offer.mark_as_verified()

        # 8. Salva
        await self.offer_repo.update(offer)

        logger.info(f"Offer {offer.id} verified: score={offer.deal_score}, cat={offer.category}")
        return "active"

    async def _check_and_merge_duplicates(self, offer: Offer, metadata: dict) -> bool:
        """Controlla duplicati e fa merge se necessario"""
        if not offer.asin:
            return False

        # Cerca altre offerte con stesso ASIN
        duplicate = await self.offer_repo.get_by_asin(offer.asin)
        if duplicate and duplicate.id != offer.id:
            logger.info(f"Merging duplicate: {offer.id} -> {duplicate.id}")

            # Aggiorna il duplicato esistente e cancella questa
            duplicate.view_count += offer.view_count
            duplicate.click_count += offer.click_count
            duplicate.save_count += offer.save_count

            if offer.status == OfferStatus.ACTIVE:
                duplicate.status = OfferStatus.ACTIVE

            await self.offer_repo.update(duplicate)
            await self.offer_repo.delete(offer.id)

            return True

        return False

    async def _save_price_history(self, asin: str, price: Decimal) -> None:
        """Salva prezzo nello storico"""
        history = PriceHistory(asin=asin, price=price)
        await self.price_history_repo.add_entry(history)

    def _extract_title_from_text(self, text: str, url: str) -> str:
        """Estrae titolo dal testo Telegram se scraping fallisce"""
        if not text:
            return "Offerta del Giorno"

        lines = [l.strip() for l in text.split('\n') if l.strip()]
        if not lines:
            return "Offerta"

        # Cerca la linea prima dell'URL
        for i, line in enumerate(lines):
            if url in line and i > 0:
                return lines[i - 1][:100]

        return lines[0][:100]
