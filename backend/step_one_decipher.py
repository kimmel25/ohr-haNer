"""
Step 1: DECIPHER - V4 Architecture (Mixed Query Support)
=========================================================

Transliteration → Hebrew using:
1. Mixed Query Detection (NEW in V4)
2. Word Dictionary (instant cache) - FREE
3. Transliteration Map V3 with:
   - Input normalization (typo tolerance)
   - Prefix detection (she+root handling)
   - Preference-ordered variants (כתיב מלא first)
4. Sefaria Validation with "First Valid Wins" logic

NO VECTOR SEARCH. NO CLAUDE.

KEY ARCHITECTURAL CHANGES in V4:
- Detects mixed English/Hebrew queries ("what is chezkas haguf")
- Extracts Hebrew candidates from mixed queries
- Transliterates each candidate separately
- Returns multiple hebrew_terms for Step 2 to verify
- Double defense: Step 1 extracts, Step 2 (Claude) verifies

V4.1 FIX:
- Expanded ENGLISH_MARKERS with common verbs/adverbs
- Word-level candidate splitting and validation
- Better handling of mixed phrases like "ran learn up"
"""

import sys
import os
import re
import asyncio
from pathlib import Path
from typing import Dict, List, Optional

# Add current directory to path (for local imports)
sys.path.insert(0, str(Path(__file__).parent))

# Import Pydantic models (now works with local imports)
from models import DecipherResult, ConfidenceLevel

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
    from tools.transliteration_map import (
        generate_smart_variants,
        generate_hebrew_variants,
        transliteration_confidence,
        normalize_input
    )
    from sefaria_validator import get_validator

import logging
logger = logging.getLogger(__name__)


# ==========================================
#  MIXED QUERY DETECTION (V4.1 - EXPANDED)
# ==========================================

# English words that signal "this is a mixed query, not pure transliteration"
# These are words that would NEVER appear as Hebrew transliterations
# V4.1: EXPANDED with common verbs and adverbs
ENGLISH_MARKERS = {
    # Question words
    'what', 'which', 'how', 'why', 'when', 'where', 'who', 'whose',
    'does', 'do', 'did', 'is', 'are', 'was', 'were', 'can', 'could',
    'would', 'should', 'will',
    
    # Common verbs (V4.1: EXPANDED)
    'explain', 'describe', 'compare', 'define', 'tell', 'show',
    'find', 'get', 'give', 'list', 'search', 'look',
    'learn', 'study', 'teach', 'read', 'write', 'understand',
    'know', 'think', 'say', 'said', 'says', 'talk', 'discuss',
    'analyze', 'interpret', 'translate', 'mean', 'means',
    
    # Articles & prepositions  
    'the', 'a', 'an', 'of', 'in', 'on', 'at', 'to', 'for', 'from',
    'with', 'by', 'about', 'into', 'through', 'during', 'before',
    'after', 'above', 'below', 'between', 'under', 'again',
    
    # Adverbs & directions (V4.1: NEW)
    'up', 'down', 'out', 'over', 'off', 'away', 'back', 'here', 'there',
    'now', 'then', 'always', 'never', 'often', 'sometimes', 'usually',
    'very', 'too', 'quite', 'rather', 'just', 'only', 'also', 'even',
    
    # Conjunctions & comparisons
    'or', 'and', 'but', 'nor', 'yet', 'so',
    'vs', 'versus', 'than', 'as',
    'stronger', 'better', 'different', 'difference', 'same',
    'similar', 'like', 'unlike',
    
    # Common phrases
    'meaning', 'regarding', 'concerning',
    'me', 'i', 'my', 'you', 'your', 'we', 'our', 'they', 'their',
    'please', 'thanks', 'thank', 'help',
    
    # Pronouns & misc
    'this', 'that', 'these', 'those', 'it', 'its',
    'all', 'any', 'both', 'each', 'every', 'some', 'many', 'few',
    'more', 'most', 'other', 'such', 'no', 'not', 'only', 'own',
}

# Minimum English markers to trigger mixed-query mode
MIN_ENGLISH_MARKERS = 2


def is_mixed_query(query: str) -> bool:
    """
    Detect if query contains English + transliterated Hebrew.
    
    Returns True if 2+ English marker words found.
    
    Examples:
        "chezkas haguf" → False (pure transliteration)
        "what is chezkas haguf" → True (mixed)
        "explain migu" → True (mixed)
        "how does the ran learn up the sugya" → True (mixed)
    """
    words = query.lower().split()
    # Strip punctuation for matching
    clean_words = [re.sub(r'[?,.\'"!;:]', '', w) for w in words]
    english_count = sum(1 for w in clean_words if w in ENGLISH_MARKERS)
    
    is_mixed = english_count >= MIN_ENGLISH_MARKERS
    
    if is_mixed:
        logger.debug(f"Mixed query check: '{query}' → {english_count} English markers → MIXED")
    else:
        logger.debug(f"Mixed query check: '{query}' → {english_count} markers → PURE TRANSLITERATION")
    
    return is_mixed


