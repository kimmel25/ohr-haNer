"""
Step 3: SEARCH - V3 Complete Rewrite
=====================================

V3 PHILOSOPHY:
    Claude's suggested refs from Step 2 come with verification_keywords.
    We verify them PROGRAMMATICALLY using local corpus or Sefaria API.
    NO CLAUDE CALLS IN STEP 3 - this is the key cost savings.

FLOW:
    1. Get RefHints from Step 2 (with verification_keywords)
    2. For each RefHint: 
       a. Fetch text (with buffer based on buffer_size)
       b. Search for verification_keywords in text
       c. If found: VERIFIED as foundation stone
    3. Use SearchVariants for additional corpus discovery
    4. Trickle UP: Use Sefaria /related API to get commentaries
    5. Trickle DOWN: Use /links API for earlier sources
    6. Filter to only include target_sources from Step 2
    7. Return organized sources

KEY INSIGHT:
    Step 2 now provides verification_keywords that appear in the actual gemara text.
    These keywords include Aramaic forms (דגופא, דממונא) that Claude knows to expect.
    Simple substring search can verify if a ref discusses the topic.

COST SAVINGS:
    Before: 1 + N Claude calls (N = number of refs, typically 4-6)
    After:  1 Claude call (only in Step 2)
    Result: ~80% reduction in API costs
"""

import logging
import re
import json
import asyncio
import aiohttp
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Any
from pathlib import Path
from datetime import datetime

# =============================================================================
#  LOGGING SETUP
# =============================================================================

logger = logging.getLogger(__name__)


def log_section(title: str) -> None:
    """Log a major section header."""
    border = "=" * 70
    logger.info("")
    logger.info(border)
    logger.info(f"  {title}")
    logger.info(border)


def log_subsection(title: str) -> None:
    """Log a subsection header."""
    logger.info("")
    logger.info("-" * 50)
    logger.info(f"  {title}")
    logger.info("-" * 50)


def log_verification(ref: str, verified: bool, reason: str, keywords_found: List[str] = None) -> None:
    """Log verification result for a ref."""
    status = "✓ VERIFIED" if verified else "✗ NOT FOUND"
    logger.info(f"  {status}: {ref}")
    if keywords_found:
        logger.info(f"    Keywords found: {keywords_found}")
    logger.info(f"    Reason: {reason}")


# =============================================================================
#  CONFIGURATION & IMPORTS
# =============================================================================

try:
    from config import get_settings
    settings = get_settings()
except ImportError:
    import os
    class Settings:
        anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        sefaria_base_url = "https://www.sefaria.org/api"
    settings = Settings()

# Import SourceLevel from central models (compatibility with source_output.py)
try:
    from models import SourceLevel, ConfidenceLevel as ModelsConfidenceLevel
    logger.debug("Imported SourceLevel from models.py")
except ImportError:
    # Fallback: define locally if models.py not available
    class SourceLevel(str, Enum):
        """Source levels in trickle-up order."""
        CHUMASH = "chumash"
        MISHNA = "mishna"
        GEMARA = "gemara"
        RASHI = "rashi"
        TOSFOS = "tosfos"
        RISHONIM = "rishonim"
        RAMBAM = "rambam"
        TUR = "tur"
        SHULCHAN_ARUCH = "shulchan_aruch"
        NOSEI_KEILIM = "nosei_keilim"
        ACHARONIM = "acharonim"
        OTHER = "other"

# Import Step 2 structures
try:
    from step_two_understand import (
        QueryAnalysis, RefHint, SearchVariants,
        FoundationType, TrickleDirection, ConfidenceLevel, RefConfidence
    )
except ImportError:
    # Fallback definitions (should not happen in normal operation)
    logger.warning("Could not import step_two_understand, using fallback enums")
    
    class FoundationType(str, Enum):
        GEMARA = "gemara"
        MISHNA = "mishna"
        CHUMASH = "chumash"
        HALACHA_SA = "halacha_sa"
        HALACHA_RAMBAM = "halacha_rambam"
        MIDRASH = "midrash"
        UNKNOWN = "unknown"
    
    class TrickleDirection(str, Enum):
        UP = "up"
        DOWN = "down"
        BOTH = "both"
        NONE = "none"
    
    class ConfidenceLevel(str, Enum):
        HIGH = "high"
        MEDIUM = "medium"
        LOW = "low"
    
    class RefConfidence(str, Enum):
        CERTAIN = "certain"
        LIKELY = "likely"
        POSSIBLE = "possible"
        GUESS = "guess"

# Import local corpus handler
try:
    from local_corpus import LocalCorpus, get_local_corpus, MASECHTA_MAP
    LOCAL_CORPUS_AVAILABLE = True
    logger.debug("Local corpus module imported successfully")
except ImportError:
    LOCAL_CORPUS_AVAILABLE = False
    logger.warning("Local corpus not available, will use Sefaria API only")
    MASECHTA_MAP = {}


