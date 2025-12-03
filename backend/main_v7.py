"""
Marei Mekomos V7 - Main Orchestrator
=====================================

Clean rebuild based on Architecture.md:
- Step 1: DECIPHER (transliteration → Hebrew)
- Step 2: UNDERSTAND (Hebrew → Intent + Strategy)  [TODO]
- Step 3: SEARCH (Intent + Strategy → Sources)      [TODO]

Currently: Step 1 only
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, Optional

# Add to path
sys.path.append(str(Path(__file__).parent))

from step_one_decipher import decipher
from logging_config import setup_logging, get_logger

# Initialize logging
setup_logging()
logger = get_logger(__name__)


# ==========================================
#  MAIN PIPELINE
# ==========================================

async def search_sources(query: str, clarification: Optional[str] = None) -> Dict:
    """
    Main pipeline for Marei Mekomos V7.
    
    Args:
        query: User's input (transliteration or Hebrew)
        clarification: Optional user response to clarification questions
    
    Returns:
        Complete search results (will expand as we build Steps 2 and 3)
    """
    logger.info("="*100)
    logger.info(f"MAREI MEKOMOS V7 - NEW SEARCH")
    logger.info(f"Query: '{query}'")
    if clarification:
        logger.info(f"Clarification: '{clarification}'")
    logger.info("="*100)
    
    # ========================================
    # STEP 1: DECIPHER
    # ========================================
    
    logger.info("\n" + ">"*80)
    logger.info("STEP 1: DECIPHER")
    logger.info(">"*80)
    
    step_one_result = await decipher(query)
    
    if not step_one_result["success"]:
        logger.warning("Step 1 failed or needs clarification")
        
        return {
            "step_completed": 1,
            "needs_clarification": True,
            "message": step_one_result.get("message", ""),
            "alternatives": step_one_result.get("alternatives", []),
            "step_one_result": step_one_result
        }
    
    logger.info(f"\n✓ Step 1 Complete")
    logger.info(f"  Hebrew term: {step_one_result['hebrew_term']}")
    logger.info(f"  Method: {step_one_result['method']}")
    logger.info(f"  Confidence: {step_one_result['confidence']}")
    
    # ========================================
    # STEP 2: UNDERSTAND [TODO]
    # ========================================
    
    logger.info("\n" + ">"*80)
    logger.info("STEP 2: UNDERSTAND - [NOT YET IMPLEMENTED]")
    logger.info(">"*80)
    logger.info("  → Will determine query intent and search strategy")
    
    # Placeholder
    step_two_result = {
        "intent": "unknown",
        "strategy": "tbd",
        "layers_needed": [],
        "message": "Step 2 not yet implemented"
    }
    
    # ========================================
    # STEP 3: SEARCH [TODO]
    # ========================================
    
    logger.info("\n" + ">"*80)
    logger.info("STEP 3: SEARCH - [NOT YET IMPLEMENTED]")
    logger.info(">"*80)
    logger.info("  → Will execute search based on strategy from Step 2")
    
    # Placeholder
    step_three_result = {
        "sources": [],
        "message": "Step 3 not yet implemented"
    }
    
    # ========================================
    # RETURN RESULTS
    # ========================================
    
    logger.info("\n" + "="*100)
    logger.info("PIPELINE COMPLETE (Step 1 only for now)")
    logger.info("="*100)
    
    return {
        "step_completed": 1,
        "success": True,
        "query": query,
        "step_one": step_one_result,
        "step_two": step_two_result,
        "step_three": step_three_result,
        "message": "Step 1 complete. Steps 2 and 3 coming soon."
    }


# ==========================================
#  CONVENIENCE FUNCTIONS
# ==========================================

async def quick_test(query: str):
    """Quick test of the pipeline"""
    print(f"\n{'='*80}")
    print(f"QUICK TEST: '{query}'")
    print(f"{'='*80}\n")
    
    result = await search_sources(query)
    
    print(f"\n{'='*80}")
    print("RESULT")
    print(f"{'='*80}")
    
    if result.get("needs_clarification"):
        print(f"❓ Needs clarification: {result.get('message', '')}")
        if result.get("alternatives"):
            print(f"   Alternatives: {result['alternatives'][:3]}")
    else:
        print(f"✓ Pipeline Status: Step {result['step_completed']} complete")
        
        if result.get("step_one"):
            s1 = result["step_one"]
            print(f"\nStep 1 (DECIPHER):")
            print(f"  Hebrew: {s1.get('hebrew_term', '')}")
            print(f"  Method: {s1.get('method', '')}")
            print(f"  Confidence: {s1.get('confidence', '')}")
        
        print(f"\nNote: Steps 2 and 3 not yet implemented")


# ==========================================
#  MAIN
# ==========================================

async def main():
    """Main entry point"""
    
    print("=" * 100)
    print("MAREI MEKOMOS V7 - GROUND-UP REBUILD")
    print("=" * 100)
    print()
    print("Status:")
    print("  ✓ Step 1 (DECIPHER) - Complete and tested")
    print("  ⏳ Step 2 (UNDERSTAND) - Coming next")
    print("  ⏳ Step 3 (SEARCH) - Coming after Step 2")
    print()
    
    # Example queries
    test_queries = [
        "chezkas haguf",
        "bari vishma",
        "shaviya anafshe",
    ]
    
    print(f"Testing with {len(test_queries)} queries...\n")
    
    for query in test_queries:
        await quick_test(query)
        print()


if __name__ == "__main__":
    asyncio.run(main())