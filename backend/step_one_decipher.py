"""
Step 1: DECIPHER - V3 Architecture
===================================

Transliteration → Hebrew using:
1. Word Dictionary (instant cache) - FREE
2. Transliteration Map V3 with:
   - Input normalization (typo tolerance)
   - Prefix detection (she+root handling)
   - Preference-ordered variants (כתיב מלא first)
3. Sefaria Validation with "First Valid Wins" logic

NO VECTOR SEARCH. NO CLAUDE.

KEY ARCHITECTURAL CHANGES in V3:
- Input is normalized FIRST (lolam → leolam)
- Prefixes are detected and handled (shenagach → ש+נגח)
- Variants generated in preference order
- Sefaria returns FIRST valid, not highest hits
"""

import sys
import os
import re
import asyncio
from pathlib import Path
from typing import Dict, List, Optional

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent))

# Import our V3 modules
try:
    # Try relative import (when run as part of backend)
    from tools.word_dictionary import get_dictionary
    from tools.transliteration_map import (
        generate_smart_variants,
        generate_hebrew_variants,
        transliteration_confidence,
        normalize_input
    )
    from tools.sefaria_validator import get_validator
except ImportError:
    # Fallback for standalone testing
    from word_dictionary import get_dictionary
    from transliteration_map_v3 import (
        generate_smart_variants,
        generate_hebrew_variants,
        transliteration_confidence,
        normalize_input
    )
    from sefaria_validator_v2 import get_validator

import logging
logger = logging.getLogger(__name__)


# ==========================================
#  HEBREW NORMALIZATION (for comparison)
# ==========================================

def normalize_hebrew(text: str) -> str:
    """Normalize Hebrew for comparison."""
    if not text:
        return ""
    # Remove spaces and punctuation
    text = re.sub(r'[\s,.;:!?()\[\]{}"\'\-]', '', text)
    # Normalize final forms for comparison
    finals = {'ך': 'כ', 'ם': 'מ', 'ן': 'נ', 'ף': 'פ', 'ץ': 'צ'}
    for f, s in finals.items():
        text = text.replace(f, s)
    # Remove niqqud
    text = re.sub(r'[\u0591-\u05C7]', '', text)
    return text


# ==========================================
#  CONFIDENCE DETERMINATION
# ==========================================

def determine_confidence(hits: int, method: str) -> str:
    """
    Determine confidence level based on hit count and method.
    
    Args:
        hits: Number of Sefaria hits
        method: How the term was found ("dictionary", "sefaria", etc.)
    
    Returns:
        "high", "medium", or "low"
    """
    if method == "dictionary":
        return "high"
    
    # Sefaria-based confidence
    if hits >= 100:
        return "high"
    elif hits >= 20:
        return "medium"
    else:
        return "low"


# ==========================================
#  MAIN DECIPHER FUNCTION
# ==========================================

