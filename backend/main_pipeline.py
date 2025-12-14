"""
Marei Mekomos V7 - Main Pipeline (V4 Mixed Query Support)
=========================================================

The complete flow:
1. DECIPHER: transliteration → Hebrew (Step 1)
2. UNDERSTAND: Hebrew → Intent + Strategy (Step 2)
3. SEARCH: Strategy → Organized Sources (Step 3)

V4 UPDATE: 
- Pass step1_result to step2 for mixed query context
- Handle multiple Hebrew terms
- Double defense: Step 1 extracts, Step 2 verifies
"""

import sys
from pathlib import Path

# Add backend/ to path for local imports
sys.path.insert(0, str(Path(__file__).parent))

import asyncio
import logging
from dataclasses import asdict, is_dataclass
from enum import Enum

# Import Pydantic models
from models import MareiMekomosResult, DecipherResult, ConfidenceLevel

logger = logging.getLogger(__name__)


# ==========================================
#  MAIN PIPELINE
# ==========================================

async def search_sources(query: str) -> MareiMekomosResult:
    """
    Main entry point for Marei Mekomos.
    
    Takes a user query (transliteration or Hebrew) and returns
    organized Torah sources.
    
    V4: Now handles mixed queries with multiple Hebrew terms.
    
    Args:
        query: User's input (e.g., "chezkas haguf" or "what is chezkas haguf")
    
    Returns:
        MareiMekomosResult with all sources and metadata
    """
    logger.info("=" * 100)
    logger.info("MAREI MEKOMOS V7 - FULL PIPELINE (V4 Mixed Query Support)")
    logger.info("=" * 100)
    logger.info(f"Query: '{query}'")
    
    # ========================================
    # STEP 1: DECIPHER
    # ========================================
    logger.info("\n" + ">" * 80)
    logger.info("STEP 1: DECIPHER")
    logger.info(">" * 80)
    
    try:
        from step_one_decipher import decipher
        step1_result = await decipher(query)
    except ImportError:
        logger.warning("step_one_decipher not found, checking if query is Hebrew")
        step1_result = _fallback_step1(query)
    
    # Helper to safely extract enum values (handles both enum and string)
    def get_enum_value(val):
        return val.value if hasattr(val, 'value') else val

    # Log Step 1 results
    if step1_result.is_mixed_query:
        logger.info(f"Step 1 detected MIXED QUERY")
        logger.info(f"  Extracted terms: {step1_result.hebrew_terms}")
        logger.info(f"  Extraction confident: {step1_result.extraction_confident}")
    else:
        logger.info(f"Step 1 complete: '{query}' → '{step1_result.hebrew_term}'")

    # Step 1 failed - can't proceed
    if not step1_result.success and not step1_result.hebrew_term:
        logger.warning("Step 1 failed - returning early")
        return MareiMekomosResult(
            original_query=query,
            hebrew_term=None,
            hebrew_terms=[],
            transliteration_confidence=get_enum_value(step1_result.confidence),
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
            confidence=get_enum_value(step1_result.confidence),
            needs_clarification=True,
            clarification_prompt=step1_result.message or "Please try a different spelling",
            message="Could not understand the query"
        )

    # Get primary Hebrew term (for backwards compatibility)
    hebrew_term = step1_result.hebrew_term or query
    hebrew_terms = step1_result.hebrew_terms or [hebrew_term]
    
    # ========================================
    # STEP 2: UNDERSTAND
    # ========================================
    logger.info("\n" + ">" * 80)
    logger.info("STEP 2: UNDERSTAND")
    logger.info(">" * 80)
    
    try:
        from step_two_understand import understand
        # V4: Pass step1_result for mixed query context
        strategy = await understand(
            hebrew_term=hebrew_term,
            original_query=query,
            step1_result=step1_result  # NEW: Pass full Step 1 result
        )
    except TypeError:
        # Fallback if step2 doesn't support step1_result parameter yet
        logger.warning("Step 2 doesn't support step1_result parameter, using legacy call")
        from step_two_understand import understand
        strategy = await understand(hebrew_term, query)
    except Exception as e:
        logger.error(f"Step 2 error: {e}", exc_info=True)
        strategy = _fallback_step2(hebrew_term)
        
    logger.info(f"Step 2 complete: type={get_enum_value(strategy.query_type)}, primary={strategy.primary_source}")
    if step1_result.is_mixed_query:
        logger.info(f"  Comparison terms: {getattr(strategy, 'comparison_terms', [])}")
    
    # ========================================
    # STEP 3: SEARCH
    # ========================================
    logger.info("\n" + ">" * 80)
    logger.info("STEP 3: SEARCH")
    logger.info(">" * 80)
    
    try:
        from step_three_search import search
        search_result = await search(strategy, query, hebrew_term)
    except Exception as e:
        logger.error(f"Step 3 error: {e}", exc_info=True)
        search_result = _fallback_step3(strategy, query, hebrew_term)
    
    logger.info(f"Step 3 complete: {search_result.total_sources} sources")
    
    # ========================================
    # BUILD FINAL RESULT
    # ========================================
    logger.info("\n" + "=" * 100)
    logger.info("PIPELINE COMPLETE")
    logger.info("=" * 100)

    # Convert nested models (dataclasses or Pydantic) to dicts for proper validation
    def enum_dict_factory(items):
        """Convert enums to their values when creating dict from dataclass."""
        result = {}
        for key, value in items:
            if isinstance(value, Enum):
                result[key] = value.value
            else:
                result[key] = value
        return result

    def to_dict(obj):
        """Convert dataclass or Pydantic model to dict."""
        if is_dataclass(obj):
            return asdict(obj, dict_factory=enum_dict_factory)
        elif hasattr(obj, 'model_dump'):
            return obj.model_dump()
        return obj

    sources_dict = [to_dict(s) for s in search_result.sources]
    sources_by_level_dict = {
        level: [to_dict(s) for s in sources]
        for level, sources in search_result.sources_by_level.items()
    }
    related_sugyos_dict = [to_dict(s) for s in search_result.related_sugyos]
    
    # V4: Handle sources_by_term if present
    sources_by_term_dict = {}
    if hasattr(search_result, 'sources_by_term') and search_result.sources_by_term:
        sources_by_term_dict = {
            term: [to_dict(s) for s in sources]
            for term, sources in search_result.sources_by_term.items()
        }

    result = MareiMekomosResult(
        original_query=query,
        hebrew_term=hebrew_term,
        hebrew_terms=hebrew_terms,
        transliteration_confidence=get_enum_value(step1_result.confidence),
        transliteration_method=step1_result.method,
        is_mixed_query=step1_result.is_mixed_query,
        query_type=get_enum_value(strategy.query_type),
        primary_source=strategy.primary_source,
        primary_source_he=strategy.primary_source_he,
        primary_sources=getattr(strategy, 'primary_sources', []),
        interpretation=strategy.reasoning,
        sources=sources_dict,
        sources_by_level=sources_by_level_dict,
        sources_by_term=sources_by_term_dict,
        related_sugyos=related_sugyos_dict,
        total_sources=search_result.total_sources,
        levels_included=search_result.levels_included,
        success=True,
        confidence=get_enum_value(search_result.confidence),
        needs_clarification=search_result.needs_clarification,
        clarification_prompt=search_result.clarification_prompt,
        message=f"Found {search_result.total_sources} sources for {hebrew_term}"
    )
    
    logger.info(f"  Hebrew: {result.hebrew_term}")
    if result.hebrew_terms and len(result.hebrew_terms) > 1:
        logger.info(f"  All terms: {result.hebrew_terms}")
    logger.info(f"  Primary: {result.primary_source}")
    logger.info(f"  Sources: {result.total_sources}")
    logger.info(f"  Levels: {result.levels_included}")
    
    return result


