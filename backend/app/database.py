# backend/app/database.py
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool

DATABASE_URL = "postgresql+asyncpg://offer_user:offer_pass@postgres:5432/offersdb"

engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    poolclass=NullPool
)

async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

metadata = declarative_base().metadata


async def connect():
    pass

async def disconnect():
    await engine.dispose()
