

try:
    from backend.utils.cache import cache, CacheService
except ImportError:
    from utils.cache import cache, CacheService

__all__ = ["cache", "CacheService"]
