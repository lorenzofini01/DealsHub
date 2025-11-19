"""
Celery Tasks v2 - Usa i nuovi Use Cases
"""
from .celery_app import celery
import asyncio
import logging

logger = logging.getLogger(__name__)


@celery.task(name="app.tasks.verify_offers_task_v2")
def verify_offers_task_v2():
    """
    Task Celery per verificare batch di offerte.
    Usa il nuovo VerifyOffersUseCase.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(_verify_offers())
        logger.info(f"Verification complete: {result}")
        return result
    finally:
        loop.close()


async def _verify_offers():
    """Worker asincrono che usa il Use Case"""
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    import os

    # Setup DB connection
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://offer_user:offer_pass@postgres:5432/offersdb")
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with async_session_factory() as session:
        # Import use case
        from .api_v2.dependencies import get_verify_offers_use_case

        # Execute
        use_case = await get_verify_offers_use_case(session)
        result = await use_case.execute(batch_size=40)

        return result
