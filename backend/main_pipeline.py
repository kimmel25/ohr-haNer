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
from typing import Optional
from dataclasses import asdict

logger = logging.getLogger(__name__)


# ==============================================================================
#  MAIN PIPELINE
# ==============================================================================

async def search_sources(query: str) -> dict:
    """
    Main entry point for Ohr Haner.
    
    Takes a user query and returns organized Torah sources.
    
    Args:
        query: User's input (transliteration, Hebrew, or mixed)
    
    Returns:
        Dict with sources, analysis, and any clarification needed
    """
    logger.info("=" * 80)
    logger.info("OHR HANER - TORAH SOURCE FINDER")
    logger.info("=" * 80)
    logger.info(f"Query: '{query}'")
    
    result = {
        "original_query": query,
        "success": False,
        "hebrew_terms": [],
        "sources": [],
        "sources_by_level": {},
        "total_sources": 0,
        "needs_clarification": False,
        "clarification_question": None,
        "clarification_options": [],
        "search_description": "",
        "message": "",
    }
    
    # ========================================
    # STEP 1: DECIPHER
    # ========================================
    logger.info("\n" + ">" * 60)
    logger.info("STEP 1: DECIPHER")
    logger.info(">" * 60)
    
    try:
        from step_one_decipher import decipher
        step1_result = await decipher(query)
    except ImportError as e:
        logger.error(f"Step 1 import error: {e}")
        # Try to handle Hebrew directly
        step1_result = _fallback_decipher(query)
    except Exception as e:
        logger.error(f"Step 1 error: {e}")
        result["message"] = "Could not process your query. Please try again."
        return result
    
    # Check if Step 1 succeeded
    if not step1_result.success and not step1_result.hebrew_term:
        logger.warning("Step 1 failed - no Hebrew terms identified")
        result["message"] = step1_result.message or "Could not identify Hebrew terms in your query."
        result["needs_clarification"] = True
        result["clarification_question"] = "What Hebrew topic are you looking for?"
        return result
    
    hebrew_terms = step1_result.hebrew_terms or [step1_result.hebrew_term]
    result["hebrew_terms"] = hebrew_terms
    
    logger.info(f"Step 1 complete: {hebrew_terms}")
    
    # ========================================
    # STEP 2: UNDERSTAND
    # ========================================
    logger.info("\n" + ">" * 60)
    logger.info("STEP 2: UNDERSTAND")
    logger.info(">" * 60)
    
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
        result["message"] = "Error analyzing your query."
        return result
    
    logger.info(f"Step 2 complete: {analysis.query_type.value}, confidence={analysis.confidence.value}")
    
    # Check if clarification needed
    if analysis.needs_clarification:
        logger.info(f"Clarification needed: {analysis.clarification_question}")
        result["needs_clarification"] = True
        result["clarification_question"] = analysis.clarification_question
        result["clarification_options"] = analysis.clarification_options
        result["message"] = "I need a bit more information to help you better."
        # Still continue to search with what we have...
    
    # ========================================
    # STEP 3: SEARCH
    # ========================================
    logger.info("\n" + ">" * 60)
    logger.info("STEP 3: SEARCH")
    logger.info(">" * 60)
    
    try:
        from step_three_search import search
        search_result = await search(analysis)
    except Exception as e:
        logger.error(f"Step 3 error: {e}")
        import traceback
        traceback.print_exc()
        result["message"] = "Error searching for sources."
        return result
    
    logger.info(f"Step 3 complete: {search_result.total_sources} sources")
    
    # ========================================
    # BUILD FINAL RESULT
    # ========================================
    result["success"] = True
    result["sources"] = [_source_to_dict(s) for s in search_result.sources]
    result["sources_by_level"] = {
        level: [_source_to_dict(s) for s in sources]
        for level, sources in search_result.sources_by_level.items()
    }
    result["total_sources"] = search_result.total_sources
    result["levels_found"] = search_result.levels_found
    result["search_description"] = search_result.search_description
    result["confidence"] = analysis.confidence.value
    result["query_analysis"] = analysis.to_dict()
    
    if not result["needs_clarification"]:
        result["message"] = f"Found {search_result.total_sources} sources for {', '.join(hebrew_terms)}"
    
    logger.info("=" * 80)
    logger.info("PIPELINE COMPLETE")
    logger.info(f"  Sources: {result['total_sources']}")
    logger.info(f"  Levels: {result.get('levels_found', [])}")
    logger.info("=" * 80)
    
    return result


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
        print(f"  Success: {result['success']}")
        print(f"  Hebrew terms: {result['hebrew_terms']}")
        print(f"  Total sources: {result['total_sources']}")
        print(f"  Levels: {result.get('levels_found', [])}")
        
        if result.get('needs_clarification'):
            print(f"\n  ⚠️ Needs clarification: {result['clarification_question']}")
            if result.get('clarification_options'):
                print(f"  Options: {result['clarification_options']}")
        
        if result['sources']:
            print(f"\n  First 3 sources:")
            for source in result['sources'][:3]:
                print(f"    • {source['ref']} ({source['level_hebrew']})")
        
        print(f"\n  Message: {result['message']}")


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