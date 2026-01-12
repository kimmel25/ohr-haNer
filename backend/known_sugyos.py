"""
Known Sugyos Database Lookup
============================

This module provides lookup functionality for the known_sugyos database.
When a user queries a classic Torah concept, we check here FIRST before
relying on Claude's semantic suggestions.

If we have a known mapping, we use those exact locations as primary sources
with HIGH confidence, solving the "Primary Sources Issue" where Claude
returns Rishonim instead of the underlying gemara.

USAGE:
    from known_sugyos import lookup_known_sugya, KnownSugyaMatch
    
    match = lookup_known_sugya(query, hebrew_terms)
    if match:
        # Use match.primary_refs as the foundation
        # Use match.key_terms for validation
        # Confidence is HIGH when we have a known mapping
"""

import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

# =============================================================================
#  CONFIGURATION
# =============================================================================

# Path to the known_sugyos database.
# Default: repo-local file at backend/data/sugyos.json (Windows-safe).
KNOWN_SUGYOS_DB_PATH = str(Path(__file__).resolve().parent / "data" / "sugyos.json")

# Fallback paths to check if main path is empty
FALLBACK_PATHS = [
    # If this module is imported from different working directories.
    str(Path(__file__).resolve().parent / "data" / "sugyos.json"),
    "./data/sugyos.json",
    "./backend/data/sugyos.json",
    "../backend/data/sugyos.json",
]


# =============================================================================
#  DATA STRUCTURES
# =============================================================================

@dataclass
class PrimaryGemaraLocation:
    """A known gemara location for a sugya."""
    ref: str                    # Sefaria-compatible ref, e.g., "Kesubos 12b"
    he_ref: str = ""           # Hebrew ref, e.g., "כתובות יב:"
    description: str = ""       # What's discussed there


@dataclass
class KnownSugyaMatch:
    """Result of matching a query against known sugyos database."""
    sugya_id: str                                           # Unique ID like "chezkas_haguf_vs_mammon"
    matched: bool = False                                   # Did we find a match?
    match_confidence: str = "none"                          # "high", "medium", "low", "none"
    match_reason: str = ""                                  # Why we matched
    
    # Primary sources - THE GEMARA locations
    primary_gemara: List[PrimaryGemaraLocation] = field(default_factory=list)
    primary_refs: List[str] = field(default_factory=list)   # Just the refs for easy use
    
    # Also discussed locations
    also_discussed_refs: List[str] = field(default_factory=list)
    
    # Metadata for search/validation
    key_terms: List[str] = field(default_factory=list)      # Hebrew terms to validate
    key_concepts: List[str] = field(default_factory=list)   # What the sugya is about
    rishonim_who_discuss: List[str] = field(default_factory=list)
    related_sugyos: List[str] = field(default_factory=list)
    
    # Raw sugya data
    raw_data: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
#  DATABASE LOADING
# =============================================================================

_sugyos_cache: Optional[Dict[str, Any]] = None

def _load_database() -> Dict[str, Any]:
    """Load the known_sugyos database, with caching."""
    global _sugyos_cache
    
    if _sugyos_cache is not None:
        return _sugyos_cache
    
    # Try main path first
    paths_to_try = []
    if KNOWN_SUGYOS_DB_PATH:
        paths_to_try.append(KNOWN_SUGYOS_DB_PATH)
    paths_to_try.extend(FALLBACK_PATHS)
    
    for path in paths_to_try:
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    _sugyos_cache = data
                    logger.info(f"Loaded known_sugyos database from: {path}")
                    logger.info(f"  Contains {len(data.get('sugyos', []))} sugyos")
                    return data
        except Exception as e:
            logger.debug(f"Could not load from {path}: {e}")
            continue
    
    logger.warning("Known sugyos database not found. Set KNOWN_SUGYOS_DB_PATH.")
    _sugyos_cache = {"sugyos": []}
    return _sugyos_cache


def reload_database() -> None:
    """Force reload of the database (useful after updates)."""
    global _sugyos_cache
    _sugyos_cache = None
    _load_database()


# =============================================================================
#  MATCHING LOGIC
# =============================================================================

