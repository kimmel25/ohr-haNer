"""
Console Tester for Full Pipeline (Steps 1 + 2 + 3)
===================================================

Interactive tool for testing the complete DECIPHER -> UNDERSTAND -> SEARCH flow.

Usage:
    python console_full_pipeline.py

Commands:
    - Type any query to run full pipeline (Step 1 + Step 2 + Step 3)
    - Type 'q' or 'quit' to exit
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

# Set up logging with file handler
def setup_logging():
    """Set up logging to both file and console."""
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / f"marei_mekomos_{datetime.now().strftime('%Y%m%d')}.log"
    
    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # File handler (DEBUG level)
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)
    
    # Console handler (INFO level)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    print(f"Logging to: {log_file}")
    root_logger.info("=" * 80)
    root_logger.info("Marei Mekomos V5 - Full Pipeline Console - Logging initialized")
    root_logger.info(f"Log file: {log_file}")
    root_logger.info("=" * 80)

setup_logging()

logger = logging.getLogger(__name__)

if not os.environ.get("ANTHROPIC_API_KEY"):
    logger.warning("ANTHROPIC_API_KEY not set - Step 2 Claude analysis unavailable")
    print("\n⚠️  WARNING: ANTHROPIC_API_KEY not set!")
    print("    Step 2 will use fallback strategy instead of Claude.\n")
else:
    logger.info("ANTHROPIC_API_KEY found - full analysis enabled")


def _print_divider(label: str) -> None:
    print("\n" + "=" * 60)
    print(f"  {label}")
    print("=" * 60)


def _wrap_text(text: str, indent: int = 5, width: int = 65) -> None:
    line = " " * indent
    for word in text.split():
        if len(line) + len(word) + 1 > width:
            print(line)
            line = " " * indent
        line += word + " "
    if line.strip():
        print(line)


def print_step1_result(result: Any) -> None:
    """Pretty print Step 1 result."""
    logger.info(
        "Step 1 complete - Success: %s, Hebrew: %s, Method: %s",
        result.success,
        result.hebrew_term,
        result.method,
    )

    _print_divider("STEP 1: DECIPHER RESULT")
    print(f"  Success:        {result.success}")
    print(f"  Hebrew Term:    {result.hebrew_term or '(none)'}")

    if getattr(result, "hebrew_terms", None) and len(result.hebrew_terms) > 1:
        print(f"  All Terms:      {result.hebrew_terms}")

    conf = getattr(result.confidence, "value", result.confidence)
    print(f"  Confidence:     {conf}")
    print(f"  Method:         {result.method}")

    if getattr(result, "is_mixed_query", False):
        print("\n  Mixed Query:    True")
        print(f"  Original:       {result.original_query}")
        print(f"  Extraction OK:  {result.extraction_confident}")

    if result.alternatives:
        print("\n  Alternatives:")
        for idx, alt in enumerate(result.alternatives[:5], 1):
            print(f"     {idx}. {alt}")

    if result.message:
        print(f"\n  Message: {result.message}")


def print_step2_result(strategy: Any) -> None:
    """Pretty print Step 2 result (QueryAnalysis)."""
    qtype = getattr(strategy.query_type, "value", strategy.query_type)
    realm = getattr(strategy.realm, "value", strategy.realm)
    conf = getattr(strategy.confidence, "value", strategy.confidence)

    # Get primary author/target for logging
    primary = strategy.target_authors[0] if strategy.target_authors else "(none)"

    logger.info(
        "Step 2 complete - Type: %s, Primary: %s, Confidence: %s",
        qtype,
        primary,
        conf,
    )

    _print_divider("STEP 2: QUERY ANALYSIS")
    print(f"  Query Type:     {qtype}")
    print(f"  Realm:          {realm}")

    if strategy.target_authors:
        print(f"  Target Authors: {', '.join(strategy.target_authors)}")

    if strategy.target_masechtos:
        print(f"  Target Masechtos: {', '.join(strategy.target_masechtos)}")

    topics = getattr(strategy, "target_topics", None) or getattr(
        strategy, "search_topics", []
    )
    if topics:
        print(f"  Search Topics:  {', '.join(topics)}")

    search_method = getattr(strategy.search_method, "value", strategy.search_method)
    breadth = getattr(strategy.breadth, "value", strategy.breadth)
    print(f"  Search Method:  {search_method}")
    print(f"  Breadth:        {breadth}")
    print(f"  Confidence:     {conf}")

    if strategy.reasoning:
        print("\n  Reasoning:")
        _wrap_text(strategy.reasoning)

    if strategy.search_description:
        print("\n  Search Description:")
        _wrap_text(strategy.search_description)

    if strategy.needs_clarification and strategy.clarification_question:
        print(f"\n  Needs Clarification: {strategy.clarification_question}")
        if strategy.clarification_options:
            print(f"  Options: {strategy.clarification_options}")


def print_step3_result(result: Any) -> None:
    """Pretty print Step 3 result (SearchResult)."""
    levels_found = getattr(result, "levels_found", [])
    logger.info(
        "Step 3 complete - Sources: %s, Levels: %s",
        result.total_sources,
        levels_found,
    )

    _print_divider("STEP 3: SEARCH RESULTS")
    print(f"  Total Sources:   {result.total_sources}")
    print(
        f"  Levels Found:    {', '.join(levels_found) if levels_found else '(none)'}"
    )

    conf = getattr(result.confidence, "value", result.confidence)
    print(f"  Confidence:      {conf}")

    if result.sources_by_level:
        print("\n  Sources by Level:")
        for level, sources in result.sources_by_level.items():
            level_name = level.value if hasattr(level, "value") else level
            print(f"\n     {level_name.upper()} ({len(sources)}):")
            for source in sources[:3]:
                ref = source.ref if hasattr(source, "ref") else source.get("ref", "?")
                author = (
                    source.author if hasattr(source, "author") else source.get("author", "")
                )
                is_primary = (
                    source.is_primary
                    if hasattr(source, "is_primary")
                    else source.get("is_primary", False)
                )
                marker = " *" if is_primary else ""
                print(f"        - {ref}{' (' + author + ')' if author else ''}{marker}")
            if len(sources) > 3:
                print(f"        ... and {len(sources) - 3} more")

    if result.sources:
        primary_source = next(
            (
                s
                for s in result.sources
                if (s.is_primary if hasattr(s, "is_primary") else s.get("is_primary"))
            ),
            None,
        )
        if primary_source:
            hebrew = (
                primary_source.hebrew_text
                if hasattr(primary_source, "hebrew_text")
                else primary_source.get("hebrew_text", "")
            )
            if hebrew:
                preview = hebrew[:150] + ("..." if len(hebrew) > 150 else "")
                print("\n  Primary Text Preview:")
                _wrap_text(preview, indent=5, width=70)

    if getattr(result, "search_description", None):
        print("\n  Search Description:")
        _wrap_text(result.search_description)

    if result.needs_clarification and getattr(result, "clarification_question", None):
        print(f"\n  Needs Clarification: {result.clarification_question}")


async def run_pipeline(query: str) -> None:
    """Run the full Step 1 + Step 2 + Step 3 pipeline."""
    logger.info("=" * 80)
    logger.info("PIPELINE START: '%s'", query)
    logger.info("=" * 80)

    print("\n" + "=" * 70)
    print(f"  RUNNING FULL PIPELINE")
    print(f"  Query: '{query}'")
    print("=" * 70)

    # STEP 1: DECIPHER
    print("\n-> STEP 1: DECIPHER")
    logger.info("Starting Step 1: DECIPHER")
    try:
        from step_one_decipher import decipher

        step1_result = await decipher(query)
        print_step1_result(step1_result)
    except ImportError as exc:
        logger.error("Step 1 import failed: %s", exc, exc_info=True)
        print(f"\n  ❌ Step 1 Import Error: {exc}")
        print("     Make sure step_one_decipher.py exists and is in the backend folder")
        return
    except Exception as exc:  # noqa: BLE001
        logger.error("Step 1 failed: %s", exc, exc_info=True)
        print(f"\n  ❌ Step 1 Error: {exc}")
        return

    if not step1_result.success and not step1_result.hebrew_term:
        logger.warning("Step 1 failed - cannot proceed")
        print("\n  ❌ Step 1 failed - cannot proceed to Step 2")
        return

    hebrew_term = step1_result.hebrew_term
    hebrew_terms = (
        step1_result.hebrew_terms if hasattr(step1_result, "hebrew_terms") else [hebrew_term]
    )

    # STEP 2: UNDERSTAND
    print("\n-> STEP 2: UNDERSTAND")
    logger.info("Starting Step 2: UNDERSTAND for '%s'", hebrew_term)
    try:
        from step_two_understand import understand

        # Try new signature first, fall back to legacy
        try:
            strategy = await understand(
                hebrew_term=hebrew_term,
                original_query=query,
                step1_result=step1_result,
            )
        except TypeError:
            logger.warning("Step 2 doesn't support step1_result, using legacy call")
            strategy = await understand(hebrew_term, query)
        
        print_step2_result(strategy)
    except ImportError as exc:
        logger.error("Step 2 import failed: %s", exc, exc_info=True)
        print(f"\n  ❌ Step 2 Import Error: {exc}")
        print("     Make sure step_two_understand.py exists and is in the backend folder")
        return
    except Exception as exc:  # noqa: BLE001
        logger.error("Step 2 failed: %s", exc, exc_info=True)
        print(f"\n  ❌ Step 2 Error: {exc}")
        return

    # STEP 3: SEARCH
    print("\n-> STEP 3: SEARCH")
    logger.info("Starting Step 3: SEARCH")
    try:
        from step_three_search import search

        search_result = await search(strategy)
        print_step3_result(search_result)
    except ImportError as exc:
        logger.error("Step 3 import error: %s", exc, exc_info=True)
        print(f"\n  ❌ Step 3 Import Error: {exc}")
        print("     Make sure step_three_search.py exists and is in the backend folder")
        print("     Steps 1 & 2 completed successfully!")
        return
    except Exception as exc:  # noqa: BLE001
        logger.error("Step 3 failed: %s", exc, exc_info=True)
        print(f"\n  ❌ Step 3 Error: {exc}")
        print("\n     Note: Steps 1 & 2 completed successfully!")
        return

    # FINAL SUMMARY
    print("\n" + "=" * 70)
    print("  ✅ FULL PIPELINE COMPLETE")
    print("=" * 70)
    print(f"  Input:       '{query}'")
    print(f"  Hebrew:      {hebrew_term}")
    if hebrew_terms and len(hebrew_terms) > 1:
        print(f"  All terms:   {hebrew_terms}")

    qtype = getattr(strategy.query_type, "value", strategy.query_type)
    print(f"  Query type:  {qtype}")
    primary = strategy.target_authors[0] if strategy.target_authors else "(none)"
    print(f"  Primary:     {primary}")
    print(f"  Sources:     {search_result.total_sources}")
    levels_found = getattr(search_result, "levels_found", [])
    print(
        f"  Levels:      {', '.join(levels_found) if levels_found else '(none)'}"
    )

    logger.info("=" * 80)
    logger.info("PIPELINE COMPLETE")
    logger.info("=" * 80)


def main() -> None:
    """Main interactive loop."""
    logger.info("Full Pipeline Console Tester started")
    print("\n" + "=" * 70)
    print("  MAREI MEKOMOS FULL PIPELINE TESTER")
    print("  Step 1 (DECIPHER) -> Step 2 (UNDERSTAND) -> Step 3 (SEARCH)")
    print("=" * 70)
    print("\nCommands:")
    print("  <query>  - Run full pipeline")
    print("  q / quit - Exit")
    print("=" * 70 + "\n")

    while True:
        try:
            user_input = input("\nEnter query: ").strip()
            logger.debug("User input: '%s'", user_input)
        except (EOFError, KeyboardInterrupt):
            logger.info("User interrupted - exiting")
            print("\n\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ("q", "quit", "exit"):
            logger.info("User requested exit")
            print("\nGoodbye!")
            break

        asyncio.run(run_pipeline(user_input))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        logger.critical("Unexpected error: %s", exc, exc_info=True)
        raise
    finally:
        logger.info("Full Pipeline Console Tester exiting")