async def decipher(query: str) -> Dict:
    """
    Turn user's transliteration into Hebrew.
    
    V3 Flow:
    1. Normalize input (fix typos like lolam → leolam)
    2. Check dictionary (instant lookup)
    3. Generate variants (with prefix detection, in preference order)
    4. Validate with Sefaria (first valid wins)
    5. Return result
    
    Args:
        query: User's input (transliteration or Hebrew)
    
    Returns:
        {
            "success": True/False,
            "hebrew_term": "מיגו",
            "confidence": "high/medium/low",
            "method": "dictionary/sefaria/transliteration",
            "message": "...",
            "alternatives": [...],
            "needs_clarification": False
        }
    """
    logger.info("=" * 80)
    logger.info("STEP 1: DECIPHER (V3)")
    logger.info("=" * 80)
    logger.info(f"Query: '{query}'")
    
    # ==========================================
    # STEP 0: Normalize Input
    # ==========================================
    query_normalized = normalize_input(query)
    
    if query_normalized != query.lower().strip():
        logger.info(f"Normalized: '{query_normalized}' (from '{query}')")
    else:
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
    logger.info("\n[TOOL 2] Transliteration Map V3 - Generating variants...")
    
    # Generate variants in PREFERENCE ORDER (כתיב מלא first)
    variants = generate_smart_variants(query_normalized, max_variants=15)
    
    logger.info(f"  Generated {len(variants)} variants (in preference order)")
    if variants:
        logger.info(f"  Top variants: {variants[:5]}{'...' if len(variants) > 5 else ''}")
    
    if not variants:
        logger.warning("  ✗ Could not generate Hebrew variants")
        return {
            "success": False,
            "needs_clarification": True,
            "message": "Could not generate Hebrew spellings. Try different spelling?",
            "hebrew_term": None,
            "confidence": "low",
            "method": "unknown",
            "alternatives": []
        }
    
    # ==========================================
    # TOOL 3: Sefaria Validation (First Valid Wins)
    # ==========================================
    logger.info("\n[TOOL 3] Sefaria Validation - Finding first valid term...")
    
    validator = get_validator()
    
    # KEY CHANGE: Use find_first_valid(), not find_best_variant()
    # This returns the FIRST variant with any hits, preserving our preference order
    best_result = await validator.find_first_valid(variants, min_hits=1)
    
    if best_result and best_result.get("found"):
        hebrew = best_result["term"]
        hits = best_result.get("hits", 0)
        sample_refs = best_result.get("sample_refs", [])
        
        confidence = determine_confidence(hits, "sefaria")
        
        logger.info(f"  ✓ Found valid term: '{hebrew}' ({hits} hits)")
        logger.info(f"  Confidence: {confidence}")
        if sample_refs:
            logger.info(f"  Sample: {sample_refs[0]}")
        
        # Learn this for next time
        dictionary.add_entry(
            transliteration=query_normalized,
            hebrew=hebrew,
            confidence=confidence,
            source="sefaria"
        )
        logger.info(f"  ✓ Added to dictionary for future lookups")
        
        return {
            "success": True,
            "hebrew_term": hebrew,
            "confidence": confidence,
            "method": "sefaria",
            "message": f"Found in Sefaria: {hebrew} ({hits} occurrences)",
            "alternatives": [v for v in variants if v != hebrew][:5],
            "needs_clarification": False,
            "sample_refs": sample_refs
        }
    
    # ==========================================
    # FALLBACK: Return best guess without validation
    # ==========================================
    logger.warning("  ✗ No variants found in Sefaria corpus")
    
    # If Sefaria found nothing, return the first (best) variant anyway
    # but with low confidence
    best_guess = variants[0] if variants else None
    
    if best_guess:
        logger.info(f"  Returning best guess: '{best_guess}' (unvalidated)")
        
        return {
            "success": True,
            "hebrew_term": best_guess,
            "confidence": "low",
            "method": "transliteration",
            "message": f"Best transliteration guess: {best_guess} (not found in Sefaria)",
            "alternatives": variants[1:6],
            "needs_clarification": True
        }
    
    # Complete failure
    return {
        "success": False,
        "needs_clarification": True,
        "message": "Could not determine Hebrew spelling",
        "hebrew_term": None,
        "confidence": "low",
        "method": "unknown",
        "alternatives": variants[:5] if variants else []
    }


# ==========================================
#  SYNC WRAPPER
# ==========================================

def decipher_sync(query: str) -> Dict:
    """Synchronous wrapper for decipher."""
    return asyncio.run(decipher(query))


# ==========================================
#  TESTING
# ==========================================

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    async def test():
        print("\n" + "=" * 70)
        print("STEP 1 DECIPHER V3 - TEST")
        print("=" * 70)
        
        # The 6 originally failing tests
        test_cases = [
            ("migu", "מיגו"),
            ("gezeira shava", "גזירה שווה"),
            ("davar halamd meinyano", "דבר הלמד מעניינו"),
            ("tzad hashaveh", "צד השווה"),
            ("shor hamuad shenagach", "שור המועד שנגח"),
            ("ain adam oser davar shelo ba lolam", "אין אדם אוסר דבר שלא בא לעולם"),
        ]
        
        passed = 0
        failed = 0
        
        for query, expected in test_cases:
            print(f"\n{'='*60}")
            result = await decipher(query)
            
            got = result.get("hebrew_term", "N/A")
            success = (got == expected) or (expected in result.get("alternatives", []))
            
            if success:
                passed += 1
                status = "✓ PASS"
            else:
                failed += 1
                status = "✗ FAIL"
            
            print(f"\n{status}: '{query}'")
            print(f"  Expected: {expected}")
            print(f"  Got: {got}")
            print(f"  Method: {result.get('method')}")
            print(f"  Confidence: {result.get('confidence')}")
        
        print(f"\n{'='*70}")
        print(f"RESULTS: {passed}/{passed + failed} passed")
        print("=" * 70)
    
    asyncio.run(test())