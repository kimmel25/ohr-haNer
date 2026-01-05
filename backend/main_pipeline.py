"""
Ohr Haner - Main Pipeline
=========================

The complete flow:
1. DECIPHER: User query → Hebrew terms
2. UNDERSTAND: Claude analyzes → QueryAnalysis
3. SEARCH: Sefaria search → Organized sources

Philosophy (from Architecture):
- "Getting into the user's head is most important"
- "We aren't scared to show our own lack of understanding"
- "Better to ask than get it wrong"
"""

import asyncio
import logging

from models import MareiMekomosResult, ConfidenceLevel, QueryType, SourceLevel

logger = logging.getLogger(__name__)

_QUERY_TYPE_MAP = {
    "topic": QueryType.SUGYA_CONCEPT,
    "question": QueryType.AMBIGUOUS,
    "source_request": QueryType.UNKNOWN,
    "comparison": QueryType.COMPARISON,
    "shittah": QueryType.AMBIGUOUS,
    "sugya": QueryType.SUGYA_CONCEPT,
    "pasuk": QueryType.PASUK,
    "halacha": QueryType.HALACHA_TERM,
    "machlokes": QueryType.COMPARISON,
    "machloket": QueryType.COMPARISON,
    "unknown": QueryType.UNKNOWN,
}

_SOURCE_LEVEL_MAP = {
    "pasuk": SourceLevel.CHUMASH,
    "targum": SourceLevel.OTHER,
    "mishna": SourceLevel.MISHNA,
    "tosefta": SourceLevel.OTHER,
    "gemara_bavli": SourceLevel.GEMARA,
    "gemara_yerushalmi": SourceLevel.GEMARA,
    "midrash": SourceLevel.OTHER,
    "rashi": SourceLevel.RASHI,
    "tosfos": SourceLevel.TOSFOS,
    "rishonim": SourceLevel.RISHONIM,
    "rambam": SourceLevel.RAMBAM,
    "tur": SourceLevel.TUR,
    "shulchan_aruch": SourceLevel.SHULCHAN_ARUCH,
    "nosei_keilim": SourceLevel.NOSEI_KEILIM,
    "acharonim": SourceLevel.ACHARONIM,
}


def _enum_value(value):
    if value is None:
        return ""
    if hasattr(value, "value"):
        return value.value
    return value


def _map_query_type(value) -> QueryType:
    raw = str(_enum_value(value)).lower()
    return _QUERY_TYPE_MAP.get(raw, QueryType.UNKNOWN)


def _map_source_level(value) -> SourceLevel:
    raw = str(_enum_value(value)).lower()
    return _SOURCE_LEVEL_MAP.get(raw, SourceLevel.OTHER)


def _get_attr(source, key, default=None):
    if isinstance(source, dict):
        return source.get(key, default)
    return getattr(source, key, default)


def _serialize_source(source, truncate=500) -> dict:
    hebrew_text = _get_attr(source, "hebrew_text", "") or ""
    english_text = _get_attr(source, "english_text", "") or ""
    relevance_note = _get_attr(source, "relevance_description", "") or _get_attr(
        source, "relevance_note", ""
    )

    return {
        "ref": _get_attr(source, "ref"),
        "he_ref": _get_attr(source, "he_ref"),
        "level": _map_source_level(_get_attr(source, "level")),
        "level_hebrew": _get_attr(source, "level_hebrew", ""),
        "hebrew_text": hebrew_text[:truncate],
        "english_text": english_text[:truncate],
        "author": _get_attr(source, "author", ""),
        "categories": _get_attr(source, "categories", []) or [],
        "relevance_note": relevance_note,
        "is_primary": bool(_get_attr(source, "is_primary", False)),
        "related_term": _get_attr(source, "related_term"),
    }


def _build_failure_result(query: str, step1_result, message: str) -> MareiMekomosResult:
    return MareiMekomosResult(
        original_query=query,
        hebrew_term=getattr(step1_result, "hebrew_term", None),
        hebrew_terms=getattr(step1_result, "hebrew_terms", []),
        transliteration_confidence=getattr(step1_result, "confidence", ConfidenceLevel.LOW),
        transliteration_method=getattr(step1_result, "method", "failed"),
        is_mixed_query=bool(getattr(step1_result, "is_mixed_query", False)),
        query_type=QueryType.UNKNOWN,
        primary_source=None,
        primary_source_he=None,
        primary_sources=[],
        interpretation="",
        sources=[],
        sources_by_level={},
        sources_by_term={},
        related_sugyos=[],
        total_sources=0,
        levels_included=[],
        success=False,
        confidence=ConfidenceLevel.LOW,
        needs_clarification=False,
        clarification_prompt=None,
        message=message,
    )


