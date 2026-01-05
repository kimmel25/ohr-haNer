"""
User Feedback System for Marei Mekomos
======================================

Interface-agnostic feedback collection and calculation system.
Follows SOLID principles for easy integration with any UI.

Usage:
    # 1. Collect feedback (from any interface)
    feedback = QueryFeedback(
        query_id="abc123",
        original_query="chezkas haguf",
        hebrew_terms=["חזקת הגוף"],
        overall_satisfaction=SatisfactionLevel.SATISFIED,
        source_feedbacks=[
            SourceFeedback(source_ref="Kesubos 12b", rating=FeedbackRating.THUMBS_UP),
            SourceFeedback(source_ref="Bava Kamma 46a", rating=FeedbackRating.THUMBS_DOWN),
        ]
    )

    # 2. Calculate overall score
    calculator = FeedbackCalculator()
    result = calculator.calculate(feedback)

    # 3. Check if should cache
    if result.should_cache:
        # Store in feedback cache
        pass
"""

from typing import Protocol, Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum
from datetime import datetime
from abc import ABC, abstractmethod
import hashlib


# ==========================================
#  ENUMS
# ==========================================

class FeedbackRating(str, Enum):
    """Rating for individual sources."""
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"
    NEUTRAL = "neutral"  # No rating given


class SatisfactionLevel(str, Enum):
    """Overall satisfaction with the results."""
    VERY_SATISFIED = "very_satisfied"
    SATISFIED = "satisfied"
    NEUTRAL = "neutral"
    DISSATISFIED = "dissatisfied"
    VERY_DISSATISFIED = "very_dissatisfied"


# ==========================================
#  FEEDBACK MODELS
# ==========================================

class SourceFeedback(BaseModel):
    """Feedback for a single source."""

    source_ref: str  # e.g., "Kesubos 12b"
    rating: FeedbackRating = FeedbackRating.NEUTRAL

    # Optional: why the user rated this way
    comment: Optional[str] = None

    # Timestamp
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True


class QueryFeedback(BaseModel):
    """Complete feedback for a query result."""

    # Identification
    query_id: str  # Unique ID for this query session
    original_query: str  # Original user query
    hebrew_terms: List[str] = []  # Resolved Hebrew terms

    # Overall feedback
    overall_satisfaction: SatisfactionLevel = SatisfactionLevel.NEUTRAL
    overall_comment: Optional[str] = None

    # Per-source feedback
    source_feedbacks: List[SourceFeedback] = []

    # Metadata
    timestamp: datetime = Field(default_factory=datetime.now)
    user_id: Optional[str] = None  # Optional user identifier

    class Config:
        use_enum_values = True

    def get_thumbs_up_sources(self) -> List[str]:
        """Get refs of all sources with thumbs up."""
        return [
            sf.source_ref for sf in self.source_feedbacks
            if sf.rating == FeedbackRating.THUMBS_UP
        ]

    def get_thumbs_down_sources(self) -> List[str]:
        """Get refs of all sources with thumbs down."""
        return [
            sf.source_ref for sf in self.source_feedbacks
            if sf.rating == FeedbackRating.THUMBS_DOWN
        ]

    def thumbs_up_count(self) -> int:
        """Count of thumbs up ratings."""
        return len(self.get_thumbs_up_sources())

    def thumbs_down_count(self) -> int:
        """Count of thumbs down ratings."""
        return len(self.get_thumbs_down_sources())

    def rated_count(self) -> int:
        """Count of sources with any rating (not neutral)."""
        return sum(
            1 for sf in self.source_feedbacks
            if sf.rating != FeedbackRating.NEUTRAL
        )


class FeedbackResult(BaseModel):
    """Result of feedback calculation."""

    # Calculated scores (0.0 to 1.0)
    overall_score: float = Field(ge=0.0, le=1.0)
    source_score: float = Field(ge=0.0, le=1.0)  # Based on thumbs ratio
    combined_score: float = Field(ge=0.0, le=1.0)

    # Decision flags
    should_cache: bool = False
    is_positive: bool = False
    has_majority_thumbs_up: bool = False

    # Source-level analysis
    thumbs_up_refs: List[str] = []
    thumbs_down_refs: List[str] = []

    # Priority adjustments for sources (ref -> priority_delta)
    # Positive = higher priority, Negative = lower priority
    priority_adjustments: Dict[str, float] = {}

    # Reasoning
    reasoning: str = ""


# ==========================================
#  PROTOCOLS (Dependency Inversion)
# ==========================================

