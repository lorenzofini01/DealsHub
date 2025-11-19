"""
Dependency Injection Container
Wires tutti i component insieme (Domain, Application, Infrastructure)
"""
from functools import lru_cache
import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from typing import AsyncGenerator

from ..domain import (
    CategoryDetectionService, DuplicateDetectionService,
    DealScoringService, PriceAlertService
)
from ..application import (
    IngestOfferUseCase, SearchOffersUseCase,
    TrackUserEventUseCase, VerifyOffersUseCase
)
from ..infrastructure import (
    SQLAlchemyOfferRepository, SQLAlchemyUserPreferenceRepository,
    SQLAlchemyPriceHistoryRepository, RedisCacheService, HTTPXScraperService,
    create_all_tables
)


# ===== Database Setup =====
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://offer_user:offer_pass@postgres:5432/offersdb")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True, pool_size=20, max_overflow=40)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency per ottenere DB session"""
    async with async_session_factory() as session:
        yield session


@lru_cache()
def get_cache_service() -> RedisCacheService:
    """Singleton Cache Service"""
    return RedisCacheService(REDIS_URL, max_memory_items=2000)


@lru_cache()
def get_scraper_service() -> HTTPXScraperService:
    """Singleton Scraper Service"""
    return HTTPXScraperService()


# ===== Domain Services (stateless, singleton) =====

@lru_cache()
def get_category_service() -> CategoryDetectionService:
    return CategoryDetectionService()


@lru_cache()
def get_duplicate_service() -> DuplicateDetectionService:
    return DuplicateDetectionService()


@lru_cache()
def get_scoring_service() -> DealScoringService:
    return DealScoringService()


@lru_cache()
def get_price_alert_service() -> PriceAlertService:
    return PriceAlertService()


# ===== Use Cases (factory per dependency injection) =====

async def get_ingest_offer_use_case(session: AsyncSession) -> IngestOfferUseCase:
    """Factory per IngestOfferUseCase"""
    offer_repo = SQLAlchemyOfferRepository(session)
    cache = get_cache_service()
    duplicate_svc = get_duplicate_service()
    category_svc = get_category_service()
    scoring_svc = get_scoring_service()

    return IngestOfferUseCase(offer_repo, cache, duplicate_svc, category_svc, scoring_svc)


async def get_search_offers_use_case(session: AsyncSession) -> SearchOffersUseCase:
    """Factory per SearchOffersUseCase"""
    offer_repo = SQLAlchemyOfferRepository(session)
    cache = get_cache_service()

    return SearchOffersUseCase(offer_repo, cache)


async def get_track_event_use_case(session: AsyncSession) -> TrackUserEventUseCase:
    """Factory per TrackUserEventUseCase"""
    offer_repo = SQLAlchemyOfferRepository(session)
    user_pref_repo = SQLAlchemyUserPreferenceRepository(session)

    return TrackUserEventUseCase(offer_repo, user_pref_repo)


async def get_verify_offers_use_case(session: AsyncSession) -> VerifyOffersUseCase:
    """Factory per VerifyOffersUseCase"""
    offer_repo = SQLAlchemyOfferRepository(session)
    price_history_repo = SQLAlchemyPriceHistoryRepository(session)
    cache = get_cache_service()
    scraper = get_scraper_service()
    scoring_svc = get_scoring_service()
    category_svc = get_category_service()
    duplicate_svc = get_duplicate_service()

    return VerifyOffersUseCase(
        offer_repo, price_history_repo, cache, scraper,
        scoring_svc, category_svc, duplicate_svc
    )


# ===== Startup/Shutdown =====

async def startup_event():
    """Eseguito all'avvio dell'app"""
    # Crea tabelle se non esistono
    await create_all_tables(engine)


async def shutdown_event():
    """Eseguito allo shutdown dell'app"""
    await engine.dispose()
