"""
Step 1: DECIPHER - V4.3 Architecture (Multi-Term Dictionary Support)
=====================================================================

IMPROVEMENTS FROM V4.2:
1. MULTI-TERM DICTIONARY: Uses lookup_all() to find multiple terms
   - "chezkas haguf chezkas mammon" → ['חזקת הגוף', 'חזקת ממון']
   - No longer stops at first match!

2. AUTHOR-AWARE EXTRACTION: Skip phrase validation for known author names
   - Detects "ran", "rashi", "tosfos" etc. BEFORE trying phrase combinations
   - Prevents wasting API calls on "rans shittah" variants

3. AUTHOR-PRIORITY VALIDATION: Author names beat generic words
   - Uses find_best_validated_with_authors() from V3 validator
   - "רש"י" (133 hits) beats "ראשי" (10000 hits)

4. PARALLEL VALIDATION: Batch validation for phrases
   - Validates multiple variants concurrently
   - Significant speedup for multi-word phrases

5. CONNECTION POOLING: Reuses HTTP connections
   - Via V3 SefariaValidator with shared client

Architecture:
- Detects mixed queries (English + Hebrew)
- Extracts Hebrew candidates with author awareness
- Transliterates each candidate using cascade
- Returns validated Hebrew terms for Step 2

NO VECTOR SEARCH. NO CLAUDE.
"""

import sys
import os
import re
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Add current directory to path (for local imports)
sys.path.insert(0, str(Path(__file__).parent))

# Import Pydantic models
from models import DecipherResult, ConfidenceLevel

# Import V3 modules
try:
    from tools.word_dictionary import get_dictionary
    from tools.transliteration_map import (
        generate_smart_variants,
        generate_hebrew_variants,
        transliteration_confidence,
        normalize_input
    )
    from tools.sefaria_validator import get_validator
except ImportError:
    from word_dictionary import get_dictionary
    from transliteration_map import (
        generate_smart_variants,
        generate_hebrew_variants,
        transliteration_confidence,
        normalize_input
    )
    from sefaria_validator import get_validator

import logging
logger = logging.getLogger(__name__)


# ==========================================
#  LOGGING HELPERS
# ==========================================

def log_section(title: str) -> None:
    line = "=" * 90
    logger.info("\n%s\n%s\n%s", line, title, line)


def log_subsection(title: str) -> None:
    line = "-" * 70
    logger.info("\n%s\n%s\n%s", line, title, line)


def log_list(label: str, items: List[str]) -> None:
    if not items:
        return
    logger.info("%s:", label)
    for item in items:
        logger.info("  - %s", item)


# ==========================================
#  KNOWN AUTHOR TRANSLITERATIONS (V4.2 NEW)
# ==========================================

# Common English transliterations of author names
# These trigger "author mode" - skip phrase validation, treat as individual
AUTHOR_TRANSLITERATIONS = {
    # Rishonim - Commentators
    'rashi', 'rashis',
    'tosfos', 'tosafos', 'tosfot', 'tosafot', 'tosfoses',
    'ran', 'rans',
    'rosh', 'roshs',
    'rashba', 'rashbas',
    'ritva', 'ritvas',
    'ramban', 'rambans',
    'rambam', 'rambams',
    'meiri', 'meiris',
    'nimukei', 'nimukay',  # Nimukei Yosef
    'mordechai', 'mordechais',
    'rif', 'rifs',
    'rabbeinu', 'rabeinu',
    
    # Acharonim
    'shach', 'shachs',
    'taz', 'tazs',
    'magen', 'avraham',  # Magen Avraham
    'ketzos', 'ktzos', 'ketzot',
    'nesivos', 'nsivos', 'nesivot',
    'pnei', 'pney', 'peni',  # Pnei Yehoshua
    'maharsha', 'maharshas',
    'maharal', 'maharals',
    'maharam', 'maharams',
    'chavos', 'chavas', 'chavot',  # Chavos Daas
    
    # Common abbreviations
    'sma', 'sm"a',
    'gra', 'gr"a',
    'bach', 'bachs',
    'pri', 'megadim',  # Pri Megadim
}