class FeedbackStorageProtocol(Protocol):
    """Protocol for feedback storage backends."""

    def store(self, feedback: QueryFeedback, result: FeedbackResult) -> bool:
        """Store feedback and calculated result."""
        ...

    def get_by_query(self, original_query: str) -> Optional[List[QueryFeedback]]:
        """Get all feedback for a query."""
        ...

    def get_by_hebrew_terms(self, hebrew_terms: List[str]) -> Optional[List[QueryFeedback]]:
        """Get all feedback matching Hebrew terms."""
        ...

    def get_source_history(self, source_ref: str) -> Dict[str, int]:
        """Get thumbs up/down counts for a source across all queries."""
        ...


class FeedbackCollectorProtocol(Protocol):
    """Protocol for feedback collection interfaces."""

    def collect_overall(self, query_id: str) -> SatisfactionLevel:
        """Collect overall satisfaction."""
        ...

    def collect_source_rating(self, query_id: str, source_ref: str) -> FeedbackRating:
        """Collect rating for a specific source."""
        ...

    def get_feedback(self, query_id: str) -> Optional[QueryFeedback]:
        """Get the complete feedback for a query."""
        ...


# ==========================================
#  FEEDBACK CALCULATOR
# ==========================================

class FeedbackCalculator:
    """
    Calculates overall feedback scores and determines caching decisions.

    Scoring:
    - Overall satisfaction is mapped to 0.0-1.0
    - Source score is (thumbs_up - thumbs_down) / total_rated, normalized
    - Combined score weighs both with configurable weights

    Caching decision:
    - Cache if overall is positive OR majority thumbs up
    """

    # Satisfaction level to score mapping
    SATISFACTION_SCORES = {
        SatisfactionLevel.VERY_SATISFIED: 1.0,
        SatisfactionLevel.SATISFIED: 0.75,
        SatisfactionLevel.NEUTRAL: 0.5,
        SatisfactionLevel.DISSATISFIED: 0.25,
        SatisfactionLevel.VERY_DISSATISFIED: 0.0,
    }

    def __init__(
        self,
        overall_weight: float = 0.6,
        source_weight: float = 0.4,
        cache_threshold: float = 0.6,
        majority_threshold: float = 0.5,
        priority_boost_per_thumbs_up: float = 0.1,
        priority_penalty_per_thumbs_down: float = 0.15,
    ):
        """
        Initialize calculator with configurable weights.

        Args:
            overall_weight: Weight for overall satisfaction (0-1)
            source_weight: Weight for source-level feedback (0-1)
            cache_threshold: Minimum combined score to trigger caching
            majority_threshold: Ratio needed for "majority thumbs up"
            priority_boost_per_thumbs_up: Priority increase per thumbs up
            priority_penalty_per_thumbs_down: Priority decrease per thumbs down
        """
        if abs(overall_weight + source_weight - 1.0) > 0.01:
            raise ValueError("Weights must sum to 1.0")

        self.overall_weight = overall_weight
        self.source_weight = source_weight
        self.cache_threshold = cache_threshold
        self.majority_threshold = majority_threshold
        self.priority_boost = priority_boost_per_thumbs_up
        self.priority_penalty = priority_penalty_per_thumbs_down

    def calculate(self, feedback: QueryFeedback) -> FeedbackResult:
        """
        Calculate feedback scores and make caching decision.

        Takes into account:
        - Overall satisfaction level
        - Individual source thumbs up/down
        - Combined threshold for caching
        """
        # Calculate overall score from satisfaction level
        overall_score = self.SATISFACTION_SCORES.get(
            SatisfactionLevel(feedback.overall_satisfaction),
            0.5
        )

        # Calculate source score from thumbs ratio
        source_score = self._calculate_source_score(feedback)

        # Combined weighted score
        combined_score = (
            self.overall_weight * overall_score +
            self.source_weight * source_score
        )

        # Check if majority thumbs up
        rated_count = feedback.rated_count()
        has_majority = (
            rated_count > 0 and
            feedback.thumbs_up_count() / rated_count > self.majority_threshold
        )

        # Caching decision: positive overall OR majority thumbs up
        is_positive = overall_score >= 0.6  # SATISFIED or higher
        should_cache = is_positive or has_majority or combined_score >= self.cache_threshold

        # Calculate priority adjustments for each source
        priority_adjustments = self._calculate_priority_adjustments(feedback)

        # Build reasoning
        reasoning = self._build_reasoning(
            overall_score, source_score, combined_score,
            is_positive, has_majority, should_cache, feedback
        )

        return FeedbackResult(
            overall_score=overall_score,
            source_score=source_score,
            combined_score=combined_score,
            should_cache=should_cache,
            is_positive=is_positive,
            has_majority_thumbs_up=has_majority,
            thumbs_up_refs=feedback.get_thumbs_up_sources(),
            thumbs_down_refs=feedback.get_thumbs_down_sources(),
            priority_adjustments=priority_adjustments,
            reasoning=reasoning,
        )

    def _calculate_source_score(self, feedback: QueryFeedback) -> float:
        """Calculate score based on source ratings."""
        rated_count = feedback.rated_count()
        if rated_count == 0:
            return 0.5  # Neutral if no ratings

        # Net thumbs (up - down), normalized to 0-1 range
        net_thumbs = feedback.thumbs_up_count() - feedback.thumbs_down_count()
        # Range is [-rated_count, +rated_count], normalize to [0, 1]
        normalized = (net_thumbs + rated_count) / (2 * rated_count)
        return normalized

    def _calculate_priority_adjustments(self, feedback: QueryFeedback) -> Dict[str, float]:
        """
        Calculate priority adjustments for each rated source.

        Thumbs up = higher priority (positive adjustment)
        Thumbs down = lower priority (negative adjustment)
        """
        adjustments = {}

        for sf in feedback.source_feedbacks:
            if sf.rating == FeedbackRating.THUMBS_UP:
                adjustments[sf.source_ref] = self.priority_boost
            elif sf.rating == FeedbackRating.THUMBS_DOWN:
                adjustments[sf.source_ref] = -self.priority_penalty
            # NEUTRAL = no adjustment

        return adjustments

    def _build_reasoning(
        self,
        overall_score: float,
        source_score: float,
        combined_score: float,
        is_positive: bool,
        has_majority: bool,
        should_cache: bool,
        feedback: QueryFeedback,
    ) -> str:
        """Build human-readable reasoning for the decision."""
        parts = []

        parts.append(f"Overall satisfaction: {feedback.overall_satisfaction} (score: {overall_score:.2f})")

        if feedback.rated_count() > 0:
            parts.append(
                f"Source ratings: {feedback.thumbs_up_count()} up, "
                f"{feedback.thumbs_down_count()} down (score: {source_score:.2f})"
            )
        else:
            parts.append("No individual source ratings provided")

        parts.append(f"Combined score: {combined_score:.2f}")

        if should_cache:
            reasons = []
            if is_positive:
                reasons.append("positive overall satisfaction")
            if has_majority:
                reasons.append("majority thumbs up")
            if combined_score >= self.cache_threshold:
                reasons.append(f"combined score >= {self.cache_threshold}")
            parts.append(f"CACHE: Yes ({', '.join(reasons)})")
        else:
            parts.append("CACHE: No (threshold not met)")

        return " | ".join(parts)


