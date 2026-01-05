"""
Step 3: SEARCH - V5 with Topic-Filtered Commentary and Line-Level Targeting
============================================================================

V5 CHANGES FROM V4:
1. PROPER SOURCE MAPPING: Ran writes on Rif, not directly on Gemara
2. TOPIC-FILTERED COMMENTARIES: Only fetch commentaries on relevant segments
3. LINE-LEVEL TARGETING: Score gemara segments, expand only high-scoring lines
4. BETTER CATEGORY MATCHING: Fix false positives (Likutei Moharan != Ran)
5. AUTHOR-SPECIFIC FETCHING: When asking for Ran's shittah, prioritize Ran sources

KEY IMPROVEMENTS:
- trickle_up_filtered(): Only gets commentaries on segments containing focus terms
- fetch_author_commentary(): Specifically fetches one author's commentary
- RISHON_SEFARIA_MAP: Maps rishon names to correct Sefaria patterns
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

# Import SourceLevel from central models
try:
    from models import SourceLevel, ConfidenceLevel as ModelsConfidenceLevel
    logger.debug("Imported SourceLevel from models.py")
except ImportError:
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

# Import Step 2 V5 structures
try:
    from step_two_understand import (
        QueryAnalysis, RefHint, SearchVariants,
        FoundationType, TrickleDirection, ConfidenceLevel, 
        RefConfidence, LandmarkConfidence, QueryType
    )
except ImportError:
    logger.warning("Could not import step_two_understand, using fallback enums")
    
    class FoundationType(str, Enum):
        GEMARA = "gemara"
        MISHNA = "mishna"
        CHUMASH = "chumash"
        HALACHA_SA = "halacha_sa"
        HALACHA_RAMBAM = "halacha_rambam"
        MIDRASH = "midrash"
        RISHON = "rishon"
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
    
    class LandmarkConfidence(str, Enum):
        HIGH = "high"
        MEDIUM = "medium"
        GUESSING = "guessing"
        NONE = "none"
    
    class QueryType(str, Enum):
        TOPIC = "topic"
        NUANCE = "nuance"
        SHITTAH = "shittah"
        COMPARISON = "comparison"
        MACHLOKES = "machlokes"
        UNKNOWN = "unknown"

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
#  V5: PROPER RISHON-TO-SEFARIA MAPPING
# =============================================================================

# Maps rishon names to their ACTUAL Sefaria patterns
# This is critical because different rishonim have different structures

RISHON_SEFARIA_MAP = {
    # Ran writes on RIF, not directly on Gemara
    "ran": {
        "patterns": ["Ran on Rif", "Chiddushei HaRan"],
        "sefaria_prefix": "Ran on Rif",
        "writes_on": "rif",
        "fallback_search": "ran",
    },
    
    # Direct gemara commentaries
    "rashi": {
        "patterns": ["Rashi on"],
        "sefaria_prefix": "Rashi on",
        "writes_on": "gemara",
    },
    "tosafos": {
        "patterns": ["Tosafot on", "Tosafos on"],
        "sefaria_prefix": "Tosafot on",
        "writes_on": "gemara",
    },
    "rashba": {
        "patterns": ["Rashba on"],
        "sefaria_prefix": "Rashba on",
        "writes_on": "gemara",
    },
    "ritva": {
        "patterns": ["Ritva on"],
        "sefaria_prefix": "Ritva on",
        "writes_on": "gemara",
    },
    "ramban": {
        "patterns": ["Ramban on"],
        "sefaria_prefix": "Ramban on",
        "writes_on": "gemara",
    },
    "meiri": {
        "patterns": ["Meiri on"],
        "sefaria_prefix": "Meiri on",
        "writes_on": "gemara",
    },
    
    # Rosh has its own structure (chapter:siman)
    "rosh": {
        "patterns": ["Rosh on"],
        "sefaria_prefix": "Rosh on",
        "writes_on": "gemara",
        "structure": "chapter_siman",
    },
    
    # Rif (Alfasi)
    "rif": {
        "patterns": ["Rif"],
        "sefaria_prefix": "Rif",
        "writes_on": "gemara",
    },
    
    # Rambam - Mishneh Torah
    "rambam": {
        "patterns": ["Mishneh Torah", "Rambam"],
        "sefaria_prefix": "Mishneh Torah",
        "writes_on": "halacha",
    },

    # === ACHARONIM ON GEMARA ===
    # Note: Keys use underscores since fetch_author_commentary normalizes with replace(" ", "_")
    "pnei_yehoshua": {
        "patterns": ["Penei Yehoshua on", "Pnei Yehoshua on"],
        "sefaria_prefix": "Penei Yehoshua on",
        "writes_on": "gemara",
    },
    "shitah_yeshanah": {
        "patterns": ["Shitah Mekubetzet on"],  # Often Shitah Yeshanah is in Shitah Mekubetzet
        "sefaria_prefix": "Shitah Mekubetzet on",
        "writes_on": "gemara",
    },
    "shita_mekubetzet": {
        "patterns": ["Shitah Mekubetzet on"],
        "sefaria_prefix": "Shitah Mekubetzet on",
        "writes_on": "gemara",
    },
    "shitah_mekubetzet": {
        "patterns": ["Shitah Mekubetzet on"],
        "sefaria_prefix": "Shitah Mekubetzet on",
        "writes_on": "gemara",
    },

    # === ACHARONIM ON SHULCHAN ARUCH ===
    "ketzos": {
        "patterns": ["Ketzot HaChoshen", "Ketzos HaChoshen"],
        "sefaria_prefix": "Ketzot HaChoshen",
        "writes_on": "choshen_mishpat",
    },
    "ketzos_hachoshen": {
        "patterns": ["Ketzot HaChoshen"],
        "sefaria_prefix": "Ketzot HaChoshen",
        "writes_on": "choshen_mishpat",
    },
    "ketzot_hachoshen": {
        "patterns": ["Ketzot HaChoshen"],
        "sefaria_prefix": "Ketzot HaChoshen",
        "writes_on": "choshen_mishpat",
    },
    "nesivos": {
        "patterns": ["Netivot HaMishpat", "Nesivos HaMishpat"],
        "sefaria_prefix": "Netivot HaMishpat",
        "writes_on": "choshen_mishpat",
    },
    "nesivos_hamishpat": {
        "patterns": ["Netivot HaMishpat"],
        "sefaria_prefix": "Netivot HaMishpat",
        "writes_on": "choshen_mishpat",
    },
    "netivot_hamishpat": {
        "patterns": ["Netivot HaMishpat"],
        "sefaria_prefix": "Netivot HaMishpat",
        "writes_on": "choshen_mishpat",
    },
    "taz": {
        "patterns": ["Turei Zahav on Shulchan Arukh"],
        "sefaria_prefix": "Turei Zahav on Shulchan Arukh",
        "writes_on": "shulchan_aruch",
    },
    "shach": {
        "patterns": ["Siftei Kohen on Shulchan Arukh"],
        "sefaria_prefix": "Siftei Kohen on Shulchan Arukh",
        "writes_on": "shulchan_aruch",
    },
    "gra": {
        "patterns": ["Biur HaGra on Shulchan Arukh"],
        "sefaria_prefix": "Biur HaGra on Shulchan Arukh",
        "writes_on": "shulchan_aruch",
    },
    "pri_chadash": {
        "patterns": ["Pri Chadash on Shulchan Arukh"],
        "sefaria_prefix": "Pri Chadash on Shulchan Arukh",
        "writes_on": "shulchan_aruch",
    },

    # === OTHER ACHARONIM ===
    "noda_byehuda": {
        "patterns": ["Noda BiYehuda"],
        "sefaria_prefix": "Noda BiYehuda",
        "writes_on": "responsa",
        "fallback_search": "noda biyehuda",
    },
    "noda_b'yehuda": {
        "patterns": ["Noda BiYehuda"],
        "sefaria_prefix": "Noda BiYehuda",
        "writes_on": "responsa",
        "fallback_search": "noda biyehuda",
    },
    "beis_yaakov": {
        "patterns": ["Beit Ya'akov"],  # On Ketubot
        "sefaria_prefix": "Beit Ya'akov on",
        "writes_on": "gemara",
    },
}

# V5: Better category-to-level mapping with exclusions
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

# V5: Expanded source name map with proper patterns
SOURCE_NAME_MAP = {
    "gemara": ["Talmud", "Bavli"],
    "rashi": ["Rashi on"],
    "tosafos": ["Tosafot on", "Tosafos on"],
    "ran": ["Ran on Rif", "Chiddushei HaRan"],  # V5: Fixed - Ran writes on Rif!
    "rashba": ["Rashba on"],
    "ritva": ["Ritva on"],
    "ramban": ["Ramban on"],
    "rambam": ["Rambam", "Mishneh Torah"],
    "rosh": ["Rosh on"],
    "rif": ["Rif "],  # Note the space to avoid matching other things
    "meiri": ["Meiri on"],
    "shulchan_arukh": ["Shulchan Arukh"],
    "mishnah_berurah": ["Mishnah Berurah"],
    "taz": ["Taz", "Turei Zahav"],
    "shach": ["Shakh", "Siftei Kohen"],
    "magen_avraham": ["Magen Avraham"],
    "ketzos": ["Ketzot HaChoshen", "Ketzos"],
    "nesivos": ["Netivot HaMishpat", "Nesivos"],
    "chumash": ["Torah", "Tanakh"],
}

# V5: Exclusion patterns - refs that should NOT match certain categories
EXCLUSION_PATTERNS = {
    "ran": ["Likutei Moharan", "Otzar", "Midrash"],  # These are NOT Ran
    "rashi": ["Otzar", "Likutei"],
    "tosafos": ["Piskei Tosafot"],  # This is a summary, not Tosafos itself
}


# =============================================================================
#  DATA STRUCTURES
# =============================================================================

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
    # V4: Nuance scoring
    is_landmark: bool = False
    is_primary: bool = True
    focus_score: float = 0.0
    tier: str = "background"
    # V5: Segment info
    segment_index: Optional[int] = None  # Which segment of the daf this is from


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
class LandmarkResult:
    """Result of landmark discovery."""
    landmark_ref: Optional[str] = None
    discovery_method: str = "none"
    confidence: str = "low"
    reasoning: str = ""
    focus_keywords_found: List[str] = field(default_factory=list)
    topic_keywords_found: List[str] = field(default_factory=list)


@dataclass
class SearchResult:
    """Complete search result - V5 with topic-filtered sources."""
    original_query: str
    
    # V5: Tiered sources
    landmark_source: Optional[Source] = None
    primary_sources: List[Source] = field(default_factory=list)
    context_sources: List[Source] = field(default_factory=list)
    background_sources: List[Source] = field(default_factory=list)
    
    # Legacy: flat lists for backward compatibility
    foundation_stones: List[Source] = field(default_factory=list)
    commentary_sources: List[Source] = field(default_factory=list)
    earlier_sources: List[Source] = field(default_factory=list)
    
    # V5: Author-specific sources (for shittah queries)
    author_sources: Dict[str, List[Source]] = field(default_factory=dict)
    
    all_sources: List[Source] = field(default_factory=list)
    sources_by_level: Dict[str, List[Source]] = field(default_factory=dict)
    
    total_sources: int = 0
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    search_description: str = ""
    
    needs_clarification: bool = False
    clarification_question: Optional[str] = None
    
    # V5: Enhanced stats
    is_nuance_result: bool = False
    landmark_discovery: Optional[LandmarkResult] = None
    refs_verified: int = 0
    refs_checked: int = 0
    verification_method: str = "programmatic"
    segments_analyzed: int = 0
    segments_relevant: int = 0


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


async def sefaria_search(query: str, session: aiohttp.ClientSession, filters: Dict = None) -> Optional[Dict]:
    """Search Sefaria for a query."""
    try:
        url = f"{SEFARIA_BASE_URL}/search-wrapper"
        params = {
            "query": query,
            "type": "text",
            "size": 20
        }
        if filters:
            params.update(filters)
        
        async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=30)) as response:
            if response.status == 200:
                return await response.json()
            else:
                logger.debug(f"Sefaria search returned {response.status}")
                return None
    except Exception as e:
        logger.debug(f"Error searching Sefaria: {e}")
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
            result.append(text_obj)
    elif isinstance(text_obj, list):
        for item in text_obj:
            result.extend(flatten_text(item))
    return result


def extract_text_segments(sefaria_response: Dict) -> List[Dict]:
    """
    V6 FIX: Extract individual segments from Sefaria response.

    Instead of flattening all text into one blob, returns a list of segments
    with their index, Hebrew text, and English text.

    Returns:
        List of dicts with keys: index, he_text, en_text
    """
    segments = []

    if not sefaria_response:
        return segments

    he = sefaria_response.get("he", "")
    en = sefaria_response.get("text", "")

    # Handle string case (single segment)
    if isinstance(he, str):
        if he.strip():
            segments.append({
                "index": 1,
                "he_text": he,
                "en_text": en if isinstance(en, str) else ""
            })
        return segments

    # Handle list case (multiple segments)
    if isinstance(he, list):
        for i, he_item in enumerate(he):
            # Get corresponding English text
            en_item = ""
            if isinstance(en, list) and i < len(en):
                en_item = en[i] if isinstance(en[i], str) else ""

            # Flatten nested arrays within this segment
            if isinstance(he_item, list):
                he_text = " ".join(flatten_text(he_item))
            else:
                he_text = str(he_item) if he_item else ""

            if isinstance(en_item, list):
                en_text = " ".join(flatten_text(en_item))
            else:
                en_text = str(en_item) if en_item else ""

            if he_text.strip():
                segments.append({
                    "index": i + 1,  # 1-indexed like Sefaria
                    "he_text": he_text,
                    "en_text": en_text
                })

    return segments


def determine_level(categories: List[str], ref: str) -> SourceLevel:
    """Determine the source level from Sefaria categories."""
    ref_lower = ref.lower()
    
    # Check ref patterns first
    if "rashi on" in ref_lower:
        return SourceLevel.RASHI
    if "tosafot on" in ref_lower or "tosafos on" in ref_lower:
        return SourceLevel.TOSFOS
    if "rambam" in ref_lower or "mishneh torah" in ref_lower:
        return SourceLevel.RAMBAM
    if "shulchan arukh" in ref_lower or "shulchan aruch" in ref_lower:
        return SourceLevel.SHULCHAN_ARUCH
    if "tur " in ref_lower:
        return SourceLevel.TUR
    
    # V5: Check for Ran on Rif specifically
    if "ran on rif" in ref_lower:
        return SourceLevel.RISHONIM
    
    # Check categories
    for cat in categories:
        if cat in CATEGORY_TO_LEVEL:
            return CATEGORY_TO_LEVEL[cat]
    
    # Check for rishonim patterns
    rishonim_patterns = ["rashba", "ritva", "ramban", "ran ", "rosh ", "meiri", "nimukei"]
    for pattern in rishonim_patterns:
        if pattern in ref_lower:
            return SourceLevel.RISHONIM
    
    return SourceLevel.OTHER


# =============================================================================
#  TEXT NORMALIZATION & KEYWORD MATCHING
# =============================================================================

def normalize_for_search(text: str) -> str:
    """Normalize Hebrew text for keyword matching."""
    if not text:
        return ""
    
    # Strip HTML
    text = re.sub(r'<[^>]+>', '', text)
    
    # Remove nikud
    text = re.sub(r'[\u05B0-\u05BD\u05BF\u05C1\u05C2\u05C4\u05C5\u05C7]', '', text)
    
    # Normalize geresh/gershayim
    text = text.replace('״', '').replace('׳', '')
    text = text.replace('"', '').replace("'", '')
    
    # Normalize sofits
    sofit_map = {'ם': 'מ', 'ן': 'נ', 'ף': 'פ', 'ך': 'כ', 'ץ': 'צ'}
    for sofit, regular in sofit_map.items():
        text = text.replace(sofit, regular)
    
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text)
    
    return text


def generate_keyword_variants(keyword: str) -> List[str]:
    """Generate variations of a keyword for flexible matching."""
    variants = [keyword]

    # Smichut: ה ↔ ת
    if keyword.endswith('ה'):
        variants.append(keyword[:-1] + 'ת')
    if keyword.endswith('ת'):
        variants.append(keyword[:-1] + 'ה')

    # Handle דגופא / דממונא spacing
    if ' ד' in keyword:
        variants.append(keyword.replace(' ד', 'ד'))

    # Handle הגוף / גוף
    if 'הגוף' in keyword:
        variants.append(keyword.replace('הגוף', 'גוף'))
    if 'גוף' in keyword and 'הגוף' not in keyword:
        variants.append(keyword.replace('גוף', 'הגוף'))

    # V6 FIX: For multi-word phrases, also include significant individual words
    # This helps match when gemara uses shorter forms (e.g., "חזקה" instead of "חזקת הגוף")
    words = keyword.split()
    if len(words) > 1:
        # Add individual words that are significant (> 2 chars)
        for word in words:
            # Skip articles and prefixes
            if len(word) > 2 and word not in {'את', 'על', 'אל', 'מן', 'עם'}:
                variants.append(word)
                # Also add smichut variants for individual words
                if word.endswith('ה'):
                    variants.append(word[:-1] + 'ת')
                if word.endswith('ת'):
                    variants.append(word[:-1] + 'ה')

    # Add common Aramaic forms for Hebrew terms
    aramaic_mappings = {
        'חזקה': ['חזקא', 'דחזקה', 'דחזקא'],
        'ממון': ['ממונא', 'דממונא', 'דממון'],
        'גוף': ['גופא', 'דגופא', 'דגוף'],
        'מוחזק': ['מוחזקת', 'מוחזקין'],
        'רוב': ['רובא', 'דרובא'],
    }
    for base, aramaic_forms in aramaic_mappings.items():
        if base in keyword:
            variants.extend(aramaic_forms)

    return list(set(variants))


# Generic words that appear everywhere
GENERIC_KEYWORDS = {
    'חזקה', 'ספק', 'רוב', 'מום', 'גוף', 'ממון', 'טהור', 'טמא',
    'אמר', 'רבא', 'אביי', 'רב', 'שמואל', 'מתני', 'גמרא',
    'ברי', 'שמא', 'דאמר', 'תנן', 'מאי',
}


def calculate_keyword_score(keywords_found: List[str], is_focus_term: bool = False) -> float:
    """Calculate weighted score for keywords found."""
    score = 0.0
    
    for keyword in keywords_found:
        base_score = 1.0
        
        # Multi-word phrases are specific
        if ' ' in keyword:
            base_score = 3.0
        # Aramaic construct forms
        elif keyword.startswith('ד') and len(keyword) > 3:
            base_score = 3.0
        # Known generic words
        elif keyword in GENERIC_KEYWORDS:
            base_score = 0.5
        # Other single words
        else:
            base_score = 1.5
        
        # Focus terms get bonus
        if is_focus_term:
            base_score *= 2.0
        
        score += base_score
    
    return score


def verify_text_contains_keywords(
    text: str,
    keywords: List[str],
    require_all: bool = False,
    min_score: float = 3.0
) -> Tuple[bool, List[str], float]:
    """Check if text contains keywords with weighted scoring."""
    if not text or not keywords:
        return False, [], 0.0
    
    text_normalized = normalize_for_search(text)
    text_no_spaces = text_normalized.replace(" ", "")
    keywords_found = []
    
    for keyword in keywords:
        variants = generate_keyword_variants(keyword)
        
        found = False
        for variant in variants:
            variant_normalized = normalize_for_search(variant)
            
            if variant in text or variant_normalized in text_normalized:
                found = True
                break
            
            variant_no_space = variant_normalized.replace(" ", "")
            if variant_no_space in text_no_spaces:
                found = True
                break
        
        if found:
            keywords_found.append(keyword)
    
    score = calculate_keyword_score(keywords_found)
    
    if require_all:
        verified = len(keywords_found) == len(keywords)
    else:
        verified = score >= min_score
    
    return verified, keywords_found, score


# =============================================================================
#  V5: SOURCE MATCHING WITH EXCLUSIONS
# =============================================================================

def matches_source_target(
    link_ref: str,
    categories: str,
    collective_title: str,
    target: str
) -> bool:
    """
    V5: Check if a link matches the target source with proper exclusions.
    """
    target_lower = target.lower().replace(" ", "_")
    
    # Get search patterns
    search_patterns = SOURCE_NAME_MAP.get(target_lower, [target])
    
    # Get exclusion patterns
    exclusions = EXCLUSION_PATTERNS.get(target_lower, [])
    
    # Check exclusions first
    for excl in exclusions:
        if excl.lower() in link_ref.lower():
            return False
        if excl.lower() in categories.lower():
            return False
        if excl.lower() in collective_title.lower():
            return False
    
    # Check for positive match
    for pattern in search_patterns:
        pattern_lower = pattern.lower()
        if pattern_lower in categories.lower():
            return True
        if pattern_lower in collective_title.lower():
            return True
        if pattern_lower in link_ref.lower():
            return True
    
    return False


# =============================================================================
#  V5: SEGMENT-LEVEL ANALYSIS
# =============================================================================

def analyze_segments(
    sefaria_response: Dict,
    focus_terms: List[str],
    topic_terms: List[str]
) -> List[Dict]:
    """
    V5: Analyze each segment of a daf to find which contain the topic.
    
    Returns list of dicts with:
    - segment_index: position in the text
    - segment_text: the Hebrew text
    - focus_score: score based on focus terms
    - topic_score: score based on topic terms
    - is_relevant: True if above threshold
    """
    he_content = sefaria_response.get("he", [])
    
    # Handle non-list content
    if not isinstance(he_content, list):
        he_content = [he_content] if he_content else []
    
    results = []
    all_keywords = focus_terms + topic_terms
    
    for idx, segment in enumerate(he_content):
        if isinstance(segment, list):
            # Nested structure - flatten
            segment_text = " ".join(flatten_text(segment))
        else:
            segment_text = str(segment) if segment else ""
        
        if not segment_text.strip():
            continue
        
        # Score this segment
        _, focus_found, focus_score = verify_text_contains_keywords(
            segment_text, focus_terms, min_score=0
        )
        _, topic_found, topic_score = verify_text_contains_keywords(
            segment_text, topic_terms, min_score=0
        )
        
        total_score = focus_score * 2 + topic_score
        
        results.append({
            "segment_index": idx,
            "segment_text": segment_text[:200],  # First 200 chars for logging
            "focus_found": focus_found,
            "topic_found": topic_found,
            "focus_score": focus_score,
            "topic_score": topic_score,
            "total_score": total_score,
            "is_relevant": total_score >= 3.0  # Threshold for relevance
        })
    
    return results


def get_relevant_segment_refs(
    base_ref: str,
    sefaria_response: Dict,
    focus_terms: List[str],
    topic_terms: List[str],
    min_score: float = 3.0
) -> List[str]:
    """
    V5: Get specific ref strings for segments that contain focus/topic terms.
    
    For example, if Pesachim 6b has discussion on segment 5,
    returns "Pesachim 6b:5" rather than the whole daf.
    """
    segments = analyze_segments(sefaria_response, focus_terms, topic_terms)
    
    relevant_refs = []
    for seg in segments:
        if seg["total_score"] >= min_score:
            # Build specific ref
            # Sefaria uses 1-indexed segments
            segment_ref = f"{base_ref}:{seg['segment_index'] + 1}"
            relevant_refs.append(segment_ref)
            logger.debug(f"    Relevant segment: {segment_ref} (score: {seg['total_score']})")
    
    return relevant_refs


# =============================================================================
#  PHASE 1: LANDMARK VERIFICATION & DISCOVERY
# =============================================================================

async def verify_landmark(
    suggested_landmark: str,
    landmark_confidence: LandmarkConfidence,
    focus_terms: List[str],
    topic_terms: List[str],
    session: aiohttp.ClientSession
) -> LandmarkResult:
    """Verify Claude's suggested landmark."""
    log_subsection("PHASE 1A: VERIFY CLAUDE'S LANDMARK")
    
    if not suggested_landmark:
        logger.info("  No landmark suggested by Claude")
        return LandmarkResult(discovery_method="none", reasoning="No landmark suggested")
    
    logger.info(f"  Suggested landmark: {suggested_landmark}")
    logger.info(f"  Confidence: {landmark_confidence.value if hasattr(landmark_confidence, 'value') else landmark_confidence}")
    logger.info(f"  Focus terms: {focus_terms}")
    logger.info(f"  Topic terms: {topic_terms}")
    
    # Step 1: Check if it exists
    response = await fetch_text(suggested_landmark, session)
    
    if not response:
        logger.warning(f"  ✗ Landmark doesn't exist: {suggested_landmark}")
        return LandmarkResult(
            discovery_method="none",
            reasoning=f"Landmark '{suggested_landmark}' not found in Sefaria - possible hallucination or wrong format"
        )
    
    he_text, en_text = extract_text_content(response)
    
    if not he_text:
        logger.warning(f"  ✗ Landmark has no text: {suggested_landmark}")
        return LandmarkResult(
            discovery_method="none",
            reasoning=f"Landmark '{suggested_landmark}' has no text content"
        )
    
    logger.info(f"  ✓ Landmark exists, text length: {len(he_text)} chars")
    
    # Step 2: Verify it contains focus_terms AND topic_terms
    _, focus_found, focus_score = verify_text_contains_keywords(
        he_text, focus_terms, min_score=0
    )
    _, topic_found, topic_score = verify_text_contains_keywords(
        he_text, topic_terms, min_score=0
    )
    
    logger.info(f"  Focus terms found: {focus_found} (score: {focus_score})")
    logger.info(f"  Topic terms found: {topic_found} (score: {topic_score})")
    
    # Must have at least one of each
    has_focus = len(focus_found) > 0
    has_topic = len(topic_found) > 0
    
    if has_focus and has_topic:
        logger.info(f"  ✓ LANDMARK VERIFIED: {suggested_landmark}")
        return LandmarkResult(
            landmark_ref=suggested_landmark,
            discovery_method="claude_verified",
            confidence="high" if focus_score >= 3.0 else "medium",
            reasoning=f"Contains {len(focus_found)} focus terms and {len(topic_found)} topic terms",
            focus_keywords_found=focus_found,
            topic_keywords_found=topic_found
        )
    else:
        missing = []
        if not has_focus:
            missing.append("focus terms")
        if not has_topic:
            missing.append("topic terms")
        
        logger.warning(f"  ✗ Landmark missing {', '.join(missing)}")
        return LandmarkResult(
            discovery_method="none",
            reasoning=f"Landmark exists but missing: {', '.join(missing)}"
        )


