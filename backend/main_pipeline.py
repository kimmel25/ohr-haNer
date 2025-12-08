"""
Marei Mekomos V7 - Main Pipeline
=================================

The complete flow:
1. DECIPHER: transliteration → Hebrew (Step 1)
2. UNDERSTAND: Hebrew → Intent + Strategy (Step 2)
3. SEARCH: Strategy → Organized Sources (Step 3)

This file orchestrates the entire process.
"""

import asyncio
import logging
from typing import Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# ==========================================
#  COMPLETE RESULT
# ==========================================

@dataclass
class MareiMekomosResult:
    """Complete result from the full pipeline."""
    
    # Input
    original_query: str
    
    # Step 1 results
    hebrew_term: Optional[str]
    transliteration_confidence: str
    transliteration_method: str
    
    # Step 2 results  
    query_type: str
    primary_source: Optional[str]
    primary_source_he: Optional[str]
    interpretation: str
    
    # Step 3 results (the actual sources)
    sources: list
    sources_by_level: dict
    related_sugyos: list
    total_sources: int
    levels_included: list
    
    # Overall status
    success: bool
    confidence: str
    needs_clarification: bool
    clarification_prompt: Optional[str]
    message: str
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON/API response."""
        return {
            "original_query": self.original_query,
            "hebrew_term": self.hebrew_term,
            "transliteration": {
                "confidence": self.transliteration_confidence,
                "method": self.transliteration_method
            },
            "interpretation": {
                "query_type": self.query_type,
                "primary_source": self.primary_source,
                "primary_source_he": self.primary_source_he,
                "reasoning": self.interpretation
            },
            "sources": [s.to_dict() if hasattr(s, 'to_dict') else s for s in self.sources],
            "sources_by_level": {
                level: [s.to_dict() if hasattr(s, 'to_dict') else s for s in sources]
                for level, sources in self.sources_by_level.items()
            },
            "related_sugyos": [
                s.to_dict() if hasattr(s, 'to_dict') else s 
                for s in self.related_sugyos
            ],
            "total_sources": self.total_sources,
            "levels_included": self.levels_included,
            "success": self.success,
            "confidence": self.confidence,
            "needs_clarification": self.needs_clarification,
            "clarification_prompt": self.clarification_prompt,
            "message": self.message
        }


# ==========================================
#  MAIN PIPELINE
# ==========================================

async def search_sources(query: str) -> MareiMekomosResult:
    """
    Main entry point for Marei Mekomos.
    
    Takes a user query (transliteration or Hebrew) and returns
    organized Torah sources.
    
    Args:
        query: User's input (e.g., "chezkas haguf" or "חזקת הגוף")
    
    Returns:
        MareiMekomosResult with all sources and metadata
    """
    logger.info("=" * 100)
    logger.info("MAREI MEKOMOS V7 - FULL PIPELINE")
    logger.info("=" * 100)
    logger.info(f"Query: '{query}'")
    
    # ========================================
    # STEP 1: DECIPHER
    # ========================================
    logger.info("\n" + ">" * 80)
    logger.info("STEP 1: DECIPHER")
    logger.info(">" * 80)
    
    try:
        # Try to import the existing Step 1 module
        # This should be the user's existing decipher code
        from step_one_decipher import decipher
        step1_result = await decipher(query)
    except ImportError:
        # Fallback: If Step 1 isn't available, check if query is already Hebrew
        logger.warning("step_one_decipher not found, checking if query is Hebrew")
        step1_result = _fallback_step1(query)
    
    if not step1_result.get("success") and not step1_result.get("hebrew_term"):
        # Step 1 failed - can't proceed
        logger.warning("Step 1 failed - returning early")
        return MareiMekomosResult(
            original_query=query,
            hebrew_term=None,
            transliteration_confidence="low",
            transliteration_method="failed",
            query_type="unknown",
            primary_source=None,
            primary_source_he=None,
            interpretation="Could not translate the query to Hebrew",
            sources=[],
            sources_by_level={},
            related_sugyos=[],
            total_sources=0,
            levels_included=[],
            success=False,
            confidence="low",
            needs_clarification=True,
            clarification_prompt=step1_result.get("message", "Please try a different spelling"),
            message="Could not understand the query"
        )
    
    hebrew_term = step1_result.get("hebrew_term", query)
    logger.info(f"Step 1 complete: '{query}' → '{hebrew_term}'")
    
    # ========================================
    # STEP 2: UNDERSTAND
    # ========================================
    logger.info("\n" + ">" * 80)
    logger.info("STEP 2: UNDERSTAND")
    logger.info(">" * 80)
    
    try:
        from step_two_understand import understand
        strategy = await understand(hebrew_term, query)
    except Exception as e:
        logger.error(f"Step 2 error: {e}", exc_info=True)
        strategy = _fallback_step2(hebrew_term)
    
    logger.info(f"Step 2 complete: type={strategy.query_type.value}, primary={strategy.primary_source}")
    
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
    
    result = MareiMekomosResult(
        original_query=query,
        hebrew_term=hebrew_term,
        transliteration_confidence=step1_result.get("confidence", "medium"),
        transliteration_method=step1_result.get("method", "unknown"),
        query_type=strategy.query_type.value,
        primary_source=strategy.primary_source,
        primary_source_he=strategy.primary_source_he,
        interpretation=strategy.reasoning,
        sources=search_result.sources,
        sources_by_level=search_result.sources_by_level,
        related_sugyos=search_result.related_sugyos,
        total_sources=search_result.total_sources,
        levels_included=search_result.levels_included,
        success=True,
        confidence=search_result.confidence,
        needs_clarification=search_result.needs_clarification,
        clarification_prompt=search_result.clarification_prompt,
        message=f"Found {search_result.total_sources} sources for {hebrew_term}"
    )
    
    logger.info(f"  Hebrew: {result.hebrew_term}")
    logger.info(f"  Primary: {result.primary_source}")
    logger.info(f"  Sources: {result.total_sources}")
    logger.info(f"  Levels: {result.levels_included}")
    
    return result


# ==========================================
#  FALLBACK FUNCTIONS
# ==========================================

def _fallback_step1(query: str) -> Dict:
    """Fallback when Step 1 module not available."""
    import re
    
    # Check if query is already Hebrew
    hebrew_chars = sum(1 for c in query if '\u0590' <= c <= '\u05FF')
    total_chars = sum(1 for c in query if c.isalpha())
    
    if total_chars > 0 and hebrew_chars / total_chars > 0.5:
        # Already Hebrew
        return {
            "success": True,
            "hebrew_term": query,
            "confidence": "high",
            "method": "passthrough"
        }
    
    return {
        "success": False,
        "hebrew_term": None,
        "confidence": "low",
        "method": "failed",
        "message": "Step 1 module not available and query is not Hebrew"
    }


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
        primary_source=strategy.primary_source,
        primary_source_he=strategy.primary_source_he,
        sources=[],
        sources_by_level={},
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
    print("MAREI MEKOMOS V7 - FULL PIPELINE TEST")
    print("=" * 100)
    print()
    print("Pipeline:")
    print("  1. DECIPHER: transliteration → Hebrew")
    print("  2. UNDERSTAND: Hebrew → Intent + Strategy")
    print("  3. SEARCH: Strategy → Organized Sources")
    print()
    
    # Test queries
    test_queries = [
        "chezkas haguf",       # Classic sugya concept
        "migu",                # Halachic term
        "bari vishma",         # Another concept
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