def is_author_transliteration(word: str) -> bool:
    """
    Check if a word is a known author transliteration.
    
    This helps us avoid trying phrase validation for author names.
    E.g., "rans shittah" should NOT be tried as a phrase because
    "rans" is clearly an author name (Ran with possessive 's').
    """
    cleaned = word.lower().strip()
    
    # Direct match
    if cleaned in AUTHOR_TRANSLITERATIONS:
        return True
    
    # Check if stripping suffix matches
    stripped, _ = strip_english_suffixes(cleaned)
    if stripped in AUTHOR_TRANSLITERATIONS:
        return True
    
    return False


# ==========================================
#  ENGLISH MARKERS (Mixed Query Detection)
# ==========================================

ENGLISH_MARKERS = {
    # Question words
    'what', 'which', 'how', 'why', 'when', 'where', 'who', 'whose',
    'does', 'do', 'did', 'is', 'are', 'was', 'were', 'can', 'could',
    'would', 'should', 'will',

    # Common verbs
    'explain', 'describe', 'compare', 'define', 'tell', 'show',
    'find', 'get', 'give', 'list', 'search', 'look', 'looking',
    'learn', 'study', 'teach', 'read', 'write', 'understand',
    'know', 'think', 'say', 'said', 'says', 'talk', 'discuss',
    'analyze', 'interpret', 'translate', 'mean', 'means',
    'need', 'want', 'cover', 'covering', 'covered', 'covers',
    'have', 'has', 'had', 'having', 'been', 'being', 'be',

    # Articles & prepositions
    'the', 'a', 'an', 'of', 'in', 'on', 'at', 'to', 'for', 'from',
    'with', 'by', 'about', 'into', 'through', 'during', 'before',
    'after', 'above', 'below', 'between', 'under', 'again',

    # Adverbs & directions
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

    # Common English nouns that appear in Torah queries
    'sources', 'source', 'references', 'reference', 'texts', 'text',
    'women', 'woman', 'men', 'man', 'person', 'people',
    'hair', 'head', 'body', 'hand', 'hands', 'food', 'water', 'wine',
    'marriage', 'married', 'husband', 'wife', 'children', 'child',
    'prayer', 'prayers', 'praying', 'blessing', 'blessings',
    'sabbath', 'holiday', 'holidays', 'passover', 'purim',
    'law', 'laws', 'rule', 'rules', 'requirement', 'requirements',
    'obligation', 'obligations', 'forbidden', 'permitted', 'allowed',
    'reason', 'reasons', 'opinion', 'opinions', 'view', 'views',
    'concept', 'concepts', 'idea', 'ideas', 'topic', 'topics',
    'discussion', 'discussions', 'debate', 'debates',
}

MIN_ENGLISH_MARKERS = 2


def is_pure_english_query(query: str) -> bool:
    """
    Detect if a query is ENTIRELY English (asking about a topic in English).

    V4.5: Uses improved language_detector module for better classification.

    Examples that should return True:
    - "sources for women covering hair"
    - "what is the law about eating on Yom Kippur"
    - "why do we light candles on Shabbat"

    Examples that should return False (contain Hebrew transliteration):
    - "what is chezkas haguf"
    - "explain bari vishema"
    - "sources for kisui rosh"
    """
    # Try using the improved language detector
    try:
        from tools.language_detector import analyze_query, is_hebrew_transliteration
        analysis = analyze_query(query)

        logger.debug(f"[PURE_ENGLISH] Analysis: {analysis['english_count']} English, {analysis['hebrew_count']} Hebrew")
        for word, classification, reason in analysis['words']:
            logger.debug(f"  '{word}': {classification} ({reason})")

        # Pure English = no Hebrew words detected
        if analysis['is_pure_english']:
            logger.info(f"[PURE_ENGLISH] Query is pure English: '{query}'")
            return True

        # Even if not "pure", if there's no Hebrew and 3+ English words, treat as pure English
        if analysis['hebrew_count'] == 0 and analysis['english_count'] >= 3:
            logger.info(f"[PURE_ENGLISH] Query appears pure English (no Hebrew detected): '{query}'")
            return True

        return False

    except ImportError:
        logger.warning("[PURE_ENGLISH] language_detector not available, using fallback")
        # Fallback to original logic
        return _is_pure_english_fallback(query)