async def discover_via_achronim(
    focus_terms: List[str],
    topic_terms: List[str],
    session: aiohttp.ClientSession,
    target_chelek: Optional[str] = None
) -> LandmarkResult:
    """Discover landmark by searching achronim."""
    log_subsection("PHASE 1B: DISCOVER VIA ACHRONIM")
    
    if not focus_terms and not topic_terms:
        logger.info("  No terms to search for")
        return LandmarkResult(discovery_method="none", reasoning="No search terms provided")
    
    # Build search query
    search_terms = []
    if focus_terms:
        search_terms.extend(focus_terms[:2])
    if topic_terms:
        search_terms.extend(topic_terms[:2])
    
    search_query = " ".join(search_terms)
    logger.info(f"  Search query: {search_query}")
    
    # Search collections
    search_collections = [
        ("Shulchan Arukh", target_chelek),
        ("Tur", target_chelek),
        ("Mishnah Berurah", None)
    ]
    
    candidate_refs = []
    
    for collection, chelek in search_collections:
        logger.info(f"  Searching {collection}...")
        
        filters = {"filters": [collection]}
        if chelek:
            filters["filters"].append(chelek)
        
        results = await sefaria_search(search_query, session, filters)
        
        if results and results.get("hits", {}).get("hits"):
            hits = results["hits"]["hits"]
            logger.info(f"    Found {len(hits)} hits")
            
            for hit in hits[:10]:
                source = hit.get("_source", {})
                ref = source.get("ref", "")
                if ref:
                    candidate_refs.append(ref)
        else:
            logger.info(f"    No hits in {collection}")
    
    if not candidate_refs:
        logger.info("  No candidates found in achronim")
        return LandmarkResult(discovery_method="none", reasoning="No matching sources in SA/Tur/MB")
    
    logger.info(f"  Found {len(candidate_refs)} candidate refs")
    
    # Extract citations and find rishonim
    rishonim_candidates = []
    
    for ref in candidate_refs[:5]:
        logger.info(f"  Checking citations in: {ref}")
        
        links = await fetch_links(ref, session)
        
        if not links:
            continue
        
        for link in links:
            if not isinstance(link, dict):
                continue
            
            link_ref = link.get("ref", "")
            category = link.get("category", "")
            
            # Look for rishonim citations
            if any(cat in category for cat in ["Rishonim", "Rosh", "Ran", "Rashba", "Ritva"]):
                if link_ref not in [r["ref"] for r in rishonim_candidates]:
                    rishonim_candidates.append({
                        "ref": link_ref,
                        "category": category,
                        "cited_by": ref
                    })
    
    if not rishonim_candidates:
        logger.info("  No rishon citations found")
        return LandmarkResult(discovery_method="none", reasoning="Found achronim but no rishon citations")
    
    logger.info(f"  Found {len(rishonim_candidates)} rishon candidates")
    
    # Score each candidate
    scored_candidates = []
    
    for candidate in rishonim_candidates[:10]:
        ref = candidate["ref"]
        logger.info(f"  Scoring: {ref}")
        
        response = await fetch_text(ref, session)
        if not response:
            continue
        
        he_text, _ = extract_text_content(response)
        if not he_text:
            continue
        
        _, focus_found, _ = verify_text_contains_keywords(he_text, focus_terms, min_score=0)
        _, topic_found, _ = verify_text_contains_keywords(he_text, topic_terms, min_score=0)
        
        focus_score = calculate_keyword_score(focus_found, is_focus_term=True)
        topic_score = calculate_keyword_score(topic_found, is_focus_term=False)
        total_score = focus_score + topic_score
        
        scored_candidates.append({
            "ref": ref,
            "focus_found": focus_found,
            "topic_found": topic_found,
            "focus_score": focus_score,
            "topic_score": topic_score,
            "total_score": total_score
        })
        
        logger.info(f"    Score: {total_score} (focus: {focus_score}, topic: {topic_score})")
    
    if not scored_candidates:
        return LandmarkResult(discovery_method="none", reasoning="Could not score any rishon candidates")
    
    scored_candidates.sort(key=lambda x: x["total_score"], reverse=True)
    best = scored_candidates[0]
    
    if best["focus_found"] and best["topic_found"]:
        logger.info(f"  ✓ DISCOVERED LANDMARK: {best['ref']}")
        return LandmarkResult(
            landmark_ref=best["ref"],
            discovery_method="achronim_discovery",
            confidence="medium",
            reasoning=f"Found via achronim search, score: {best['total_score']}",
            focus_keywords_found=best["focus_found"],
            topic_keywords_found=best["topic_found"]
        )
    else:
        logger.info(f"  Best candidate missing required terms")
        return LandmarkResult(
            discovery_method="none",
            reasoning=f"Best candidate ({best['ref']}) missing focus or topic terms"
        )


