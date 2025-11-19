"""
Use Case: Track User Event
Workflow per tracking eventi utente (view, click, save)
"""
from ...domain import Offer, IOfferRepository, IUserPreferenceRepository
from ..dtos import TrackEventDTO
import logging

logger = logging.getLogger(__name__)


class TrackUserEventUseCase:
    """
    Use Case per tracking eventi utente.
    Fondamentale per recommendation engine e analytics.
    """

    def __init__(
        self,
        offer_repo: IOfferRepository,
        user_pref_repo: IUserPreferenceRepository
    ):
        self.offer_repo = offer_repo
        self.user_pref_repo = user_pref_repo

    async def execute(self, dto: TrackEventDTO) -> dict:
        """Processa evento utente"""

        # 1. Recupera offerta
        offer = await self.offer_repo.get_by_id(dto.offer_id)
        if not offer:
            logger.warning(f"Offerta {dto.offer_id} non trovata per tracking")
            return {"success": False, "error": "Offer not found"}

        # 2. Aggiorna metriche offerta
        if dto.event_type == "view":
            offer.increment_view()
        elif dto.event_type == "click":
            offer.increment_click()
        elif dto.event_type == "save":
            offer.save_count += 1
        elif dto.event_type == "unsave":
            offer.save_count = max(0, offer.save_count - 1)

        await self.offer_repo.update(offer)

        # 3. Aggiorna preferenze utente (per recommendation)
        await self._update_user_preferences(dto.user_id, offer, dto.event_type)

        logger.info(f"Event tracked: {dto.event_type} by {dto.user_id} on offer {dto.offer_id}")

        return {
            "success": True,
            "offer_id": offer.id,
            "new_view_count": offer.view_count,
            "new_ctr": offer.get_ctr()
        }

    async def _update_user_preferences(self, user_id: str, offer: Offer, event_type: str) -> None:
        """Aggiorna preferenze utente basate su eventi"""
        pref = await self.user_pref_repo.get_by_user_id(user_id)
        if not pref:
            from ...domain import UserPreference
            pref = UserPreference(user_id=user_id)

        # Se l'utente clicca/salva, aggiungi categoria alle preferite
        if event_type in ["click", "save"] and offer.category:
            if offer.category not in pref.preferred_categories:
                pref.preferred_categories.append(offer.category)
                # Mantieni solo top 10 categorie
                pref.preferred_categories = pref.preferred_categories[-10:]

        # Se l'utente salva, aggiungi a saved_offers
        if event_type == "save" and offer.id not in pref.saved_offer_ids:
            pref.saved_offer_ids.append(offer.id)
        elif event_type == "unsave" and offer.id in pref.saved_offer_ids:
            pref.saved_offer_ids.remove(offer.id)

        await self.user_pref_repo.save(pref)