# ==========================================
#  HEBREW CANDIDATE EXTRACTION (V4.1 - IMPROVED)
# ==========================================

async def extract_hebrew_candidates(text: str) -> List[str]:
    """
    Extract likely Hebrew transliterations from mixed English/Hebrew query.
    
    V4.1 IMPROVEMENTS:
    - Word-level splitting and validation
    - Don't bundle English words with Hebrew terms
    - Validate individual words, not just phrases
    
    Strategy:
    1. Split on English markers to get segments
    2. For each segment, split into words
    3. Validate each word individually via Sefaria
    4. Return words that validate, not arbitrary phrases
    
    Examples:
        "how does the ran learn up the sugya of bittul chometz"
        → Segments: ["ran learn up", "sugya", "bittul chometz"]
        → Word validation: "ran"✓, "learn"✗, "up"✗, "sugya"✓, "bittul chometz"✓
        → Returns: ["ran", "sugya", "bittul chometz"]
    """
    logger.debug(f"[EXTRACT] Starting extraction from: '{text}'")
    
    words = text.split()
    
    # Step 1: Split into segments at English markers
    segments = []
    current_segment = []
    
    for word in words:
        if word.lower() in ENGLISH_MARKERS:
            # Flush current segment if we have one
            if current_segment:
                segments.append(current_segment)
                current_segment = []
        else:
            # Not a known English word - might be Hebrew
            current_segment.append(word)
    
    # Don't forget the last segment
    if current_segment:
        segments.append(current_segment)
    
    logger.debug(f"[EXTRACT] Split into {len(segments)} segments: {segments}")
    
    # Step 2: For each segment, validate words individually AND as phrases
    validator = get_validator()
    validated_candidates = []
    
    for segment in segments:
        if not segment:
            continue
            
        # Try full segment first (handles multi-word terms like "bittul chometz")
        full_phrase = ' '.join(segment)
        logger.debug(f"[EXTRACT] Checking full phrase: '{full_phrase}'")
        
        # Quick transliteration check for the phrase
        variants = generate_hebrew_variants(full_phrase, max_variants=5)
        if variants:
            first_variant = variants[0]
            result = await validator.validate_term(first_variant)
            if result and result.get('hits', 0) > 0:
                logger.debug(f"[EXTRACT]   ✓ Full phrase '{full_phrase}' validated ({result['hits']} hits)")
                validated_candidates.append(full_phrase)
                continue  # Don't split if the whole phrase works
        
        # If phrase doesn't validate, try individual words
        logger.debug(f"[EXTRACT]   ✗ Full phrase didn't validate, trying individual words...")
        for word in segment:
            if len(word) <= 1:
                continue
                
            # Skip if it's a pure English word we somehow missed
            if word.lower() in ENGLISH_MARKERS:
                continue
            
            # Try to validate this individual word
            logger.debug(f"[EXTRACT]   Checking word: '{word}'")
            word_variants = generate_hebrew_variants(word, max_variants=5)
            if word_variants:
                first_variant = word_variants[0]
                result = await validator.validate_term(first_variant)
                if result and result.get('hits', 0) > 0:
                    logger.debug(f"[EXTRACT]     ✓ Word '{word}' validated ({result['hits']} hits)")
                    validated_candidates.append(word)
                else:
                    logger.debug(f"[EXTRACT]     ✗ Word '{word}' failed validation")
    
    # Remove duplicates while preserving order
    seen = set()
    unique_candidates = []
    for c in validated_candidates:
        if c not in seen:
            seen.add(c)
            unique_candidates.append(c)
    
    logger.info(f"[EXTRACT] Extracted validated Hebrew candidates: {unique_candidates}")
    return unique_candidates


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

def determine_confidence(hits: int, method: str) -> ConfidenceLevel:
    """
    Determine confidence level based on hit count and method.

    Args:
        hits: Number of Sefaria hits
        method: How the term was found ("dictionary", "sefaria", etc.")

    Returns:
        ConfidenceLevel enum
    """
    if method == "dictionary":
        return ConfidenceLevel.HIGH

    # Sefaria-based confidence
    if hits >= 100:
        return ConfidenceLevel.HIGH
    elif hits >= 10:
        return ConfidenceLevel.MEDIUM
    elif hits >= 1:
        return ConfidenceLevel.LOW
    else:
        return ConfidenceLevel.LOW


# ==========================================
#  SINGLE TERM DECIPHER (for each candidate)
# ==========================================

