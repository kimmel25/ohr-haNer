"""
Console Tester for Step 1 + Step 2 Pipeline
============================================

Interactive tool for testing the full DECIPHER → UNDERSTAND flow.

Usage:
    python console_pipeline.py

Commands:
    - Type any query to run full pipeline (Step 1 → Step 2)
    - Type 'q' or 'quit' to exit
"""

import sys
import os
import asyncio
import logging
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

# Set up logging
try:
    from logging_config import setup_logging
    setup_logging(log_level=logging.DEBUG)
except ImportError:
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%H:%M:%S'
    )

logger = logging.getLogger(__name__)

# Check for API key
if not os.environ.get("ANTHROPIC_API_KEY"):
    logger.warning("ANTHROPIC_API_KEY not set - Step 2 Claude analysis unavailable")
    print("\n⚠️  WARNING: ANTHROPIC_API_KEY not set!")
    print("   Step 2 will use fallback strategy instead of Claude.\n")
else:
    logger.info("ANTHROPIC_API_KEY found - full analysis enabled")


def print_header():
    """Print welcome header."""
    logger.info("Starting Pipeline Console Tester")
    print("\n" + "=" * 60)
    print("  MAREI MEKOMOS PIPELINE TESTER")
    print("  Step 1 (DECIPHER) → Step 2 (UNDERSTAND)")
    print("=" * 60)
    print("\nCommands:")
    print("  <query>  - Run full pipeline")
    print("  q / quit - Exit")
    print("=" * 60 + "\n")


def print_step1_result(result):
    """Pretty print Step 1 result."""
    logger.info(f"Step 1 complete - Success: {result.success}, "
                f"Hebrew: {result.hebrew_term}, Method: {result.method}")
    
    print(f"\n{'─' * 50}")
    print(f"  📝 STEP 1: DECIPHER RESULT")
    print(f"{'─' * 50}")
    print(f"  Success:        {result.success}")
    print(f"  Hebrew Term:    {result.hebrew_term or '(none)'}")
    
    # Multiple terms (V4)
    if hasattr(result, 'hebrew_terms') and result.hebrew_terms and len(result.hebrew_terms) > 1:
        print(f"  All Terms:      {result.hebrew_terms}")
    
    conf = result.confidence.value if hasattr(result.confidence, 'value') else result.confidence
    print(f"  Confidence:     {conf}")
    print(f"  Method:         {result.method}")
    
    # Mixed query info (V4)
    if hasattr(result, 'is_mixed_query') and result.is_mixed_query:
        print(f"\n  🔀 Mixed Query:  True")
        print(f"  Original:       {result.original_query}")
        print(f"  Extraction OK:  {result.extraction_confident}")
    
    if result.alternatives:
        print(f"\n  Alternatives:")
        for i, alt in enumerate(result.alternatives[:5], 1):
            print(f"     {i}. {alt}")
    
    if result.message:
        print(f"\n  Message: {result.message}")


def print_step2_result(strategy):
    """Pretty print Step 2 result."""
    logger.info(f"Step 2 complete - Type: {strategy.query_type.value}, "
                f"Primary: {strategy.primary_source}, Confidence: {strategy.confidence}")
    
    print(f"\n{'─' * 50}")
    print(f"  📊 STEP 2: SEARCH STRATEGY")
    print(f"{'─' * 50}")
    
    qtype = strategy.query_type.value if hasattr(strategy.query_type, 'value') else strategy.query_type
    print(f"  Query Type:     {qtype}")
    print(f"  Primary Source: {strategy.primary_source or '(none)'}")
    
    if strategy.primary_sources and len(strategy.primary_sources) > 1:
        print(f"  All Primaries:  {strategy.primary_sources}")
    
    # Comparison (V4)
    if hasattr(strategy, 'is_comparison_query') and strategy.is_comparison_query:
        print(f"\n  ⚖️ Comparison:   Yes")
        print(f"  Compare Terms:  {strategy.comparison_terms}")
    
    fetch = strategy.fetch_strategy.value if hasattr(strategy.fetch_strategy, 'value') else strategy.fetch_strategy
    print(f"  Fetch Strategy: {fetch}")
    print(f"  Depth:          {strategy.depth}")
    print(f"  Confidence:     {strategy.confidence}")
    
    if strategy.reasoning:
        print(f"\n  📝 Reasoning:")
        words = strategy.reasoning.split()
        line = "     "
        for word in words:
            if len(line) + len(word) > 65:
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
    
    print(f"\n  📈 Sefaria Stats:")
    print(f"     Total hits: {strategy.sefaria_hits}")
    if strategy.hits_by_masechta:
        top_3 = sorted(strategy.hits_by_masechta.items(), 
                      key=lambda x: x[1], reverse=True)[:3]
        print(f"     Top: {', '.join(f'{m}({c})' for m,c in top_3)}")
    
    if strategy.clarification_prompt:
        print(f"\n  ❓ Clarification: {strategy.clarification_prompt}")