# ==========================================
#  ABSTRACT FEEDBACK STORAGE
# ==========================================

class FeedbackStorage(ABC):
    """Abstract base class for feedback storage implementations."""

    @abstractmethod
    def store(self, feedback: QueryFeedback, result: FeedbackResult) -> bool:
        """Store feedback and calculated result."""
        pass

    @abstractmethod
    def get_by_query(self, original_query: str) -> Optional[List[QueryFeedback]]:
        """Get all feedback for a query (exact match)."""
        pass

    @abstractmethod
    def get_by_hebrew_terms(self, hebrew_terms: List[str]) -> Optional[List[QueryFeedback]]:
        """Get all feedback matching Hebrew terms."""
        pass

    @abstractmethod
    def get_source_history(self, source_ref: str) -> Dict[str, int]:
        """Get thumbs up/down counts for a source across all queries."""
        pass

    @abstractmethod
    def get_aggregate_priority(self, source_ref: str) -> float:
        """Get aggregate priority adjustment for a source based on all feedback."""
        pass


# ==========================================
#  UTILITY FUNCTIONS
# ==========================================

def generate_query_id(query: str, timestamp: Optional[datetime] = None) -> str:
    """Generate a unique query ID."""
    ts = timestamp or datetime.now()
    data = f"{query}|{ts.isoformat()}"
    return hashlib.md5(data.encode()).hexdigest()[:12]


def create_feedback_from_sources(
    query_id: str,
    original_query: str,
    hebrew_terms: List[str],
    source_refs: List[str],
) -> QueryFeedback:
    """
    Create a QueryFeedback with all sources set to NEUTRAL.
    Ready for user to provide ratings.
    """
    source_feedbacks = [
        SourceFeedback(source_ref=ref, rating=FeedbackRating.NEUTRAL)
        for ref in source_refs
    ]

    return QueryFeedback(
        query_id=query_id,
        original_query=original_query,
        hebrew_terms=hebrew_terms,
        overall_satisfaction=SatisfactionLevel.NEUTRAL,
        source_feedbacks=source_feedbacks,
    )
