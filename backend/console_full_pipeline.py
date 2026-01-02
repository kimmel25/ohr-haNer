"""
Console Pipeline for Ohr Haner V3
==================================

Interactive console for testing the pipeline with step-by-step control.

FEATURES:
    - Choose which steps to run (1, 1+2, or 1+2+3)
    - Detailed output at each step
    - Save intermediate results
    - Debug mode for verbose logging

USAGE:
    python console_full_pipeline.py              # Interactive mode
    python console_full_pipeline.py "migu"       # Run specific query
    python console_full_pipeline.py --test       # Run test queries
    python console_full_pipeline.py --steps 2    # Run only steps 1 and 2
"""

import asyncio
import logging
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple, List
from dataclasses import asdict

# =============================================================================
#  PATH SETUP
# =============================================================================

# Add current directory to path for imports
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

# Also add logging subdirectory if it exists
LOGGING_DIR = SCRIPT_DIR / "logging"
if LOGGING_DIR.exists():
    sys.path.insert(0, str(LOGGING_DIR))


# =============================================================================
#  LOGGING SETUP
# =============================================================================

def setup_console_logging(debug: bool = False) -> None:
    """Setup logging for console testing."""
    
    # Try to use the project's logging config
    try:
        from logging_config import setup_logging
        setup_logging()
        return
    except ImportError:
        pass
    
    # Fallback to basic logging
    level = logging.DEBUG if debug else logging.INFO
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    
    # File handler (canonical backend/logging/logs; avoid backend/logs)
    log_dir = SCRIPT_DIR / "logging" / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"ohr_haner_{datetime.now().strftime('%Y%m%d')}.log"
    
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    logging.info(f"Logging initialized. File: {log_file}")


logger = logging.getLogger(__name__)


# =============================================================================
#  IMPORT PIPELINE MODULES
# =============================================================================

def import_modules():
    """Import pipeline modules with helpful error messages."""
    modules = {}
    
    # Step 1: Decipher
    try:
        from step_one_decipher import decipher, DecipherResult
        modules['step1'] = {'decipher': decipher, 'DecipherResult': DecipherResult}
        logger.debug("Step 1 (decipher) imported successfully")
    except ImportError as e:
        logger.warning(f"Step 1 import failed: {e}")
        modules['step1'] = None
    
    # Step 2: Understand
    try:
        from step_two_understand import (
            understand, QueryAnalysis, RefHint, SearchVariants,
            QueryType, FoundationType, ConfidenceLevel
        )
        modules['step2'] = {
            'understand': understand,
            'QueryAnalysis': QueryAnalysis,
            'RefHint': RefHint,
            'SearchVariants': SearchVariants,
            'QueryType': QueryType,
            'FoundationType': FoundationType,
            'ConfidenceLevel': ConfidenceLevel,
        }
        logger.debug("Step 2 (understand) imported successfully")
    except ImportError as e:
        logger.warning(f"Step 2 import failed: {e}")
        modules['step2'] = None
    
    # Step 3: Search
    try:
        from step_three_search import search, SearchResult
        modules['step3'] = {'search': search, 'SearchResult': SearchResult}
        logger.debug("Step 3 (search) imported successfully")
    except ImportError as e:
        logger.warning(f"Step 3 import failed: {e}")
        modules['step3'] = None
    
    # Output writer
    try:
        from source_output import write_output
        modules['output'] = {'write_output': write_output}
        logger.debug("Output writer imported successfully")
    except ImportError as e:
        logger.warning(f"Output writer import failed: {e}")
        modules['output'] = None
    
    return modules


# =============================================================================
#  DISPLAY HELPERS
# =============================================================================

def print_header(text: str, char: str = "=", width: int = 70) -> None:
    """Print a header with borders."""
    border = char * width
    print(f"\n{border}")
    print(f"  {text}")
    print(border)


def print_subheader(text: str) -> None:
    """Print a subheader."""
    print(f"\n{'─' * 50}")
    print(f"  {text}")
    print(f"{'─' * 50}")


def print_key_value(key: str, value, indent: int = 2) -> None:
    """Print a key-value pair with indentation."""
    prefix = " " * indent
    print(f"{prefix}{key}: {value}")


