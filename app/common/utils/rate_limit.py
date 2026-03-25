from time import time


class RateLimit:
    @staticmethod
    def _calculate(key: str, expire_after: int) -> int:
        from .redis_client import get_redis_client

        r = get_redis_client()
        window = int(time())  # current Unix second
        key = f"{key}:{window}"

        pipe = r.pipeline()
        pipe.incr(key)
        pipe.expire(
            key, expire_after
        )  # keep for n seconds so the key outlives the window
        results = pipe.execute()

        current_count: int = results[0]
        return current_count

    @classmethod
    def has_rate_limit(cls, key: str, rate_limit: int, expire_after: int = 2) -> bool:
        """Check if the request identified by `key` is within the `rate_limit` (req/s).

        The counter key expires after 2 seconds so Redis never accumulates
        stale keys.

        Returns:
            True  – the request is within the token's rate_limit (req/s).
            False – the rate limit has been exceeded for the current second.
        """
        limit_count = cls._calculate(key, expire_after)
        return limit_count <= rate_limit
