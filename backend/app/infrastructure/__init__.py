"""
Infrastructure Layer Package
Implementazioni concrete di tutti i servizi
"""
from .persistence import (
    SQLAlchemyOfferRepository,
    SQLAlchemyUserPreferenceRepository,
    SQLAlchemyPriceHistoryRepository,
    create_all_tables
)
from .cache.redis_cache import RedisCacheService
from .scraping.scraper_service import HTTPXScraperService

__all__ = [
    "SQLAlchemyOfferRepository",
    "SQLAlchemyUserPreferenceRepository",
    "SQLAlchemyPriceHistoryRepository",
    "create_all_tables",
    "RedisCacheService",
    "HTTPXScraperService",
]
