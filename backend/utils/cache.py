import os
import time
import json
import functools
from datetime import datetime
from typing import Any, Optional, Callable
from flask import request, make_response, jsonify, current_app

try:
    import redis
    REDIS_INSTALLED = True
except ImportError:
    REDIS_INSTALLED = False

try:
    from backend.config import Config
except ImportError:
    from config import Config


class CacheService:
    """
    High-performance Redis Caching Service with dynamic key formatting,
    TTL expiration, targeted invalidation, and seamless in-memory fallback.
    """

    def __init__(self, redis_url: Optional[str] = None, default_timeout: int = 300):
        self.redis_url = redis_url or getattr(Config, "CACHE_REDIS_URL", "redis://localhost:6379/2")
        self.default_timeout = default_timeout
        self._redis_client: Optional[Any] = None
        self._redis_tested = False
        self._redis_available = False
        self._memory_cache: dict[str, tuple[str, float]] = {}

    def _get_redis(self):
        """Lazy-initialize Redis client with failover tolerance."""
        if not REDIS_INSTALLED:
            self._redis_available = False
            return None

        if self._redis_client is None:
            try:
                self._redis_client = redis.Redis.from_url(
                    self.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=1.0,
                    socket_timeout=1.0,
                )
            except Exception as e:
                self._redis_available = False
                return None

        return self._redis_client

    def ping(self) -> bool:
        """Check if Redis connection is live."""
        client = self._get_redis()
        if client is None:
            return False
        try:
            return bool(client.ping())
        except Exception:
            return False

    def get(self, key: str) -> Optional[Any]:
        """Retrieve and deserialize a cached object by key."""
        client = self._get_redis()
        if client:
            try:
                raw = client.get(key)
                if raw is not None:
                    return json.loads(raw)
                return None
            except Exception:
                # Fall back to in-memory store if Redis drops connection
                pass

        # In-memory fallback
        now = time.time()
        if key in self._memory_cache:
            raw_val, expiry = self._memory_cache[key]
            if now < expiry:
                return json.loads(raw_val)
            else:
                del self._memory_cache[key]
        return None

    def set(self, key: str, value: Any, timeout: Optional[int] = None) -> bool:
        """Serialize and store an object in cache with a TTL (seconds)."""
        ttl = timeout if timeout is not None else self.default_timeout
        serialized = json.dumps(value, default=str)

        stored_in_redis = False
        client = self._get_redis()
        if client:
            try:
                client.set(key, serialized, ex=ttl)
                stored_in_redis = True
            except Exception:
                pass

        # Always maintain in memory store as fallback
        self._memory_cache[key] = (serialized, time.time() + ttl)
        return stored_in_redis or True

    def delete(self, key: str) -> bool:
        """Purge a specific cache key."""
        client = self._get_redis()
        deleted_from_redis = False
        if client:
            try:
                client.delete(key)
                deleted_from_redis = True
            except Exception:
                pass

        if key in self._memory_cache:
            del self._memory_cache[key]

        return deleted_from_redis or True

    def delete_pattern(self, pattern: str) -> int:
        """Purge all keys matching a wildcard pattern (e.g. 'rubrics_exam_*')."""
        count = 0
        client = self._get_redis()
        if client:
            try:
                keys = list(client.scan_iter(match=pattern))
                if keys:
                    count = client.delete(*keys)
            except Exception:
                pass

        # Also purge from memory cache
        import fnmatch
        keys_to_delete = [k for k in self._memory_cache if fnmatch.fnmatch(k, pattern)]
        for k in keys_to_delete:
            del self._memory_cache[k]
            count += 1

        return count

    def clear(self) -> bool:
        """Flush the active cache."""
        client = self._get_redis()
        if client:
            try:
                client.flushdb()
            except Exception:
                pass
        self._memory_cache.clear()
        return True

    def cached(self, key_template: str, timeout: int = 300):
        """
        Decorator for caching endpoint responses.
        Sets X-Cache: HIT or X-Cache: MISS and measures latency in X-Response-Time.
        Supports dynamic interpolation like 'rubrics_exam_{exam_id}'.
        """
        def decorator(fn):
            @functools.wraps(fn)
            def wrapper(*args, **kwargs):
                # Dynamically resolve cache key using kwargs and request args
                eval_kwargs = dict(kwargs)
                for k, v in request.view_args.items() if request and request.view_args else {}:
                    eval_kwargs[k] = v

                try:
                    cache_key = key_template.format(**eval_kwargs)
                except KeyError:
                    cache_key = key_template

                start_time = time.perf_counter()

                # Attempt Cache Lookup
                cached_data = self.get(cache_key)
                if cached_data is not None:
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    resp = make_response(jsonify(cached_data), 200)
                    resp.headers["X-Cache"] = "HIT"
                    resp.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
                    resp.headers["X-Cache-Key"] = cache_key
                    return resp

                # Cache Miss - Execute View Function
                rv = fn(*args, **kwargs)
                duration_ms = (time.perf_counter() - start_time) * 1000

                resp = make_response(rv)
                if resp.status_code == 200:
                    json_data = resp.get_json(silent=True)
                    if json_data is not None:
                        self.set(cache_key, json_data, timeout=timeout)

                resp.headers["X-Cache"] = "MISS"
                resp.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
                resp.headers["X-Cache-Key"] = cache_key
                return resp

            return wrapper
        return decorator


# Singleton instance
cache = CacheService()