async def decipher_single(query: str) -> DecipherResult:
    """
    Decipher a single transliteration term.
    
    This is the core V3 logic, used for:
    - Pure transliteration queries
    - Each candidate extracted from mixed queries
    
    Tools (cascading):
    1. Word Dictionary (cache) - FREE, instant
    2. Transliteration Map - FREE, generates variants
    3. Sefaria Validation - FREE, validates against corpus
    
    Returns DecipherResult with success/hebrew_term/confidence.
    """
    logger.info(f"[DECIPHER_SINGLE] Processing: '{query}'")
    
    # Normalize input
    normalized_query = normalize_input(query)
    logger.debug(f"  Normalized: '{normalized_query}'")
    
    # ========================================
    # TOOL 1: Word Dictionary (Cache)
    # ========================================
    logger.debug(f"  [TOOL 1] Word Dictionary - Checking cache...")
    dictionary = get_dictionary()
    cached_result = dictionary.lookup(normalized_query)
    
    if cached_result:
        hebrew_term = cached_result['hebrew']
        hits = cached_result.get('hits', 999)  # Assume high if cached
        logger.info(f"    ✓ Dictionary HIT: '{normalized_query}' → '{hebrew_term}'")
        
        return DecipherResult(
            success=True,
            hebrew_term=hebrew_term,
            hebrew_terms=[hebrew_term],
            confidence=ConfidenceLevel.HIGH,
            method="dictionary",
            message=f"Found in dictionary cache",
            is_mixed_query=False,
            original_query=query,
            extraction_confident=True
        )
    
    logger.debug(f"    → Dictionary miss, continuing to transliteration...")
    
    # ========================================
    # TOOL 2: Transliteration Map
    # ========================================
    logger.debug(f"  [TOOL 2] Transliteration Map - Generating variants...")
    
    # Generate preference-ordered Hebrew variants
    variants = generate_hebrew_variants(normalized_query, max_variants=15)
    logger.debug(f"    Generated {len(variants)} variants")
    logger.debug(f"    Top variants: {variants[:5]}")
    
    if not variants:
        logger.warning(f"  No variants generated for '{query}'")
        return DecipherResult(
            success=False,
            hebrew_term=None,
            hebrew_terms=[],
            confidence=ConfidenceLevel.LOW,
            method="failed",
            message="Could not generate Hebrew variants",
            is_mixed_query=False,
            original_query=query,
            extraction_confident=False
        )
    
    # ========================================
    # TOOL 3: Sefaria Validation
    # ========================================
    logger.debug(f"  [TOOL 3] Sefaria Validation - Finding first valid term...")
    
    validator = get_validator()
    validation_result = await validator.find_first_valid(variants, min_hits=1)
    
    if not validation_result or not validation_result.get('found'):
        logger.warning(f"  No valid Hebrew term found for '{query}'")
        
        # Return first variant as a guess with LOW confidence
        return DecipherResult(
            success=False,
            hebrew_term=variants[0],
            hebrew_terms=[variants[0]],
            confidence=ConfidenceLevel.LOW,
            method="sefaria_no_hits",
            message=f"No results found in Sefaria. Using best guess: {variants[0]}",
            alternatives=variants[1:6],
            is_mixed_query=False,
            original_query=query,
            extraction_confident=False
        )
    
    # Success!
    hebrew_term = validation_result['term']  # FIX: Use 'term' not 'hebrew'
    hits = validation_result.get('hits', 0)
    sample_refs = validation_result.get('sample_refs', [])
    confidence = determine_confidence(hits, "sefaria")
    
    logger.info(f"  ✓ SUCCESS: '{query}' → '{hebrew_term}' ({hits} hits, {confidence.value} confidence)")
    
    # Cache the result for next time
    dictionary.add(
        normalized_query,
        hebrew_term,
        hits=hits,
        confidence=confidence.value,
        source="sefaria",
    )
    
    return DecipherResult(
        success=True,
        hebrew_term=hebrew_term,
        hebrew_terms=[hebrew_term],
        confidence=confidence,
        method="sefaria",
        message=f"Found in Sefaria with {hits} references",
        alternatives=variants[1:6],  # Other options
        sample_refs=sample_refs,  # Include sample references
        is_mixed_query=False,
        original_query=query,
        extraction_confident=True
    )


# ==========================================
#  MAIN DECIPHER FUNCTION (V4 + V4.1)
# ==========================================