async def find_landmark(
    analysis: 'QueryAnalysis',
    session: aiohttp.ClientSession
) -> LandmarkResult:
    """Find the landmark source for a nuance query."""
    log_section("FINDING LANDMARK FOR NUANCE QUERY")
    
    nuance_desc = getattr(analysis, 'nuance_description', '')
    focus_terms = getattr(analysis, 'focus_terms', [])
    topic_terms = getattr(analysis, 'topic_terms', [])
    suggested_landmark = getattr(analysis, 'suggested_landmark', None)
    landmark_confidence = getattr(analysis, 'landmark_confidence', LandmarkConfidence.NONE)
    target_chelek = getattr(analysis, 'target_chelek', None)
    
    logger.info(f"  Nuance: {nuance_desc}")
    logger.info(f"  Focus terms: {focus_terms}")
    logger.info(f"  Topic terms: {topic_terms}")
    
    # Phase 1A: Try Claude's suggested landmark
    if suggested_landmark:
        result = await verify_landmark(
            suggested_landmark, landmark_confidence,
            focus_terms, topic_terms, session
        )
        if result.landmark_ref:
            return result
    
    # Phase 1B: Discover via achronim
    result = await discover_via_achronim(
        focus_terms, topic_terms, session, target_chelek
    )
    if result.landmark_ref:
        return result
    
    # All methods failed
    return LandmarkResult(
        discovery_method="none",
        confidence="low",
        reasoning="Could not verify or discover a landmark source"
    )


