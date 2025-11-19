"""
Domain Layer Package
Cuore del sistema - Zero dipendenze esterne
"""
from .entities import Offer, UserPreference, PriceHistory, OfferStatus, DealQuality
from .value_objects import Price, ProductURL, CategoryScore
from .services import (
    CategoryDetectionService,
    DuplicateDetectionService,
    DealScoringService,
    PriceAlertService
)
from .interfaces import (
    IOfferRepository,
    IUserPreferenceRepository,
    IPriceHistoryRepository,
    ICacheService,
    IScraperService,
    IMLService,
    INotificationService
)

__all__ = [
    # Entities
    "Offer",
    "UserPreference",
    "PriceHistory",
    "OfferStatus",
    "DealQuality",

    # Value Objects
    "Price",
    "ProductURL",
    "CategoryScore",

    # Services
    "CategoryDetectionService",
    "DuplicateDetectionService",
    "DealScoringService",
    "PriceAlertService",

    # Interfaces
    "IOfferRepository",
    "IUserPreferenceRepository",
    "IPriceHistoryRepository",
    "ICacheService",
    "IScraperService",
    "IMLService",
    "INotificationService",
]