def _is_pure_english_fallback(query: str) -> bool:
    """Fallback detection when language_detector is not available."""
    words = query.lower().split()
    clean_words = [re.sub(r'[?,.\'"!;:]', '', w) for w in words]

    english_count = 0
    potential_hebrew_count = 0

    for word in clean_words:
        if not word or len(word) <= 1:
            continue

        if word in ENGLISH_MARKERS:
            english_count += 1
        elif word in AUTHOR_TRANSLITERATIONS:
            potential_hebrew_count += 1
        else:
            # Simple heuristic: Hebrew transliterations often have tz, ch patterns
            hebrew_indicators = ['tz', 'chm', 'chz', 'shv', 'shm']
            has_hebrew_indicator = any(ind in word for ind in hebrew_indicators)

            english_endings = ['ing', 'tion', 'ness', 'ment', 'able', 'ible', 'ous', 'ive', 'ly', 'ed']
            has_english_ending = any(word.endswith(end) for end in english_endings)

            if has_hebrew_indicator and not has_english_ending:
                potential_hebrew_count += 1
            elif has_english_ending:
                english_count += 1

    total_counted = english_count + potential_hebrew_count
    if total_counted == 0:
        return False

    english_ratio = english_count / total_counted if total_counted > 0 else 0
    is_pure_english = english_ratio >= 0.8 and english_count >= 3

    if is_pure_english:
        logger.debug(f"Pure English (fallback): '{query}' ({english_count} English, {potential_hebrew_count} Hebrew)")

    return is_pure_english


# ==========================================
#  ENGLISH SUFFIX STRIPPING
# ==========================================

def strip_english_suffixes(word: str) -> Tuple[str, bool]:
    """
    Strip common English grammatical suffixes from transliterated Hebrew terms.
    
    Examples:
        "rans" → ("ran", True)
        "rashis" → ("rashi", True)
        "tosfoses" → ("tosfos", True)
    """
    original = word.lower()
    
    # Explicit possessive with apostrophe
    if original.endswith("'s"):
        return (word[:-2], True)
    if original.endswith("s'"):
        return (word[:-2], True)
    
    # Handle "es" plural
    if original.endswith('es') and len(original) > 3:
        return (word[:-2], True)
    
    # Handle simple "s" suffix
    if original.endswith('s') and len(original) > 3:
        # DON'T strip if ends in 'os' (tosfos, malkos - natural)
        if original.endswith('os'):
            return (word, False)
        return (word[:-1], True)
    
    return (word, False)


def is_mixed_query(query: str) -> bool:
    """
    Detect if query contains English + transliterated Hebrew.
    Returns True if 2+ English marker words found.
    """
    words = query.lower().split()
    clean_words = [re.sub(r'[?,.\'"!;:]', '', w) for w in words]
    english_count = sum(1 for w in clean_words if w in ENGLISH_MARKERS)
    
    is_mixed = english_count >= MIN_ENGLISH_MARKERS
    
    if is_mixed:
        logger.debug(f"Mixed query check: '{query}' → {english_count} English markers → MIXED")
    else:
        logger.debug(f"Mixed query check: '{query}' → {english_count} markers → PURE TRANSLITERATION")
    
    return is_mixed


# ==========================================
#  AUTHOR-AWARE WEIGHTED VALIDATION (V4.2)
# ==========================================