# =============================================================================
#  V5: TOPIC-FILTERED TRICKLE UP
# =============================================================================

async def trickle_up_filtered(
    foundation_refs: List[str],
    target_sources: List[str],
    focus_terms: List[str],
    topic_terms: List[str],
    session: aiohttp.ClientSession
) -> Tuple[List[Source], int, int]:
    """
    V5: Fetch commentaries only on segments that contain focus/topic terms.
    
    Returns:
    - List of commentary sources
    - Number of segments analyzed
    - Number of segments found relevant
    """
    log_subsection("TRICKLE UP FILTERED (V5)")
    
    if not foundation_refs:
        logger.info("  No foundation refs to trickle up from")
        return [], 0, 0
    
    target_lower = [t.lower().replace(" ", "_") for t in target_sources]
    
    logger.info(f"  Foundation refs: {foundation_refs}")
    logger.info(f"  Target sources: {target_lower}")
    logger.info(f"  Focus terms: {focus_terms}")
    logger.info(f"  Topic terms: {topic_terms}")
    
    commentary_sources = []
    seen_refs = set()
    total_segments = 0
    relevant_segments = 0
    
    for ref in foundation_refs:
        logger.info(f"  Analyzing segments for: {ref}")
        
        # First, fetch the base text and find relevant segments
        base_response = await fetch_text(ref, session)
        if not base_response:
            continue
        
        # Analyze which segments contain our terms
        segments = analyze_segments(base_response, focus_terms, topic_terms)
        total_segments += len(segments)
        
        # Get relevant segment refs
        relevant_seg_indices = []
        for seg in segments:
            if seg["is_relevant"]:
                relevant_segments += 1
                relevant_seg_indices.append(seg["segment_index"])
        
        logger.info(f"    Found {len(relevant_seg_indices)}/{len(segments)} relevant segments")
        
        # If no relevant segments found, use the whole ref but with lower priority
        if not relevant_seg_indices:
            logger.info(f"    No focused segments, using whole ref")
            relevant_seg_indices = list(range(min(5, len(segments))))  # First 5 at most
        
        # Get related for each relevant segment
        for seg_idx in relevant_seg_indices[:10]:  # Max 10 segments
            seg_ref = f"{ref}:{seg_idx + 1}"
            
            related = await fetch_related(seg_ref, session)
            if not related:
                # Fall back to base ref if segment ref doesn't work
                related = await fetch_related(ref, session)
                if not related:
                    continue
            
            links = related.get("links", [])
            for link in links:
                link_ref = link.get("ref", "")
                if not link_ref or link_ref in seen_refs:
                    continue
                
                categories = link.get("category", "")
                collective_title = link.get("collectiveTitle", {}).get("en", "")
                
                # V5: Use improved matching with exclusions
                is_target = False
                matched_target = None
                
                for target in target_lower:
                    if target == "gemara":
                        continue
                    
                    if matches_source_target(link_ref, categories, collective_title, target):
                        is_target = True
                        matched_target = target
                        break
                
                if not is_target:
                    continue
                
                seen_refs.add(link_ref)
                
                text_response = await fetch_text(link_ref, session)
                if not text_response:
                    continue
                
                he_text, en_text = extract_text_content(text_response)
                
                # V5: Score this commentary by focus terms
                _, kw_found, score = verify_text_contains_keywords(
                    he_text, focus_terms + topic_terms, min_score=0
                )
                
                source = Source(
                    ref=link_ref,
                    he_ref=text_response.get("heRef", link_ref),
                    level=determine_level(text_response.get("categories", []), link_ref),
                    hebrew_text=he_text,
                    english_text=en_text,
                    author=collective_title,
                    categories=text_response.get("categories", []),
                    is_foundation=False,
                    is_verified=score >= 2.0,
                    verification_keywords_found=kw_found,
                    focus_score=score,
                    segment_index=seg_idx
                )
                
                # Only add if it scores above threshold or is from a primary target
                if score >= 2.0 or matched_target in ["rashi", "tosafos"]:
                    commentary_sources.append(source)
                    logger.debug(f"      Added: {link_ref} ({matched_target}) score={score}")
                else:
                    logger.debug(f"      Skipped low-scoring: {link_ref} score={score}")
    
    # Sort by focus score
    commentary_sources.sort(key=lambda s: s.focus_score, reverse=True)
    
    logger.info(f"  Found {len(commentary_sources)} filtered commentaries")
    logger.info(f"  Segments: {relevant_segments}/{total_segments} relevant")
    
    return commentary_sources, total_segments, relevant_segments