# ==============================================================================
#  MAIN PIPELINE
# ==============================================================================

async def search_sources(query: str) -> MareiMekomosResult:
    """
    Run the full 3-step pipeline.
    
    Takes a user query and returns organized Torah sources.
    
    Args:
        query: User's input (transliteration, Hebrew, or mixed)
    
    Returns:
        MareiMekomosResult with sources, analysis, and any clarification needed
    """
    logger.info("=" * 80)
    logger.info("FULL PIPELINE STARTING")
    logger.info("=" * 80)
    logger.info(f"Query: '{query}'")
    
    # Step 1: Decipher
    logger.info("\n--- STEP 1: DECIPHER ---")
    try:
        from step_one_decipher import decipher
        step1_result = await decipher(query)
    except ImportError as e:
        logger.error(f"Step 1 import error: {e}")
        # Try to handle Hebrew directly
        step1_result = _fallback_decipher(query)
    except Exception as e:
        logger.error(f"Step 1 error: {e}")
        return _build_failure_result(query, None, "Could not process your query. Please try again.")
    
    logger.info(f"Step 1 complete:")
    logger.info(f"  Success: {step1_result.success}")
    logger.info(f"  Hebrew term: {step1_result.hebrew_term}")
    logger.info(f"  All terms: {step1_result.hebrew_terms}")
    logger.info(f"  Method: {step1_result.method}")
    
    if not step1_result.success or not step1_result.hebrew_terms:
        logger.warning("Step 1 failed - cannot continue")
        return _build_failure_result(query, step1_result, "Could not transliterate query")
    
    hebrew_terms = step1_result.hebrew_terms
    
    # Step 2: Understand
    logger.info("\n--- STEP 2: UNDERSTAND ---")
    try:
        from step_two_understand import understand
        analysis = await understand(
            hebrew_terms=hebrew_terms,
            query=query,
            decipher_result=step1_result
        )
    except Exception as e:
        logger.error(f"Step 2 error: {e}")
        import traceback
        traceback.print_exc()
        return _build_failure_result(query, step1_result, "Error analyzing your query.")
    logger.info(f"Step 2 complete:")
    logger.info(f"  Query type: {analysis.query_type.value}")
    logger.info(f"  Search topics (INYAN): {analysis.search_topics_hebrew}")
    logger.info(f"  Primary refs: {getattr(analysis, 'primary_refs', [])}")
    logger.info(f"  Contrast refs: {getattr(analysis, 'contrast_refs', [])}")
    logger.info(f"  Target sources: {getattr(analysis, 'target_sources', [])}")
    logger.info(f"  Target authors: {getattr(analysis, 'target_authors', [])}")
    
    # Check if clarification needed
    if analysis.needs_clarification:
        logger.info(f"Clarification needed: {analysis.clarification_question}")
        clarification_prompt = analysis.clarification_question
        clarification_options = analysis.clarification_options
    else:
        clarification_prompt = None
        clarification_options = []
        # Still continue to search with what we have...
    
    # Step 3: Search
    logger.info("\n--- STEP 3: SEARCH ---")
    try:
        from step_three_search import search
        search_result = await search(analysis)
    except Exception as e:
        logger.error(f"Step 3 error: {e}")
        import traceback
        traceback.print_exc()
        return _build_failure_result(query, step1_result, "Error searching for sources.")
    
    logger.info(f"Step 3 complete:")
    logger.info(f"  Total sources: {search_result.total_sources}")
    logger.info(f"  Main sugyos: {getattr(search_result, 'discovered_dapim', [])}")
    levels_found = list(getattr(search_result, "sources_by_level", {}) or {})
    logger.info(f"  Levels: {levels_found}")
    
    logger.info("\n" + "=" * 80)
    logger.info("FULL PIPELINE COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Final result: {search_result.total_sources} sources across {len(levels_found)} levels")

    sources_list = (
        getattr(search_result, "all_sources", None)
        or getattr(search_result, "sources", None)
        or []
    )
    if not sources_list:
        sources_list = (
            list(getattr(search_result, "foundation_stones", []) or [])
            + list(getattr(search_result, "commentary_sources", []) or [])
            + list(getattr(search_result, "earlier_sources", []) or [])
        )

    sources_payload = [_serialize_source(source) for source in sources_list]
    sources_by_level = {}
    for level, sources in (getattr(search_result, "sources_by_level", {}) or {}).items():
        sources_by_level[level] = [_serialize_source(source) for source in sources]

    needs_clarification = bool(
        analysis.needs_clarification
        or getattr(search_result, "needs_clarification", False)
    )
    clarification_prompt = clarification_prompt or getattr(
        search_result, "clarification_question", None
    )

    # Convert to API response format
    return MareiMekomosResult(
        original_query=query,
        hebrew_term=step1_result.hebrew_term,
        hebrew_terms=step1_result.hebrew_terms,
        transliteration_confidence=step1_result.confidence,
        transliteration_method=step1_result.method,
        is_mixed_query=bool(getattr(step1_result, "is_mixed_query", False)),
        query_type=_map_query_type(analysis.query_type),
        primary_source=(analysis.primary_refs[0] if getattr(analysis, "primary_refs", []) else None),
        primary_source_he=None,
        primary_sources=list(getattr(analysis, "primary_refs", []) or []),
        interpretation=(getattr(analysis, "reasoning", "") or getattr(analysis, "inyan_description", "")),
        sources=sources_payload,
        sources_by_level=sources_by_level,
        sources_by_term={},
        related_sugyos=[],
        total_sources=search_result.total_sources,
        levels_included=levels_found,
        success=True,
        confidence=search_result.confidence,
        needs_clarification=needs_clarification,
        clarification_prompt=clarification_prompt,
        message=getattr(search_result, "search_description", ""),
        clarification_options=clarification_options,
    )