def print_list(label: str, items: list, indent: int = 2, max_items: int = 10) -> None:
    """Print a labeled list."""
    prefix = " " * indent
    print(f"{prefix}{label}:")
    for i, item in enumerate(items[:max_items]):
        print(f"{prefix}  • {item}")
    if len(items) > max_items:
        print(f"{prefix}  ... and {len(items) - max_items} more")


# =============================================================================
#  STEP 1: DECIPHER
# =============================================================================

async def run_step1(query: str, modules: dict) -> Optional[object]:
    """
    Run Step 1: Decipher transliterated Hebrew.
    
    Args:
        query: User's query string
        modules: Imported modules dict
        
    Returns:
        DecipherResult or None if step unavailable
    """
    print_header("STEP 1: DECIPHER")
    
    if modules['step1'] is None:
        print("  ⚠️  Step 1 module not available")
        print("  Skipping decipher, passing query directly to Step 2")
        return None
    
    decipher = modules['step1']['decipher']
    
    print(f"  Input: {query}")
    print("  Processing...")
    
    try:
        result = await decipher(query)
        
        print_subheader("DECIPHER RESULT")
        print_key_value("Success", result.success)
        print_key_value("Hebrew Term", result.hebrew_term)
        
        if hasattr(result, 'hebrew_terms') and result.hebrew_terms:
            print_list("All Hebrew Terms", result.hebrew_terms)
        
        print_key_value("Confidence", result.confidence.value if hasattr(result.confidence, 'value') else result.confidence)
        print_key_value("Method", result.method if hasattr(result, 'method') else "N/A")
        
        if hasattr(result, 'is_mixed_query'):
            print_key_value("Mixed Query", result.is_mixed_query)
        
        if hasattr(result, 'message') and result.message:
            print_key_value("Message", result.message)
        
        return result
        
    except Exception as e:
        logger.error(f"Step 1 error: {e}")
        print(f"  ❌ Error: {e}")
        return None


# =============================================================================
#  STEP 2: UNDERSTAND
# =============================================================================

async def run_step2(
    query: str, 
    hebrew_terms: List[str], 
    modules: dict,
    decipher_result: object = None
) -> Optional[object]:
    """
    Run Step 2: Understand query with Claude.
    
    Args:
        query: Original query string
        hebrew_terms: Hebrew terms from Step 1 or user
        modules: Imported modules dict
        decipher_result: Optional result from Step 1
        
    Returns:
        QueryAnalysis or None if step unavailable
    """
    print_header("STEP 2: UNDERSTAND")
    
    if modules['step2'] is None:
        print("  ⚠️  Step 2 module not available")
        return None
    
    understand = modules['step2']['understand']
    
    print(f"  Query: {query}")
    print(f"  Hebrew Terms: {hebrew_terms}")
    print("  Calling Claude...")
    
    try:
        if decipher_result is not None:
            result = await understand(decipher_result=decipher_result, query=query)
        else:
            result = await understand(hebrew_terms=hebrew_terms, query=query)
        
        # Display results
        print_subheader("QUERY ANALYSIS")
        
        print_key_value("Query Type", result.query_type.value if hasattr(result.query_type, 'value') else result.query_type)
        print_key_value("Foundation Type", result.foundation_type.value if hasattr(result.foundation_type, 'value') else result.foundation_type)
        print_key_value("Breadth", result.breadth.value if hasattr(result.breadth, 'value') else result.breadth)
        print_key_value("Trickle Direction", result.trickle_direction.value if hasattr(result.trickle_direction, 'value') else result.trickle_direction)
        print_key_value("Confidence", result.confidence.value if hasattr(result.confidence, 'value') else result.confidence)
        
        if result.needs_clarification:
            print()
            print("  ⚠️  NEEDS CLARIFICATION:")
            print(f"     {result.clarification_question}")
            if result.clarification_options:
                print_list("Options", result.clarification_options, indent=5)
        
        # Ref hints
        print_subheader("REF HINTS")
        if hasattr(result, 'ref_hints') and result.ref_hints:
            for hint in result.ref_hints:
                conf = hint.confidence.value if hasattr(hint.confidence, 'value') else hint.confidence
                print(f"  • {hint.ref} [{conf}]")
                if hint.verification_keywords:
                    print(f"    Keywords: {hint.verification_keywords[:5]}")
                if hint.reasoning:
                    print(f"    Reason: {hint.reasoning[:60]}...")
        elif hasattr(result, 'suggested_refs'):
            # Backward compatibility
            print_list("Suggested Refs", result.suggested_refs)
        else:
            print("  No ref hints provided")
        
        # Search variants
        print_subheader("SEARCH VARIANTS")
        if hasattr(result, 'search_variants') and result.search_variants:
            sv = result.search_variants
            if sv.primary_hebrew:
                print_list("Primary Hebrew", sv.primary_hebrew)
            if sv.aramaic_forms:
                print_list("Aramaic Forms", sv.aramaic_forms)
            if sv.gemara_language:
                print_list("Gemara Language", sv.gemara_language)
            if sv.root_words:
                print_list("Root Words", sv.root_words)
            if sv.related_terms:
                print_list("Related Terms", sv.related_terms)
        else:
            print("  No search variants provided")
        
        # Target sources
        print_subheader("TARGET SOURCES")
        if result.target_sources:
            print_list("Sources to Fetch", result.target_sources)
        if hasattr(result, 'target_simanim') and result.target_simanim:
            print_list("Target Simanim", result.target_simanim)
        if hasattr(result, 'target_chelek') and result.target_chelek:
            print_key_value("Target Chelek", result.target_chelek)
        
        # Inyan description
        if result.inyan_description:
            print_subheader("INYAN DESCRIPTION")
            print(f"  {result.inyan_description}")
        
        # Reasoning
        if result.reasoning:
            print_subheader("CLAUDE'S REASONING")
            # Wrap long text
            reasoning = result.reasoning
            if len(reasoning) > 300:
                reasoning = reasoning[:300] + "..."
            print(f"  {reasoning}")
        
        # Processing time
        if hasattr(result, 'processing_time_ms') and result.processing_time_ms:
            print()
            print(f"  ⏱️  Processing time: {result.processing_time_ms}ms")
        
        return result
        
    except Exception as e:
        logger.error(f"Step 2 error: {e}")
        import traceback
        traceback.print_exc()
        print(f"  ❌ Error: {e}")
        return None