# =============================================================================
#  V5: AUTHOR-SPECIFIC FETCHING
# =============================================================================

async def fetch_author_commentary(
    author: str,
    foundation_refs: List[str],
    focus_terms: List[str],
    topic_terms: List[str],
    session: aiohttp.ClientSession
) -> List[Source]:
    """
    V5: Specifically fetch one author's commentary with proper Sefaria mapping.
    
    For example, if author="Ran" and foundation_ref="Pesachim 6b":
    - Knows Ran writes on Rif
    - Fetches "Ran on Rif Pesachim" instead
    """
    log_subsection(f"FETCHING {author.upper()} COMMENTARY")
    
    author_lower = author.lower().replace(" ", "_")
    author_info = RISHON_SEFARIA_MAP.get(author_lower, {})
    
    sources = []
    
    if not author_info:
        logger.warning(f"  No mapping for author: {author}")
        return sources
    
    writes_on = author_info.get("writes_on", "gemara")
    sefaria_prefix = author_info.get("sefaria_prefix", f"{author} on")
    patterns = author_info.get("patterns", [])
    
    logger.info(f"  Author: {author}")
    logger.info(f"  Writes on: {writes_on}")
    logger.info(f"  Sefaria prefix: {sefaria_prefix}")
    
    for base_ref in foundation_refs:
        # Extract tractate and daf from base ref
        # e.g., "Pesachim 6b" -> tractate="Pesachim", daf="6b"
        parts = base_ref.split()
        if len(parts) < 2:
            continue
        
        tractate = parts[0]
        daf = parts[1] if len(parts) > 1 else ""
        
        # Build the correct ref based on what this author writes on
        if writes_on == "rif":
            # Ran writes on Rif - different daf numbers!
            # Try the ref but note Rif has different pagination
            test_ref = f"{sefaria_prefix} {tractate}"
            logger.info(f"  Looking for: {test_ref}")
            
            # Search for this author's commentary on this tractate
            search_query = f"{author} {tractate} {' '.join(topic_terms[:2])}"
            results = await sefaria_search(search_query, session)
            
            if results and results.get("hits", {}).get("hits"):
                for hit in results["hits"]["hits"][:5]:
                    hit_ref = hit.get("_source", {}).get("ref", "")
                    
                    # Check if it matches our author's patterns
                    is_match = any(p.lower() in hit_ref.lower() for p in patterns)
                    if not is_match:
                        continue
                    
                    logger.info(f"    Found: {hit_ref}")
                    
                    response = await fetch_text(hit_ref, session)
                    if not response:
                        continue
                    
                    he_text, en_text = extract_text_content(response)
                    _, kw_found, score = verify_text_contains_keywords(
                        he_text, focus_terms + topic_terms, min_score=0
                    )
                    
                    sources.append(Source(
                        ref=hit_ref,
                        he_ref=response.get("heRef", hit_ref),
                        level=SourceLevel.RISHONIM,
                        hebrew_text=he_text,
                        english_text=en_text,
                        author=author,
                        categories=response.get("categories", []),
                        is_foundation=False,
                        is_verified=score >= 3.0,
                        verification_keywords_found=kw_found,
                        focus_score=score,
                        is_primary=True
                    ))
        
        elif writes_on == "gemara":
            # Direct gemara commentary - V6 FIX: Filter by segment
            test_ref = f"{sefaria_prefix} {base_ref}"
            logger.info(f"  Trying: {test_ref}")

            response = await fetch_text(test_ref, session)
            if response:
                # V6: Extract individual segments and score each one
                segments = extract_text_segments(response)
                logger.info(f"    Found {len(segments)} segments in {test_ref}")

                matching_segments = []
                for seg in segments:
                    _, kw_found, score = verify_text_contains_keywords(
                        seg["he_text"], focus_terms + topic_terms, min_score=0
                    )
                    if score >= 2.0:  # Only include segments with keyword matches
                        matching_segments.append({
                            **seg,
                            "kw_found": kw_found,
                            "score": score
                        })

                logger.info(f"    {len(matching_segments)}/{len(segments)} segments match focus terms")

                if matching_segments:
                    # Add each matching segment as a separate source
                    for seg in matching_segments[:5]:  # Max 5 segments per ref
                        seg_ref = f"{test_ref}:{seg['index']}"
                        he_ref_base = response.get("heRef", test_ref)

                        sources.append(Source(
                            ref=seg_ref,
                            he_ref=f"{he_ref_base}:{seg['index']}",
                            level=SourceLevel.RISHONIM,
                            hebrew_text=seg["he_text"],
                            english_text=seg["en_text"],
                            author=author,
                            categories=response.get("categories", []),
                            is_foundation=False,
                            is_verified=True,
                            verification_keywords_found=seg["kw_found"],
                            focus_score=seg["score"],
                            is_primary=True,
                            segment_index=seg["index"]
                        ))
                        logger.info(f"      Added segment {seg['index']} (score={seg['score']:.1f}): {seg['kw_found'][:3]}...")
                else:
                    # No matching segments - log but don't add unfiltered content
                    logger.info(f"    No segments matched focus terms for {author} on {base_ref}")
            else:
                logger.warning(f"    Not found: {test_ref}")
    
    # Sort by score
    sources.sort(key=lambda s: s.focus_score, reverse=True)
    
    logger.info(f"  Found {len(sources)} {author} sources")
    return sources


