"""Test script for V10 contextual filter fix."""
import asyncio
import sys
import logging
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

# Set up logging to file to avoid console Unicode issues
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler('test_v10_fix.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

from step_one_decipher import decipher
from step_two_understand import understand
from step_three_search import search

async def test_bedikas_chometz():
    """Test the full pipeline with bedikas chometz."""

    query = "bedikas chometz"
    logger.info("="*60)
    logger.info(f"Testing: {query}")
    logger.info("="*60)

    # Step 1: Decipher
    logger.info("Step 1: DECIPHER")
    step1_result = await decipher(query)
    logger.info(f"  Success: {step1_result.success}")

    # Step 2: Understand
    logger.info("Step 2: UNDERSTAND")
    hebrew_terms = [step1_result.hebrew_term] if step1_result.hebrew_term else []
    strategy = await understand(
        hebrew_terms=hebrew_terms,
        query=query,
        decipher_result=step1_result
    )
    logger.info(f"  Query Type: {strategy.query_type}")
    logger.info(f"  Target Authors: {strategy.target_authors}")

    # Step 3: Search
    logger.info("Step 3: SEARCH")
    search_result = await search(strategy)
    logger.info(f"  Total Sources: {search_result.total_sources}")
    logger.info(f"  Levels Found: {search_result.levels_found}")
    logger.info(f"  Discovered Dapim (first 5): {search_result.discovered_dapim[:5]}")

    # Check output directory
    output_dir = Path(__file__).parent / "output"
    if output_dir.exists():
        files = list(output_dir.glob("*.txt"))
        logger.info(f"  Output files created: {len(files)}")
        if files:
            latest = max(files, key=lambda p: p.stat().st_mtime)
            logger.info(f"  Latest: {latest.name}")
    else:
        logger.warning("  Output directory not found")

    logger.info("="*60)
    logger.info("TEST COMPLETE")
    logger.info("="*60)

    return search_result

if __name__ == "__main__":
    result = asyncio.run(test_bedikas_chometz())
    logger.info(f"\nFinal count: {result.total_sources} sources")
    if result.total_sources == 0:
        logger.error("FAILED: No sources found!")
        sys.exit(1)
    else:
        logger.info("SUCCESS: Sources found!")
        sys.exit(0)