def _normalize_text(text: str) -> str:
    """Normalize text for matching."""
    # Lowercase
    text = text.lower()
    # Remove punctuation
    text = re.sub(r'[^\w\s\u0590-\u05FF]', ' ', text)
    # Collapse whitespace
    text = ' '.join(text.split())
    return text


def _get_words(text: str) -> set:
    """Split normalized text into a set of words for word-boundary matching."""
    return set(text.split())


def _phrase_in_text_word_bounded(phrase: str, text: str) -> bool:
    """
    Check if a phrase exists in text with proper word boundaries.

    This prevents false positives like "mukas" matching inside "bedikas".

    Args:
        phrase: The phrase to search for (already normalized)
        text: The text to search in (already normalized)

    Returns:
        True only if the phrase appears as complete words in the text
    """
    # For single words, check if it's in the word set
    phrase_words = phrase.split()
    text_words = _get_words(text)

    if len(phrase_words) == 1:
        return phrase_words[0] in text_words

    # For multi-word phrases, check if all words appear consecutively
    # First, all words must be present
    if not all(w in text_words for w in phrase_words):
        return False

    # Then check for consecutive appearance using word boundary regex
    # Escape special regex chars and build pattern
    pattern = r'\b' + r'\s+'.join(re.escape(w) for w in phrase_words) + r'\b'
    return bool(re.search(pattern, text))


def _calculate_match_score(
    query: str,
    hebrew_terms: List[str],
    sugya: Dict[str, Any]
) -> tuple[float, str]:
    """
    Calculate how well a query matches a known sugya.
    Returns (score, reason).
    Score ranges from 0 to 1.

    IMPORTANT: All matching uses word-boundary checking to prevent false positives
    like "mukas" matching inside "bedikas". See _phrase_in_text_word_bounded().
    """
    score = 0.0
    reasons = []

    query_normalized = _normalize_text(query)
    query_words = _get_words(query_normalized)  # Pre-compute word set
    hebrew_terms_normalized = [_normalize_text(t) for t in hebrew_terms]

    names = sugya.get("names", {})

    # Check Hebrew names
    for hebrew_name in names.get("hebrew", []):
        hebrew_normalized = _normalize_text(hebrew_name)

        # Exact match in hebrew_terms
        if hebrew_normalized in hebrew_terms_normalized:
            score += 0.5
            reasons.append(f"Hebrew term match: {hebrew_name}")

        # Word-bounded match in query (not substring!)
        if _phrase_in_text_word_bounded(hebrew_normalized, query_normalized):
            score += 0.3
            reasons.append(f"Hebrew in query: {hebrew_name}")

    # Check English names
    for english_name in names.get("english", []):
        english_normalized = _normalize_text(english_name)

        # Word-bounded match (not substring!)
        if _phrase_in_text_word_bounded(english_normalized, query_normalized):
            score += 0.4
            reasons.append(f"English match: {english_name}")

    # Check transliterations (most common match type)
    for translit in names.get("transliterations", []):
        translit_normalized = _normalize_text(translit)

        # Word-bounded match for full transliteration (not substring!)
        if _phrase_in_text_word_bounded(translit_normalized, query_normalized):
            score += 0.45
            reasons.append(f"Transliteration match: {translit}")

        # Check each word of multi-word transliterations
        # CRITICAL FIX: Use word set matching, NOT substring matching!
        # This prevents "mukas" from matching inside "bedikas"
        translit_words = translit_normalized.split()
        if len(translit_words) > 1:
            # Count how many transliteration words appear as WHOLE WORDS in query
            matches = sum(1 for w in translit_words if w in query_words)
            if matches >= len(translit_words) - 1:  # Allow one word missing
                score += 0.3
                reasons.append(f"Partial transliteration: {translit}")

    # Check key terms against hebrew_terms
    key_terms = sugya.get("key_terms", [])
    for term in key_terms:
        term_normalized = _normalize_text(term)
        if term_normalized in hebrew_terms_normalized:
            score += 0.2
            reasons.append(f"Key term match: {term}")

    # Cap at 1.0
    score = min(score, 1.0)

    return score, "; ".join(reasons) if reasons else "No match"


