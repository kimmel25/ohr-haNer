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

from models import MareiMekomosResult, ConfidenceLevel

logger = logging.getLogger(__name__)


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
        Dict with sources, analysis, and any clarification needed
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
        result["message"] = "Could not process your query. Please try again."
        return result
    
    logger.info(f"Step 1 complete:")
    logger.info(f"  Success: {step1_result.success}")
    logger.info(f"  Hebrew term: {step1_result.hebrew_term}")
    logger.info(f"  All terms: {step1_result.hebrew_terms}")
    logger.info(f"  Method: {step1_result.method}")
    
    if not step1_result.success or not step1_result.hebrew_terms:
        logger.warning("Step 1 failed - cannot continue")
        return MareiMekomosResult(
            success=False,
            hebrew_terms=[],
            sources=[],
            total_sources=0,
            confidence=ConfidenceLevel.LOW,
            message="Could not transliterate query"
        )
    
    hebrew_terms = step1_result.hebrew_terms
    result["hebrew_terms"] = hebrew_terms
    
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
        result["message"] = "Error analyzing your query."
        return result
    logger.info(f"Step 2 complete:")
    logger.info(f"  Query type: {analysis.query_type.value}")
    logger.info(f"  Search topics (INYAN): {analysis.search_topics_hebrew}")
    logger.info(f"  Target masechtos: {analysis.target_masechtos}")
    logger.info(f"  Target authors: {analysis.target_authors}")
    logger.info(f"  Search method: {analysis.search_method.value}")
    
    # Check if clarification needed
    if analysis.needs_clarification:
        logger.info(f"Clarification needed: {analysis.clarification_question}")
        result["needs_clarification"] = True
        result["clarification_question"] = analysis.clarification_question
        result["clarification_options"] = analysis.clarification_options
        result["message"] = "I need a bit more information to help you better."
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
        result["message"] = "Error searching for sources."
        return result
    
    logger.info(f"Step 3 complete:")
    logger.info(f"  Total sources: {search_result.total_sources}")
    logger.info(f"  Base refs: {search_result.base_refs_found}")
    logger.info(f"  Levels: {search_result.levels_found}")
    
    logger.info("\n" + "=" * 80)
    logger.info("FULL PIPELINE COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Final result: {search_result.total_sources} sources across {len(search_result.levels_found)} levels")
    
    # Convert to API response format
    return MareiMekomosResult(
        success=True,
        hebrew_terms=step1_result.hebrew_terms,
        sources=[{
            'ref': s.ref,
            'he_ref': s.he_ref,
            'level': s.level,
            'level_hebrew': s.level_hebrew,
            'hebrew_text': s.hebrew_text[:500],  # Truncate for response
            'author': s.author,
            'is_primary': s.is_primary,
        } for s in search_result.sources],
        sources_by_level={
            level: [{
                'ref': s.ref,
                'he_ref': s.he_ref,
                'hebrew_text': s.hebrew_text[:500],
            } for s in sources]
            for level, sources in search_result.sources_by_level.items()
        },
        total_sources=search_result.total_sources,
        levels_found=search_result.levels_found,
        confidence=search_result.confidence,
        message=search_result.search_description
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