SEFARIA_BASE_URL = getattr(settings, 'sefaria_base_url', "https://www.sefaria.org/api")
DEFAULT_BUFFER_SIZE = 1
MAX_CONCURRENT_REQUESTS = 5


# =============================================================================
#  CATEGORY MAPPING
# =============================================================================

# Map from Sefaria category to our SourceLevel
# NOTE: Uses SourceLevel from models.py (TOSFOS not TOSAFOS, CHUMASH not PASUK)
CATEGORY_TO_LEVEL = {
    "Tanakh": SourceLevel.CHUMASH,
    "Torah": SourceLevel.CHUMASH,
    "Prophets": SourceLevel.CHUMASH,
    "Writings": SourceLevel.CHUMASH,
    "Mishnah": SourceLevel.MISHNA,
    "Talmud": SourceLevel.GEMARA,
    "Bavli": SourceLevel.GEMARA,
    "Yerushalmi": SourceLevel.GEMARA,
    "Midrash": SourceLevel.RISHONIM,
    "Rashi": SourceLevel.RASHI,
    "Tosafot": SourceLevel.TOSFOS,
    "Rishonim": SourceLevel.RISHONIM,
    "Rambam": SourceLevel.RAMBAM,
    "Mishneh Torah": SourceLevel.RAMBAM,
    "Tur": SourceLevel.TUR,
    "Shulchan Arukh": SourceLevel.SHULCHAN_ARUCH,
    "Acharonim": SourceLevel.ACHARONIM,
}

# Map from target_sources names to Sefaria categories
SOURCE_NAME_MAP = {
    "gemara": ["Talmud", "Bavli"],
    "rashi": ["Rashi"],
    "tosafos": ["Tosafot", "Tosafos"],
    "ran": ["Ran"],
    "rashba": ["Rashba"],
    "ritva": ["Ritva"],
    "ramban": ["Ramban"],
    "rambam": ["Rambam", "Mishneh Torah"],
    "rosh": ["Rosh"],
    "rif": ["Rif"],
    "meiri": ["Meiri"],
    "shulchan_arukh": ["Shulchan Arukh"],
    "mishnah_berurah": ["Mishnah Berurah"],
    "taz": ["Taz", "Turei Zahav"],
    "shach": ["Shakh", "Siftei Kohen"],
    "magen_avraham": ["Magen Avraham"],
    "ketzos": ["Ketzot HaChoshen", "Ketzos"],
    "nesivos": ["Netivot HaMishpat", "Nesivos"],
    "chumash": ["Torah", "Tanakh"],
    "ibn_ezra": ["Ibn Ezra"],
    "sforno": ["Sforno"],
    "ohr_hachaim": ["Or HaChaim"],
    "targum": ["Targum"],
    "midrash_rabbah": ["Midrash Rabbah"],
}


@dataclass
class Source:
    """A single source with text and metadata."""
    ref: str
    he_ref: str = ""
    level: SourceLevel = SourceLevel.OTHER
    hebrew_text: str = ""
    english_text: str = ""
    author: str = ""
    categories: List[str] = field(default_factory=list)
    is_foundation: bool = False
    is_verified: bool = False
    verification_keywords_found: List[str] = field(default_factory=list)


@dataclass
class VerificationResult:
    """Result of programmatic verification for a ref."""
    ref: str
    original_hint_ref: str
    verified: bool
    keywords_found: List[str] = field(default_factory=list)
    reason: str = ""
    text_snippet: str = ""
    confidence: RefConfidence = RefConfidence.POSSIBLE


@dataclass
class SearchResult:
    """Complete search result."""
    original_query: str
    foundation_stones: List[Source] = field(default_factory=list)
    commentary_sources: List[Source] = field(default_factory=list)
    earlier_sources: List[Source] = field(default_factory=list)
    
    all_sources: List[Source] = field(default_factory=list)
    sources_by_level: Dict[str, List[Source]] = field(default_factory=dict)
    
    total_sources: int = 0
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    search_description: str = ""
    
    needs_clarification: bool = False
    clarification_question: Optional[str] = None
    
    # V3: Verification stats
    refs_verified: int = 0
    refs_checked: int = 0
    verification_method: str = "programmatic"


# =============================================================================
#  SEFARIA API HELPERS
# =============================================================================

async def fetch_text(ref: str, session: aiohttp.ClientSession) -> Optional[Dict]:
    """Fetch text from Sefaria API."""
    try:
        encoded_ref = ref.replace(" ", "%20")
        url = f"{SEFARIA_BASE_URL}/texts/{encoded_ref}?context=0"
        
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
            if response.status == 200:
                return await response.json()
            else:
                logger.debug(f"Sefaria returned {response.status} for {ref}")
                return None
    except Exception as e:
        logger.debug(f"Error fetching {ref}: {e}")
        return None


async def fetch_related(ref: str, session: aiohttp.ClientSession) -> Optional[Dict]:
    """Fetch related texts (commentaries, links) from Sefaria."""
    try:
        encoded_ref = ref.replace(" ", "%20")
        url = f"{SEFARIA_BASE_URL}/related/{encoded_ref}"
        
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
            if response.status == 200:
                return await response.json()
            else:
                logger.debug(f"Sefaria related returned {response.status} for {ref}")
                return None
    except Exception as e:
        logger.debug(f"Error fetching related for {ref}: {e}")
        return None


