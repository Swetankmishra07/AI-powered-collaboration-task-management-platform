import json
import logging
from typing import Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisCache:
    """Best-effort Redis cache; failures never replace the database source of truth."""

    def __init__(self, url: Optional[str] = None, ttl_seconds: Optional[int] = None):
        self.url = url if url is not None else settings.REDIS_URL
        self.ttl_seconds = ttl_seconds if ttl_seconds is not None else settings.REDIS_CACHE_TTL_SECONDS
        self._client = None

    def _get_client(self):
        if not self.url:
            return None
        if self._client is None:
            try:
                import redis

                self._client = redis.Redis.from_url(self.url, decode_responses=True)
            except Exception:
                logger.exception("Redis client initialization failed")
                self._client = None
        return self._client

    def get_json(self, key: str) -> Optional[Any]:
        client = self._get_client()
        if client is None:
            return None
        try:
            value = client.get(key)
            return json.loads(value) if value is not None else None
        except Exception:
            logger.warning("Redis read failed; bypassing cache", exc_info=True)
            return None

    def set_json(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        client = self._get_client()
        if client is None:
            return False
        try:
            client.setex(key, ttl_seconds or self.ttl_seconds, json.dumps(value))
            return True
        except Exception:
            logger.warning("Redis write failed; continuing without cache", exc_info=True)
            return False

    def delete(self, *keys: str) -> bool:
        client = self._get_client()
        if client is None or not keys:
            return False
        try:
            client.delete(*keys)
            return True
        except Exception:
            logger.warning("Redis invalidation failed; continuing without cache", exc_info=True)
            return False

    def ping(self) -> bool:
        client = self._get_client()
        if client is None:
            return False
        try:
            return bool(client.ping())
        except Exception:
            return False


redis_cache = RedisCache()
