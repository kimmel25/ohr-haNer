"""
Feedback-Aware Cache for Marei Mekomos
======================================

Caches verified search results based on user feedback.
Follows SOLID principles for interface-agnostic usage.

Features:
- Cache results when user gives positive feedback
- Match queries by exact string OR Hebrew terms
- Apply priority adjustments based on feedback history
- Sources with thumbs down get lower priority (not blocked)

Usage:
    # Initialize cache
    cache = FeedbackCache(storage=JsonFileFeedbackStorage("cache/feedback"))

    # After getting positive feedback, cache the result
    if feedback_result.should_cache:
        cache.store_verified_result(
            query="chezkas haguf",
            hebrew_terms=["חזקת הגוף"],
            sources=sources,
            feedback_result=feedback_result,
        )

    # On new query, check cache first
    cached = cache.get_cached_result(query="chezkas haguf")
    if cached:
        # Use cached sources with priority adjustments applied
        return cached.sources
"""

from typing import Protocol, Optional, List, Dict, Any, Tuple
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
from pathlib import Path
import json
import hashlib
import os

from backend.models import Source, ConfidenceLevel
from backend.user_feedback import (
    QueryFeedback,
    FeedbackResult,
    FeedbackRating,
    SourceFeedback,
)


# ==========================================
#  CACHE MODELS
# ==========================================

class CachedSource(BaseModel):
    """A source with cached priority adjustment."""

    source: Source
    priority_adjustment: float = 0.0  # From feedback history
    feedback_count: int = 0  # How many times rated
    thumbs_up_count: int = 0
    thumbs_down_count: int = 0

    class Config:
        use_enum_values = True


class CachedResult(BaseModel):
    """A cached query result with metadata."""

    # Query identification
    original_query: str
    hebrew_terms: List[str]
    query_hash: str  # For fast exact matching
    terms_hash: str  # For Hebrew terms matching

    # Cached sources with priority adjustments
    sources: List[CachedSource]

    # Feedback that triggered caching
    feedback_score: float
    was_positive_overall: bool
    had_majority_thumbs_up: bool

    # Metadata
    cached_at: datetime = Field(default_factory=datetime.now)
    access_count: int = 0
    last_accessed: Optional[datetime] = None

    # Cache validity
    ttl_hours: int = 168  # 1 week default

    class Config:
        use_enum_values = True

    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        expiry = self.cached_at + timedelta(hours=self.ttl_hours)
        return datetime.now() > expiry


class SourceFeedbackHistory(BaseModel):
    """Aggregate feedback history for a source across all queries."""

    source_ref: str
    thumbs_up_count: int = 0
    thumbs_down_count: int = 0
    total_appearances: int = 0

    # Calculated priority adjustment
    priority_adjustment: float = 0.0

    # Last updated
    last_updated: datetime = Field(default_factory=datetime.now)

    def recalculate_priority(
        self,
        boost_per_up: float = 0.1,
        penalty_per_down: float = 0.15,
    ) -> None:
        """Recalculate priority based on feedback counts."""
        self.priority_adjustment = (
            self.thumbs_up_count * boost_per_up -
            self.thumbs_down_count * penalty_per_down
        )
        # Clamp to [-1.0, 1.0]
        self.priority_adjustment = max(-1.0, min(1.0, self.priority_adjustment))


# ==========================================
#  STORAGE PROTOCOL
# ==========================================

class CacheStorageProtocol(Protocol):
    """Protocol for cache storage backends."""

    def store_result(self, result: CachedResult) -> bool:
        """Store a cached result."""
        ...

    def get_by_query_hash(self, query_hash: str) -> Optional[CachedResult]:
        """Get cached result by exact query hash."""
        ...

    def get_by_terms_hash(self, terms_hash: str) -> Optional[CachedResult]:
        """Get cached result by Hebrew terms hash."""
        ...

    def update_source_history(self, source_ref: str, rating: FeedbackRating) -> None:
        """Update the feedback history for a source."""
        ...

    def get_source_history(self, source_ref: str) -> Optional[SourceFeedbackHistory]:
        """Get feedback history for a source."""
        ...

    def get_all_source_histories(self) -> Dict[str, SourceFeedbackHistory]:
        """Get all source feedback histories."""
        ...

    def clear_expired(self) -> int:
        """Clear expired cache entries. Returns count of cleared entries."""
        ...


# ==========================================
#  FEEDBACK CACHE
# ==========================================

