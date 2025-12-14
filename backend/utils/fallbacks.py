"""
Fallback behaviors for pipeline steps.
"""

from typing import Any

from models import ConfidenceLevel, DecipherResult


def fallback_step1(query: str) -> DecipherResult:
    """Fallback when Step 1 module is not available."""
    hebrew_chars = sum(1 for char in query if "\u0590" <= char <= "\u05FF")
    total_chars = sum(1 for char in query if char.isalpha())

    if total_chars > 0 and hebrew_chars / total_chars > 0.5:
        return DecipherResult(
            success=True,
            hebrew_term=query,
            hebrew_terms=[query],
            confidence=ConfidenceLevel.HIGH,
            method="passthrough",
            is_mixed_query=False,
            original_query=query,
            extraction_confident=True,
            message="Query is already in Hebrew",
        )

    return DecipherResult(
        success=False,
        hebrew_term=None,
        hebrew_terms=[],
        confidence=ConfidenceLevel.LOW,
        method="failed",
        is_mixed_query=False,
        original_query=query,
        extraction_confident=False,
        message="Step 1 module not available and query is not Hebrew",
    )


def fallback_step2(hebrew_term: str):
    """Fallback when Step 2 fails."""
    from step_two_understand import FetchStrategy, QueryType, SearchStrategy

    return SearchStrategy(
        query_type=QueryType.UNKNOWN,
        primary_source=None,
        reasoning="Could not analyze query (Step 2 error)",
        fetch_strategy=FetchStrategy.TRICKLE_UP,
        depth="basic",
        confidence=ConfidenceLevel.LOW,
        clarification_prompt="What specific aspect of this topic are you looking for?",
    )


def fallback_step3(strategy: Any, query: str, hebrew_term: str):
    """Fallback when Step 3 fails."""
    from step_three_search import SearchResult

    return SearchResult(
        original_query=query,
        hebrew_term=hebrew_term,
        hebrew_terms=[hebrew_term],
        primary_source=strategy.primary_source,
        primary_source_he=strategy.primary_source_he,
        sources=[],
        sources_by_level={},
        sources_by_term={},
        related_sugyos=[],
        total_sources=0,
        levels_included=[],
        interpretation=strategy.reasoning,
        confidence="low",
        needs_clarification=True,
        clarification_prompt="We had trouble fetching sources. Could you try again?",
    )