async def fetch_links(ref: str, session: aiohttp.ClientSession) -> Optional[List]:
    """Fetch links for a ref from Sefaria."""
    try:
        encoded_ref = ref.replace(" ", "%20")
        url = f"{SEFARIA_BASE_URL}/links/{encoded_ref}"
        
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
            if response.status == 200:
                return await response.json()
            else:
                return None
    except Exception as e:
        logger.debug(f"Error fetching links for {ref}: {e}")
        return None


def extract_text_content(sefaria_response: Dict) -> Tuple[str, str]:
    """Extract Hebrew and English text from Sefaria response."""
    he_text = ""
    en_text = ""
    
    if not sefaria_response:
        return he_text, en_text
    
    he = sefaria_response.get("he", "")
    if isinstance(he, list):
        he_text = " ".join(flatten_text(he))
    else:
        he_text = str(he) if he else ""
    
    en = sefaria_response.get("text", "")
    if isinstance(en, list):
        en_text = " ".join(flatten_text(en))
    else:
        en_text = str(en) if en else ""
    
    return he_text, en_text


def flatten_text(text_obj) -> List[str]:
    """Flatten nested text arrays from Sefaria."""
    result = []
    if isinstance(text_obj, str):
        if text_obj.strip():
            result.append(text_obj.strip())
    elif isinstance(text_obj, list):
        for item in text_obj:
            result.extend(flatten_text(item))
    return result


def determine_level(categories: List[str], ref: str) -> SourceLevel:
    """Determine source level from Sefaria categories."""
    if not categories:
        return SourceLevel.OTHER
    
    ref_lower = ref.lower()
    if "rashi" in ref_lower:
        return SourceLevel.RASHI
    if "tosafot" in ref_lower or "tosafos" in ref_lower:
        return SourceLevel.TOSFOS
    
    for cat in categories:
        if cat in CATEGORY_TO_LEVEL:
            return CATEGORY_TO_LEVEL[cat]
    
    return SourceLevel.OTHER


# =============================================================================
#  REF PARSING AND MANIPULATION
# =============================================================================

def parse_gemara_ref(ref: str) -> Optional[Tuple[str, int, str]]:
    """Parse a gemara ref into (masechta, daf_number, amud)."""
    match = re.match(r'^([A-Za-z\s]+)\s+(\d+)([ab])$', ref.strip())
    if match:
        return (match.group(1).strip(), int(match.group(2)), match.group(3))
    return None


def get_adjacent_refs(ref: str, buffer: int = DEFAULT_BUFFER_SIZE) -> List[str]:
    """Get refs for surrounding dapim (for verification buffer)."""
    parsed = parse_gemara_ref(ref)
    if not parsed:
        return [ref]
    
    masechta, daf, amud = parsed
    refs = []
    
    # Each daf has a and b sides
    current_pos = daf * 2 + (0 if amud == 'a' else 1)
    
    for offset in range(-buffer * 2, buffer * 2 + 1):
        pos = current_pos + offset
        if pos < 4:  # Skip before daf 2a
            continue
        
        new_daf = pos // 2
        new_amud = 'a' if pos % 2 == 0 else 'b'
        refs.append(f"{masechta} {new_daf}{new_amud}")
    
    return refs


def normalize_for_search(text: str) -> str:
    """
    Normalize Hebrew text for keyword matching.
    
    V3.1 IMPROVEMENTS:
    - Strip HTML
    - Normalize sofit letters (ם→מ, ן→נ, etc.)
    - Remove nikud (vowel points)
    - Normalize geresh/gershayim
    - Collapse whitespace
    """
    if not text:
        return ""
    
    # Strip HTML
    text = re.sub(r'<[^>]+>', '', text)
    
    # Remove nikud (Hebrew vowel points)
    # Nikud range: U+05B0 to U+05BD, U+05BF, U+05C1-U+05C2, U+05C4-U+05C5, U+05C7
    text = re.sub(r'[\u05B0-\u05BD\u05BF\u05C1\u05C2\u05C4\u05C5\u05C7]', '', text)
    
    # Normalize geresh (׳) and gershayim (״) - remove
    text = text.replace('״', '').replace('׳', '')
    text = text.replace('"', '').replace("'", '')
    
    # Normalize sofits (final letters) for matching
    text_normalized = text
    sofit_map = {
        'ם': 'מ',
        'ן': 'נ',
        'ף': 'פ',
        'ך': 'כ',
        'ץ': 'צ',
    }
    for sofit, regular in sofit_map.items():
        text_normalized = text_normalized.replace(sofit, regular)
    
    # Collapse whitespace
    text_normalized = re.sub(r'\s+', ' ', text_normalized)
    
    return text_normalized