# =============================================================================
#  MAIN QUERY HANDLERS
# =============================================================================

async def handle_nuance_query(
    analysis: 'QueryAnalysis',
    session: aiohttp.ClientSession
) -> SearchResult:
    """Handle nuance queries (including shittah, comparison, machlokes)."""
    log_section("HANDLING NUANCE/SHITTAH QUERY (V5)")
    
    result = SearchResult(
        original_query=analysis.original_query,
        is_nuance_result=True
    )
    
    focus_terms = getattr(analysis, 'focus_terms', [])
    topic_terms = getattr(analysis, 'topic_terms', [])
    target_authors = getattr(analysis, 'target_authors', [])
    primary_author = getattr(analysis, 'primary_author', None)
    
    logger.info(f"  Focus terms: {focus_terms}")
    logger.info(f"  Topic terms: {topic_terms}")
    logger.info(f"  Target authors: {target_authors}")
    logger.info(f"  Primary author: {primary_author}")
    
    # Phase 1: Find landmark
    landmark_result = await find_landmark(analysis, session)
    result.landmark_discovery = landmark_result
    
    if landmark_result.landmark_ref:
        # Fetch landmark text
        response = await fetch_text(landmark_result.landmark_ref, session)
        if response:
            he_text, en_text = extract_text_content(response)
            landmark_source = Source(
                ref=landmark_result.landmark_ref,
                he_ref=response.get("heRef", landmark_result.landmark_ref),
                level=determine_level(response.get("categories", []), landmark_result.landmark_ref),
                hebrew_text=he_text,
                english_text=en_text,
                categories=response.get("categories", []),
                is_landmark=True,
                is_foundation=True,
                is_verified=True,
                tier="landmark",
                focus_score=100.0,
                verification_keywords_found=landmark_result.focus_keywords_found + landmark_result.topic_keywords_found
            )
            result.landmark_source = landmark_source
            result.foundation_stones.append(landmark_source)
    
    # Get primary refs for expansion
    primary_refs = getattr(analysis, 'primary_refs', [])
    expansion_refs = [landmark_result.landmark_ref] if landmark_result.landmark_ref else []
    expansion_refs.extend([r for r in primary_refs if r not in expansion_refs])
    expansion_refs = expansion_refs[:5]  # Max 5 expansion refs
    
    logger.info(f"  Expansion refs: {expansion_refs}")
    
    # V5: If this is a shittah query, prioritize fetching that author's commentary
    if primary_author or target_authors:
        authors_to_fetch = [primary_author] if primary_author else []
        authors_to_fetch.extend([a for a in target_authors if a not in authors_to_fetch])
        
        for author in authors_to_fetch[:3]:  # Max 3 authors
            author_sources = await fetch_author_commentary(
                author, expansion_refs, focus_terms, topic_terms, session
            )
            result.author_sources[author] = author_sources
            result.primary_sources.extend(author_sources)
    
    # Phase 2: Topic-filtered trickle up
    if expansion_refs and analysis.trickle_direction in [TrickleDirection.UP, TrickleDirection.BOTH]:
        commentaries, total_seg, relevant_seg = await trickle_up_filtered(
            expansion_refs,
            analysis.target_sources,
            focus_terms,
            topic_terms,
            session
        )
        result.commentary_sources = commentaries
        result.segments_analyzed = total_seg
        result.segments_relevant = relevant_seg
    
    # Phase 3: Contrast refs (no expansion)
    contrast_refs = getattr(analysis, 'contrast_refs', [])
    if contrast_refs:
        log_subsection("FETCHING CONTRAST REFS")
        for ref in contrast_refs[:2]:
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
                    is_foundation=False,
                    is_primary=False,
                    tier="context"
                )
                result.context_sources.append(source)
    
    return result