class FeedbackCache:
    """
    Main feedback-aware cache system.

    Responsibilities:
    - Store verified results based on positive feedback
    - Retrieve cached results with priority adjustments
    - Apply source-level priority based on feedback history
    - Match queries by exact string OR Hebrew terms
    """

    def __init__(
        self,
        storage: CacheStorageProtocol,
        priority_boost: float = 0.1,
        priority_penalty: float = 0.15,
    ):
        """
        Initialize the feedback cache.

        Args:
            storage: Storage backend implementation
            priority_boost: Priority increase per thumbs up
            priority_penalty: Priority decrease per thumbs down
        """
        self.storage = storage
        self.priority_boost = priority_boost
        self.priority_penalty = priority_penalty

    def store_verified_result(
        self,
        query: str,
        hebrew_terms: List[str],
        sources: List[Source],
        feedback_result: FeedbackResult,
        ttl_hours: int = 168,
    ) -> bool:
        """
        Store a verified result in the cache.

        Called when feedback indicates the result was good.

        Args:
            query: Original query string
            hebrew_terms: Resolved Hebrew terms
            sources: The sources to cache
            feedback_result: The calculated feedback result
            ttl_hours: Time to live in hours

        Returns:
            True if stored successfully
        """
        if not feedback_result.should_cache:
            return False

        # Create cached sources with priority adjustments
        cached_sources = []
        for source in sources:
            adjustment = feedback_result.priority_adjustments.get(source.ref, 0.0)
            thumbs_up = 1 if source.ref in feedback_result.thumbs_up_refs else 0
            thumbs_down = 1 if source.ref in feedback_result.thumbs_down_refs else 0

            cached_sources.append(CachedSource(
                source=source,
                priority_adjustment=adjustment,
                feedback_count=1 if (thumbs_up or thumbs_down) else 0,
                thumbs_up_count=thumbs_up,
                thumbs_down_count=thumbs_down,
            ))

        # Create cached result
        cached = CachedResult(
            original_query=query,
            hebrew_terms=hebrew_terms,
            query_hash=self._hash_query(query),
            terms_hash=self._hash_terms(hebrew_terms),
            sources=cached_sources,
            feedback_score=feedback_result.combined_score,
            was_positive_overall=feedback_result.is_positive,
            had_majority_thumbs_up=feedback_result.has_majority_thumbs_up,
            ttl_hours=ttl_hours,
        )

        # Store and update source histories
        success = self.storage.store_result(cached)

        if success:
            # Update individual source histories
            for ref in feedback_result.thumbs_up_refs:
                self.storage.update_source_history(ref, FeedbackRating.THUMBS_UP)
            for ref in feedback_result.thumbs_down_refs:
                self.storage.update_source_history(ref, FeedbackRating.THUMBS_DOWN)

        return success

    def get_cached_result(
        self,
        query: str,
        hebrew_terms: Optional[List[str]] = None,
    ) -> Optional[CachedResult]:
        """
        Get a cached result for a query.

        Tries exact query match first, then falls back to Hebrew terms match.

        Args:
            query: The query string
            hebrew_terms: Optional Hebrew terms (for fallback matching)

        Returns:
            CachedResult with priority adjustments applied, or None
        """
        # Try exact query match first
        query_hash = self._hash_query(query)
        result = self.storage.get_by_query_hash(query_hash)

        if result and not result.is_expired():
            self._apply_current_priorities(result)
            return result

        # Fall back to Hebrew terms match
        if hebrew_terms:
            terms_hash = self._hash_terms(hebrew_terms)
            result = self.storage.get_by_terms_hash(terms_hash)

            if result and not result.is_expired():
                self._apply_current_priorities(result)
                return result

        return None

    def get_source_priority_adjustment(self, source_ref: str) -> float:
        """
        Get the current priority adjustment for a source.

        Based on aggregate feedback across all queries.
        """
        history = self.storage.get_source_history(source_ref)
        if history:
            return history.priority_adjustment
        return 0.0

    def apply_priority_to_sources(self, sources: List[Source]) -> List[Tuple[Source, float]]:
        """
        Apply priority adjustments to a list of sources.

        Returns list of (source, adjusted_priority) tuples.
        Higher priority = should appear higher in results.
        """
        result = []
        for source in sources:
            adjustment = self.get_source_priority_adjustment(source.ref)
            # Base priority from level_order (lower = higher priority)
            # Invert so higher number = higher priority
            base_priority = 100 - source.level_order
            adjusted = base_priority + (adjustment * 10)  # Scale adjustment
            result.append((source, adjusted))

        # Sort by adjusted priority (descending)
        result.sort(key=lambda x: x[1], reverse=True)
        return result

    def _apply_current_priorities(self, cached: CachedResult) -> None:
        """Apply current priority adjustments from source histories."""
        for cached_source in cached.sources:
            history = self.storage.get_source_history(cached_source.source.ref)
            if history:
                cached_source.priority_adjustment = history.priority_adjustment
                cached_source.thumbs_up_count = history.thumbs_up_count
                cached_source.thumbs_down_count = history.thumbs_down_count

    def _hash_query(self, query: str) -> str:
        """Create hash for exact query matching."""
        normalized = query.strip().lower()
        return hashlib.md5(normalized.encode()).hexdigest()

    def _hash_terms(self, terms: List[str]) -> str:
        """Create hash for Hebrew terms matching."""
        # Sort to ensure consistent ordering
        sorted_terms = sorted(terms)
        combined = "|".join(sorted_terms)
        return hashlib.md5(combined.encode()).hexdigest()

    def clear_expired(self) -> int:
        """Clear expired cache entries."""
        return self.storage.clear_expired()


