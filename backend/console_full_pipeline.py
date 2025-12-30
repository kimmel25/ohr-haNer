"""
Console Tester for Ohr Haner V2 Pipeline
=========================================

Tests the new Step 2 + Step 3 architecture.
Run with: python console_tester_v2.py
"""

import asyncio
import logging
import sys
from pathlib import Path

# Setup logging FIRST (before other imports)
try:
    # Add logging directory to path to avoid conflict with built-in logging module
    sys.path.insert(0, str(Path(__file__).parent / "logging"))
    from logging_config import setup_logging, get_logger
    sys.path.pop(0)  # Remove from path after import
    setup_logging()
except ImportError as e:
    # Fallback basic logging
    print(f"Warning: Could not import logging_config: {e}")
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s | %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )

logger = logging.getLogger(__name__)

# Import the V2 modules
try:
    from step_two_understand import understand, QueryAnalysis
    from step_three_search import search, SearchResult
    from source_output import write_output, SourceOutputWriter
except ImportError as e:
    logger.error(f"Import error: {e}")
    logger.error("Make sure all V2 files are in the same directory:")
    logger.error("  - step_two_understand_v2.py")
    logger.error("  - step_three_search_v2.py")
    logger.error("  - source_output_v2.py")
    logger.error("  - logging_config_v2.py")
    sys.exit(1)


async def run_pipeline(query: str, hebrew_terms: list = None):
    """Run the full V2 pipeline on a query."""
    print("\n" + "=" * 70)
    print(f"QUERY: {query}")
    print("=" * 70)
    
    # If no hebrew terms provided, use query as-is
    if hebrew_terms is None:
        # Simple extraction - in real usage, Step 1 would do this
        hebrew_terms = [query]
    
    # Step 2: Understand
    print("\n[STEP 2: UNDERSTAND]")
    print("-" * 40)
    
    analysis = await understand(hebrew_terms=hebrew_terms, query=query)
    
    print(f"  Query type: {analysis.query_type}")
    print(f"  Foundation type: {analysis.foundation_type}")
    print(f"  Suggested refs: {analysis.suggested_refs}")
    print(f"  Target sources: {analysis.target_sources}")
    print(f"  Trickle direction: {analysis.trickle_direction}")
    print(f"  Confidence: {analysis.confidence}")
    
    if analysis.needs_clarification:
        print(f"\n  ⚠️  NEEDS CLARIFICATION:")
        print(f"  {analysis.clarification_question}")
        if analysis.clarification_options:
            for opt in analysis.clarification_options:
                print(f"    - {opt}")
        return None
    
    print(f"\n  Reasoning: {analysis.reasoning[:200]}...")
    
    # Step 3: Search
    print("\n[STEP 3: SEARCH]")
    print("-" * 40)
    
    result = await search(analysis)
    
    if result.needs_clarification:
        print(f"\n  ⚠️  NEEDS CLARIFICATION:")
        print(f"  {result.clarification_question}")
        return result
    
    # Display results
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    
    print(f"\n📖 Foundation Stones ({len(result.foundation_stones)}):")
    for s in result.foundation_stones:
        print(f"  • {s.ref}")
        if s.hebrew_text:
            preview = s.hebrew_text[:150].replace('\n', ' ')
            print(f"    {preview}...")
    
    print(f"\n📚 Commentaries ({len(result.commentary_sources)}):")
    for s in result.commentary_sources[:10]:  # Limit display
        print(f"  • {s.ref} ({s.author})")
    if len(result.commentary_sources) > 10:
        print(f"  ... and {len(result.commentary_sources) - 10} more")
    
    print(f"\n📜 Earlier Sources ({len(result.earlier_sources)}):")
    for s in result.earlier_sources[:5]:
        print(f"  • {s.ref}")
    
    print(f"\n{result.search_description}")
    print(f"Confidence: {result.confidence}")
    
    # Write output files
    print("\n[WRITING OUTPUT FILES]")
    print("-" * 40)
    try:
        output_files = write_output(result, query, formats=["txt", "html"])
        for fmt, path in output_files.items():
            print(f"  ✓ {fmt.upper()}: {path}")
    except Exception as e:
        logger.error(f"Error writing output: {e}")
    
    return result


async def interactive_mode():
    """Interactive console mode."""
    print("\n" + "=" * 70)
    print("       OHR HANER V2 - Interactive Console")
    print("=" * 70)
    print("Type a query to search, or 'q' to quit.")
    print("Examples:")
    print("  - migu")
    print("  - chezkas haguf vs chezkas mammon")
    print("  - show me rashi on pesachim 4b")
    print("  - hilchos carrying on shabbos")
    print("=" * 70)
    
    while True:
        try:
            query = input("\n> ").strip()
            
            if not query:
                continue
            
            if query.lower() in ['q', 'quit', 'exit']:
                print("Goodbye!")
                break
            
            await run_pipeline(query)
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            logger.error(f"Error: {e}")
            import traceback
            traceback.print_exc()


async def run_test_queries():
    """Run a set of test queries."""
    test_queries = [
        "migu",
        "chezkas haguf vs chezkas mammon",
        "show me rashi on pesachim 4b",
        # "hilchos carrying on shabbos",  # Takes longer
    ]
    
    for query in test_queries:
        try:
            await run_pipeline(query)
            print("\n" + "-" * 70 + "\n")
        except Exception as e:
            logger.error(f"Error with query '{query}': {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Ohr Haner V2 Console Tester")
    parser.add_argument("--test", action="store_true", help="Run test queries")
    parser.add_argument("query", nargs="*", help="Query to run (or interactive if none)")
    
    args = parser.parse_args()
    
    if args.test:
        asyncio.run(run_test_queries())
    elif args.query:
        query = " ".join(args.query)
        asyncio.run(run_pipeline(query))
    else:
        asyncio.run(interactive_mode())