async def handle_general_query(
    analysis: 'QueryAnalysis',
    session: aiohttp.ClientSession
) -> SearchResult:
    """Handle general (non-nuance) queries."""
    log_section("HANDLING GENERAL QUERY (V5)")
    
    result = SearchResult(original_query=analysis.original_query)
    
    ref_hints = getattr(analysis, 'ref_hints', [])
    
    if not ref_hints and hasattr(analysis, 'suggested_refs'):
        for ref in analysis.suggested_refs:
            ref_hints.append(RefHint(
                ref=ref,
                confidence=RefConfidence.POSSIBLE,
                verification_keywords=[],
                buffer_size=DEFAULT_BUFFER_SIZE
            ))
    
    if not ref_hints:
        result.needs_clarification = True
        result.clarification_question = "I couldn't identify specific sources. Could you provide more details?"
        result.confidence = ConfidenceLevel.LOW
        return result
    
    # Verify refs
    search_variants = getattr(analysis, 'search_variants', None)
    verified_refs = []
    focus_terms = getattr(analysis, 'focus_terms', [])
    topic_terms = getattr(analysis, 'topic_terms', [])
    
    log_subsection("VERIFYING REFS")
    
    for hint in ref_hints:
        logger.info(f"  Checking: {hint.ref}")
        
        if hint.confidence.value == "certain":
            verified_refs.append(hint.ref)
            response = await fetch_text(hint.ref, session)
            if response:
                he_text, en_text = extract_text_content(response)
                source = Source(
                    ref=hint.ref,
                    he_ref=response.get("heRef", hint.ref),
                    level=determine_level(response.get("categories", []), hint.ref),
                    hebrew_text=he_text,
                    english_text=en_text,
                    categories=response.get("categories", []),
                    is_foundation=True,
                    is_verified=True
                )
                result.foundation_stones.append(source)
            continue
        
        keywords = list(hint.verification_keywords) if hint.verification_keywords else []
        if search_variants:
            keywords.extend(search_variants.aramaic_forms)
        
        response = await fetch_text(hint.ref, session)
        if response:
            he_text, en_text = extract_text_content(response)
            
            if keywords:
                verified, found, score = verify_text_contains_keywords(he_text, keywords, min_score=3.0)
            else:
                verified = True
                found = []
            
            if verified or hint.confidence in [RefConfidence.CERTAIN, RefConfidence.LIKELY]:
                verified_refs.append(hint.ref)
                source = Source(
                    ref=hint.ref,
                    he_ref=response.get("heRef", hint.ref),
                    level=determine_level(response.get("categories", []), hint.ref),
                    hebrew_text=he_text,
                    english_text=en_text,
                    categories=response.get("categories", []),
                    is_foundation=True,
                    is_verified=verified,
                    verification_keywords_found=found
                )
                result.foundation_stones.append(source)
    
    result.refs_checked = len(ref_hints)
    result.refs_verified = len(verified_refs)
    
    # V5: Use topic-filtered trickle up even for general queries
    if analysis.trickle_direction in [TrickleDirection.UP, TrickleDirection.BOTH]:
        if focus_terms or topic_terms:
            commentaries, total_seg, relevant_seg = await trickle_up_filtered(
                verified_refs,
                analysis.target_sources,
                focus_terms,
                topic_terms,
                session
            )
            result.commentary_sources = commentaries
            result.segments_analyzed = total_seg
            result.segments_relevant = relevant_seg
        else:
            # Fallback to unfiltered for truly general queries
            result.commentary_sources = await trickle_up_unfiltered(
                verified_refs,
                analysis.target_sources,
                session
            )
    
    return result