async def find_best_validated(
    variants: List[str],
    validator,
    original_word: str = None,
    parallel: bool = True
) -> Optional[Dict]:
    """
    Find the BEST valid variant using author-aware weighted scoring.
    
    V4.2: Uses the new find_best_validated_with_authors() which:
    - Prioritizes author names over generic words
    - Validates in parallel for speed
    
    Falls back to legacy validation if new method unavailable.
    """
    # Try new author-aware validation
    if hasattr(validator, 'find_best_validated_with_authors'):
        return await validator.find_best_validated_with_authors(
            variants, 
            original_word=original_word,
            parallel=parallel
        )
    
    # Legacy fallback: weighted scoring without author awareness
    logger.debug(f"[WEIGHTED-VALIDATION] Checking {len(variants)} variants for '{original_word}'")
    
    best_score = 0
    best_result = None
    best_variant = None
    
    for variant in variants:
        result = await validator.validate_term(variant)
        hits = result.get('hits', 0)
        
        if hits == 0:
            continue
        
        # Calculate weighted score
        if hits >= 1000:
            score = hits * 20
            confidence = "very_high"
        elif hits >= 100:
            score = hits * 10
            confidence = "high"
        elif hits >= 10:
            score = hits * 5
            confidence = "medium"
        else:
            score = hits * 1
            confidence = "low"
        
        logger.debug(f"[WEIGHTED-VALIDATION]   {variant}: {hits} hits, score={score}, confidence={confidence}")
        
        if score > best_score:
            best_score = score
            best_result = result
            best_variant = variant
    
    if best_result:
        logger.info(f"[WEIGHTED-VALIDATION] ✓ Best match: '{best_variant}' ({best_result['hits']} hits, score={best_score})")
    else:
        logger.warning(f"[WEIGHTED-VALIDATION] ✗ No valid variants found")
    
    return best_result


# ==========================================
#  AUTHOR-AWARE EXTRACTION (V4.2 NEW)
# ==========================================

