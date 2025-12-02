"""
Simple file-based cache to avoid repeated API calls.
"""

import json
import os
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from logging_config import get_logger

logger = get_logger(__name__)


class SimpleCache:
    """File-based cache with expiration support"""

    def __init__(self, cache_dir: str = "cache", ttl_hours: int = 24):
        self.cache_dir = os.path.join(os.path.dirname(__file__), cache_dir)
        self.ttl = timedelta(hours=ttl_hours)
        self.enabled = os.environ.get("USE_CACHE", "true").lower() in ("true", "1", "yes")
        os.makedirs(self.cache_dir, exist_ok=True)
        logger.info(f"Cache initialized at {self.cache_dir} with TTL={ttl_hours}h, enabled={self.enabled}")

    def _get_cache_key(self, key: str) -> str:
        """Generate a safe filename from a cache key using hash"""
        return hashlib.md5(key.encode()).hexdigest()

    def _get_cache_path(self, key: str) -> str:
        """Get the full path to a cache file"""
        filename = self._get_cache_key(key) + ".json"
        return os.path.join(self.cache_dir, filename)

    def get(self, key: str) -> Optional[dict]:
        """Get a value from cache if it exists and hasn't expired."""
        if not self.enabled:
            return None

        cache_path = self._get_cache_path(key)

        if not os.path.exists(cache_path):
            return None

        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)

            # Check expiration
            cached_time = datetime.fromisoformat(cached_data['timestamp'])
            if datetime.now() - cached_time > self.ttl:
                os.remove(cache_path)
                return None

            logger.debug(f"Cache HIT: {key[:50]}")
            return cached_data['data']

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Error reading cache file {cache_path}: {e}")
            try:
                os.remove(cache_path)
            except:
                pass
            return None

    def set(self, key: str, value: dict):
        """Save a value to cache"""
        if not self.enabled:
            return

        cache_path = self._get_cache_path(key)

        cached_data = {
            'timestamp': datetime.now().isoformat(),
            'key': key,
            'data': value
        }

        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cached_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error writing cache file {cache_path}: {e}")

    def clear(self):
        """Clear all cache files"""
        count = 0
        for filename in os.listdir(self.cache_dir):
            if filename.endswith('.json'):
                try:
                    os.remove(os.path.join(self.cache_dir, filename))
                    count += 1
                except Exception as e:
                    logger.error(f"Error deleting cache file {filename}: {e}")
        logger.info(f"Cleared {count} cache files")

    def stats(self) -> dict:
        """Get cache statistics"""
        files = [f for f in os.listdir(self.cache_dir) if f.endswith('.json')]
        total_size = sum(
            os.path.getsize(os.path.join(self.cache_dir, f))
            for f in files
        )
        return {
            'total_entries': len(files),
            'total_size_bytes': total_size,
            'total_size_kb': round(total_size / 1024, 2)
        }


# Global cache instance (just Sefaria - no Claude cache needed)
sefaria_cache = SimpleCache(cache_dir="cache/sefaria", ttl_hours=168)  # 1 week