async def trickle_up_unfiltered(
    foundation_refs: List[str],
    target_sources: List[str],
    session: aiohttp.ClientSession
) -> List[Source]:
    """Original trickle up without filtering (for general queries without focus terms)."""
    log_subsection("TRICKLE UP (UNFILTERED)")
    
    if not foundation_refs:
        return []
    
    target_lower = [t.lower().replace(" ", "_") for t in target_sources]
    commentary_sources = []
    seen_refs = set()
    
    for ref in foundation_refs:
        logger.info(f"  Getting commentaries for: {ref}")
        
        related = await fetch_related(ref, session)
        if not related:
            continue
        
        links = related.get("links", [])
        for link in links:
            link_ref = link.get("ref", "")
            if not link_ref or link_ref in seen_refs:
                continue
            
            categories = link.get("category", "")
            collective_title = link.get("collectiveTitle", {}).get("en", "")
            
            is_target = False
            matched_target = None
            
            for target in target_lower:
                if target == "gemara":
                    continue
                
                if matches_source_target(link_ref, categories, collective_title, target):
                    is_target = True
                    matched_target = target
                    break
            
            if not is_target:
                continue
            
            seen_refs.add(link_ref)
            
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
#  MAIN SEARCH FUNCTION
# =============================================================================

async def search(analysis: 'QueryAnalysis') -> SearchResult:
    """
    Main search function - V5 with topic filtering and author-specific fetching.
    """
    log_section("STEP 3: SEARCH [V5 - TOPIC FILTERED]")
    
    logger.info(f"  Query: {analysis.original_query}")
    logger.info(f"  Query type: {analysis.query_type.value}")
    logger.info(f"  Is nuance: {getattr(analysis, 'is_nuance_query', False)}")
    logger.info(f"  Foundation type: {analysis.foundation_type.value}")
    logger.info(f"  Trickle direction: {analysis.trickle_direction.value}")
    logger.info(f"  Target authors: {getattr(analysis, 'target_authors', [])}")
    
    # Handle clarification case
    if analysis.needs_clarification:
        return SearchResult(
            original_query=analysis.original_query,
            needs_clarification=True,
            clarification_question=analysis.clarification_question,
            confidence=ConfidenceLevel.LOW,
            search_description="Needs clarification before searching"
        )
    
    async with aiohttp.ClientSession() as session:
        is_nuance = getattr(analysis, 'is_nuance_query', False)
        
        if is_nuance:
            result = await handle_nuance_query(analysis, session)
        else:
            result = await handle_general_query(analysis, session)
    
    # Organize results
    all_sources = (
        result.foundation_stones +
        result.primary_sources +
        result.commentary_sources +
        result.earlier_sources +
        result.context_sources +
        result.background_sources
    )
    
    # Add author sources
    for author, sources in result.author_sources.items():
        for s in sources:
            if s not in all_sources:
                all_sources.append(s)
    
    # Deduplicate
    seen_refs = set()
    unique_sources = []
    for s in all_sources:
        if s.ref not in seen_refs:
            seen_refs.add(s.ref)
            unique_sources.append(s)
    
    result.all_sources = unique_sources
    result.total_sources = len(unique_sources)
    
    # Group by level
    by_level: Dict[str, List[Source]] = defaultdict(list)
    for s in unique_sources:
        by_level[s.level.value].append(s)
    result.sources_by_level = dict(by_level)
    
    # Set confidence
    if result.is_nuance_result and result.landmark_source:
        result.confidence = ConfidenceLevel.HIGH
    elif len(result.foundation_stones) >= 2:
        result.confidence = ConfidenceLevel.HIGH
    elif len(result.foundation_stones) >= 1:
        result.confidence = ConfidenceLevel.MEDIUM
    else:
        result.confidence = ConfidenceLevel.LOW
    
    # Summary
    if result.is_nuance_result:
        landmark_info = f"Landmark: {result.landmark_source.ref}" if result.landmark_source else "No landmark found"
        author_info = f"Authors: {list(result.author_sources.keys())}" if result.author_sources else ""
        result.search_description = (
            f"Nuance query. {landmark_info}. {author_info}"
            f"Found {len(result.primary_sources)} primary, "
            f"{len(result.commentary_sources)} commentaries. "
            f"Segments: {result.segments_relevant}/{result.segments_analyzed} relevant. "
            f"Total: {result.total_sources} sources."
        )
    else:
        result.search_description = (
            f"General query. "
            f"Verified {result.refs_verified}/{result.refs_checked} refs. "
            f"Found {len(result.foundation_stones)} foundations, "
            f"{len(result.commentary_sources)} commentaries. "
            f"Total: {result.total_sources} sources."
        )
    
    # Log summary
    log_section("SEARCH COMPLETE (V5)")
    logger.info(f"  Is nuance: {result.is_nuance_result}")
    if result.is_nuance_result:
        logger.info(f"  Landmark: {result.landmark_source.ref if result.landmark_source else 'None'}")
        logger.info(f"  Author sources: {list(result.author_sources.keys())}")
        logger.info(f"  Segments: {result.segments_relevant}/{result.segments_analyzed} relevant")
    logger.info(f"  Foundation stones: {[s.ref for s in result.foundation_stones]}")
    logger.info(f"  Primary sources: {len(result.primary_sources)}")
    logger.info(f"  Commentaries: {len(result.commentary_sources)}")
    logger.info(f"  Total: {result.total_sources}")
    logger.info(f"  Confidence: {result.confidence.value}")
    
    return result


# =============================================================================
#  ENTRY POINT
# =============================================================================

run_step_three = search


__all__ = [
    'search',
    'run_step_three',
    'SearchResult',
    'Source',
    'SourceLevel',
    'LandmarkResult',
    'VerificationResult',
    'RISHON_SEFARIA_MAP',
]