def _source_to_dict(source) -> dict:
    """Convert a Source dataclass to dict."""
    return {
        "ref": source.ref,
        "he_ref": source.he_ref,
        "level": source.level,
        "level_hebrew": source.level_hebrew,
        "hebrew_text": source.hebrew_text,
        "english_text": source.english_text,
        "author": source.author,
        "relevance_description": source.relevance_description,
        "is_primary": source.is_primary,
    }


def _fallback_decipher(query: str):
    """Fallback when Step 1 module not available."""
    from dataclasses import dataclass
    from models import ConfidenceLevel
    
    # Check if query has Hebrew characters
    hebrew_chars = sum(1 for c in query if '\u0590' <= c <= '\u05FF')
    total_chars = sum(1 for c in query if c.isalpha())
    
    @dataclass
    class FallbackResult:
        success: bool
        hebrew_term: str
        hebrew_terms: list
        confidence: ConfidenceLevel
        method: str
        message: str
        is_mixed_query: bool = False
        original_query: str = ""
    
    if total_chars > 0 and hebrew_chars / total_chars > 0.5:
        # Query is mostly Hebrew
        return FallbackResult(
            success=True,
            hebrew_term=query,
            hebrew_terms=[query],
            confidence=ConfidenceLevel.HIGH,
            method="passthrough",
            message="Query is Hebrew",
            original_query=query
        )
    
    return FallbackResult(
        success=False,
        hebrew_term=None,
        hebrew_terms=[],
        confidence=ConfidenceLevel.LOW,
        method="failed",
        message="Could not identify Hebrew terms",
        original_query=query
    )


# ==============================================================================
#  QUICK TEST
# ==============================================================================

async def test_pipeline():
    """Test the full pipeline."""
    
    print("=" * 80)
    print("OHR HANER - PIPELINE TEST")
    print("=" * 80)
    
    test_queries = [
        "bittul chometz",
        "what is the Ran's shittah on bittul chometz",
        "chezkas haguf",
        "machloket rashi tosfos pesachim",
    ]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Testing: '{query}'")
        print("=" * 60)
        
        result = await search_sources(query)
        
        print(f"\nResult:")
        print(f"  Success: {result.success}")
        print(f"  Hebrew terms: {result.hebrew_terms}")
        print(f"  Total sources: {result.total_sources}")
        print(f"  Levels: {result.levels_included}")
        
        if result.needs_clarification:
            print(f"\n  ⚠️ Needs clarification: {result.clarification_prompt}")
            if result.clarification_options:
                print(f"  Options: {result.clarification_options}")
        
        if result.sources:
            print(f"\n  First 3 sources:")
            for source in result.sources[:3]:
                print(f"    • {source.ref} ({source.level_hebrew})")
        
        print(f"\n  Message: {result.message}")


# ==============================================================================
#  MAIN
# ==============================================================================

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    asyncio.run(test_pipeline())