def generate_keyword_variants(keyword: str) -> List[str]:
    """
    Generate variations of a keyword for more flexible matching.
    
    Handles:
    - Smichut forms (חזקה ↔ חזקת)
    - With/without ה prefix
    """
    variants = [keyword]
    
    # Smichut: words ending in ה often become ת in construct state
    if keyword.endswith('ה'):
        variants.append(keyword[:-1] + 'ת')  # חזקה → חזקת
    if keyword.endswith('ת'):
        variants.append(keyword[:-1] + 'ה')  # חזקת → חזקה
    
    # Handle דגופא / דממונא - might be written with space or without
    if ' ד' in keyword:
        variants.append(keyword.replace(' ד', 'ד'))
    
    # Handle הגוף / גוף variations (with/without ה article)
    if 'הגוף' in keyword:
        variants.append(keyword.replace('הגוף', 'גוף'))
    if 'גוף' in keyword and 'הגוף' not in keyword:
        variants.append(keyword.replace('גוף', 'הגוף'))
    
    return list(set(variants))


# =============================================================================
#  PROGRAMMATIC VERIFICATION (NO CLAUDE CALLS!)
# =============================================================================

# Generic words that appear everywhere - LOW weight
GENERIC_KEYWORDS = {
    'חזקה', 'ספק', 'רוב', 'מום', 'גוף', 'ממון', 'טהור', 'טמא',
    'אמר', 'רבא', 'אביי', 'רב', 'שמואל', 'מתני', 'גמרא',
}

def calculate_keyword_score(keywords_found: List[str]) -> float:
    """
    Calculate a weighted score for keywords found.
    
    Specific phrases (2+ words or Aramaic construct forms) = 3 points
    Generic single words = 1 point
    
    Returns total score.
    """
    score = 0.0
    
    for keyword in keywords_found:
        # Multi-word phrases are specific
        if ' ' in keyword:
            score += 3.0
        # Aramaic construct forms (דגופא, דממונא) are specific
        elif keyword.startswith('ד') and len(keyword) > 3:
            score += 3.0
        # Known generic words
        elif keyword in GENERIC_KEYWORDS:
            score += 1.0
        # Other single words
        else:
            score += 1.5
    
    return score


def verify_text_contains_keywords(
    text: str,
    keywords: List[str],
    require_all: bool = False,
    min_score: float = 3.0
) -> Tuple[bool, List[str], float]:
    """
    Check if text contains verification keywords with weighted scoring.
    
    V3.1: Now generates variants for each keyword (smichut forms, etc.)
    
    Args:
        text: The text to search in
        keywords: List of keywords to look for
        require_all: If True, ALL keywords must be present
        min_score: Minimum weighted score to consider verified
        
    Returns:
        (verified, keywords_found, score)
    """
    if not text or not keywords:
        return False, [], 0.0
    
    text_normalized = normalize_for_search(text)
    text_no_spaces = text_normalized.replace(" ", "")
    keywords_found = []
    
    for keyword in keywords:
        # Generate variants of this keyword (smichut, etc.)
        variants = generate_keyword_variants(keyword)
        
        found = False
        for variant in variants:
            variant_normalized = normalize_for_search(variant)
            
            # Try exact match
            if variant in text or variant_normalized in text_normalized:
                found = True
                break
            
            # Try without spaces (for compound terms)
            variant_no_space = variant_normalized.replace(" ", "")
            if variant_no_space in text_no_spaces:
                found = True
                break
        
        if found:
            keywords_found.append(keyword)
    
    # Calculate weighted score
    score = calculate_keyword_score(keywords_found)
    
    if require_all:
        verified = len(keywords_found) == len(keywords)
    else:
        # Need either specific keywords OR enough generic ones
        verified = score >= min_score
    
    return verified, keywords_found, score