async def extract_hebrew_candidates(text: str) -> List[str]:
    """
    Extract likely Hebrew transliterations from mixed English/Hebrew query.
    
    V4.2 IMPROVEMENTS:
    - AUTHOR DETECTION: If a word is a known author name, treat it individually
      (don't try to combine with next word as phrase)
    - PARALLEL VALIDATION: Validate phrase variants in parallel
    - SMARTER PHRASE HANDLING: Only try phrases when both words are non-authors
    
    Strategy:
    1. Split on English markers to get segments
    2. For each segment:
       a. If first word is author name → extract individually, not as phrase
       b. Otherwise → try full phrase first, then individual words
    3. Validate each candidate
    """
    logger.debug(f"[EXTRACT] Starting extraction from: '{text}'")
    
    words = text.split()
    
    # Step 1: Split into segments at English markers
    segments = []
    current_segment = []
    
    for word in words:
        if word.lower() in ENGLISH_MARKERS:
            if current_segment:
                segments.append(current_segment)
                current_segment = []
        else:
            current_segment.append(word)
    
    if current_segment:
        segments.append(current_segment)
    
    logger.debug(f"[EXTRACT] Split into {len(segments)} segments: {segments}")
    
    # Step 2: Process each segment with author awareness
    validator = get_validator()
    validated_candidates = []
    
    for segment in segments:
        if not segment:
            continue
        
        # V4.2: Check if first word is an author name
        first_word = segment[0]
        first_word_cleaned, _ = strip_english_suffixes(first_word)
        first_is_author = is_author_transliteration(first_word_cleaned)
        
        if first_is_author:
            # AUTHOR MODE: Don't try phrase validation, process words individually
            logger.debug(f"[EXTRACT] Author detected: '{first_word_cleaned}' - processing segment individually")
            
            for word in segment:
                if len(word) <= 1:
                    continue
                if word.lower() in ENGLISH_MARKERS:
                    continue
                
                cleaned_word, was_stripped = strip_english_suffixes(word)
                if was_stripped:
                    logger.debug(f"[EXTRACT]   Stripped suffix: '{word}' → '{cleaned_word}'")
                
                # Validate individual word
                word_variants = generate_hebrew_variants(cleaned_word, max_variants=8)
                if word_variants:
                    result = await find_best_validated(word_variants, validator, cleaned_word, parallel=True)
                    if result and result.get('hits', 0) > 0:
                        logger.debug(f"[EXTRACT]     ✓ '{cleaned_word}' validated ({result['hits']} hits)")
                        validated_candidates.append(cleaned_word)
                    else:
                        logger.debug(f"[EXTRACT]     ✗ '{cleaned_word}' failed validation")
        else:
            # STANDARD MODE: Try full phrase first, then individual words
            full_phrase = ' '.join(segment)
            logger.debug(f"[EXTRACT] Checking full phrase: '{full_phrase}'")
            
            cleaned_phrase, phrase_stripped = strip_english_suffixes(full_phrase)
            if phrase_stripped:
                logger.debug(f"[EXTRACT]   Stripped suffix from phrase: '{full_phrase}' → '{cleaned_phrase}'")
                full_phrase = cleaned_phrase
            
            # Generate and validate phrase variants (in parallel)
            variants = generate_hebrew_variants(full_phrase, max_variants=8)
            if variants:
                result = await find_best_validated(variants, validator, full_phrase, parallel=True)
                if result and result.get('hits', 0) > 0:
                    logger.debug(f"[EXTRACT]   ✓ Full phrase '{full_phrase}' validated ({result['hits']} hits)")
                    validated_candidates.append(full_phrase)
                    continue  # Don't split if phrase works
            
            # Phrase didn't validate - try individual words
            logger.debug(f"[EXTRACT]   ✗ Full phrase didn't validate, trying individual words...")
            
            for word in segment:
                if len(word) <= 1:
                    continue
                if word.lower() in ENGLISH_MARKERS:
                    continue
                
                cleaned_word, was_stripped = strip_english_suffixes(word)
                if was_stripped:
                    logger.debug(f"[EXTRACT]   Stripped suffix: '{word}' → '{cleaned_word}'")
                
                logger.debug(f"[EXTRACT]   Checking word: '{cleaned_word}'")
                word_variants = generate_hebrew_variants(cleaned_word, max_variants=8)
                
                if word_variants:
                    result = await find_best_validated(word_variants, validator, cleaned_word, parallel=True)
                    if result and result.get('hits', 0) > 0:
                        logger.debug(f"[EXTRACT]     ✓ Word '{cleaned_word}' validated ({result['hits']} hits)")
                        validated_candidates.append(cleaned_word)
                    else:
                        logger.debug(f"[EXTRACT]     ✗ Word '{cleaned_word}' failed validation")
    
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
#  HEBREW NORMALIZATION
# ==========================================

def normalize_hebrew(text: str) -> str:
    """Normalize Hebrew for comparison."""
    if not text:
        return ""
    text = re.sub(r'[\s,.;:!?()\[\]{}"\'\-]', '', text)
    finals = {'ך': 'כ', 'ם': 'מ', 'ן': 'נ', 'ף': 'פ', 'ץ': 'צ'}
    for f, s in finals.items():
        text = text.replace(f, s)
    text = re.sub(r'[\u0591-\u05C7]', '', text)
    return text


# ==========================================
#  CONFIDENCE DETERMINATION
# ==========================================

def determine_confidence(hits: int, method: str) -> ConfidenceLevel:
    """Determine confidence level based on hit count and method."""
    if method == "dictionary":
        return ConfidenceLevel.HIGH

    if hits >= 100:
        return ConfidenceLevel.HIGH
    elif hits >= 10:
        return ConfidenceLevel.MEDIUM
    elif hits >= 1:
        return ConfidenceLevel.LOW
    else:
        return ConfidenceLevel.LOW


# ==========================================
#  SINGLE TERM DECIPHER (V4.3 - Multi-Term Dictionary)
# ==========================================

