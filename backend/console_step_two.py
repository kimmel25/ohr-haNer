"""
Console Tester for Step 2: UNDERSTAND
======================================

Interactive tool for manually testing Step 2 (query analysis).
Run this file directly to enter test mode.

Usage:
    python test_step_two_console.py

Commands:
    - Type any Hebrew term to see Claude's analysis
    - Type 'sefaria <term>' to see just the Sefaria data
    - Type 'mock <term>' to test with mock data (no API)
    - Type 'q' or 'quit' to exit
"""

import sys
import os
import asyncio
import json
import logging
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

# Set up logging
from logging_config import setup_logging
setup_logging(log_level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Check for API key early
if not os.environ.get("ANTHROPIC_API_KEY"):
    logger.warning("ANTHROPIC_API_KEY not set - full analysis will be unavailable")
    print("\n⚠️  WARNING: ANTHROPIC_API_KEY not set!")
    print("   Full analysis requires Claude API access.")
    print("   You can still use 'sefaria' and 'mock' commands.\n")
else:
    logger.info("ANTHROPIC_API_KEY found - full analysis enabled")


def print_header():
    """Print welcome header."""
    logger.info("Starting Step 2 Console Tester")
    print("\n" + "=" * 60)
    print("  STEP 2 CONSOLE TESTER: UNDERSTAND")
    print("  Query Analysis & Strategy Builder")
    print("=" * 60)
    print("\nCommands:")
    print("  <hebrew>         - Full analysis (Sefaria + Claude)")
    print("  sefaria <hebrew> - Just show Sefaria data")
    print("  mock <hebrew>    - Test with mock Claude response")
    print("  q / quit         - Exit")
    print("=" * 60 + "\n")


def print_strategy(strategy):
    """Pretty print a SearchStrategy."""
    logger.info(f"Generated strategy - Type: {strategy.query_type.value}, "
                f"Confidence: {strategy.confidence}, "
                f"Primary: {strategy.primary_source or 'none'}, "
                f"Sefaria hits: {strategy.sefaria_hits}")
    logger.debug(f"Strategy details - Fetch: {strategy.fetch_strategy.value}, "
                 f"Depth: {strategy.depth}, Related sugyos: {len(strategy.related_sugyos)}")
    
    print(f"\n{'─' * 50}")
    print(f"  📊 SEARCH STRATEGY")
    print(f"{'─' * 50}")
    print(f"  Query Type:     {strategy.query_type.value}")
    print(f"  Primary Source: {strategy.primary_source or '(none)'}")
    print(f"  Primary (Heb):  {strategy.primary_source_he or '(none)'}")
    print(f"  Fetch Strategy: {strategy.fetch_strategy.value}")
    print(f"  Depth:          {strategy.depth}")
    print(f"  Confidence:     {strategy.confidence}")
    
    if strategy.reasoning:
        print(f"\n  📝 Reasoning:")
        # Word wrap
        words = strategy.reasoning.split()
        line = "     "
        for word in words:
            if len(line) + len(word) > 70:
                print(line)
                line = "     "
            line += word + " "
        if line.strip():
            print(line)
    
    if strategy.related_sugyos:
        print(f"\n  🔗 Related Sugyos ({len(strategy.related_sugyos)}):")
        for i, sugya in enumerate(strategy.related_sugyos[:5], 1):
            print(f"     {i}. {sugya.ref} ({sugya.importance})")
            print(f"        └─ {sugya.connection}")
    
    if strategy.clarification_prompt:
        print(f"\n  ❓ Clarification Needed:")
        print(f"     {strategy.clarification_prompt}")
    
    print(f"\n  📈 Sefaria Stats:")
    print(f"     Total hits: {strategy.sefaria_hits}")
    if strategy.hits_by_masechta:
        top_3 = sorted(strategy.hits_by_masechta.items(), 
                      key=lambda x: x[1], reverse=True)[:3]
        print(f"     Top masechttos: {', '.join(f'{m}({c})' for m,c in top_3)}")


def print_sefaria_data(data: dict):
    """Pretty print Sefaria search results."""
    total_hits = data.get('total_hits', 0)
    query = data.get('query', '?')
    logger.info(f"Sefaria data retrieved - Query: '{query}', Total hits: {total_hits}")
    
    if data.get('error'):
        logger.error(f"Sefaria error for query '{query}': {data.get('error')}")
    else:
        logger.debug(f"Sefaria categories: {len(data.get('hits_by_category', {}))} categories, "
                     f"{len(data.get('hits_by_masechta', {}))} masechtot")
    
    print(f"\n{'─' * 50}")
    print(f"  🔍 SEFARIA DATA")
    print(f"{'─' * 50}")
    print(f"  Query: {query}")
    print(f"  Total Hits: {total_hits}")
    
    if data.get('hits_by_category'):
        print(f"\n  By Category:")
        for cat, count in sorted(data['hits_by_category'].items(), 
                                 key=lambda x: x[1], reverse=True)[:5]:
            print(f"     {cat}: {count}")
    
    if data.get('hits_by_masechta'):
        print(f"\n  By Masechta:")
        for mas, count in sorted(data['hits_by_masechta'].items(), 
                                 key=lambda x: x[1], reverse=True)[:5]:
            print(f"     {mas}: {count}")
    
    if data.get('top_refs'):
        print(f"\n  Top References:")
        for i, ref in enumerate(data['top_refs'][:5], 1):
            print(f"     {i}. {ref}")
    
    if data.get('sample_hits'):
        print(f"\n  Sample Snippets:")
        for i, hit in enumerate(data['sample_hits'][:3], 1):
            snippet = hit.get('snippet', '')[:80]
            print(f"     {i}. {hit.get('ref', '?')}")
            print(f"        {snippet}...")
    
    if data.get('error'):
        print(f"\n  ⚠️ Error: {data['error']}")


async def test_sefaria(hebrew_term: str):
    """Test just the Sefaria data gathering."""
    logger.info(f"Testing Sefaria-only mode for term: '{hebrew_term}'")
    print(f"\n🔍 Gathering Sefaria data for: {hebrew_term}")
    
    try:
        from step_two_understand import gather_sefaria_data
        data = await gather_sefaria_data(hebrew_term)
        print_sefaria_data(data)
        logger.info(f"Sefaria test completed successfully for '{hebrew_term}'")
    except Exception as e:
        logger.error(f"Sefaria test failed for '{hebrew_term}': {e}", exc_info=True)
        print(f"\n  ✗ Error: {e}")


async def test_full(hebrew_term: str):
    """Test full Step 2 analysis."""
    logger.info(f"Starting full analysis (Sefaria + Claude) for term: '{hebrew_term}'")
    print(f"\n🔍 Full analysis for: {hebrew_term}")
    
    try:
        from step_two_understand import understand
        strategy = await understand(hebrew_term)
        print_strategy(strategy)
        logger.info(f"Full analysis completed successfully for '{hebrew_term}'")
    except Exception as e:
        logger.error(f"Full analysis failed for '{hebrew_term}': {e}", exc_info=True)
        print(f"\n  ✗ Error: {e}")
        import traceback
        traceback.print_exc()


async def test_mock(hebrew_term: str):
    """Test with mock Claude response (no API call)."""
    logger.info(f"Starting mock analysis (Sefaria + mock strategy) for term: '{hebrew_term}'")
    print(f"\n🔍 Mock analysis for: {hebrew_term}")
    
    try:
        from step_two_understand import (
            gather_sefaria_data, 
            _fallback_strategy,
            SearchStrategy,
            QueryType,
            FetchStrategy,
            RelatedSugya
        )
        
        # Get real Sefaria data
        logger.debug(f"Fetching Sefaria data for mock test: '{hebrew_term}'")
        print("   Getting Sefaria data...")
        sefaria_data = await gather_sefaria_data(hebrew_term)
        print_sefaria_data(sefaria_data)
        
        # Create mock strategy based on Sefaria data
        logger.debug("Creating mock strategy from Sefaria results")
        print("\n   Creating mock strategy from Sefaria data...")
        
        # Find top masechta
        top_masechta = None
        top_count = 0
        for mas, count in sefaria_data.get('hits_by_masechta', {}).items():
            if count > top_count:
                top_masechta = mas
                top_count = count
        
        logger.debug(f"Top masechta identified: {top_masechta} ({top_count} hits)")
        
        # Use top ref
        top_refs = sefaria_data.get('top_refs', [])
        primary = top_refs[0] if top_refs else None
        
        # Build mock strategy
        strategy = SearchStrategy(
            query_type=QueryType.SUGYA_CONCEPT,
            primary_source=primary,
            primary_source_he=None,
            reasoning=f"Mock analysis: Found {sefaria_data.get('total_hits', 0)} hits. "
                     f"Most hits in {top_masechta} ({top_count}). "
                     f"Using top reference as primary source.",
            fetch_strategy=FetchStrategy.TRICKLE_UP,
            depth="standard",
            confidence="medium",
            sefaria_hits=sefaria_data.get('total_hits', 0),
            hits_by_masechta=sefaria_data.get('hits_by_masechta', {})
        )
        
        print_strategy(strategy)
        logger.info(f"Mock analysis completed successfully for '{hebrew_term}'")
        
    except Exception as e:
        logger.error(f"Mock analysis failed for '{hebrew_term}': {e}", exc_info=True)
        print(f"\n  ✗ Error: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main interactive loop."""
    logger.info("Console Step Two tester started")
    print_header()
    
    while True:
        try:
            user_input = input("\n🔹 Enter Hebrew term: ").strip()
            logger.debug(f"User input received: '{user_input}'")
        except (EOFError, KeyboardInterrupt):
            logger.info("User interrupted - exiting console tester")
            print("\n\nGoodbye!")
            break
        
        if not user_input:
            continue
        
        # Check for commands
        lower_input = user_input.lower()
        
        if lower_input in ('q', 'quit', 'exit'):
            logger.info("User requested exit")
            print("\nGoodbye!")
            break
        
        if lower_input.startswith('sefaria '):
            term = user_input[8:].strip()
            if term:
                logger.info(f"User selected 'sefaria' command with term: '{term}'")
                asyncio.run(test_sefaria(term))
            else:
                logger.warning("User entered 'sefaria' without a term")
                print("Usage: sefaria <hebrew term>")
            continue
        
        if lower_input.startswith('mock '):
            term = user_input[5:].strip()
            if term:
                logger.info(f"User selected 'mock' command with term: '{term}'")
                asyncio.run(test_mock(term))
            else:
                logger.warning("User entered 'mock' without a term")
                print("Usage: mock <hebrew term>")
            continue
        
        # Check for API key for full analysis
        if not os.environ.get("ANTHROPIC_API_KEY"):
            logger.warning(f"User attempted full analysis without API key for term: '{user_input}'")
            print("\n⚠️  ANTHROPIC_API_KEY not set. Use 'mock' or 'sefaria' commands.")
            print("   Example: mock חזקת הגוף")
            continue
        
        # Full analysis
        logger.info(f"User requested full analysis for term: '{user_input}'")
        asyncio.run(test_full(user_input))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"Unexpected error in main: {e}", exc_info=True)
        raise
    finally:
        logger.info("Console Step Two tester exiting")