# =============================================================================
#  STEP 3: SEARCH
# =============================================================================

async def run_step3(analysis: object, modules: dict) -> Optional[object]:
    """
    Run Step 3: Search and fetch sources.
    
    Args:
        analysis: QueryAnalysis from Step 2
        modules: Imported modules dict
        
    Returns:
        SearchResult or None if step unavailable
    """
    print_header("STEP 3: SEARCH")
    
    if modules['step3'] is None:
        print("  ⚠️  Step 3 module not available")
        return None
    
    if analysis is None:
        print("  ⚠️  No analysis from Step 2, cannot search")
        return None
    
    search = modules['step3']['search']
    
    print("  Searching...")
    
    try:
        result = await search(analysis)
        
        print_subheader("SEARCH RESULT")
        
        if result.needs_clarification:
            print(f"  ⚠️  NEEDS CLARIFICATION: {result.clarification_question}")
            return result
        
        # Foundation stones
        if hasattr(result, 'foundation_stones') and result.foundation_stones:
            print_subheader(f"FOUNDATION STONES ({len(result.foundation_stones)})")
            for source in result.foundation_stones:
                print(f"  📖 {source.ref}")
                if source.hebrew_text:
                    preview = source.hebrew_text[:100].replace('\n', ' ')
                    print(f"     {preview}...")
        
        # Commentaries
        if hasattr(result, 'commentary_sources') and result.commentary_sources:
            print_subheader(f"COMMENTARIES ({len(result.commentary_sources)})")
            for source in result.commentary_sources[:10]:
                author = source.author if hasattr(source, 'author') and source.author else ""
                print(f"  📚 {source.ref} ({author})")
            if len(result.commentary_sources) > 10:
                print(f"  ... and {len(result.commentary_sources) - 10} more")
        
        # Earlier sources
        if hasattr(result, 'earlier_sources') and result.earlier_sources:
            print_subheader(f"EARLIER SOURCES ({len(result.earlier_sources)})")
            for source in result.earlier_sources[:5]:
                print(f"  📜 {source.ref}")
        
        # Summary
        print_subheader("SUMMARY")
        print_key_value("Total Sources", result.total_sources if hasattr(result, 'total_sources') else len(result.all_sources) if hasattr(result, 'all_sources') else 0)
        print_key_value("Confidence", result.confidence.value if hasattr(result.confidence, 'value') else result.confidence)
        
        if hasattr(result, 'search_description') and result.search_description:
            print_key_value("Description", result.search_description)
        
        return result
        
    except Exception as e:
        logger.error(f"Step 3 error: {e}")
        import traceback
        traceback.print_exc()
        print(f"  ❌ Error: {e}")
        return None