async def decipher_single(query: str) -> DecipherResult:
    """
    Decipher a single transliteration term.
    
    V4.3 IMPROVEMENT: Uses lookup_all() to find MULTIPLE dictionary matches.
    "chezkas haguf chezkas mammon" → ['חזקת הגוף', 'חזקת ממון']
    
    Tools (cascading):
    1. Word Dictionary (cache) - FREE, instant, NOW MULTI-TERM!
    2. Transliteration Map - FREE, generates variants
    3. Sefaria Validation (author-aware weighted) - FREE, validates
    """
    logger.info(f"[DECIPHER_SINGLE] Processing: '{query}'")
    
    # Strip English suffixes FIRST
    cleaned_query, was_stripped = strip_english_suffixes(query)
    if was_stripped:
        logger.info(f"  Stripped suffix: '{query}' → '{cleaned_query}'")
        query = cleaned_query
    
    # Normalize input
    normalized_query = normalize_input(query)
    logger.debug(f"  Normalized: '{normalized_query}'")
    
    # ========================================
    # TOOL 1: Word Dictionary (Cache) - V4.3 Multi-Term Support
    # ========================================
    logger.debug(f"  [TOOL 1] Word Dictionary - Checking cache...")
    dictionary = get_dictionary()
    
    # V4.3: Try lookup_all first to find multiple terms
    # This handles "chezkas haguf chezkas mammon" → both terms!
    # V4.5 FIX: Also process UNMATCHED words through transliteration
    if hasattr(dictionary, 'lookup_all'):
        all_matches = dictionary.lookup_all(normalized_query)

        # Find unmatched words that need transliteration
        words = normalized_query.split()
        matched_words = set()
        for translit, _, _ in (all_matches or []):
            matched_words.update(translit.split())
        unmatched_words = [w for w in words if w not in matched_words]

        if all_matches and not unmatched_words:
            # All words matched - return dictionary results
            hebrew_terms = [hebrew for _, hebrew, _ in all_matches]
            translit_terms = [translit for translit, _, _ in all_matches]

            logger.info(f"    ✓ Dictionary HIT: Found {len(all_matches)} term(s)")
            for translit, hebrew, _ in all_matches:
                logger.info(f"      '{translit}' → '{hebrew}'")

            # If multiple terms, combine them
            if len(hebrew_terms) > 1:
                primary_term = ' '.join(hebrew_terms)
                return DecipherResult(
                    success=True,
                    hebrew_term=primary_term,
                    hebrew_terms=hebrew_terms,
                    confidence=ConfidenceLevel.HIGH,
                    method="dictionary_multi",
                    message=f"Found {len(hebrew_terms)} terms in dictionary: {translit_terms}",
                    is_mixed_query=False,
                    original_query=query,
                    extraction_confident=True
                )
            else:
                # Single term - original behavior
                return DecipherResult(
                    success=True,
                    hebrew_term=hebrew_terms[0],
                    hebrew_terms=hebrew_terms,
                    confidence=ConfidenceLevel.HIGH,
                    method="dictionary",
                    message=f"Found in dictionary cache",
                    is_mixed_query=False,
                    original_query=query,
                    extraction_confident=True
                )
        elif all_matches and unmatched_words:
            # PARTIAL match - some words in dict, some need transliteration
            logger.info(f"    ✓ Dictionary PARTIAL: Found {len(all_matches)} term(s), {len(unmatched_words)} unmatched")
            for translit, hebrew, _ in all_matches:
                logger.info(f"      '{translit}' → '{hebrew}'")
            logger.info(f"    Unmatched words need transliteration: {unmatched_words}")
            # Don't return - continue to transliteration for unmatched words
            # Store matched results to combine later
            dict_hebrew_terms = [hebrew for _, hebrew, _ in all_matches]
        else:
            dict_hebrew_terms = []
            unmatched_words = words  # All words need transliteration
    else:
        # Fallback to legacy lookup() if lookup_all not available
        cached_result = dictionary.lookup(normalized_query)
        
        if cached_result:
            hebrew_term = cached_result['hebrew']
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
    
    # V4.5: If we have partial dictionary matches, only transliterate unmatched words
    if 'dict_hebrew_terms' not in dir() or not dict_hebrew_terms:
        dict_hebrew_terms = []
    if 'unmatched_words' not in dir() or not unmatched_words:
        unmatched_words = normalized_query.split()

    logger.debug(f"    → Continuing to transliteration for: {unmatched_words}")

    # ========================================
    # TOOL 2: Transliteration Map
    # ========================================
    # V4.5: Process each unmatched word separately
    transliterated_terms = []

    for word in unmatched_words:
        logger.debug(f"  [TOOL 2] Transliteration Map - Generating variants for '{word}'...")

        variants = generate_hebrew_variants(word, max_variants=15)
        logger.debug(f"    Generated {len(variants)} variants")

        if not variants:
            logger.warning(f"  No variants generated for '{word}'")
            continue

        # ========================================
        # TOOL 3: Sefaria Validation (Author-Aware)
        # ========================================
        logger.debug(f"  [TOOL 3] Sefaria Validation - Finding best validated term for '{word}'...")

        validator = get_validator()
        validation_result = await find_best_validated(variants, validator, word, parallel=True)

        if validation_result and validation_result.get('hits', 0) > 0:
            hebrew_term = validation_result['term']
            hits = validation_result.get('hits', 0)
            logger.info(f"  ✓ SUCCESS: '{word}' → '{hebrew_term}' ({hits} hits)")
            transliterated_terms.append(hebrew_term)
            # Cache the result
            dictionary.add(word, hebrew_term, hits=hits)
        else:
            # Use best guess even if no Sefaria hits
            best_guess = variants[0]
            logger.warning(f"  No Sefaria hits for '{word}', using best guess: {best_guess}")
            transliterated_terms.append(best_guess)

    # Combine dictionary matches + transliterated terms
    all_hebrew_terms = dict_hebrew_terms + transliterated_terms

    if not all_hebrew_terms:
        logger.warning(f"  No Hebrew terms found for '{query}'")
        return DecipherResult(
            success=False,
            hebrew_term=None,
            hebrew_terms=[],
            confidence=ConfidenceLevel.LOW,
            method="failed",
            message="Could not transliterate any terms",
            is_mixed_query=False,
            original_query=query,
            extraction_confident=False
        )

    # Determine method and confidence
    if dict_hebrew_terms and transliterated_terms:
        method = "dictionary_plus_transliteration"
        confidence = ConfidenceLevel.MEDIUM
    elif dict_hebrew_terms:
        method = "dictionary"
        confidence = ConfidenceLevel.HIGH
    else:
        method = "transliteration"
        confidence = ConfidenceLevel.MEDIUM

    primary_term = ' '.join(all_hebrew_terms)
    logger.info(f"  ✓ COMBINED RESULT: {all_hebrew_terms} ({method})")

    return DecipherResult(
        success=True,
        hebrew_term=primary_term,
        hebrew_terms=all_hebrew_terms,
        confidence=confidence,
        method=method,
        message=f"Found {len(all_hebrew_terms)} term(s)",
        is_mixed_query=False,
        original_query=query,
        extraction_confident=True
    )


