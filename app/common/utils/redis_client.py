from functools import lru_cache

import redis
from django.conf import settings

_pool: redis.ConnectionPool | None = None


@lru_cache(maxsize=1)
def get_redis_client() -> redis.Redis:
    """
    Return a Redis client backed by a module-level connection pool.

    The pool is created once on the first call (lazy initialisation) so that
    Django settings are fully loaded before we read REDIS_* values.
    """
    global _pool

    if _pool is None:
        _pool = redis.ConnectionPool(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True,
            max_connections=20,
        )

    return redis.Redis(connection_pool=_pool)
