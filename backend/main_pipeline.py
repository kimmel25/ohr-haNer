"""
Marei Mekomos V7 - Main Pipeline (V4 Mixed Query Support)
=========================================================

Complete flow:
1. DECIPHER: transliteration -> Hebrew (Step 1)
2. UNDERSTAND: Hebrew -> Intent + Strategy (Step 2)
3. SEARCH: Strategy -> Organized Sources (Step 3)

V4 highlights:
- Passes the full Step 1 result into Step 2 for mixed query context
- Handles multiple Hebrew terms and comparison queries
- Provides fallbacks when any step fails
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

# Add backend/ to path for local imports
sys.path.insert(0, str(Path(__file__).parent))

from models import ConfidenceLevel, DecipherResult, MareiMekomosResult
from utils.fallbacks import fallback_step1, fallback_step2, fallback_step3
from utils.serialization import enum_value, to_serializable

logger = logging.getLogger("pipeline.main")


# ==========================================
#  MAIN PIPELINE
# ==========================================

async def search_sources(query: str) -> MareiMekomosResult:
    """
    Main entry point for Marei Mekomos.

    Args:
        query: User's input (e.g., "chezkas haguf" or "what is chezkas haguf")

    Returns:
        MareiMekomosResult with all sources and metadata.
    """
    logger.info("=" * 80)
    logger.info("MAREI MEKOMOS V7 - FULL PIPELINE (V4 Mixed Query Support)")
    logger.info("=" * 80)
    logger.info("Query: '%s'", query)

    # ========================================
    # STEP 1: DECIPHER
    # ========================================
    logger.info("STEP 1: DECIPHER")
    try:
        from step_one_decipher import decipher

        step1_result = await decipher(query)
    except ImportError:
        logger.warning("step_one_decipher not found, using fallback")
        step1_result = fallback_step1(query)

    if getattr(step1_result, "is_mixed_query", False):
        logger.info("Step 1 detected mixed query")
        logger.info("  Extracted terms: %s", step1_result.hebrew_terms)
        logger.info("  Extraction confident: %s", step1_result.extraction_confident)
    else:
        logger.info("Step 1 complete: '%s' -> '%s'", query, step1_result.hebrew_term)

    if not step1_result.success and not step1_result.hebrew_term:
        logger.warning("Step 1 failed - returning early")
        return MareiMekomosResult(
            original_query=query,
            hebrew_term=None,
            hebrew_terms=[],
            transliteration_confidence=enum_value(step1_result.confidence),
            transliteration_method=step1_result.method,
            is_mixed_query=step1_result.is_mixed_query,
            query_type="unknown",
            primary_source=None,
            primary_source_he=None,
            interpretation="Could not translate the query to Hebrew",
            sources=[],
            sources_by_level={},
            sources_by_term={},
            related_sugyos=[],
            total_sources=0,
            levels_included=[],
            success=False,
            confidence=enum_value(step1_result.confidence),
            needs_clarification=True,
            clarification_prompt=step1_result.message
            or "Please try a different spelling",
            message="Could not understand the query",
        )

    hebrew_term = step1_result.hebrew_term or query
    hebrew_terms = step1_result.hebrew_terms or [hebrew_term]

    # ========================================
    # STEP 2: UNDERSTAND
    # ========================================
    logger.info("STEP 2: UNDERSTAND")
    try:
        from step_two_understand import understand

        strategy = await understand(
            hebrew_term=hebrew_term,
            original_query=query,
            step1_result=step1_result,
        )
    except TypeError:
        logger.warning(
            "Step 2 doesn't support step1_result parameter, using legacy call"
        )
        from step_two_understand import understand

        strategy = await understand(hebrew_term, query)
    except Exception as exc:  # noqa: BLE001
        logger.error("Step 2 error: %s", exc, exc_info=True)
        strategy = fallback_step2(hebrew_term)

    logger.info(
        "Step 2 complete: type=%s, primary=%s",
        enum_value(strategy.query_type),
        strategy.primary_source,
    )
    if getattr(step1_result, "is_mixed_query", False):
        logger.info(
            "  Comparison terms: %s",
            getattr(strategy, "comparison_terms", []),
        )

    # ========================================
    # STEP 3: SEARCH
    # ========================================
    logger.info("STEP 3: SEARCH")
    try:
        from step_three_search import search

        search_result = await search(strategy, query, hebrew_term)
    except Exception as exc:  # noqa: BLE001
        logger.error("Step 3 error: %s", exc, exc_info=True)
        search_result = fallback_step3(strategy, query, hebrew_term)

    logger.info("Step 3 complete: %s sources", search_result.total_sources)

    # ========================================
    # BUILD FINAL RESULT
    # ========================================
    logger.info("PIPELINE COMPLETE")

    sources_dict = [to_serializable(source) for source in search_result.sources]
    sources_by_level_dict = {
        level: [to_serializable(source) for source in sources]
        for level, sources in search_result.sources_by_level.items()
    }
    related_sugyos_dict = [
        to_serializable(sugya) for sugya in search_result.related_sugyos
    ]

    sources_by_term_dict: Dict[str, List[Dict[str, Any]]] = {}
    if getattr(search_result, "sources_by_term", None):
        sources_by_term_dict = {
            term: [to_serializable(source) for source in sources]
            for term, sources in search_result.sources_by_term.items()
        }

    result = MareiMekomosResult(
        original_query=query,
        hebrew_term=hebrew_term,
        hebrew_terms=hebrew_terms,
        transliteration_confidence=enum_value(step1_result.confidence),
        transliteration_method=step1_result.method,
        is_mixed_query=step1_result.is_mixed_query,
        query_type=enum_value(strategy.query_type),
        primary_source=strategy.primary_source,
        primary_source_he=strategy.primary_source_he,
        primary_sources=getattr(strategy, "primary_sources", []),
        interpretation=strategy.reasoning,
        sources=sources_dict,
        sources_by_level=sources_by_level_dict,
        sources_by_term=sources_by_term_dict,
        related_sugyos=related_sugyos_dict,
        total_sources=search_result.total_sources,
        levels_included=search_result.levels_included,
        success=True,
        confidence=enum_value(search_result.confidence),
        needs_clarification=search_result.needs_clarification,
        clarification_prompt=search_result.clarification_prompt,
        message=f"Found {search_result.total_sources} sources for {hebrew_term}",
    )

    logger.info("  Hebrew: %s", result.hebrew_term)
    if result.hebrew_terms and len(result.hebrew_terms) > 1:
        logger.info("  All terms: %s", result.hebrew_terms)
    logger.info("  Primary: %s", result.primary_source)
    logger.info("  Sources: %s", result.total_sources)
    logger.info("  Levels: %s", result.levels_included)

    return result


# ==========================================
#  QUICK TEST
# ==========================================

async def quick_test(query: str) -> MareiMekomosResult:
    """Run a quick test of the full pipeline."""
    print(f"\n{'='*80}")
    print(f"TESTING: '{query}'")
    print(f"{'='*80}\n")

    result = await search_sources(query)

    print(f"\n{'='*80}")
    print("RESULT SUMMARY")
    print(f"{'='*80}")
    print(f"  Hebrew: {result.hebrew_term}")
    if result.hebrew_terms and len(result.hebrew_terms) > 1:
        print(f"  All terms: {result.hebrew_terms}")
    print(f"  Is mixed query: {result.is_mixed_query}")
    print(f"  Type: {result.query_type}")
    print(f"  Primary: {result.primary_source}")
    print(f"  Sources: {result.total_sources}")
    print(f"  Levels: {result.levels_included}")
    print(f"  Confidence: {result.confidence}")

    if result.sources:
        print("\n  Sources found:")
        for source in result.sources[:5]:
            ref = source.get("ref", "?") if isinstance(source, dict) else source.ref
            level = (
                source.get("level", "?") if isinstance(source, dict) else source.level
            )
            print(f"    - {ref} ({level})")

    if result.related_sugyos:
        print("\n  Related sugyos:")
        for rel in result.related_sugyos[:3]:
            ref = rel.get("ref", "?") if isinstance(rel, dict) else rel.ref
            conn = rel.get("connection", "?") if isinstance(rel, dict) else rel.connection
            print(f"    - {ref}: {conn}")

    if result.needs_clarification:
        print(f"\n  Needs clarification: {result.clarification_prompt}")

    return result


# ==========================================
#  MAIN
# ==========================================

async def main() -> None:
    """Main entry point for testing."""
    print("=" * 80)
    print("MAREI MEKOMOS V7 - FULL PIPELINE TEST (V4 Mixed Query Support)")
    print("=" * 80)
    print()
    print("Pipeline:")
    print("  1. DECIPHER: transliteration -> Hebrew (with mixed query detection)")
    print("  2. UNDERSTAND: Hebrew -> Intent + Strategy (with Claude verification)")
    print("  3. SEARCH: Strategy -> Organized Sources")
    print()

    test_queries = [
        "chezkas haguf",
        "migu",
        "what is chezkas haguf",
        "what is stronger, chezkas haguf or chezkas mamon",
        "explain migu",
    ]

    for query in test_queries:
        await quick_test(query)
        print()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )

    asyncio.run(main())
