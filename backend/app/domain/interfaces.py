"""
Domain Layer - Interfaces (Ports)
Definiscono i contratti per l'infrastructure layer.
Dependency Inversion: il dominio NON dipende dall'infra, ma viceversa.
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from .entities import Offer, UserPreference, PriceHistory
from decimal import Decimal


class IOfferRepository(ABC):
    """Repository interface per Offer"""

    @abstractmethod
    async def create(self, offer: Offer) -> Offer:
        """Crea nuova offerta"""
        pass

    @abstractmethod
    async def update(self, offer: Offer) -> Offer:
        """Aggiorna offerta esistente"""
        pass

    @abstractmethod
    async def get_by_id(self, offer_id: int) -> Optional[Offer]:
        """Recupera per ID"""
        pass

    @abstractmethod
    async def get_by_url(self, url: str) -> Optional[Offer]:
        """Recupera per URL (dedup)"""
        pass

    @abstractmethod
    async def get_by_asin(self, asin: str) -> Optional[Offer]:
        """Recupera per ASIN Amazon"""
        pass

    @abstractmethod
    async def find_active(
        self,
        limit: int = 50,
        offset: int = 0,
        category: Optional[str] = None,
        search: Optional[str] = None,
        min_score: Optional[int] = None
    ) -> List[Offer]:
        """Trova offerte attive con filtri"""
        pass

    @abstractmethod
    async def find_needs_verification(self, limit: int) -> List[Offer]:
        """Trova offerte che necessitano verifica"""
        pass

    @abstractmethod
    async def delete(self, offer_id: int) -> bool:
        """Elimina offerta"""
        pass


class IUserPreferenceRepository(ABC):
    """Repository per preferenze utente"""

    @abstractmethod
    async def get_by_user_id(self, user_id: str) -> Optional[UserPreference]:
        pass

    @abstractmethod
    async def save(self, preference: UserPreference) -> UserPreference:
        pass


class IPriceHistoryRepository(ABC):
    """Repository per storico prezzi"""

    @abstractmethod
    async def add_entry(self, history: PriceHistory) -> PriceHistory:
        pass

    @abstractmethod
    async def get_average_price(self, asin: str, days: int = 30) -> Optional[Decimal]:
        """Ritorna il prezzo medio negli ultimi N giorni"""
        pass

    @abstractmethod
    async def get_lowest_price(self, asin: str, days: int = 30) -> Optional[Decimal]:
        """Ritorna il prezzo minimo storico"""
        pass


class ICacheService(ABC):
    """Cache service interface"""

    @abstractmethod
    async def get(self, key: str) -> Optional[any]:
        pass

    @abstractmethod
    async def set(self, key: str, value: any, ttl: int = 300) -> None:
        pass

    @abstractmethod
    async def delete(self, key: str) -> None:
        pass

    @abstractmethod
    async def clear_pattern(self, pattern: str) -> None:
        """Cancella tutte le chiavi che matchano il pattern"""
        pass


class IScraperService(ABC):
    """Scraper service interface"""

    @abstractmethod
    async def scrape_product(self, url: str) -> dict:
        """
        Scrape metadata da URL.
        Returns: {
            'title': str,
            'price': Decimal,
            'original_price': Decimal,
            'image_url': str,
            'is_available': bool
        }
        """
        pass


class IMLService(ABC):
    """Machine Learning service interface"""

    @abstractmethod
    async def predict_category(self, text: str, title: str) -> tuple[str, float]:
        """Predice categoria con confidence score"""
        pass

    @abstractmethod
    async def calculate_sentiment(self, text: str) -> float:
        """Calcola sentiment 0-1 di un testo"""
        pass

    @abstractmethod
    async def recommend_offers(self, user_id: str, limit: int = 10) -> List[int]:
        """Ritorna IDs delle offerte raccomandate per l'utente"""
        pass


class INotificationService(ABC):
    """Notification service interface"""

    @abstractmethod
    async def send_price_alert(self, user_id: str, offer: Offer) -> None:
        """Invia notifica price alert"""
        pass

    @abstractmethod
    async def send_new_deal_alert(self, user_id: str, offer: Offer) -> None:
        """Invia notifica nuovo deal hot"""
        pass