async def run_pipeline(query: str):
    """Run the full Step 1 → Step 2 pipeline."""
    logger.info("=" * 80)
    logger.info(f"PIPELINE START: '{query}'")
    logger.info("=" * 80)
    
    print(f"\n{'=' * 60}")
    print(f"  🔄 RUNNING PIPELINE")
    print(f"  Query: '{query}'")
    print(f"{'=' * 60}")
    
    # ========================================
    # STEP 1: DECIPHER
    # ========================================
    print(f"\n▶ STEP 1: DECIPHER")
    logger.info("Starting Step 1: DECIPHER")
    
    try:
        from step_one_decipher import decipher
        step1_result = await decipher(query)
        print_step1_result(step1_result)
    except Exception as e:
        logger.error(f"Step 1 failed: {e}", exc_info=True)
        print(f"\n  ✗ Step 1 Error: {e}")
        return
    
    if not step1_result.success and not step1_result.hebrew_term:
        logger.warning("Step 1 failed - cannot proceed")
        print(f"\n  ✗ Step 1 failed - cannot proceed to Step 2")
        return
    
    hebrew_term = step1_result.hebrew_term
    
    # ========================================
    # STEP 2: UNDERSTAND
    # ========================================
    print(f"\n▶ STEP 2: UNDERSTAND")
    logger.info(f"Starting Step 2: UNDERSTAND for '{hebrew_term}'")
    
    try:
        from step_two_understand import understand
        strategy = await understand(
            hebrew_term=hebrew_term,
            original_query=query,
            step1_result=step1_result
        )
        print_step2_result(strategy)
    except TypeError:
        # Fallback if step2 doesn't support step1_result
        logger.warning("Step 2 doesn't support step1_result, using legacy call")
        from step_two_understand import understand
        strategy = await understand(hebrew_term, query)
        print_step2_result(strategy)
    except Exception as e:
        logger.error(f"Step 2 failed: {e}", exc_info=True)
        print(f"\n  ✗ Step 2 Error: {e}")
        return
    
    # ========================================
    # SUMMARY
    # ========================================
    print(f"\n{'=' * 60}")
    print(f"  ✅ PIPELINE COMPLETE")
    print(f"{'=' * 60}")
    print(f"  Input:    '{query}'")
    print(f"  Hebrew:   {hebrew_term}")
    if hasattr(step1_result, 'hebrew_terms') and len(step1_result.hebrew_terms) > 1:
        print(f"  All:      {step1_result.hebrew_terms}")
    print(f"  Type:     {strategy.query_type.value}")
    print(f"  Primary:  {strategy.primary_source}")
    
    logger.info("=" * 80)
    logger.info("PIPELINE COMPLETE")
    logger.info("=" * 80)


def main():
    """Main interactive loop."""
    logger.info("Pipeline Console Tester started")
    print_header()
    
    while True:
        try:
            user_input = input("\n🔹 Enter query: ").strip()
            logger.debug(f"User input: '{user_input}'")
        except (EOFError, KeyboardInterrupt):
            logger.info("User interrupted - exiting")
            print("\n\nGoodbye!")
            break
        
        if not user_input:
            continue
        
        if user_input.lower() in ('q', 'quit', 'exit'):
            logger.info("User requested exit")
            print("\nGoodbye!")
            break
        
        asyncio.run(run_pipeline(user_input))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"Unexpected error: {e}", exc_info=True)
        raise
    finally:
        logger.info("Pipeline Console Tester exiting")