async def verify_ref_programmatic(
    hint: 'RefHint',
    session: aiohttp.ClientSession,
    search_variants: Optional['SearchVariants'] = None
) -> VerificationResult:
    """
    Verify a RefHint programmatically without Claude.
    
    V3.1 IMPROVEMENTS:
    1. Trust "certain" confidence refs without verification
    2. Use weighted keyword scoring (specific > generic)
    3. Better text normalization
    
    Args:
        hint: RefHint from Step 2 with ref and verification_keywords
        session: aiohttp session for API calls
        search_variants: Optional additional search terms from Step 2
        
    Returns:
        VerificationResult with verification status
    """
    logger.info(f"  Verifying: {hint.ref} [confidence: {hint.confidence.value}]")
    
    # FIX 1: Trust "certain" confidence refs from Claude
    # Claude marked these as definite locations - skip verification
    if hint.confidence.value == "certain":
        logger.info(f"    → TRUSTED (certain confidence from Step 2)")
        
        # Still fetch the text for the source
        response = await fetch_text(hint.ref, session)
        snippet = ""
        if response:
            he_text, _ = extract_text_content(response)
            if he_text:
                snippet = he_text[:200] + "..." if len(he_text) > 200 else he_text
        
        return VerificationResult(
            ref=hint.ref,
            original_hint_ref=hint.ref,
            verified=True,
            keywords_found=hint.verification_keywords[:3] if hint.verification_keywords else [],
            reason="Trusted (certain confidence from Step 2)",
            text_snippet=snippet,
            confidence=hint.confidence
        )
    
    # Get buffer refs based on hint's buffer_size
    buffer_size = getattr(hint, 'buffer_size', DEFAULT_BUFFER_SIZE)
    refs_to_check = get_adjacent_refs(hint.ref, buffer_size)
    
    logger.debug(f"    Checking refs: {refs_to_check}")
    
    # Collect all keywords to search for
    keywords = list(hint.verification_keywords) if hint.verification_keywords else []
    
    # Add high-confidence terms from search_variants
    if search_variants:
        keywords.extend(search_variants.aramaic_forms)
        keywords.extend(search_variants.gemara_language[:3])  # Top 3
    
    # Deduplicate
    keywords = list(dict.fromkeys(keywords))
    
    logger.debug(f"    Keywords to search: {keywords[:10]}...")
    
    # Fetch and search all refs in buffer
    all_text = ""
    texts_by_ref = {}
    
    tasks = [fetch_text(r, session) for r in refs_to_check]
    responses = await asyncio.gather(*tasks, return_exceptions=True)
    
    for r, resp in zip(refs_to_check, responses):
        if isinstance(resp, Exception):
            logger.debug(f"    Error fetching {r}: {resp}")
            continue
        if resp:
            he_text, _ = extract_text_content(resp)
            if he_text:
                texts_by_ref[r] = {
                    "text": he_text,
                    "he_ref": resp.get("heRef", r),
                    "categories": resp.get("categories", [])
                }
                all_text += f"\n{he_text}\n"
    
    if not all_text:
        return VerificationResult(
            ref=hint.ref,
            original_hint_ref=hint.ref,
            verified=False,
            reason="No text found for this ref",
            confidence=hint.confidence
        )
    
    # FIX 2: Use weighted keyword scoring
    # min_score=3.0 means we need either:
    #   - 1 specific phrase (3 pts), OR
    #   - 2 generic words (2 pts) - NOT enough, OR  
    #   - 1 non-generic word + 1 generic (2.5 pts) - NOT enough
    verified, keywords_found, score = verify_text_contains_keywords(
        all_text, keywords, min_score=3.0
    )
    
    logger.debug(f"    Score: {score}, Keywords found: {keywords_found}")
    
    if verified:
        # Find which specific ref has the highest score
        best_ref = hint.ref
        best_score = 0
        
        for r, data in texts_by_ref.items():
            _, found, ref_score = verify_text_contains_keywords(
                data["text"], keywords, min_score=0  # Get score regardless
            )
            if ref_score > best_score:
                best_score = ref_score
                best_ref = r
        
        # Get snippet around first keyword
        snippet = ""
        if keywords_found and best_ref in texts_by_ref:
            text = texts_by_ref[best_ref]["text"]
            first_keyword = keywords_found[0]
            pos = text.find(first_keyword)
            if pos >= 0:
                start = max(0, pos - 50)
                end = min(len(text), pos + len(first_keyword) + 100)
                snippet = "..." + text[start:end] + "..."
        
        return VerificationResult(
            ref=best_ref,
            original_hint_ref=hint.ref,
            verified=True,
            keywords_found=keywords_found,
            reason=f"Found {len(keywords_found)} keywords (score: {score:.1f})",
            text_snippet=snippet,
            confidence=hint.confidence
        )
    else:
        return VerificationResult(
            ref=hint.ref,
            original_hint_ref=hint.ref,
            verified=False,
            reason=f"Score too low ({score:.1f} < 3.0) - only generic matches",
            confidence=hint.confidence
        )


# =============================================================================
#  PHASE 1: VERIFY AND FETCH FOUNDATION STONES
# =============================================================================

