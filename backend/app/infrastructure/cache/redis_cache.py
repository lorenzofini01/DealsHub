"""
Infrastructure - Redis Cache Service con fallback in-memory
"""
from typing import Optional
import json
import redis.asyncio as aioredis
from ...domain import ICacheService
import logging

logger = logging.getLogger(__name__)


class RedisCacheService(ICacheService):
    """
    Cache multi-livello:
    1. In-memory LRU (L1) - ultrafast
    2. Redis (L2) - shared across instances
    """

    def __init__(self, redis_url: str, max_memory_items: int = 1000):
        self.redis = aioredis.from_url(redis_url, decode_responses=True)
        # L1 Cache (in-memory LRU)
        from cachetools import LRUCache
        self._memory_cache = LRUCache(maxsize=max_memory_items)

    async def get(self, key: str) -> Optional[any]:
        """Get con fallback L1 -> L2"""
        # 1. Check L1 (in-memory)
        if key in self._memory_cache:
            logger.debug(f"L1 Cache HIT: {key}")
            return self._memory_cache[key]

        # 2. Check L2 (Redis)
        try:
            value = await self.redis.get(key)
            if value:
                logger.debug(f"L2 Cache HIT: {key}")
                # Popola L1 per prossime richieste
                self._memory_cache[key] = value
                return value
        except Exception as e:
            logger.error(f"Redis GET error: {e}")

        return None

    async def set(self, key: str, value: any, ttl: int = 300) -> None:
        """Set su entrambi i livelli"""
        # 1. Set L1 (in-memory)
        self._memory_cache[key] = value

        # 2. Set L2 (Redis)
        try:
            await self.redis.setex(key, ttl, value)
        except Exception as e:
            logger.error(f"Redis SET error: {e}")

    async def delete(self, key: str) -> None:
        """Delete da entrambi i livelli"""
        # 1. Delete L1
        self._memory_cache.pop(key, None)

        # 2. Delete L2
        try:
            await self.redis.delete(key)
        except Exception as e:
            logger.error(f"Redis DELETE error: {e}")

    async def clear_pattern(self, pattern: str) -> None:
        """Cancella tutte le chiavi che matchano il pattern"""
        # 1. Clear L1 (brutally clear all for simplicity)
        self._memory_cache.clear()

        # 2. Clear L2 (Redis SCAN + DELETE)
        try:
            cursor = 0
            while True:
                cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)
                if keys:
                    await self.redis.delete(*keys)
                if cursor == 0:
                    break
        except Exception as e:
            logger.error(f"Redis CLEAR_PATTERN error: {e}")