# =============================================================================
#  OUTPUT WRITING
# =============================================================================

def write_results(result: object, query: str, modules: dict) -> None:
    """Write results to output files."""
    if modules['output'] is None:
        print("  ⚠️  Output writer not available")
        return
    
    if result is None:
        print("  ⚠️  No results to write")
        return
    
    print_subheader("WRITING OUTPUT FILES")
    
    try:
        write_output = modules['output']['write_output']
        output_files = write_output(result, query, formats=["txt", "html"])
        
        for fmt, path in output_files.items():
            print(f"  ✓ {fmt.upper()}: {path}")
            
    except Exception as e:
        logger.error(f"Error writing output: {e}")
        print(f"  ❌ Error: {e}")


# =============================================================================
#  MAIN PIPELINE
# =============================================================================

async def run_pipeline(
    query: str,
    steps: int = 3,
    modules: dict = None,
    hebrew_terms: List[str] = None
) -> Tuple[object, object, object]:
    """
    Run the pipeline with specified number of steps.
    
    Args:
        query: User's query
        steps: How many steps to run (1, 2, or 3)
        modules: Pre-imported modules (or None to import)
        hebrew_terms: Optional pre-defined Hebrew terms
        
    Returns:
        Tuple of (decipher_result, analysis, search_result)
    """
    print_header(f"OHR HANER PIPELINE - RUNNING STEPS 1-{steps}", char="═")
    print(f"  Query: {query}")
    print(f"  Steps: {steps}")
    
    if modules is None:
        modules = import_modules()
    
    decipher_result = None
    analysis = None
    search_result = None
    
    # Step 1: Decipher
    if steps >= 1:
        decipher_result = await run_step1(query, modules)
        
        # Extract Hebrew terms from result
        if decipher_result is not None:
            if hasattr(decipher_result, 'hebrew_terms') and decipher_result.hebrew_terms:
                hebrew_terms = decipher_result.hebrew_terms
            elif hasattr(decipher_result, 'hebrew_term') and decipher_result.hebrew_term:
                hebrew_terms = [decipher_result.hebrew_term]
    
    # Use query as fallback for Hebrew terms
    if not hebrew_terms:
        hebrew_terms = [query]
    
    # Step 2: Understand
    if steps >= 2:
        analysis = await run_step2(query, hebrew_terms, modules, decipher_result)
    
    # Step 3: Search
    if steps >= 3:
        search_result = await run_step3(analysis, modules)
        
        # Write output
        if search_result is not None and not search_result.needs_clarification:
            write_results(search_result, query, modules)
    
    # Final summary
    print_header("PIPELINE COMPLETE", char="═")
    print(f"  Steps run: {steps}")
    print(f"  Step 1 (Decipher): {'✓' if decipher_result else '–'}")
    print(f"  Step 2 (Understand): {'✓' if analysis else '–'}")
    print(f"  Step 3 (Search): {'✓' if search_result else '–'}")
    
    return decipher_result, analysis, search_result


# =============================================================================
#  INTERACTIVE MODE
# =============================================================================