# ==========================================
#  JSON FILE STORAGE IMPLEMENTATION
# ==========================================

class JsonFileFeedbackStorage:
    """
    JSON file-based storage implementation.

    Structure:
        cache_dir/
            results/
                {query_hash}.json
            terms_index.json  # maps terms_hash -> query_hash
            source_history.json
    """

    def __init__(self, cache_dir: str = "cache/feedback"):
        """Initialize with cache directory path."""
        self.cache_dir = Path(cache_dir)
        self.results_dir = self.cache_dir / "results"
        self.terms_index_path = self.cache_dir / "terms_index.json"
        self.source_history_path = self.cache_dir / "source_history.json"

        # Ensure directories exist
        self.results_dir.mkdir(parents=True, exist_ok=True)

        # Initialize index files if needed
        if not self.terms_index_path.exists():
            self._write_json(self.terms_index_path, {})
        if not self.source_history_path.exists():
            self._write_json(self.source_history_path, {})

    def store_result(self, result: CachedResult) -> bool:
        """Store a cached result."""
        try:
            # Store the result
            result_path = self.results_dir / f"{result.query_hash}.json"
            self._write_json(result_path, result.model_dump(mode="json"))

            # Update terms index
            terms_index = self._read_json(self.terms_index_path)
            terms_index[result.terms_hash] = result.query_hash
            self._write_json(self.terms_index_path, terms_index)

            return True
        except Exception as e:
            print(f"Error storing cached result: {e}")
            return False

    def get_by_query_hash(self, query_hash: str) -> Optional[CachedResult]:
        """Get cached result by exact query hash."""
        result_path = self.results_dir / f"{query_hash}.json"
        if not result_path.exists():
            return None

        try:
            data = self._read_json(result_path)
            result = CachedResult.model_validate(data)

            # Update access stats
            result.access_count += 1
            result.last_accessed = datetime.now()
            self._write_json(result_path, result.model_dump(mode="json"))

            return result
        except Exception as e:
            print(f"Error reading cached result: {e}")
            return None

    def get_by_terms_hash(self, terms_hash: str) -> Optional[CachedResult]:
        """Get cached result by Hebrew terms hash."""
        terms_index = self._read_json(self.terms_index_path)
        query_hash = terms_index.get(terms_hash)

        if query_hash:
            return self.get_by_query_hash(query_hash)
        return None

    def update_source_history(self, source_ref: str, rating: FeedbackRating) -> None:
        """Update the feedback history for a source."""
        histories = self._read_json(self.source_history_path)

        if source_ref not in histories:
            histories[source_ref] = {
                "source_ref": source_ref,
                "thumbs_up_count": 0,
                "thumbs_down_count": 0,
                "total_appearances": 0,
                "priority_adjustment": 0.0,
                "last_updated": datetime.now().isoformat(),
            }

        history = histories[source_ref]
        history["total_appearances"] += 1
        history["last_updated"] = datetime.now().isoformat()

        if rating == FeedbackRating.THUMBS_UP:
            history["thumbs_up_count"] += 1
        elif rating == FeedbackRating.THUMBS_DOWN:
            history["thumbs_down_count"] += 1

        # Recalculate priority
        boost = 0.1
        penalty = 0.15
        adjustment = (
            history["thumbs_up_count"] * boost -
            history["thumbs_down_count"] * penalty
        )
        history["priority_adjustment"] = max(-1.0, min(1.0, adjustment))

        self._write_json(self.source_history_path, histories)

    def get_source_history(self, source_ref: str) -> Optional[SourceFeedbackHistory]:
        """Get feedback history for a source."""
        histories = self._read_json(self.source_history_path)
        data = histories.get(source_ref)

        if data:
            return SourceFeedbackHistory.model_validate(data)
        return None

    def get_all_source_histories(self) -> Dict[str, SourceFeedbackHistory]:
        """Get all source feedback histories."""
        histories = self._read_json(self.source_history_path)
        return {
            ref: SourceFeedbackHistory.model_validate(data)
            for ref, data in histories.items()
        }

    def clear_expired(self) -> int:
        """Clear expired cache entries."""
        cleared = 0

        for result_path in self.results_dir.glob("*.json"):
            try:
                data = self._read_json(result_path)
                result = CachedResult.model_validate(data)

                if result.is_expired():
                    result_path.unlink()

                    # Remove from terms index
                    terms_index = self._read_json(self.terms_index_path)
                    if result.terms_hash in terms_index:
                        del terms_index[result.terms_hash]
                        self._write_json(self.terms_index_path, terms_index)

                    cleared += 1
            except Exception as e:
                print(f"Error checking cache entry {result_path}: {e}")

        return cleared

    def _read_json(self, path: Path) -> Dict:
        """Read JSON file."""
        if not path.exists():
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write_json(self, path: Path, data: Dict) -> None:
        """Write JSON file."""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)


