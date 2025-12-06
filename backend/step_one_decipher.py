"""
Step 1: DECIPHER - FIXED VERSION
=================================

Transliteration → Hebrew using:
1. Word Dictionary (instant cache) - FREE
2. Transliteration Map → Sefaria Validation - FREE

NO VECTOR SEARCH. NO CLAUDE.

Why this works:
- Dictionary catches known terms instantly
- Transliteration map generates candidate Hebrew spellings
- Sefaria validates which spelling actually exists in Torah texts
- Most common spelling wins
"""

import sys
import os
import re
import asyncio
from pathlib import Path
from typing import Dict, List, Optional

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from tools.word_dictionary import get_dictionary
from tools.transliteration_map import (
    generate_hebrew_variants,
    generate_smart_variants,
    transliteration_confidence,
    normalize_query
)
from tools.sefaria_validator import get_validator

import logging
logger = logging.getLogger(__name__)


# ==========================================
#  HEBREW NORMALIZATION
# ==========================================

def normalize_hebrew(text: str) -> str:
    """Normalize Hebrew for comparison"""
    if not text:
        return ""
    # Remove spaces and punctuation
    text = re.sub(r'[\s,.;:!?()\[\]{}"\'\-]', '', text)
    # Normalize final forms
    finals = {'ך': 'כ', 'ם': 'מ', 'ן': 'נ', 'ף': 'פ', 'ץ': 'צ'}
    for f, s in finals.items():
        text = text.replace(f, s)
    # Remove niqqud
    text = re.sub(r'[\u0591-\u05C7]', '', text)
    return text


# ==========================================
#  MAIN DECIPHER FUNCTION
# ==========================================

async def decipher(query: str) -> Dict:
    """
    Turn user's transliteration into Hebrew.
    
    Flow:
    1. Check dictionary (instant)
    2. Generate variants via transliteration map
    3. Validate variants against Sefaria
    4. Return best match
    
    Returns:
        {
            "success": True/False,
            "hebrew_term": "מיגו",
            "confidence": "high/medium/low",
            "method": "dictionary/sefaria",
            "message": "...",
            "alternatives": ["מגו", ...]  # Other valid options
        }
    """
    logger.info("="*80)
    logger.info("STEP 1: DECIPHER")
    logger.info("="*80)
    logger.info(f"Query: '{query}'")
    
    # Normalize query
    query_normalized = normalize_query(query)
    logger.info(f"Normalized: '{query_normalized}'")
    
    # ==========================================
    # TOOL 1: Dictionary Lookup (instant, free)
    # ==========================================
    logger.info("\n[TOOL 1] Word Dictionary - Checking cache...")
    
    dictionary = get_dictionary()
    dict_result = dictionary.lookup(query_normalized)
    
    if dict_result and dict_result.get("confidence") in ["high", "medium"]:
        hebrew = dict_result["hebrew"]
        confidence = dict_result["confidence"]
        
        logger.info(f"✓ DICTIONARY HIT! {hebrew}")
        logger.info(f"  Confidence: {confidence}")
        logger.info(f"  Usage: {dict_result.get('usage_count', 0)} times")
        
        return {
            "success": True,
            "hebrew_term": hebrew,
            "confidence": confidence,
            "method": "dictionary",
            "message": f"Found in dictionary: {hebrew}",
            "alternatives": [],
            "needs_clarification": False
        }
    
    logger.info("  → Dictionary miss, continuing to transliteration...")
    
    # ==========================================
    # TOOL 2: Transliteration Map → Generate Variants
    # ==========================================
    logger.info("\n[TOOL 2] Transliteration Map - Generating Hebrew variants...")
    
    # Generate smart variants first (fewer, higher quality)
    variants = generate_smart_variants(query_normalized, max_variants=20)
    logger.info(f"  Generated {len(variants)} variants")
    
    # If too few, try full generation
    if len(variants) < 3:
        full_variants = generate_hebrew_variants(query_normalized, max_variants=30)
        for v in full_variants:
            if v not in variants:
                variants.append(v)
        logger.info(f"  Extended to {len(variants)} variants")
    
    if variants:
        logger.info(f"  Variants: {variants[:5]}{'...' if len(variants) > 5 else ''}")
    
    if not variants:
        logger.warning("  ✗ Could not generate Hebrew variants")
        return {
            "success": False,
            "needs_clarification": True,
            "message": "Could not generate Hebrew spellings. Try different spelling?"
        }
    
    # ==========================================
    # TOOL 3: Sefaria Validation → Pick Best Variant
    # ==========================================
    logger.info("\n[TOOL 3] Sefaria Validation - Checking which variants exist...")
    
    validator = get_validator()
    best = await validator.find_best_variant(variants)
    
    if best:
        hebrew = best["term"]
        hits = best["hits"]
        
        # Determine confidence based on hit count
        if hits >= 100:
            confidence = "high"
        elif hits >= 10:
            confidence = "medium"
        else:
            confidence = "low"
        
        logger.info(f"  ✓ Best variant: '{hebrew}' ({hits} hits)")
        logger.info(f"  Confidence: {confidence}")
        
        if best.get("sample_refs"):
            logger.info(f"  Sample: {best['sample_refs'][0]}")
        
        # Add to dictionary for future lookups
        dictionary.add_entry(
            query_normalized,
            hebrew,
            confidence=confidence,
            source="sefaria"
        )
        logger.info(f"  ✓ Added to dictionary")
        
        # Get alternatives (other valid variants)
        all_valid = await validator.validate_variants(variants)
        alternatives = [r["term"] for r in all_valid[1:5] if r["hits"] > 0]
        
        return {
            "success": True,
            "hebrew_term": hebrew,
            "confidence": confidence,
            "method": "sefaria",
            "hits": hits,
            "source_ref": best.get("sample_refs", [""])[0],
            "message": f"Found: {hebrew} ({hits} occurrences in Sefaria)",
            "alternatives": alternatives,
            "needs_clarification": False
        }
    
    # No valid variant found
    logger.warning("  ✗ No variants found in Sefaria corpus")
    
    # Return variants for user to choose
    return {
        "success": False,
        "needs_clarification": True,
        "message": "Could not validate spelling. Which did you mean?",
        "hebrew_variants": variants[:5],
        "alternatives": variants[:5]
    }


# ==========================================
#  SYNC WRAPPER
# ==========================================

def decipher_sync(query: str) -> Dict:
    """Synchronous wrapper for decipher"""
    return asyncio.run(decipher(query))


# ==========================================
#  TESTING
# ==========================================

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    async def test():
        test_queries = [
            "migu",
            "umdena", 
            "kdai shiur",
            "kal vchomer",
            "binyan av",
            "sfek sfeika",
            "kesubos",  # Should hit dictionary
        ]
        
        print("\n" + "="*60)
        print("STEP 1 DECIPHER - TEST")
        print("="*60)
        
        for query in test_queries:
            print(f"\n{'='*40}")
            result = await decipher(query)
            
            if result["success"]:
                print(f"✓ '{query}' → {result['hebrew_term']}")
                print(f"  Method: {result['method']}, Confidence: {result['confidence']}")
            else:
                print(f"✗ '{query}' - {result.get('message', 'Failed')}")
                if result.get("alternatives"):
                    print(f"  Alternatives: {result['alternatives']}")
    
    asyncio.run(test())