async def interactive_mode(modules: dict = None) -> None:
    """Run in interactive console mode."""
    if modules is None:
        modules = import_modules()
    
    # Current settings
    current_steps = 3
    
    print_header("OHR HANER V3 - Interactive Console", char="═")
    print("""
Commands:
  <query>         Run a query through the pipeline
  steps <n>       Set number of steps to run (1, 2, or 3)
  status          Show current settings
  help            Show this help
  quit / q        Exit

Examples:
  > migu
  > chezkas haguf vs chezkas mammon
  > steps 2
  > show me rashi on pesachim 4b
""")
    
    while True:
        try:
            # Show current steps in prompt
            user_input = input(f"\n[steps={current_steps}] > ").strip()
            
            if not user_input:
                continue
            
            # Handle commands
            cmd_lower = user_input.lower()
            
            if cmd_lower in ['q', 'quit', 'exit']:
                print("Goodbye! 👋")
                break
            
            elif cmd_lower == 'help':
                print("""
Commands:
  <query>         Run a query through the pipeline
  steps <n>       Set number of steps to run (1, 2, or 3)
  status          Show current settings
  help            Show this help
  quit / q        Exit
""")
                continue
            
            elif cmd_lower == 'status':
                print(f"\nCurrent settings:")
                print(f"  Steps to run: {current_steps}")
                print(f"  Step 1 available: {modules['step1'] is not None}")
                print(f"  Step 2 available: {modules['step2'] is not None}")
                print(f"  Step 3 available: {modules['step3'] is not None}")
                continue
            
            elif cmd_lower.startswith('steps '):
                try:
                    n = int(user_input.split()[1])
                    if n in [1, 2, 3]:
                        current_steps = n
                        print(f"  ✓ Now running {current_steps} step(s)")
                    else:
                        print("  ⚠️  Steps must be 1, 2, or 3")
                except (ValueError, IndexError):
                    print("  ⚠️  Usage: steps <1|2|3>")
                continue
            
            elif cmd_lower.startswith('steps='):
                try:
                    n = int(cmd_lower.split('=')[1])
                    if n in [1, 2, 3]:
                        current_steps = n
                        print(f"  ✓ Now running {current_steps} step(s)")
                    else:
                        print("  ⚠️  Steps must be 1, 2, or 3")
                except (ValueError, IndexError):
                    print("  ⚠️  Usage: steps=<1|2|3>")
                continue
            
            # Otherwise, treat as query
            await run_pipeline(user_input, steps=current_steps, modules=modules)
            
        except KeyboardInterrupt:
            print("\nGoodbye! 👋")
            break
        except Exception as e:
            logger.error(f"Error: {e}")
            import traceback
            traceback.print_exc()


# =============================================================================
#  TEST QUERIES
# =============================================================================

async def run_test_queries(steps: int = 3) -> None:
    """Run a set of test queries."""
    modules = import_modules()
    
    test_cases = [
        ("migu", None),
        ("chezkas haguf vs chezkas mammon", ["חזקת הגוף", "חזקת ממון"]),
        ("show me rashi on pesachim 4b", None),
    ]
    
    for query, hebrew_terms in test_cases:
        print(f"\n{'='*70}")
        print(f"TEST: {query}")
        print(f"{'='*70}")
        
        try:
            await run_pipeline(
                query, 
                steps=steps, 
                modules=modules,
                hebrew_terms=hebrew_terms
            )
        except Exception as e:
            logger.error(f"Test failed: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "─" * 70)


# =============================================================================
#  MAIN
# =============================================================================

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Ohr Haner V3 Pipeline Console",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python console_full_pipeline.py                    # Interactive mode
  python console_full_pipeline.py "migu"             # Run specific query
  python console_full_pipeline.py --steps 2 "migu"   # Run only steps 1+2
  python console_full_pipeline.py --test             # Run test queries
  python console_full_pipeline.py --debug "migu"     # Debug mode
"""
    )
    
    parser.add_argument(
        "query", 
        nargs="*", 
        help="Query to run (or interactive if none)"
    )
    parser.add_argument(
        "--steps", "-s",
        type=int,
        choices=[1, 2, 3],
        default=3,
        help="Number of steps to run (default: 3)"
    )
    parser.add_argument(
        "--test", "-t",
        action="store_true",
        help="Run test queries"
    )
    parser.add_argument(
        "--debug", "-d",
        action="store_true",
        help="Enable debug logging"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_console_logging(debug=args.debug)
    
    # Run appropriate mode
    if args.test:
        asyncio.run(run_test_queries(steps=args.steps))
    elif args.query:
        query = " ".join(args.query)
        asyncio.run(run_pipeline(query, steps=args.steps))
    else:
        asyncio.run(interactive_mode())


if __name__ == "__main__":
    main()