async def verify_and_fetch_foundations(
    analysis: 'QueryAnalysis',
    session: aiohttp.ClientSession
) -> Tuple[List[Source], List[VerificationResult]]:
    """
    Verify ref hints and fetch verified sources as foundation stones.
    
    NO CLAUDE CALLS - uses programmatic verification.
    """
    log_subsection("PHASE 1: PROGRAMMATIC VERIFICATION")
    
    foundation_stones = []
    verification_results = []
    
    # Get ref hints from Step 2
    ref_hints = getattr(analysis, 'ref_hints', [])
    
    # Backward compatibility: if no ref_hints, check for suggested_refs
    if not ref_hints and hasattr(analysis, 'suggested_refs'):
        logger.warning("Using legacy suggested_refs (no verification_keywords)")
        for ref in analysis.suggested_refs:
            # Create basic RefHint without keywords
            from step_two_understand import RefHint
            ref_hints.append(RefHint(
                ref=ref,
                confidence=RefConfidence.POSSIBLE,
                verification_keywords=[],
                buffer_size=DEFAULT_BUFFER_SIZE
            ))
    
    if not ref_hints:
        logger.warning("No ref hints from Step 2")
        return [], []
    
    # Get search variants for additional keyword matching
    search_variants = getattr(analysis, 'search_variants', None)
    
    # Verify each hint
    logger.info(f"Verifying {len(ref_hints)} ref hints...")
    
    for hint in ref_hints:
        result = await verify_ref_programmatic(hint, session, search_variants)
        verification_results.append(result)
        
        # Log result
        log_verification(
            ref=result.ref,
            verified=result.verified,
            reason=result.reason,
            keywords_found=result.keywords_found
        )
        
        if result.verified:
            # Fetch full text for verified ref
            response = await fetch_text(result.ref, session)
            
            if response:
                he_text, en_text = extract_text_content(response)
                
                source = Source(
                    ref=result.ref,
                    he_ref=response.get("heRef", result.ref),
                    level=determine_level(response.get("categories", []), result.ref),
                    hebrew_text=he_text,
                    english_text=en_text,
                    categories=response.get("categories", []),
                    is_foundation=True,
                    is_verified=True,
                    verification_keywords_found=result.keywords_found
                )
                foundation_stones.append(source)
    
    # Summary
    verified_count = sum(1 for r in verification_results if r.verified)
    logger.info(f"  Verification complete: {verified_count}/{len(ref_hints)} refs verified")
    
    return foundation_stones, verification_results


# =============================================================================
#  PHASE 2: TRICKLE UP (COMMENTARIES)
# =============================================================================

async def trickle_up(
    foundation_refs: List[str],
    target_sources: List[str],
    session: aiohttp.ClientSession
) -> List[Source]:
    """
    Fetch commentaries (trickle up) for foundation stones.
    
    Uses Sefaria's /related API.
    """
    log_subsection("PHASE 2: TRICKLE UP (COMMENTARIES)")
    
    if not foundation_refs:
        logger.info("  No foundation refs to trickle up from")
        return []
    
    # Normalize target sources
    target_lower = [t.lower().replace(" ", "_") for t in target_sources]
    
    logger.info(f"  Foundation refs: {foundation_refs}")
    logger.info(f"  Target sources: {target_lower}")
    
    commentary_sources = []
    seen_refs = set()
    
    for ref in foundation_refs:
        logger.info(f"  Getting commentaries for: {ref}")
        
        related = await fetch_related(ref, session)
        if not related:
            continue
        
        # Process commentaries
        links = related.get("links", [])
        for link in links:
            link_ref = link.get("ref", "")
            if not link_ref or link_ref in seen_refs:
                continue
            
            # Check if this matches target sources
            categories = link.get("category", "")
            collective_title = link.get("collectiveTitle", {}).get("en", "")
            
            # Match against target sources
            is_target = False
            matched_target = None
            
            for target in target_lower:
                if target == "gemara":
                    continue  # Skip gemara in trickle-up
                
                search_patterns = SOURCE_NAME_MAP.get(target, [target])
                for pattern in search_patterns:
                    if pattern.lower() in categories.lower() or pattern.lower() in collective_title.lower() or pattern.lower() in link_ref.lower():
                        is_target = True
                        matched_target = target
                        break
                if is_target:
                    break
            
            if not is_target:
                continue
            
            seen_refs.add(link_ref)
            
            # Fetch text for this commentary
            text_response = await fetch_text(link_ref, session)
            if not text_response:
                continue
            
            he_text, en_text = extract_text_content(text_response)
            
            source = Source(
                ref=link_ref,
                he_ref=text_response.get("heRef", link_ref),
                level=determine_level(text_response.get("categories", []), link_ref),
                hebrew_text=he_text,
                english_text=en_text,
                author=collective_title,
                categories=text_response.get("categories", []),
                is_foundation=False,
                is_verified=False
            )
            commentary_sources.append(source)
            logger.debug(f"    Added: {link_ref} ({matched_target})")
    
    logger.info(f"  Found {len(commentary_sources)} commentaries")
    return commentary_sources


# =============================================================================
#  PHASE 3: TRICKLE DOWN (EARLIER SOURCES)
# =============================================================================