def lookup_known_sugya(
    query: str,
    hebrew_terms: List[str] = None,
    threshold: float = 0.5  # V4.4: Raised from 0.4 to reduce false positives
) -> Optional[KnownSugyaMatch]:
    """
    Look up a query in the known sugyos database.

    Args:
        query: The user's query string
        hebrew_terms: Hebrew terms from Step 1 (decipher)
        threshold: Minimum match score (0-1) to consider a match

    Returns:
        KnownSugyaMatch if found, None otherwise
    """
    if hebrew_terms is None:
        hebrew_terms = []
    
    database = _load_database()
    sugyos = database.get("sugyos", [])
    
    if not sugyos:
        logger.debug("No sugyos in database")
        return None
    
    logger.info(f"[KNOWN_SUGYOS] Searching for: {query}")
    logger.info(f"[KNOWN_SUGYOS] Hebrew terms: {hebrew_terms}")
    
    best_match = None
    best_score = 0.0
    best_reason = ""
    
    for sugya in sugyos:
        score, reason = _calculate_match_score(query, hebrew_terms, sugya)
        
        if score > best_score:
            best_score = score
            best_match = sugya
            best_reason = reason
    
    if best_score < threshold:
        logger.info(f"[KNOWN_SUGYOS] No match above threshold {threshold} (best: {best_score:.2f})")
        return None
    
    # Build the match result
    sugya_id = best_match.get("id", "unknown")
    logger.info(f"[KNOWN_SUGYOS] ✓ MATCH FOUND: {sugya_id} (score: {best_score:.2f})")
    logger.info(f"[KNOWN_SUGYOS]   Reason: {best_reason}")
    
    # Parse primary gemara locations
    primary_gemara = []
    primary_refs = []
    for loc in best_match.get("primary_gemara", []):
        pg = PrimaryGemaraLocation(
            ref=loc.get("ref", ""),
            he_ref=loc.get("he_ref", ""),
            description=loc.get("description", "")
        )
        primary_gemara.append(pg)
        if pg.ref:
            primary_refs.append(pg.ref)
    
    # Parse also_discussed
    also_discussed = []
    for loc in best_match.get("also_discussed", []):
        if isinstance(loc, dict):
            also_discussed.append(loc.get("ref", ""))
        elif isinstance(loc, str):
            also_discussed.append(loc)
    
    # Determine confidence based on score
    if best_score >= 0.7:
        confidence = "high"
    elif best_score >= 0.5:
        confidence = "medium"
    else:
        confidence = "low"
    
    match = KnownSugyaMatch(
        sugya_id=sugya_id,
        matched=True,
        match_confidence=confidence,
        match_reason=best_reason,
        primary_gemara=primary_gemara,
        primary_refs=primary_refs,
        also_discussed_refs=also_discussed,
        key_terms=best_match.get("key_terms", []),
        key_concepts=best_match.get("key_concepts", []),
        rishonim_who_discuss=best_match.get("rishonim_who_discuss", []),
        related_sugyos=best_match.get("related_sugyos", []),
        raw_data=best_match
    )
    
    logger.info(f"[KNOWN_SUGYOS]   Primary refs: {primary_refs}")
    logger.info(f"[KNOWN_SUGYOS]   Key terms: {match.key_terms[:3]}...")
    
    return match


def get_all_sugya_ids() -> List[str]:
    """Get list of all known sugya IDs."""
    database = _load_database()
    return [s.get("id", "") for s in database.get("sugyos", [])]


def get_sugya_by_id(sugya_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific sugya by its ID."""
    database = _load_database()
    for sugya in database.get("sugyos", []):
        if sugya.get("id") == sugya_id:
            return sugya
    return None


# =============================================================================
#  EXPORTS
# =============================================================================

__all__ = [
    'lookup_known_sugya',
    'KnownSugyaMatch',
    'PrimaryGemaraLocation',
    'get_all_sugya_ids',
    'get_sugya_by_id',
    'reload_database',
    'KNOWN_SUGYOS_DB_PATH',
]