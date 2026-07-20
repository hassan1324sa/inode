import asyncio
from typing import Any, Optional
import time

class MemoryCache:
    def __init__(self):
        self._cache = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            if key in self._cache:
                value, expires_at = self._cache[key]
                if expires_at is None or time.time() < expires_at:
                    return value
                else:
                    # Expired
                    del self._cache[key]
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        async with self._lock:
            expires_at = time.time() + ttl if ttl is not None else None
            self._cache[key] = (value, expires_at)

    async def delete(self, key: str):
        async with self._lock:
            if key in self._cache:
                del self._cache[key]

    async def clear(self):
        async with self._lock:
            self._cache.clear()
