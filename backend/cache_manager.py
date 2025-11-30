"""
Two-Tier Cache Manager for Marei Mekomos V5

Strategy:
1. AGGRESSIVE caching for Sefaria texts (TTL: 30 days)
   - Torah texts never change
   - Save every Sefaria API call possible
   
2. CAUTIOUS caching for Claude responses (TTL: 24 hours)
   - Query interpretations may improve with model updates
   - Still save repeated identical queries

This is critical for cost savings - every cached call saves real money!
"""

import json
import os
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Any
import logging

logger = logging.getLogger(__name__)


class TieredCache:
    """File-based cache with configurable TTL and statistics tracking"""
    
    def __init__(
        self,
        cache_dir: str,
        ttl_hours: int = 24,
        name: str = "cache"
    ):
        """
        Initialize cache.
        
        Args:
            cache_dir: Directory to store cache files
            ttl_hours: Time-to-live in hours
            name: Name for logging
        """
        self.cache_dir = os.path.join(os.path.dirname(__file__), cache_dir)
        self.ttl = timedelta(hours=ttl_hours)
        self.name = name
        self.enabled = os.environ.get("USE_CACHE", "true").lower() in ("true", "1", "yes")
        
        # Statistics
        self.hits = 0
        self.misses = 0
        self.saves = 0
        
        os.makedirs(self.cache_dir, exist_ok=True)
        logger.info(f"Cache '{name}' initialized: {self.cache_dir} (TTL={ttl_hours}h, enabled={self.enabled})")
    
    def _hash_key(self, key: str) -> str:
        """Generate safe filename from key"""
        return hashlib.md5(key.encode()).hexdigest()
    
    def _get_path(self, key: str) -> str:
        """Get full path for cache file"""
        return os.path.join(self.cache_dir, f"{self._hash_key(key)}.json")
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache if exists and not expired.
        Returns None if not found or expired.
        """
        if not self.enabled:
            return None
        
        path = self._get_path(key)
        
        if not os.path.exists(path):
            self.misses += 1
            return None
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                cached = json.load(f)
            
            # Check expiration
            cached_time = datetime.fromisoformat(cached['timestamp'])
            if datetime.now() - cached_time > self.ttl:
                logger.debug(f"[{self.name}] EXPIRED: {key[:50]}...")
                os.remove(path)
                self.misses += 1
                return None
            
            self.hits += 1
            logger.debug(f"[{self.name}] HIT: {key[:50]}...")
            return cached['data']
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"[{self.name}] Corrupted cache file: {e}")
            try:
                os.remove(path)
            except:
                pass
            self.misses += 1
            return None
    
    def set(self, key: str, value: Any) -> None:
        """Save value to cache"""
        if not self.enabled:
            return
        
        path = self._get_path(key)
        
        cached = {
            'timestamp': datetime.now().isoformat(),
            'key_preview': key[:100],  # For debugging
            'data': value
        }
        
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(cached, f, ensure_ascii=False, indent=2)
            self.saves += 1
            logger.debug(f"[{self.name}] SAVED: {key[:50]}...")
        except Exception as e:
            logger.error(f"[{self.name}] Error writing cache: {e}")
    
    def clear(self) -> int:
        """Clear all cache files. Returns count of deleted files."""
        count = 0
        for filename in os.listdir(self.cache_dir):
            if filename.endswith('.json'):
                try:
                    os.remove(os.path.join(self.cache_dir, filename))
                    count += 1
                except:
                    pass
        self.hits = 0
        self.misses = 0
        self.saves = 0
        logger.info(f"[{self.name}] Cleared {count} cache files")
        return count
    
    def stats(self) -> dict:
        """Get cache statistics"""
        files = [f for f in os.listdir(self.cache_dir) if f.endswith('.json')]
        total_size = sum(
            os.path.getsize(os.path.join(self.cache_dir, f))
            for f in files
        )
        
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'name': self.name,
            'total_entries': len(files),
            'total_size_bytes': total_size,
            'total_size_kb': round(total_size / 1024, 2),
            'hits': self.hits,
            'misses': self.misses,
            'saves': self.saves,
            'hit_rate_percent': round(hit_rate, 1),
            'enabled': self.enabled,
        }


# =============================
# GLOBAL CACHE INSTANCES
# =============================

# Claude API cache - 24 hour TTL
# Query interpretations and citation analysis
claude_cache = TieredCache(
    cache_dir="cache/claude",
    ttl_hours=24,
    name="claude"
)

# Sefaria API cache - 30 day TTL (texts never change!)
# Text fetches and related API responses
sefaria_cache = TieredCache(
    cache_dir="cache/sefaria",
    ttl_hours=24 * 30,  # 30 days
    name="sefaria"
)


def get_combined_stats() -> dict:
    """Get combined statistics from all caches"""
    claude_stats = claude_cache.stats()
    sefaria_stats = sefaria_cache.stats()
    
    # Estimate cost savings
    # Claude Sonnet: ~$3 per 1M input tokens, ~$15 per 1M output tokens
    # Average request: ~2000 input tokens, ~1000 output tokens
    # Cost per request: ~$0.006 + $0.015 = ~$0.021
    estimated_claude_savings = claude_stats['hits'] * 0.02
    
    # Sefaria is free but we save rate limiting issues
    
    return {
        'claude': claude_stats,
        'sefaria': sefaria_stats,
        'estimated_savings_usd': round(estimated_claude_savings, 2),
        'total_entries': claude_stats['total_entries'] + sefaria_stats['total_entries'],
    }