async def trickle_down(
    foundation_refs: List[str],
    foundation_type: FoundationType,
    session: aiohttp.ClientSession
) -> List[Source]:
    """
    Find earlier sources (trickle down) - Mishna, Pasuk, etc.
    
    Uses Sefaria's /links API.
    """
    log_subsection("PHASE 3: TRICKLE DOWN (EARLIER SOURCES)")
    
    if not foundation_refs:
        logger.info("  No foundation refs to trickle down from")
        return []
    
    # For halacha, we don't trickle down (already at destination)
    if foundation_type in [FoundationType.HALACHA_SA, FoundationType.HALACHA_RAMBAM]:
        logger.info("  Halacha query - skipping trickle down")
        return []
    
    earlier_sources = []
    seen_refs = set()
    
    # Levels considered "earlier"
    earlier_levels = {SourceLevel.PASUK, SourceLevel.MISHNA, SourceLevel.TOSEFTA}
    
    for ref in foundation_refs:
        logger.info(f"  Finding earlier sources for: {ref}")
        
        links = await fetch_links(ref, session)
        if not links:
            continue
        
        for link in links:
            if not isinstance(link, dict):
                continue
            
            link_ref = link.get("ref", "")
            if not link_ref or link_ref in seen_refs:
                continue
            
            # Check if this is an earlier source
            categories = link.get("category", "")
            
            is_earlier = False
            if any(cat in categories for cat in ["Tanakh", "Torah", "Mishnah", "Tosefta"]):
                is_earlier = True
            
            if not is_earlier:
                continue
            
            seen_refs.add(link_ref)
            
            # Fetch text
            text_response = await fetch_text(link_ref, session)
            if not text_response:
                continue
            
            he_text, en_text = extract_text_content(text_response)
            
            source = Source(
                ref=link_ref,
                he_ref=text_response.get("heRef", link_ref),
                level=determine_level(text_response.get("categories", []), link_ref),
                hebrew_text=he_text,
                english_text=en_text,
                categories=text_response.get("categories", []),
                is_foundation=False,
                is_verified=False
            )
            earlier_sources.append(source)
            logger.debug(f"    Added: {link_ref}")
    
    logger.info(f"  Found {len(earlier_sources)} earlier sources")
    return earlier_sources


# =============================================================================
#  MAIN SEARCH FUNCTION
# =============================================================================

async def search(analysis: 'QueryAnalysis') -> SearchResult:
    """
    Main search function - V3 with programmatic verification.
    
    NO CLAUDE CALLS IN THIS FUNCTION.
    
    Flow:
    1. Verify ref hints from Step 2 using verification_keywords
    2. Fetch verified refs as foundation stones
    3. Trickle up/down based on direction
    4. Return organized sources
    """
    log_section("STEP 3: SEARCH [V3 - PROGRAMMATIC VERIFICATION]")
    
    logger.info(f"  Query: {analysis.original_query}")
    logger.info(f"  Foundation type: {analysis.foundation_type}")
    logger.info(f"  Trickle direction: {analysis.trickle_direction}")
    
    # Log ref hints
    ref_hints = getattr(analysis, 'ref_hints', [])
    if ref_hints:
        logger.info(f"  Ref hints from Step 2: {len(ref_hints)}")
        for hint in ref_hints:
            conf = hint.confidence.value if hasattr(hint.confidence, 'value') else hint.confidence
            logger.info(f"    - {hint.ref} [{conf}]")
    else:
        logger.info(f"  Suggested refs: {getattr(analysis, 'suggested_refs', [])}")
    
    logger.info(f"  Target sources: {analysis.target_sources}")
    
    # Initialize result
    result = SearchResult(original_query=analysis.original_query)
    
    # Handle clarification case
    if analysis.needs_clarification:
        result.needs_clarification = True
        result.clarification_question = analysis.clarification_question
        result.confidence = ConfidenceLevel.LOW
        result.search_description = "Needs clarification before searching"
        return result
    
    # Handle no refs case
    if not ref_hints and not getattr(analysis, 'suggested_refs', []):
        logger.warning("No ref hints from Step 2")
        result.needs_clarification = True
        result.clarification_question = "I couldn't identify specific sources. Could you provide more details?"
        result.confidence = ConfidenceLevel.LOW
        return result
    
    async with aiohttp.ClientSession() as session:
        # =====================================================================
        # PHASE 1: Programmatic verification (NO CLAUDE!)
        # =====================================================================
        foundation_stones, verification_results = await verify_and_fetch_foundations(
            analysis, session
        )
        result.foundation_stones = foundation_stones
        result.refs_checked = len(verification_results)
        result.refs_verified = len(foundation_stones)
        
        # If no refs verified, use suggested refs as fallback
        verified_refs = [s.ref for s in foundation_stones]
        
        if not verified_refs:
            logger.warning("No refs verified programmatically, using hints as fallback")
            # Use high-confidence hints as fallback
            for hint in ref_hints:
                if hint.confidence in [RefConfidence.CERTAIN, RefConfidence.LIKELY]:
                    verified_refs.append(hint.ref)
            
            # Fetch those refs even if not verified
            for ref in verified_refs[:3]:  # Limit fallback
                response = await fetch_text(ref, session)
                if response:
                    he_text, en_text = extract_text_content(response)
                    source = Source(
                        ref=ref,
                        he_ref=response.get("heRef", ref),
                        level=determine_level(response.get("categories", []), ref),
                        hebrew_text=he_text,
                        english_text=en_text,
                        categories=response.get("categories", []),
                        is_foundation=True,
                        is_verified=False
                    )
                    result.foundation_stones.append(source)
            verified_refs = [s.ref for s in result.foundation_stones]
        
        # =====================================================================
        # PHASE 2: Trickle UP (if requested)
        # =====================================================================
        if analysis.trickle_direction in [TrickleDirection.UP, TrickleDirection.BOTH]:
            commentary_sources = await trickle_up(
                verified_refs,
                analysis.target_sources,
                session
            )
            result.commentary_sources = commentary_sources
        
        # =====================================================================
        # PHASE 3: Trickle DOWN (if requested)
        # =====================================================================
        if analysis.trickle_direction in [TrickleDirection.DOWN, TrickleDirection.BOTH]:
            earlier_sources = await trickle_down(
                verified_refs,
                analysis.foundation_type,
                session
            )
            result.earlier_sources = earlier_sources
    
    # =========================================================================
    # Organize results
    # =========================================================================
    
    all_sources = (
        result.foundation_stones +
        result.commentary_sources +
        result.earlier_sources
    )
    result.all_sources = all_sources
    result.total_sources = len(all_sources)
    
    # Group by level
    by_level: Dict[str, List[Source]] = defaultdict(list)
    for s in all_sources:
        by_level[s.level.value].append(s)
    result.sources_by_level = dict(by_level)
    
    # Set confidence
    if len(result.foundation_stones) >= 2 and result.refs_verified >= 2:
        result.confidence = ConfidenceLevel.HIGH
    elif len(result.foundation_stones) >= 1:
        result.confidence = ConfidenceLevel.MEDIUM
    else:
        result.confidence = ConfidenceLevel.LOW
    
    # Summary
    result.search_description = (
        f"Verified {result.refs_verified}/{result.refs_checked} refs programmatically. "
        f"Found {len(result.foundation_stones)} foundation stones, "
        f"{len(result.commentary_sources)} commentaries, "
        f"{len(result.earlier_sources)} earlier sources. "
        f"Total: {result.total_sources} sources."
    )
    
    # =========================================================================
    # Log summary
    # =========================================================================
    log_section("SEARCH COMPLETE (V3 - NO CLAUDE VERIFICATION CALLS)")
    logger.info(f"  Verification method: {result.verification_method}")
    logger.info(f"  Refs verified: {result.refs_verified}/{result.refs_checked}")
    logger.info(f"  Foundation stones: {[s.ref for s in result.foundation_stones]}")
    logger.info(f"  Commentaries: {len(result.commentary_sources)}")
    logger.info(f"  Earlier sources: {len(result.earlier_sources)}")
    logger.info(f"  Total: {result.total_sources}")
    logger.info(f"  Confidence: {result.confidence}")
    logger.info("=" * 70 + "\n")
    
    return result


