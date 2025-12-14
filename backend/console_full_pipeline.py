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
from typing import Any, Dict, Iterable, List

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

# Set up logging
try:
    from logging_config import setup_logging

    setup_logging(log_level=logging.DEBUG)
except ImportError:
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )

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
    """Pretty print Step 2 result."""
    qtype = getattr(strategy.query_type, "value", strategy.query_type)
    logger.info(
        "Step 2 complete - Type: %s, Primary: %s, Confidence: %s",
        qtype,
        strategy.primary_source,
        getattr(strategy.confidence, "value", strategy.confidence),
    )

    _print_divider("STEP 2: SEARCH STRATEGY")
    print(f"  Query Type:     {qtype}")
    print(f"  Primary Source: {strategy.primary_source or '(none)'}")

    if getattr(strategy, "primary_sources", None) and len(strategy.primary_sources) > 1:
        print(f"  All Primaries:  {strategy.primary_sources}")

    if getattr(strategy, "is_comparison_query", False):
        print("\n  Comparison:     Yes")
        print(f"  Compare Terms:  {strategy.comparison_terms}")

    fetch = getattr(strategy.fetch_strategy, "value", strategy.fetch_strategy)
    print(f"  Fetch Strategy: {fetch}")
    print(f"  Depth:          {strategy.depth}")

    conf = getattr(strategy.confidence, "value", strategy.confidence)
    print(f"  Confidence:     {conf}")

    if strategy.reasoning:
        print("\n  Reasoning:")
        _wrap_text(strategy.reasoning)

    if strategy.related_sugyos:
        print(f"\n  Related Sugyos ({len(strategy.related_sugyos)}):")
        for idx, sugya in enumerate(strategy.related_sugyos[:5], 1):
            ref = sugya.ref if hasattr(sugya, "ref") else sugya.get("ref", "?")
            imp = (
                sugya.importance
                if hasattr(sugya, "importance")
                else sugya.get("importance", "?")
            )
            conn = (
                sugya.connection
                if hasattr(sugya, "connection")
                else sugya.get("connection", "?")
            )
            print(f"     {idx}. {ref} ({imp})")
            _wrap_text(conn, indent=10)

    print("\n  Sefaria Stats:")
    print(f"     Total hits: {getattr(strategy, 'sefaria_hits', 0)}")
    if getattr(strategy, "hits_by_masechta", None):
        top_3 = sorted(
            strategy.hits_by_masechta.items(), key=lambda item: item[1], reverse=True
        )[:3]
        print(f"     Top: {', '.join(f'{m}({c})' for m, c in top_3)}")

    if strategy.clarification_prompt:
        print(f"\n  Clarification: {strategy.clarification_prompt}")


def print_step3_result(result: Any) -> None:
    """Pretty print Step 3 result."""
    logger.info(
        "Step 3 complete - Sources: %s, Levels: %s",
        result.total_sources,
        result.levels_included,
    )

    _print_divider("STEP 3: SEARCH RESULTS")
    print(f"  Primary Source:  {result.primary_source or '(none)'}")
    print(f"  Total Sources:   {result.total_sources}")
    print(
        f"  Levels Included: {', '.join(result.levels_included) if result.levels_included else '(none)'}"
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

    if result.related_sugyos:
        print(f"\n  Related Sugyos ({len(result.related_sugyos)}):")
        for idx, rel in enumerate(result.related_sugyos[:3], 1):
            ref = rel.ref if hasattr(rel, "ref") else rel.get("ref", "?")
            conn = rel.connection if hasattr(rel, "connection") else rel.get("connection", "?")
            print(f"     {idx}. {ref}")
            _wrap_text(conn, indent=10)

    if result.interpretation:
        print("\n  Interpretation:")
        _wrap_text(result.interpretation)

    if result.needs_clarification and result.clarification_prompt:
        print(f"\n  Needs Clarification: {result.clarification_prompt}")


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

        strategy = await understand(
            hebrew_term=hebrew_term,
            original_query=query,
            step1_result=step1_result,
        )
        print_step2_result(strategy)
    except TypeError:
        logger.warning("Step 2 doesn't support step1_result, using legacy call")
        from step_two_understand import understand

        strategy = await understand(hebrew_term, query)
        print_step2_result(strategy)
    except Exception as exc:  # noqa: BLE001
        logger.error("Step 2 failed: %s", exc, exc_info=True)
        print(f"\n  ❌ Step 2 Error: {exc}")
        return

    # STEP 3: SEARCH
    print("\n-> STEP 3: SEARCH")
    logger.info("Starting Step 3: SEARCH")
    try:
        from step_three_search import search

        search_result = await search(strategy, query, hebrew_term)
        print_step3_result(search_result)
    except ImportError as exc:
        logger.error("Step 3 import error: %s", exc, exc_info=True)
        print(f"\n  ❌ Step 3 Import Error: {exc}")
        print("     This is likely a missing import in step_three_search.py")
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
    print(f"  Primary:     {strategy.primary_source}")
    print(f"  Sources:     {search_result.total_sources}")
    print(
        f"  Levels:      {', '.join(search_result.levels_included) if search_result.levels_included else '(none)'}"
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