# ==========================================
#  FALLBACK FUNCTIONS
# ==========================================

def _fallback_step1(query: str) -> DecipherResult:
    """Fallback when Step 1 module not available."""
    import re

    # Check if query is already Hebrew
    hebrew_chars = sum(1 for c in query if '\u0590' <= c <= '\u05FF')
    total_chars = sum(1 for c in query if c.isalpha())

    if total_chars > 0 and hebrew_chars / total_chars > 0.5:
        # Already Hebrew
        return DecipherResult(
            success=True,
            hebrew_term=query,
            hebrew_terms=[query],
            confidence=ConfidenceLevel.HIGH,
            method="passthrough",
            is_mixed_query=False,
            original_query=query,
            extraction_confident=True,
            message="Query is already in Hebrew"
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
        message="Step 1 module not available and query is not Hebrew"
    )


def _fallback_step2(hebrew_term: str):
    """Fallback when Step 2 fails."""
    from step_two_understand import SearchStrategy, QueryType, FetchStrategy
    
    return SearchStrategy(
        query_type=QueryType.UNKNOWN,
        primary_source=None,
        reasoning="Could not analyze query (Step 2 error)",
        fetch_strategy=FetchStrategy.TRICKLE_UP,
        depth="basic",
        confidence="low",
        clarification_prompt="What specific aspect of this topic are you looking for?"
    )


def _fallback_step3(strategy, query: str, hebrew_term: str):
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
        clarification_prompt="We had trouble fetching sources. Could you try again?"
    )


# ==========================================
#  QUICK TEST
# ==========================================

async def quick_test(query: str):
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
        print(f"\n  Sources found:")
        for source in result.sources[:5]:
            ref = source.ref if hasattr(source, 'ref') else source.get('ref', '?')
            level = source.level.name if hasattr(source, 'level') else source.get('level', '?')
            print(f"    - {ref} ({level})")
    
    if result.related_sugyos:
        print(f"\n  Related sugyos:")
        for rel in result.related_sugyos[:3]:
            ref = rel.ref if hasattr(rel, 'ref') else rel.get('ref', '?')
            conn = rel.connection if hasattr(rel, 'connection') else rel.get('connection', '?')
            print(f"    - {ref}: {conn}")
    
    if result.needs_clarification:
        print(f"\n  ⚠️ Needs clarification: {result.clarification_prompt}")
    
    return result


# ==========================================
#  MAIN
# ==========================================

async def main():
    """Main entry point for testing."""
    
    print("=" * 100)
    print("MAREI MEKOMOS V7 - FULL PIPELINE TEST (V4 Mixed Query Support)")
    print("=" * 100)
    print()
    print("Pipeline:")
    print("  1. DECIPHER: transliteration → Hebrew (with mixed query detection)")
    print("  2. UNDERSTAND: Hebrew → Intent + Strategy (with Claude verification)")
    print("  3. SEARCH: Strategy → Organized Sources")
    print()
    
    # Test queries - including V4 mixed queries
    test_queries = [
        # Pure transliteration (original tests)
        "chezkas haguf",
        "migu",
        
        # V4: Mixed queries
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
        format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    asyncio.run(main())