# ENGINE: PlatformEngine
"""
PRISM Redis Service — optional speed layer.

Redis is optional. When REDIS_URL is not configured, all operations
gracefully fall back (rate limits use in-memory, no caching, no locks).

Usage:
    from redis_service import get_redis, redis_get, redis_set, redis_incr
"""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_redis_client = None
_redis_available = False


def get_redis():
    """Get Redis client. Returns None if Redis unavailable."""
    global _redis_client, _redis_available
    if _redis_client is not None:
        return _redis_client
    
    redis_url = os.getenv("REDIS_URL", "")
    if not redis_url:
        return None
    
    try:
        import redis
        _redis_client = redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=2)
        _redis_client.ping()  # Test connection
        _redis_available = True
        logger.info(f"[Redis] Connected to {redis_url[:20]}...")
        return _redis_client
    except ImportError:
        logger.debug("[Redis] redis-py not installed — Redis disabled")
        return None
    except Exception as e:
        logger.warning(f"[Redis] Connection failed: {e}")
        return None


def redis_get(key: str) -> Optional[str]:
    """Get a value from Redis. Returns None if unavailable."""
    r = get_redis()
    if r is None:
        return None
    try:
        return r.get(key)
    except Exception:
        return None


def redis_set(key: str, value: str, ex: int = 3600) -> bool:
    """Set a value in Redis with TTL. Returns False if unavailable."""
    r = get_redis()
    if r is None:
        return False
    try:
        r.set(key, value, ex=ex)
        return True
    except Exception:
        return False


def redis_incr(key: str, ex: int = 60) -> int:
    """Increment a counter in Redis. Returns -1 if unavailable."""
    r = get_redis()
    if r is None:
        return -1
    try:
        pipe = r.pipeline()
        pipe.incr(key)
        pipe.expire(key, ex)
        results = pipe.execute()
        return results[0]
    except Exception:
        return -1


def redis_acquire_lock(key: str, ttl: int = 30) -> bool:
    """Acquire a distributed lock. Returns True if acquired."""
    r = get_redis()
    if r is None:
        return True  # No Redis = no distributed locking needed (single process)
    try:
        return bool(r.set(f"lock:{key}", "1", ex=ttl, nx=True))
    except Exception:
        return True


def redis_release_lock(key: str) -> None:
    """Release a distributed lock."""
    r = get_redis()
    if r is None:
        return
    try:
        r.delete(f"lock:{key}")
    except Exception:
        pass


def get_redis_health() -> dict:
    """Return Redis health status."""
    r = get_redis()
    if r is None:
        redis_url = os.getenv("REDIS_URL", "")
        if not redis_url:
            return {"status": "disabled", "reason": "REDIS_URL not configured"}
        return {"status": "unavailable"}
    try:
        r.ping()
        return {"status": "ok"}
    except Exception as e:
        return {"status": "unavailable", "error": str(e)[:80]}