# ==========================================
#  IN-MEMORY STORAGE IMPLEMENTATION
# ==========================================

class InMemoryFeedbackStorage:
    """
    In-memory storage implementation for testing.

    Does not persist between restarts.
    """

    def __init__(self):
        self.results: Dict[str, CachedResult] = {}  # query_hash -> result
        self.terms_index: Dict[str, str] = {}  # terms_hash -> query_hash
        self.source_histories: Dict[str, SourceFeedbackHistory] = {}

    def store_result(self, result: CachedResult) -> bool:
        """Store a cached result."""
        self.results[result.query_hash] = result
        self.terms_index[result.terms_hash] = result.query_hash
        return True

    def get_by_query_hash(self, query_hash: str) -> Optional[CachedResult]:
        """Get cached result by exact query hash."""
        result = self.results.get(query_hash)
        if result:
            result.access_count += 1
            result.last_accessed = datetime.now()
        return result

    def get_by_terms_hash(self, terms_hash: str) -> Optional[CachedResult]:
        """Get cached result by Hebrew terms hash."""
        query_hash = self.terms_index.get(terms_hash)
        if query_hash:
            return self.get_by_query_hash(query_hash)
        return None

    def update_source_history(self, source_ref: str, rating: FeedbackRating) -> None:
        """Update the feedback history for a source."""
        if source_ref not in self.source_histories:
            self.source_histories[source_ref] = SourceFeedbackHistory(
                source_ref=source_ref
            )

        history = self.source_histories[source_ref]
        history.total_appearances += 1
        history.last_updated = datetime.now()

        if rating == FeedbackRating.THUMBS_UP:
            history.thumbs_up_count += 1
        elif rating == FeedbackRating.THUMBS_DOWN:
            history.thumbs_down_count += 1

        history.recalculate_priority()

    def get_source_history(self, source_ref: str) -> Optional[SourceFeedbackHistory]:
        """Get feedback history for a source."""
        return self.source_histories.get(source_ref)

    def get_all_source_histories(self) -> Dict[str, SourceFeedbackHistory]:
        """Get all source feedback histories."""
        return dict(self.source_histories)

    def clear_expired(self) -> int:
        """Clear expired cache entries."""
        expired_hashes = [
            h for h, r in self.results.items() if r.is_expired()
        ]

        for query_hash in expired_hashes:
            result = self.results.pop(query_hash)
            # Remove from terms index
            if result.terms_hash in self.terms_index:
                del self.terms_index[result.terms_hash]

        return len(expired_hashes)


# ==========================================
#  FACTORY FUNCTION
# ==========================================

def create_feedback_cache(
    storage_type: str = "json",
    cache_dir: str = "cache/feedback",
    **kwargs,
) -> FeedbackCache:
    """
    Factory function to create FeedbackCache with appropriate storage.

    Args:
        storage_type: "json" or "memory"
        cache_dir: Directory for JSON storage
        **kwargs: Additional args passed to FeedbackCache

    Returns:
        Configured FeedbackCache instance
    """
    if storage_type == "json":
        storage = JsonFileFeedbackStorage(cache_dir)
    elif storage_type == "memory":
        storage = InMemoryFeedbackStorage()
    else:
        raise ValueError(f"Unknown storage type: {storage_type}")

    return FeedbackCache(storage=storage, **kwargs)