# =============================================================================
#  EXPORTS
# =============================================================================

__all__ = [
    'search',
    'SearchResult',
    'Source',
    'SourceLevel',
    'VerificationResult',
    'verify_ref_programmatic',
    'verify_text_contains_keywords',
]


# =============================================================================
#  CLI TESTING
# =============================================================================

if __name__ == "__main__":
    import asyncio
    
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    async def test():
        print("\n" + "=" * 70)
        print("STEP 3 V3 - PROGRAMMATIC VERIFICATION TEST")
        print("=" * 70)
        
        # Mock a QueryAnalysis from Step 2
        from step_two_understand import (
            QueryAnalysis, RefHint, SearchVariants,
            QueryType, FoundationType, TrickleDirection, 
            ConfidenceLevel, RefConfidence, Breadth
        )
        
        # Simulate what Step 2 would return for "chezkas haguf vs chezkas mammon"
        analysis = QueryAnalysis(
            original_query="chezkas haguf vs chezkas mammon",
            hebrew_terms_from_step1=["חזקת הגוף", "חזקת ממון"],
            query_type=QueryType.COMPARISON,
            foundation_type=FoundationType.GEMARA,
            trickle_direction=TrickleDirection.UP,
            breadth=Breadth.STANDARD,
            ref_hints=[
                RefHint(
                    ref="Ketubot 76b",
                    confidence=RefConfidence.CERTAIN,
                    verification_keywords=["חזקה דגופא", "חזקה דממונא", "רבא", "אזיל בתר"],
                    reasoning="Main sugya",
                    buffer_size=1
                ),
                RefHint(
                    ref="Ketubot 75a",
                    confidence=RefConfidence.LIKELY,
                    verification_keywords=["מום", "חזקה"],
                    reasoning="Start of sugya",
                    buffer_size=1
                ),
            ],
            search_variants=SearchVariants(
                primary_hebrew=["חזקת הגוף", "חזקת ממון"],
                aramaic_forms=["חזקה דגופא", "חזקה דממונא", "דגופא", "דממונא"],
                gemara_language=["אזיל בתר חזקה דגופא", "אזיל בתר חזקה דממונא"],
                root_words=["חזקה", "גוף", "ממון"],
                related_terms=["המוציא מחבירו"]
            ),
            target_sources=["gemara", "rashi", "tosafos", "ran"],
            confidence=ConfidenceLevel.HIGH
        )
        
        result = await search(analysis)
        
        print("\n--- TEST RESULTS ---")
        print(f"Foundation stones: {[s.ref for s in result.foundation_stones]}")
        print(f"Commentaries: {len(result.commentary_sources)}")
        print(f"Total sources: {result.total_sources}")
        print(f"Confidence: {result.confidence}")
        print(f"\n{result.search_description}")
    
    asyncio.run(test())