async def decipher(query: str) -> DecipherResult:
    """
    Main entry point for Step 1: Transliteration → Hebrew
    
    V4 FLOW:
    1. Check if mixed query (English + Hebrew)
    2. If mixed:
       - Extract Hebrew candidates (V4.1: with word-level validation)
       - Transliterate each candidate
       - Return all terms for Step 2 to verify
    3. If pure transliteration:
       - Use V3 single-term flow (dictionary → transliteration → Sefaria)
    
    V4.1 FIX:
    - Better candidate extraction that validates individual words
    - Doesn't bundle English with Hebrew terms
    
    Returns:
        DecipherResult with:
        - success: bool
        - hebrew_term: str (primary term)
        - hebrew_terms: List[str] (all terms, for mixed queries)
        - is_mixed_query: bool
        - confidence: ConfidenceLevel
        - method: str
    """
    logger.info("=" * 80)
    logger.info("STEP 1: DECIPHER (V4.1 - Word-Level Validation)")
    logger.info("=" * 80)
    logger.info(f"Query: '{query}'")
    
    # ========================================
    # V4: MIXED QUERY DETECTION
    # ========================================
    if is_mixed_query(query):
        logger.info("⚡ Mixed query detected - extracting and validating Hebrew candidates")
        
        # V4.1: New extraction logic that validates at word level
        candidates = await extract_hebrew_candidates(query)
        
        if not candidates:
            logger.warning("No valid Hebrew candidates extracted from mixed query")
            return DecipherResult(
                success=False,
                hebrew_term=None,
                hebrew_terms=[],
                confidence=ConfidenceLevel.LOW,
                method="mixed_extraction_failed",
                message="Could not extract Hebrew terms from the query",
                is_mixed_query=True,
                original_query=query,
                extraction_confident=False
            )
        
        logger.info(f"Processing {len(candidates)} validated candidates: {candidates}")
        
        # Transliterate each candidate
        all_hebrew_terms = []
        all_confidences = []
        
        for candidate in candidates:
            logger.info(f"  → Processing candidate: '{candidate}'")
            result = await decipher_single(candidate)
            
            if result.success or result.hebrew_term:
                all_hebrew_terms.append(result.hebrew_term)
                all_confidences.append(result.confidence)
                logger.info(f"    ✓ '{candidate}' → '{result.hebrew_term}' ({result.confidence.value})")
            else:
                logger.warning(f"    ✗ '{candidate}' failed to transliterate")
        
        # Determine overall confidence
        if all_confidences:
            # Use the lowest confidence (most conservative)
            min_conf = min(all_confidences, key=lambda c: ['high', 'medium', 'low'].index(c.value))
            overall_confidence = min_conf
        else:
            overall_confidence = ConfidenceLevel.LOW
        
        # Primary term is the first one (usually most important)
        primary_term = all_hebrew_terms[0] if all_hebrew_terms else None
        
        # V4.1: Higher extraction confidence since we validated at word level
        extraction_confident = len(all_hebrew_terms) == len(candidates)
        
        logger.info(f"✓ Mixed query complete: {len(all_hebrew_terms)} terms extracted")
        logger.info(f"  Primary: {primary_term}")
        logger.info(f"  All terms: {all_hebrew_terms}")
        logger.info(f"  Extraction confident: {extraction_confident}")
        
        return DecipherResult(
            success=bool(all_hebrew_terms),
            hebrew_term=primary_term,
            hebrew_terms=all_hebrew_terms,
            confidence=overall_confidence,
            method="mixed_extraction",
            message=f"Extracted {len(all_hebrew_terms)} Hebrew terms from mixed query",
            is_mixed_query=True,
            original_query=query,
            extraction_confident=extraction_confident
        )
    
    # ========================================
    # V3: PURE TRANSLITERATION (unchanged)
    # ========================================
    else:
        logger.info("Pure transliteration query - using V3 cascade")
        result = await decipher_single(query)
        
        # Ensure hebrew_terms is populated for consistency
        if result.success and result.hebrew_term and not result.hebrew_terms:
            result.hebrew_terms = [result.hebrew_term]
        
        return result


# ==========================================
#  QUICK TEST
# ==========================================

async def quick_test():
    """Quick test of the decipher function."""
    test_queries = [
        # V3 pure transliteration
        "chezkas haguf",
        "migu",
        
        # V4 mixed queries
        "what is chezkas haguf",
        "explain migu",
        
        # V4.1 fix - the problematic query
        "how does the ran learn up the sugya of bittul chometz",
    ]
    
    for query in test_queries:
        print(f"\n{'='*80}")
        print(f"Testing: '{query}'")
        print(f"{'='*80}")
        
        result = await decipher(query)
        
        print(f"\nResult:")
        print(f"  Success: {result.success}")
        print(f"  Hebrew: {result.hebrew_term}")
        if len(result.hebrew_terms) > 1:
            print(f"  All terms: {result.hebrew_terms}")
        print(f"  Confidence: {result.confidence.value}")
        print(f"  Method: {result.method}")
        print(f"  Is mixed: {result.is_mixed_query}")
        if result.message:
            print(f"  Message: {result.message}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    asyncio.run(quick_test())
