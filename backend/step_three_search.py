"""
Step 3: SEARCH - V4 with Nuance Query Support
=============================================

V4 PHILOSOPHY:
    For NUANCE queries: Find the LANDMARK, expand only around it
    For GENERAL queries: Expand from all verified refs (existing behavior)

V4 FLOW FOR NUANCE QUERIES:
    1. PHASE 1A: Verify Claude's suggested landmark
       - Check if it exists in Sefaria
       - Check if it contains focus_terms + topic_terms
       - If verified: USE AS ANCHOR
       
    2. PHASE 1B: Discovery via achronim (if landmark not verified)
       - Search Shulchan Aruch/Tur for focus_terms + topic_terms
       - Extract citations from matching simanim
       - Score cited sources by focus_term presence
       - Highest scorer = discovered landmark
       
    3. PHASE 1C: Cheap Claude validation (if needed)
       - Send ref list + nuance description to Claude
       - Ask Claude to pick 1-2 most relevant
       - ~$0.001 cost (200 tokens in, 10 out)
       
    4. PHASE 2: Expand from landmark
       - Trickle UP: Get commentaries on the landmark
       - Trickle DOWN: Get the gemara the landmark references
       
    5. PHASE 3: Include contrast refs (no expansion)
       - Fetch text only for context
       
    6. PHASE 4: Score & Rank by focus_terms
       - Mark keystone (highest focus_term score)
       - Organize into tiers: Primary → Context → Background

COST SAVINGS:
    Before V4: All refs expanded equally → 300+ sources
    After V4: Only landmark expanded → 30-50 focused sources
    Cheap Claude call: Only when discovery needed, ~$0.001
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

# Import Step 2 V4 structures
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
#  CATEGORY MAPPING
# =============================================================================

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
    is_primary: bool = True  # Primary vs contrast
    focus_score: float = 0.0  # Score based on focus_terms
    tier: str = "background"  # "landmark", "primary", "context", "background"


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
    discovery_method: str = "none"  # "claude_verified", "achronim_discovery", "claude_tiebreaker", "none"
    confidence: str = "low"
    reasoning: str = ""
    focus_keywords_found: List[str] = field(default_factory=list)
    topic_keywords_found: List[str] = field(default_factory=list)


@dataclass
class SearchResult:
    """Complete search result - V4 with tiered sources."""
    original_query: str
    
    # V4: Tiered sources for nuance queries
    landmark_source: Optional[Source] = None
    primary_sources: List[Source] = field(default_factory=list)
    context_sources: List[Source] = field(default_factory=list)
    background_sources: List[Source] = field(default_factory=list)
    
    # Legacy: flat lists for backward compatibility
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
    
    # V4: Nuance search stats
    is_nuance_result: bool = False
    landmark_discovery: Optional[LandmarkResult] = None
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
    
    return list(set(variants))


# Generic words that appear everywhere
GENERIC_KEYWORDS = {
    'חזקה', 'ספק', 'רוב', 'מום', 'גוף', 'ממון', 'טהור', 'טמא',
    'אמר', 'רבא', 'אביי', 'רב', 'שמואל', 'מתני', 'גמרא',
    'ברי', 'שמא',  # Added for bari v'shema
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
#  PHASE 1A: VERIFY CLAUDE'S SUGGESTED LANDMARK
# =============================================================================

async def verify_landmark(
    suggested_landmark: str,
    landmark_confidence: LandmarkConfidence,
    focus_terms: List[str],
    topic_terms: List[str],
    session: aiohttp.ClientSession
) -> LandmarkResult:
    """
    Verify Claude's suggested landmark.
    
    For the landmark to be verified, it must:
    1. Exist in Sefaria
    2. Contain at least one focus_term AND at least one topic_term
    """
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
            reasoning=f"Landmark '{suggested_landmark}' not found in Sefaria - possible hallucination"
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


# =============================================================================
#  PHASE 1B: DISCOVER LANDMARK VIA ACHRONIM
# =============================================================================

async def discover_via_achronim(
    focus_terms: List[str],
    topic_terms: List[str],
    session: aiohttp.ClientSession,
    target_chelek: Optional[str] = None
) -> LandmarkResult:
    """
    Discover landmark by searching achronim (SA, Tur, MB) for focus + topic terms.
    
    Process:
    1. Search SA/Tur for both focus_terms and topic_terms
    2. Extract citations from matching simanim
    3. Fetch cited sources
    4. Score each by focus_term presence
    5. Return highest-scoring as landmark
    """
    log_subsection("PHASE 1B: DISCOVER VIA ACHRONIM")
    
    if not focus_terms and not topic_terms:
        logger.info("  No terms to search for")
        return LandmarkResult(discovery_method="none", reasoning="No search terms provided")
    
    # Build search query: combine focus + topic terms
    search_terms = []
    if focus_terms:
        search_terms.extend(focus_terms[:2])  # Top 2 focus terms
    if topic_terms:
        search_terms.extend(topic_terms[:2])  # Top 2 topic terms
    
    search_query = " ".join(search_terms)
    logger.info(f"  Search query: {search_query}")
    
    # Search Sefaria
    # Try SA first, then Tur
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
            
            for hit in hits[:10]:  # Top 10 hits
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
    
    # Now extract citations from these refs and find rishonim
    rishonim_candidates = []
    
    for ref in candidate_refs[:5]:  # Check top 5
        logger.info(f"  Checking citations in: {ref}")
        
        # Get related/links for this ref
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
    
    # Score each candidate by focus_terms
    scored_candidates = []
    
    for candidate in rishonim_candidates[:10]:  # Check top 10
        ref = candidate["ref"]
        logger.info(f"  Scoring: {ref}")
        
        response = await fetch_text(ref, session)
        if not response:
            continue
        
        he_text, _ = extract_text_content(response)
        if not he_text:
            continue
        
        # Score by focus terms (high weight) and topic terms (lower weight)
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
    
    # Sort by total score
    scored_candidates.sort(key=lambda x: x["total_score"], reverse=True)
    best = scored_candidates[0]
    
    # Only accept if it has BOTH focus and topic terms
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


# =============================================================================
#  PHASE 1C: CHEAP CLAUDE VALIDATION (TIEBREAKER)
# =============================================================================

async def cheap_claude_validation(
    candidate_refs: List[str],
    nuance_description: str,
    focus_terms: List[str]
) -> Optional[str]:
    """
    Use a cheap Claude call to pick the best landmark from candidates.
    
    Cost: ~$0.001 (200 tokens in, 10 tokens out)
    
    Only used when:
    - We have multiple candidates
    - Programmatic scoring is unclear
    """
    log_subsection("PHASE 1C: CHEAP CLAUDE VALIDATION")
    
    if not candidate_refs:
        logger.info("  No candidates to validate")
        return None
    
    if len(candidate_refs) == 1:
        logger.info(f"  Only one candidate, using: {candidate_refs[0]}")
        return candidate_refs[0]
    
    logger.info(f"  Asking Claude to pick from {len(candidate_refs)} candidates")
    logger.info(f"  Nuance: {nuance_description}")
    
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=settings.anthropic_api_key)
        
        # Build minimal prompt
        refs_list = "\n".join([f"{i+1}. {ref}" for i, ref in enumerate(candidate_refs[:10])])
        
        prompt = f"""Which 1-2 of these sources is most likely THE landmark source for:
"{nuance_description}"

Focus terms: {focus_terms[:5]}

Refs:
{refs_list}

Return ONLY the number(s), e.g. "2" or "2, 5". Nothing else."""

        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=20,
            temperature=0,
            messages=[{"role": "user", "content": prompt}]
        )
        
        answer = response.content[0].text.strip()
        logger.info(f"  Claude's answer: {answer}")
        
        # Parse the number(s)
        import re
        numbers = re.findall(r'\d+', answer)
        
        if numbers:
            idx = int(numbers[0]) - 1  # Convert to 0-indexed
            if 0 <= idx < len(candidate_refs):
                selected = candidate_refs[idx]
                logger.info(f"  ✓ Selected: {selected}")
                return selected
        
        logger.warning(f"  Could not parse Claude's response: {answer}")
        return candidate_refs[0]  # Fallback to first
        
    except Exception as e:
        logger.error(f"  Claude validation error: {e}")
        return candidate_refs[0]  # Fallback to first


# =============================================================================
#  COMBINED LANDMARK FINDING
# =============================================================================

async def find_landmark(
    analysis: 'QueryAnalysis',
    session: aiohttp.ClientSession
) -> LandmarkResult:
    """
    Find the landmark source for a nuance query.
    
    Order:
    1. Try Claude's suggestion (verify it)
    2. If fails, try discovery via achronim
    3. If multiple candidates, use cheap Claude validation
    """
    log_section("FINDING LANDMARK FOR NUANCE QUERY")
    
    # Get nuance info from analysis
    suggested_landmark = getattr(analysis, 'suggested_landmark', None)
    landmark_confidence = getattr(analysis, 'landmark_confidence', LandmarkConfidence.NONE)
    focus_terms = getattr(analysis, 'focus_terms', [])
    topic_terms = getattr(analysis, 'topic_terms', [])
    target_chelek = getattr(analysis, 'target_chelek', None)
    nuance_description = getattr(analysis, 'nuance_description', '')
    
    logger.info(f"  Nuance: {nuance_description}")
    logger.info(f"  Focus terms: {focus_terms}")
    logger.info(f"  Topic terms: {topic_terms}")
    
    # PHASE 1A: Try Claude's suggestion
    if suggested_landmark and landmark_confidence.value != "none":
        result = await verify_landmark(
            suggested_landmark,
            landmark_confidence,
            focus_terms,
            topic_terms,
            session
        )
        
        if result.landmark_ref:
            return result
        
        logger.info("  Claude's suggestion didn't verify, trying discovery...")
    
    # PHASE 1B: Try discovery via achronim
    result = await discover_via_achronim(
        focus_terms,
        topic_terms,
        session,
        target_chelek
    )
    
    if result.landmark_ref:
        return result
    
    # PHASE 1C: If we have primary_refs but no landmark, use cheap Claude
    primary_refs = getattr(analysis, 'primary_refs', [])
    
    if primary_refs and nuance_description:
        # Try to find landmark among primary refs
        selected = await cheap_claude_validation(
            primary_refs[:5],
            nuance_description,
            focus_terms
        )
        
        if selected:
            return LandmarkResult(
                landmark_ref=selected,
                discovery_method="claude_tiebreaker",
                confidence="medium",
                reasoning="Selected by Claude from primary refs"
            )
    
    # No landmark found
    logger.warning("  ✗ Could not find landmark")
    return LandmarkResult(
        discovery_method="none",
        confidence="low",
        reasoning="Could not verify or discover a landmark source"
    )


# =============================================================================
#  PHASE 2: EXPAND FROM REFS
# =============================================================================

async def trickle_up(
    foundation_refs: List[str],
    target_sources: List[str],
    session: aiohttp.ClientSession
) -> List[Source]:
    """Fetch commentaries (trickle up) for foundation stones."""
    log_subsection("TRICKLE UP (COMMENTARIES)")
    
    if not foundation_refs:
        logger.info("  No foundation refs to trickle up from")
        return []
    
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


async def trickle_down(
    foundation_refs: List[str],
    foundation_type: FoundationType,
    session: aiohttp.ClientSession
) -> List[Source]:
    """Find earlier sources (trickle down) - Mishna, Pasuk, etc."""
    log_subsection("TRICKLE DOWN (EARLIER SOURCES)")
    
    if not foundation_refs:
        logger.info("  No foundation refs to trickle down from")
        return []
    
    if foundation_type in [FoundationType.HALACHA_SA, FoundationType.HALACHA_RAMBAM]:
        logger.info("  Halacha query - skipping trickle down")
        return []
    
    earlier_sources = []
    seen_refs = set()
    
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
            
            categories = link.get("category", "")
            
            is_earlier = any(cat in categories for cat in ["Tanakh", "Torah", "Mishnah", "Tosefta"])
            
            if not is_earlier:
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
                categories=text_response.get("categories", []),
                is_foundation=False,
                is_verified=False
            )
            earlier_sources.append(source)
            logger.debug(f"    Added: {link_ref}")
    
    logger.info(f"  Found {len(earlier_sources)} earlier sources")
    return earlier_sources


# =============================================================================
#  PHASE 4: SCORE AND RANK BY FOCUS TERMS
# =============================================================================

def score_sources_by_focus(
    sources: List[Source],
    focus_terms: List[str],
    topic_terms: List[str]
) -> List[Source]:
    """Score all sources by focus term presence and assign tiers."""
    if not sources:
        return sources
    
    for source in sources:
        # Score by focus terms
        _, focus_found, focus_score = verify_text_contains_keywords(
            source.hebrew_text, focus_terms, min_score=0
        )
        # Score by topic terms (lower weight)
        _, topic_found, topic_score = verify_text_contains_keywords(
            source.hebrew_text, topic_terms, min_score=0
        )
        
        # Focus terms get 2x weight
        source.focus_score = focus_score * 2 + topic_score
        source.verification_keywords_found = focus_found + topic_found
        
        # Assign tier based on score
        if source.focus_score >= 10:
            source.tier = "primary"
        elif source.focus_score >= 5:
            source.tier = "context"
        else:
            source.tier = "background"
    
    # Sort by score
    sources.sort(key=lambda s: s.focus_score, reverse=True)
    
    return sources


# =============================================================================
#  GENERAL QUERY HANDLER (NON-NUANCE)
# =============================================================================

async def handle_general_query(
    analysis: 'QueryAnalysis',
    session: aiohttp.ClientSession
) -> SearchResult:
    """Handle general (non-nuance) queries with existing logic."""
    log_section("HANDLING GENERAL QUERY")
    
    result = SearchResult(original_query=analysis.original_query)
    
    # Get ref hints
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
    
    # Verify all refs
    search_variants = getattr(analysis, 'search_variants', None)
    verified_refs = []
    
    log_subsection("VERIFYING REFS")
    
    for hint in ref_hints:
        logger.info(f"  Checking: {hint.ref}")
        
        # For certain confidence, trust without verification
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
        
        # Verify using keywords
        keywords = list(hint.verification_keywords) if hint.verification_keywords else []
        if search_variants:
            keywords.extend(search_variants.aramaic_forms)
        
        response = await fetch_text(hint.ref, session)
        if response:
            he_text, en_text = extract_text_content(response)
            
            if keywords:
                verified, found, score = verify_text_contains_keywords(he_text, keywords, min_score=3.0)
            else:
                verified = True  # No keywords = trust
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
    
    # Trickle up/down
    if analysis.trickle_direction in [TrickleDirection.UP, TrickleDirection.BOTH]:
        result.commentary_sources = await trickle_up(
            verified_refs,
            analysis.target_sources,
            session
        )
    
    if analysis.trickle_direction in [TrickleDirection.DOWN, TrickleDirection.BOTH]:
        result.earlier_sources = await trickle_down(
            verified_refs,
            analysis.foundation_type,
            session
        )
    
    return result


# =============================================================================
#  NUANCE QUERY HANDLER
# =============================================================================

async def handle_nuance_query(
    analysis: 'QueryAnalysis',
    session: aiohttp.ClientSession
) -> SearchResult:
    """
    Handle nuance queries with landmark-focused expansion.
    
    Flow:
    1. Find landmark (verify Claude's suggestion or discover)
    2. Expand only from landmark (trickle up/down)
    3. Include contrast refs as context (no expansion)
    4. Score all sources by focus terms
    5. Organize into tiers
    """
    log_section("HANDLING NUANCE QUERY")
    
    result = SearchResult(
        original_query=analysis.original_query,
        is_nuance_result=True
    )
    
    focus_terms = getattr(analysis, 'focus_terms', [])
    topic_terms = getattr(analysis, 'topic_terms', [])
    
    logger.info(f"  Nuance: {analysis.nuance_description}")
    logger.info(f"  Focus terms: {focus_terms}")
    logger.info(f"  Topic terms: {topic_terms}")
    
    # =========================================================================
    # PHASE 1: Find landmark
    # =========================================================================
    landmark_result = await find_landmark(analysis, session)
    result.landmark_discovery = landmark_result
    
    landmark_refs = []
    
    if landmark_result.landmark_ref:
        landmark_refs.append(landmark_result.landmark_ref)
        
        # Fetch the landmark source
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
                is_foundation=True,
                is_verified=True,
                is_landmark=True,
                tier="landmark",
                verification_keywords_found=landmark_result.focus_keywords_found + landmark_result.topic_keywords_found
            )
            result.landmark_source = landmark_source
            result.foundation_stones.append(landmark_source)
    
    # =========================================================================
    # PHASE 2: Expand from landmark (and primary refs)
    # =========================================================================
    
    # Also include primary refs (but not as landmarks)
    primary_refs = getattr(analysis, 'primary_refs', [])
    expansion_refs = landmark_refs + [r for r in primary_refs if r not in landmark_refs]
    
    # Limit expansion refs for nuance queries
    expansion_refs = expansion_refs[:3]  # Max 3 refs to expand from
    
    logger.info(f"  Expanding from: {expansion_refs}")
    
    # Fetch primary ref texts (if not already fetched)
    for ref in primary_refs:
        if ref == landmark_result.landmark_ref:
            continue
        
        # Find the ref hint for this ref
        ref_hints = getattr(analysis, 'ref_hints', [])
        hint = next((h for h in ref_hints if h.ref == ref), None)
        
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
                is_verified=True,
                is_primary=True,
                tier="primary"
            )
            result.foundation_stones.append(source)
            result.primary_sources.append(source)
    
    # Trickle UP from expansion refs
    if expansion_refs and analysis.trickle_direction in [TrickleDirection.UP, TrickleDirection.BOTH]:
        commentaries = await trickle_up(
            expansion_refs,
            analysis.target_sources,
            session
        )
        result.commentary_sources = commentaries
    
    # Trickle DOWN from landmark
    if landmark_refs and analysis.trickle_direction in [TrickleDirection.DOWN, TrickleDirection.BOTH]:
        earlier = await trickle_down(
            landmark_refs,
            analysis.foundation_type,
            session
        )
        result.earlier_sources = earlier
    
    # =========================================================================
    # PHASE 3: Include contrast refs (no expansion)
    # =========================================================================
    contrast_refs = getattr(analysis, 'contrast_refs', [])
    
    if contrast_refs:
        log_subsection("FETCHING CONTRAST REFS (NO EXPANSION)")
        
        for ref in contrast_refs[:2]:  # Max 2 contrast refs
            logger.info(f"  Fetching contrast ref: {ref}")
            
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
    
    # =========================================================================
    # PHASE 4: Score and rank by focus terms
    # =========================================================================
    log_subsection("SCORING SOURCES BY FOCUS TERMS")
    
    all_sources = (
        result.foundation_stones +
        result.commentary_sources +
        result.earlier_sources +
        result.context_sources
    )
    
    # Score all sources
    all_sources = score_sources_by_focus(all_sources, focus_terms, topic_terms)
    
    # Log top scorers
    logger.info(f"  Top scoring sources:")
    for s in all_sources[:5]:
        logger.info(f"    {s.ref}: {s.focus_score:.1f} ({s.tier})")
    
    return result


# =============================================================================
#  MAIN SEARCH FUNCTION
# =============================================================================

async def search(analysis: 'QueryAnalysis') -> SearchResult:
    """
    Main search function - V4 with nuance query support.
    
    Routes to:
    - handle_nuance_query() for nuance queries (landmark-focused)
    - handle_general_query() for general queries (existing behavior)
    """
    log_section("STEP 3: SEARCH [V4 - NUANCE SUPPORT]")
    
    logger.info(f"  Query: {analysis.original_query}")
    logger.info(f"  Query type: {analysis.query_type.value}")
    logger.info(f"  Is nuance: {getattr(analysis, 'is_nuance_query', False)}")
    logger.info(f"  Foundation type: {analysis.foundation_type.value}")
    logger.info(f"  Trickle direction: {analysis.trickle_direction.value}")
    
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
        # Route to appropriate handler
        is_nuance = getattr(analysis, 'is_nuance_query', False)
        
        if is_nuance:
            result = await handle_nuance_query(analysis, session)
        else:
            result = await handle_general_query(analysis, session)
    
    # =========================================================================
    # Organize results
    # =========================================================================
    
    all_sources = (
        result.foundation_stones +
        result.commentary_sources +
        result.earlier_sources +
        result.context_sources +
        result.background_sources
    )
    
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
        result.search_description = (
            f"Nuance query. {landmark_info}. "
            f"Discovery: {result.landmark_discovery.discovery_method if result.landmark_discovery else 'none'}. "
            f"Found {len(result.foundation_stones)} foundations, "
            f"{len(result.commentary_sources)} commentaries, "
            f"{len(result.context_sources)} context sources. "
            f"Total: {result.total_sources} sources."
        )
    else:
        result.search_description = (
            f"General query. "
            f"Verified {result.refs_verified}/{result.refs_checked} refs. "
            f"Found {len(result.foundation_stones)} foundations, "
            f"{len(result.commentary_sources)} commentaries, "
            f"{len(result.earlier_sources)} earlier sources. "
            f"Total: {result.total_sources} sources."
        )
    
    # =========================================================================
    # Log summary
    # =========================================================================
    log_section("SEARCH COMPLETE (V4)")
    logger.info(f"  Is nuance: {result.is_nuance_result}")
    if result.is_nuance_result:
        logger.info(f"  Landmark: {result.landmark_source.ref if result.landmark_source else 'None'}")
        logger.info(f"  Discovery method: {result.landmark_discovery.discovery_method if result.landmark_discovery else 'none'}")
    logger.info(f"  Foundation stones: {[s.ref for s in result.foundation_stones]}")
    logger.info(f"  Commentaries: {len(result.commentary_sources)}")
    logger.info(f"  Context sources: {len(result.context_sources)}")
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
]