# ==========================================
#  MAIN DECIPHER FUNCTION (V4.3)
# ==========================================

async def decipher(query: str) -> DecipherResult:
    """
    Main entry point for Step 1: Transliteration → Hebrew

    V4.4 FLOW:
    1. Check if PURE ENGLISH query (no Hebrew content) - pass to Claude directly
    2. Check if mixed query (English + Hebrew)
    3. If mixed:
       - Extract Hebrew candidates (author-aware, V4.2)
       - Transliterate each candidate
       - Return all terms for Step 2 to verify
    4. If pure transliteration:
       - Use single-term flow (dictionary → transliteration → Sefaria)
       - V4.3: Dictionary now uses lookup_all() for multi-term support!
    """
    log_section("STEP 1: DECIPHER (V4.4) - Pure English Query Support")
    logger.info("Incoming query: %s", query)

    # ========================================
    # PURE ENGLISH QUERY DETECTION (V4.4 NEW)
    # ========================================
    if is_pure_english_query(query):
        log_subsection("Pure English Query Detected")
        logger.info("Query is entirely in English - passing to Step 2 for interpretation")
        logger.info("Query will be interpreted by Claude as a topic request")

        return DecipherResult(
            success=True,  # This IS a success - we identified it correctly
            hebrew_term=None,
            hebrew_terms=[],  # No Hebrew terms - Step 2 will use the original query
            confidence=ConfidenceLevel.HIGH,  # High confidence it's English
            method="pure_english_topic",
            message="Query is in English. Claude will interpret the topic.",
            is_mixed_query=False,
            original_query=query,
            extraction_confident=True,
            is_pure_english=True  # New flag for pipeline
        )

    # ========================================
    # MIXED QUERY DETECTION
    # ========================================
    if is_mixed_query(query):
        log_subsection("Mixed Query Detected")
        logger.info("Detected English + Hebrew mix; extracting with author awareness")
        
        # V4.2: Author-aware extraction
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
        
        log_list("Validated candidates ready for transliteration", candidates)
        log_subsection("Transliterating Validated Candidates")
        
        # Transliterate each candidate
        all_hebrew_terms = []
        all_confidences = []
        
        for idx, candidate in enumerate(candidates, start=1):
            logger.info("")
            logger.info("Candidate %d/%d: '%s'", idx, len(candidates), candidate)
            logger.info("-" * 40)
            result = await decipher_single(candidate)
            
            if result.success or result.hebrew_term:
                # V4.3: Handle multi-term results from dictionary
                if result.hebrew_terms and len(result.hebrew_terms) > 1:
                    all_hebrew_terms.extend(result.hebrew_terms)
                else:
                    all_hebrew_terms.append(result.hebrew_term)
                all_confidences.append(result.confidence)
                conf_str = result.confidence.value if hasattr(result.confidence, 'value') else result.confidence
                logger.info("Result: '%s' -> '%s' (%s confidence)", candidate, result.hebrew_term, conf_str)
            else:
                logger.warning("Result: '%s' failed to transliterate", candidate)
        
        # Determine overall confidence
        if all_confidences:
            def get_conf_str(c):
                return c.value if hasattr(c, 'value') else c
            
            order = ['high', 'medium', 'low']
            
            def conf_index(c):
                label = get_conf_str(c)
                return order.index(label) if label in order else len(order) - 1
            
            overall_confidence = min(all_confidences, key=conf_index)
        else:
            overall_confidence = ConfidenceLevel.LOW
        
        primary_term = all_hebrew_terms[0] if all_hebrew_terms else None
        extraction_confident = len(all_hebrew_terms) == len(candidates)
        
        log_subsection("Mixed Query Summary")
        logger.info("Terms extracted: %d", len(all_hebrew_terms))
        logger.info("Primary term: %s", primary_term)
        log_list("All terms", all_hebrew_terms)
        logger.info("Extraction confident: %s", extraction_confident)
        
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
    # PURE TRANSLITERATION
    # ========================================
    else:
        log_subsection("Pure Transliteration Flow")
        logger.info("No English markers detected; running dictionary -> transliteration map -> Sefaria cascade")
        result = await decipher_single(query)
        
        # V4.3: decipher_single now handles multi-term dictionary results
        if result.success and result.hebrew_term and not result.hebrew_terms:
            result.hebrew_terms = [result.hebrew_term]
        
        return result


# ==========================================
#  QUICK TEST
# ==========================================

async def quick_test():
    """Quick test of the V4.3 decipher function."""
    test_queries = [
        # V4.3 NEW: Multi-term dictionary test
        "chezkas haguf chezkas mammon",  # Should return BOTH terms!
        
        # Pure transliteration
        "chezkas haguf",
        "migu",
        
        # Mixed queries
        "what is chezkas haguf",
        "explain migu",
        
        # V4.2 test: Author names in mixed queries
        "what is the rans shittah in bittul chometz",
        "how does rashis pshat differ from tosfoses",
        
        # Author comparison
        "what is the difference between rashi and tosfos on pesachim",
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
        conf_str = result.confidence.value if hasattr(result.confidence, 'value') else result.confidence
        print(f"  Confidence: {conf_str}")
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