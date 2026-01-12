"""
Step 2: UNDERSTAND - V8 with Gemini Flash
==========================================

V8 CHANGES: Switched from Anthropic Claude to Google Gemini Flash for cost efficiency.

V6 CHANGES FROM V5:
1. KNOWN SUGYOS DATABASE CHECK - Check database FIRST before LLM
2. If known sugya found, use those exact locations as primary refs with HIGH confidence
3. LLM still provides analysis but known refs take priority
4. Solves "Primary Sources Issue" where system returned Rishonim instead of Gemara

PIPELINE LOGIC:
1. Receive query + hebrew_terms from Step 1
2. Check known_sugyos database for matches
3. If MATCH FOUND:
   - Use known gemara locations as primary_refs
   - Set confidence HIGH
   - Use key_terms for validation
   - LLM enriches with search_variants, target_authors, etc.
4. If NO MATCH:
   - Fall back to full LLM analysis (same as V5)
5. Return QueryAnalysis with refs to Step 3

KEY CLASSIFICATION RULES:
- TOPIC queries: "bari vishema" (general, wants multiple sources)
- NUANCE queries include:
  - Sub-topic: "bari vishema BEISSURIN" (specific aspect)
  - SHITTAH: "what is the RAN'S shittah" (specific author's view)
  - COMPARISON: "how does Ran differ from Rashi" (comparing views)
  - MACHLOKES: "machlokes Rashi and Tosafos" (dispute)

All of these need FOCUS TERMS and targeted expansion.
"""

import logging
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

import google.generativeai as genai

# Token tracking
try:
    from utils.token_tracker import TokenTracker, get_global_tracker
    TOKEN_TRACKING_AVAILABLE = True
except ImportError:
    TOKEN_TRACKING_AVAILABLE = False
    TokenTracker = None
    def get_global_tracker(*args, **kwargs):
        return None

# Initialize logging
try:
    from logging_config import setup_logging
    setup_logging()
except ImportError:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

# Robust imports
try:
    from models import DecipherResult, ConfidenceLevel
except ImportError:
    class ConfidenceLevel(str, Enum):
        HIGH = "high"
        MEDIUM = "medium"
        LOW = "low"
    
    @dataclass
    class DecipherResult:
        hebrew_term: str = ""
        hebrew_terms: List[str] = field(default_factory=list)
        original_query: str = ""

try:
    from config import get_settings
    settings = get_settings()
except ImportError:
    import os
    class Settings:
        gemini_api_key = os.environ.get("GEMINI_API_KEY", "")
        gemini_model = "gemini-2.0-flash"
        gemini_max_tokens = 4000
        gemini_temperature = 0.7
    settings = Settings()

# V6: Import known_sugyos lookup
try:
    from known_sugyos import lookup_known_sugya, KnownSugyaMatch
    KNOWN_SUGYOS_AVAILABLE = True
except ImportError:
    KNOWN_SUGYOS_AVAILABLE = False
    KnownSugyaMatch = None
    def lookup_known_sugya(*args, **kwargs):
        return None

# V7: Import clarification module
try:
    from clarification import (
        check_and_generate_clarification,
        ClarificationOption as ClarifyOption,
        store_clarification_session,
    )
    CLARIFICATION_AVAILABLE = True
except ImportError:
    CLARIFICATION_AVAILABLE = False
    async def check_and_generate_clarification(*args, **kwargs):
        return None
    def store_clarification_session(*args, **kwargs):
        pass

logger = logging.getLogger(__name__)


# ==============================================================================
#  ENUMS
# ==============================================================================

class QueryType(str, Enum):
    """What kind of query is this?"""
    TOPIC = "topic"                    # General exploration (wide)
    NUANCE = "nuance"                  # Specific sub-topic with known landmark
    QUESTION = "question"              # Specific question
    SOURCE_REQUEST = "source_request"  # Direct ref lookup
    COMPARISON = "comparison"          # Compare shittos
    SHITTAH = "shittah"               # One author's view
    SUGYA = "sugya"                   # Full sugya exploration
    PASUK = "pasuk"                   # Chumash-related
    CHUMASH_SUGYA = "chumash_sugya"   # Chumash topic exploration
    HALACHA = "halacha"               # Practical halacha
    MACHLOKES = "machlokes"           # Disagreement/dispute
    UNKNOWN = "unknown"


class FoundationType(str, Enum):
    """What type of source is the foundation?"""
    GEMARA = "gemara"
    MISHNA = "mishna"
    CHUMASH = "chumash"
    HALACHA_SA = "halacha_sa"
    HALACHA_RAMBAM = "halacha_rambam"
    MIDRASH = "midrash"
    RISHON = "rishon"                  # For nuance queries where landmark is a rishon
    UNKNOWN = "unknown"


class TrickleDirection(str, Enum):
    """Which direction to fetch sources?"""
    UP = "up"
    DOWN = "down"
    BOTH = "both"
    NONE = "none"


class Breadth(str, Enum):
    """How wide should the search be?"""
    NARROW = "narrow"
    STANDARD = "standard"
    WIDE = "wide"
    EXHAUSTIVE = "exhaustive"


class LandmarkConfidence(str, Enum):
    """How confident is Gemini about the suggested landmark?"""
    HIGH = "high"          # Gemini is very sure this is THE source
    MEDIUM = "medium"      # Gemini thinks this is likely the main source
    GUESSING = "guessing"  # Gemini isn't sure but giving a best guess
    NONE = "none"          # Gemini doesn't know a landmark for this


class RefConfidence(str, Enum):
    """Confidence level for a specific ref."""
    CERTAIN = "certain"
    LIKELY = "likely"
    POSSIBLE = "possible"
    GUESS = "guess"


# ==============================================================================
#  DATA STRUCTURES
# ==============================================================================

@dataclass
class RefHint:
    """A suggested reference from Gemini with verification info."""
    ref: str
    confidence: RefConfidence = RefConfidence.POSSIBLE
    verification_keywords: List[str] = field(default_factory=list)
    reasoning: str = ""
    buffer_size: int = 1
    is_primary: bool = True  # Primary refs get expanded, contrast refs don't
    # V5: Segment-level targeting
    target_segments: List[str] = field(default_factory=list)  # Specific lines/segments to focus on
    # V6: Source of ref
    source: str = "gemini"  # "gemini" or "known_sugyos_db"


@dataclass
class SearchVariants:
    """Search variants for the topic."""
    primary_hebrew: List[str] = field(default_factory=list)
    aramaic_forms: List[str] = field(default_factory=list)
    gemara_language: List[str] = field(default_factory=list)
    root_words: List[str] = field(default_factory=list)
    related_terms: List[str] = field(default_factory=list)


@dataclass
class QueryAnalysis:
    """Complete analysis of a Torah query - V6 with known sugyos support."""
    original_query: str
    hebrew_terms_from_step1: List[str] = field(default_factory=list)
    
    # Classification
    query_type: QueryType = QueryType.UNKNOWN
    foundation_type: FoundationType = FoundationType.UNKNOWN
    breadth: Breadth = Breadth.STANDARD
    trickle_direction: TrickleDirection = TrickleDirection.UP
    
    # V5: NUANCE DETECTION (includes shittah, comparison, machlokes)
    is_nuance_query: bool = False
    nuance_description: str = ""  # What specific nuance is being asked about

    # V6: DEFINITION QUERY - tight scope, core sugya only
    is_definition_query: bool = False
    
    # V5: Target authors (for shittah/comparison queries)
    target_authors: List[str] = field(default_factory=list)  # ["Ran", "Rashi", "Tosafos"]
    primary_author: Optional[str] = None  # The main author being asked about
    
    # LANDMARK (THE source for nuance queries)
    suggested_landmark: Optional[str] = None
    landmark_confidence: LandmarkConfidence = LandmarkConfidence.NONE
    landmark_reasoning: str = ""
    
    # FOCUS vs TOPIC TERMS
    focus_terms: List[str] = field(default_factory=list)  # Nuance-specific markers
    topic_terms: List[str] = field(default_factory=list)  # General topic terms
    
    # PRIMARY vs CONTRAST REFS
    ref_hints: List[RefHint] = field(default_factory=list)  # All refs with metadata
    primary_refs: List[str] = field(default_factory=list)   # Expand these
    contrast_refs: List[str] = field(default_factory=list)  # Context only
    
    # Legacy: suggested_refs for backward compatibility
    suggested_refs: List[str] = field(default_factory=list)
    
    # What Gemini understands about the query
    inyan_description: str = ""
    search_topics_hebrew: List[str] = field(default_factory=list)
    search_variants: Optional[SearchVariants] = None
    
    # Exactly which sources to fetch
    target_sources: List[str] = field(default_factory=list)
    target_simanim: List[str] = field(default_factory=list)
    target_chelek: Optional[str] = None
    
    # Confidence and clarification
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    needs_clarification: bool = False
    clarification_question: Optional[str] = None
    clarification_options: List[str] = field(default_factory=list)
    
    # Gemini's reasoning
    reasoning: str = ""
    
    # V6: Known sugyos database match info
    known_sugya_match: Optional[Any] = None  # KnownSugyaMatch if found
    used_known_sugyos: bool = False          # Did we use the database?

    # V7: Possible interpretations for ambiguous queries (from Gemini)
    # These are used directly as clarification options without extra API call
    possible_interpretations: List[Dict[str, Any]] = field(default_factory=list)


# ==============================================================================
#  LOGGING HELPERS
# ==============================================================================

def log_section(title: str) -> None:
    """Log a major section header."""
    logger.info("")
    logger.info("=" * 70)
    logger.info(f"  {title}")
    logger.info("=" * 70)


def log_subsection(title: str) -> None:
    """Log a subsection header."""
    logger.info("")
    logger.info("-" * 50)
    logger.info(f"  {title}")
    logger.info("-" * 50)


# ==============================================================================
#  HELPER FUNCTIONS
# ==============================================================================

def _parse_enum(value: Any, enum_class: type, default: Any) -> Any:
    """Safely parse a string into an enum value."""
    if value is None:
        return default
    if isinstance(value, enum_class):
        return value
    if isinstance(value, str):
        try:
            return enum_class(value.lower())
        except (ValueError, KeyError):
            return default
    return default


def _parse_ref_hint(ref_data: dict) -> RefHint:
    """Parse a RefHint from JSON data."""
    return RefHint(
        ref=ref_data.get("ref", ""),
        confidence=_parse_enum(ref_data.get("confidence"), RefConfidence, RefConfidence.POSSIBLE),
        verification_keywords=ref_data.get("verification_keywords", []),
        reasoning=ref_data.get("reasoning", ""),
        buffer_size=ref_data.get("buffer_size", 1),
        is_primary=ref_data.get("is_primary", True),
        target_segments=ref_data.get("target_segments", []),
        source=ref_data.get("source", "gemini"),
    )


def _parse_search_variants(data: dict) -> SearchVariants:
    """Parse SearchVariants from JSON data."""
    # Gemini occasionally returns a list instead of an object.
    # Be permissive so Step 2 doesn't crash on enrichment.
    if data is None:
        data = {}
    if isinstance(data, list):
        # Treat as primary Hebrew search terms.
        return SearchVariants(primary_hebrew=[x for x in data if isinstance(x, str)])
    if isinstance(data, str):
        return SearchVariants(primary_hebrew=[data])
    if not isinstance(data, dict):
        return SearchVariants()

    return SearchVariants(
        primary_hebrew=data.get("primary_hebrew", []),
        aramaic_forms=data.get("aramaic_forms", []),
        gemara_language=data.get("gemara_language", []),
        root_words=data.get("root_words", []),
        related_terms=data.get("related_terms", []),
    )


def _load_author_kb() -> tuple:
    """Load author knowledge base for detecting author names."""
    authors = {
        "rashi", "tosafos", "tosafot", "ramban", "rashba", "ritva", "ran", 
        "rosh", "rambam", "meiri", "raavad", "rabbeinu tam", "ri", "maharam",
        "rashbam", "rabbeinu chananel", "raah", "nimukei yosef", "tur",
        "shulchan aruch", "rema", "taz", "shach", "magen avraham",
        "mishnah berurah", "ketzos", "nesivos", "pnei yehoshua"
    }
    
    def is_author(term: str) -> bool:
        return term.lower().strip() in authors
    
    return is_author, authors


def _expand_daf_range(tractate: str, start_daf: str, end_daf: str) -> List[str]:
    """
    Expand a daf range into individual daf references.

    Examples:
        "Pesachim", "4a", "5b" -> ["Pesachim 4a", "Pesachim 4b", "Pesachim 5a", "Pesachim 5b"]
        "Pesachim", "4a", "4b" -> ["Pesachim 4a", "Pesachim 4b"]
    """
    import re

    # Parse start and end
    start_match = re.match(r'(\d+)([ab])', start_daf.lower())
    end_match = re.match(r'(\d+)([ab])', end_daf.lower())

    if not start_match or not end_match:
        return [f"{tractate} {start_daf}"]

    start_num = int(start_match.group(1))
    start_amud = start_match.group(2)
    end_num = int(end_match.group(1))
    end_amud = end_match.group(2)

    refs = []
    current_num = start_num
    current_amud = start_amud

    while True:
        refs.append(f"{tractate} {current_num}{current_amud}")

        # Check if we've reached the end
        if current_num == end_num and current_amud == end_amud:
            break

        # Advance to next daf/amud
        if current_amud == 'a':
            current_amud = 'b'
        else:
            current_amud = 'a'
            current_num += 1

        # Safety: don't expand more than 10 dapim
        if len(refs) > 20:
            logger.warning(f"  Range too large, limiting to first 20 dapim")
            break

    return refs


def _validate_and_fix_refs(refs: List[str]) -> List[str]:
    """V5: Validate and fix common ref format issues, expanding ranges."""
    import re
    fixed_refs = []

    for ref in refs:
        if not ref:
            continue

        # Check for range refs like "Pesachim 2a-6b" and expand them
        range_pattern = r'(.+?)\s+(\d+[ab])\s*-\s*(\d+[ab])'
        match = re.match(range_pattern, ref)
        if match:
            base = match.group(1).strip()
            start = match.group(2)
            end = match.group(3)

            # Expand the range into individual refs
            expanded = _expand_daf_range(base, start, end)
            fixed_refs.extend(expanded)
            logger.info(f"  Expanded range ref '{ref}' to {len(expanded)} refs: {expanded[:3]}{'...' if len(expanded) > 3 else ''}")
            continue
        
        # Fix "Ran on X" to "Ran on Rif X" if needed
        if ref.lower().startswith("ran on ") and "rif" not in ref.lower():
            tractates = ["pesachim", "ketubot", "bava kamma", "bava metzia", "bava batra", 
                        "shabbat", "eruvin", "yoma", "sukkah", "beitzah", "rosh hashanah",
                        "taanit", "megillah", "moed katan", "chagigah", "yevamot", "nedarim",
                        "nazir", "sotah", "gittin", "kiddushin", "sanhedrin", "makkot",
                        "shevuot", "avodah zarah", "horayot", "zevachim", "menachot",
                        "chullin", "bekhorot", "arakhin", "temurah", "keritot", "meilah", "niddah"]
            
            ref_lower = ref.lower()
            for tractate in tractates:
                if tractate in ref_lower:
                    new_ref = ref.replace("Ran on ", "Ran on Rif ", 1)
                    logger.warning(f"  Fixed Ran ref: '{ref}' -> '{new_ref}'")
                    fixed_refs.append(new_ref)
                    break
            else:
                fixed_refs.append(ref)
            continue

        fixed_refs.append(ref)

    # Post-processing: ensure we include both sides of each daf
    # If we have "Pesachim 4a" but not "Pesachim 4b", add "Pesachim 4b"
    fixed_refs = _ensure_both_amudim(fixed_refs)

    return fixed_refs


def _ensure_both_amudim(refs: List[str]) -> List[str]:
    """
    Ensure that if we have one side of a daf, we include the other side too.

    Examples:
        ["Pesachim 4a"] -> ["Pesachim 4a", "Pesachim 4b"]
        ["Pesachim 4a", "Pesachim 4b"] -> ["Pesachim 4a", "Pesachim 4b"]
        ["Pesachim 4a", "Pesachim 6a"] -> ["Pesachim 4a", "Pesachim 4b", "Pesachim 6a", "Pesachim 6b"]
    """
    import re

    # Parse all refs to find tractate/daf pairs
    daf_pattern = r'^(.+?)\s+(\d+)([ab])$'
    parsed = []
    for ref in refs:
        match = re.match(daf_pattern, ref.strip())
        if match:
            tractate = match.group(1)
            daf_num = int(match.group(2))
            amud = match.group(3)
            parsed.append((tractate, daf_num, amud, ref))
        else:
            parsed.append((None, None, None, ref))

    # Find which dapim are present
    present_dapim = set()
    for tractate, daf_num, amud, _ in parsed:
        if tractate and daf_num:
            present_dapim.add((tractate, daf_num, amud))

    # Add missing amudim
    result = list(refs)  # Start with original refs
    added = set()

    for tractate, daf_num, amud, original_ref in parsed:
        if tractate is None:
            continue

        other_amud = 'b' if amud == 'a' else 'a'
        if (tractate, daf_num, other_amud) not in present_dapim:
            new_ref = f"{tractate} {daf_num}{other_amud}"
            if new_ref not in added and new_ref not in refs:
                # Insert after the original ref to maintain order
                idx = result.index(original_ref)
                if amud == 'a':
                    # Insert 'b' after 'a'
                    result.insert(idx + 1, new_ref)
                else:
                    # Insert 'a' before 'b'
                    result.insert(idx, new_ref)
                added.add(new_ref)
                logger.info(f"  Added complementary amud: {new_ref} (from {original_ref})")

    return result


def _detect_query_vagueness(query: str, hebrew_terms: List[str]) -> tuple[bool, str]:
    """V5: Detect if query is too vague or gibberish."""
    if len(query.split()) <= 2 and not hebrew_terms:
        return True, "Your query seems very brief. Could you provide more context about what you're looking for?"
    
    generic_terms = ["gemara", "mishna", "halacha", "torah", "sugya", "inyan"]
    if len(hebrew_terms) == 0 and query.lower().strip() in generic_terms:
        return True, f"'{query}' is very broad. What specific topic or question within {query} are you interested in?"
    
    is_author, _ = _load_author_kb()
    if is_author:
        authors = [t for t in hebrew_terms if is_author(t)]
        topics = [t for t in hebrew_terms if not is_author(t)]
        
        if len(authors) > 0 and len(topics) == 0:
            return True, f"You mentioned {', '.join(authors)}, but what topic are you interested in their views on?"
    
    return False, ""


# ==============================================================================
#  GEMINI SYSTEM PROMPT - V8 (adapted from Gemini V6)
# ==============================================================================

GEMINI_SYSTEM_PROMPT_V8 = """You are an expert Torah learning assistant for Ohr Haner, a marei mekomos (source finder) system.

YOUR JOB: Understand what the user wants and tell us EXACTLY where to look.

## CRITICAL: QUERY CLASSIFICATION

### NUANCE queries (is_nuance_query = true)
These are NOT general topic queries. They need focused searching:

1. **SUB-TOPIC queries**: "bari vishema BEISSURIN" 
   - Has a qualifier narrowing the general topic
   - Needs specific landmark source

2. **SHITTAH queries**: "what is the RAN'S shittah in bittul chometz"
   - Asking for ONE AUTHOR'S specific view
   - is_nuance_query = TRUE (not false!)
   - primary_author = "Ran"
   - The LANDMARK is that author's main source on the topic

3. **COMPARISON queries**: "how does Ran differ from Rashi on bittul"
   - Comparing multiple authors' views
   - is_nuance_query = TRUE
   - target_authors = ["Ran", "Rashi"]
   - Need landmarks for BOTH authors

4. **MACHLOKES queries**: "machlokes Rashi and Tosafos on X"
   - Dispute between authorities
   - is_nuance_query = TRUE
   - Need the source where they argue

### TOPIC queries (is_nuance_query = false)
General explorations without specific focus:
- "bari vishema" (just the topic, no qualifier)
- "sugyos in ketubot" (broad)
- "explain the concept of migu" (general)

### DEFINITION queries - KEEP SCOPE TIGHT!
When someone asks for a DEFINITION or basic explanation of a term:
- "maschir socher in psachim" = definition of landlord/tenant in chametz context
- "what is X" = asking for the core concept

For definition queries:
1. **ONLY include the PRIMARY sugya** - usually 1-2 dapim max
2. **DO NOT include tangential sugyos** that mention the term but aren't the main discussion
3. The user wants to UNDERSTAND the concept, not see every mention
4. Example: "maschir socher" is PRIMARILY on Pesachim 4a-4b.
   - DON'T include 5a, 6a, 7a even if they mention it
   - ONLY include the mishna/gemara where the concept is DEFINED and EXPLAINED

## FOCUS TERMS vs TOPIC TERMS

TOPIC TERMS are generic words for the broad topic:
- For bittul chometz: ["ביטול חמץ", "בדיקת חמץ", "כל חמירא", "ביעור"]

FOCUS TERMS are specific markers that distinguish THIS query:
- For Ran's shittah on bittul: Ran's unique terminology/concepts
- For comparison queries: Terms that show the DIFFERENCE between views
- For nuance queries: Behavioral/halachic markers for the specific aspect

## AUTHOR-SPECIFIC REF FORMATS

CRITICAL: Different rishonim have different Sefaria formats!

1. **Ran** - Writes on RIF (Alfasi), NOT directly on Gemara!
   - WRONG: "Ran on Pesachim 2a" (doesn't exist)
   - RIGHT: "Ran on Rif Pesachim 1a" or similar

2. **Rashi, Tosafos** - Direct gemara commentaries
   - Format: "Rashi on Pesachim 6b" ✓

3. **Rashba, Ritva, Ramban** - Direct gemara commentaries
   - Format: "Rashba on Ketubot 12b" ✓

4. **Rosh** - Has own structure (not by daf)
   - Format: "Rosh on Ketubot 1:18" ✓ (chapter:siman)

5. **Rambam** - Mishneh Torah
   - Format: "Mishneh Torah, Chametz U'Matzah 2:2" ✓

## REF FORMAT RULES

1. **NO RANGES**: Never "2a-6b". Use specific refs.
2. **SEFARIA SPELLING**: Ketubot, Shabbat, Pesachim (not Kesubos, Shabbos)
3. **SPECIFIC LOCATIONS**: Give daf/amud, not just masechta

## OUTPUT FORMAT

Return ONLY valid JSON:
```json
{
  "query_type": "topic|definition|nuance|shittah|comparison|machlokes|question|source_request|sugya|pasuk|halacha|unknown",
  "foundation_type": "gemara|mishna|chumash|halacha_sa|halacha_rambam|midrash|rishon|unknown",
  "breadth": "narrow|standard|wide|exhaustive",
  "trickle_direction": "up|down|both|none",

  "is_definition_query": true/false,
  "is_nuance_query": true/false,
  "nuance_description": "What specific nuance is being asked (if nuance)",
  
  "target_authors": ["Ran", "Rashi"],
  "primary_author": "Ran",
  
  "suggested_landmark": "Ketubot 12b",
  "landmark_confidence": "high|medium|guessing|none",
  "landmark_reasoning": "Why this is the landmark",
  
  "focus_terms": ["specific markers"],
  "topic_terms": ["general topic terms"],
  
  "primary_refs": [
    {"ref": "Ketubot 12b", "confidence": "certain|likely|possible|guess", "verification_keywords": ["חזקת הגוף"], "reasoning": "why"}
  ],
  "contrast_refs": [
    {"ref": "Ketubot 75b", "confidence": "likely", "verification_keywords": ["רובא וחזקה"]}
  ],
  
  "search_variants": {
    "primary_hebrew": ["חזקת הגוף"],
    "aramaic_forms": [],
    "gemara_language": [],
    "related_terms": []
  },
  
  "inyan_description": "Brief description of the topic",
  "search_topics_hebrew": ["Hebrew search terms"],
  "target_sources": ["gemara", "rashi", "tosafos"],
  
  "confidence": "high|medium|low",
  "needs_clarification": false,
  "clarification_question": null,
  "reasoning": "Your reasoning",

  "possible_interpretations": [
    {
      "id": "interpretation_1",
      "label": "Short label (2-5 words)",
      "hebrew": "Hebrew equivalent if relevant",
      "description": "Brief explanation of this interpretation",
      "focus_terms": ["terms", "to", "focus", "on"],
      "refs_hint": ["Specific refs if known"]
    }
  ]
}
```

## WHEN TO PROVIDE possible_interpretations

For MACHLOKES/COMPARISON queries or queries with multiple possible meanings:
- Provide 2-4 distinct interpretations
- Each should be a valid way to understand the query
- Include focus_terms that would narrow the search for each interpretation

Example: "machlokes abaya rava on tashbisu" could mean:
1. Bittul vs Physical Biur (whether removal is mental or physical)
2. Timing derivation (how we know chametz is forbidden from 6th hour)
3. The nature of the mitzvah (aseh or lo ta'aseh)

If you set needs_clarification=true, include 2-4 possible_interpretations.
ONLY provide possible_interpretations when there are genuinely multiple valid interpretations.
For clear, unambiguous queries, leave this field empty or null.
"""


# ==============================================================================
#  V6: KNOWN SUGYOS DATABASE CHECK
# ==============================================================================

def _check_known_sugyos(query: str, hebrew_terms: List[str]) -> Optional[Any]:
    """
    V6: Check if query matches a known sugya in the database.
    Returns KnownSugyaMatch if found, None otherwise.
    """
    from config import get_settings
    
    settings = get_settings()
    if not settings.use_known_sugyos:
        logger.info("[KNOWN_SUGYOS] Disabled via USE_KNOWN_SUGYOS config")
        return None
    
    if not KNOWN_SUGYOS_AVAILABLE:
        logger.debug("[KNOWN_SUGYOS] Module not available")
        return None
    
    log_subsection("V6: CHECKING KNOWN SUGYOS DATABASE")
    
    match = lookup_known_sugya(query, hebrew_terms)
    
    if match and match.matched:
        logger.info(f"[KNOWN_SUGYOS] ✓ Found match: {match.sugya_id}")
        logger.info(f"[KNOWN_SUGYOS]   Confidence: {match.match_confidence}")
        logger.info(f"[KNOWN_SUGYOS]   Primary refs: {match.primary_refs}")
        return match
    
    logger.info("[KNOWN_SUGYOS] No match found in database")
    return None


def _build_analysis_from_known_sugya(
    query: str,
    hebrew_terms: List[str],
    known_match: Any,  # KnownSugyaMatch
    gemini_enrichment: Optional[Dict] = None
) -> QueryAnalysis:
    """
    V6: Build QueryAnalysis using known sugya data as foundation.
    Gemini enrichment provides additional context but known refs take priority.
    """
    log_subsection("V6: BUILDING ANALYSIS FROM KNOWN SUGYA")
    
    # Create ref hints from known primary refs - these are HIGH confidence
    ref_hints = []
    primary_refs = []
    
    for pg in known_match.primary_gemara:
        hint = RefHint(
            ref=pg.ref,
            confidence=RefConfidence.CERTAIN,  # Known sugyos are CERTAIN
            verification_keywords=known_match.key_terms[:5],
            reasoning=f"From known_sugyos_db: {pg.description}",
            source="known_sugyos_db",
            is_primary=True,
        )
        ref_hints.append(hint)
        primary_refs.append(pg.ref)
    
    # Add also_discussed as secondary refs
    contrast_refs = known_match.also_discussed_refs
    for ref in contrast_refs:
        hint = RefHint(
            ref=ref,
            confidence=RefConfidence.LIKELY,
            verification_keywords=known_match.key_terms[:3],
            reasoning="Also discussed in known_sugyos_db",
            source="known_sugyos_db",
            is_primary=False,
        )
        ref_hints.append(hint)
    
    # Determine landmark - first primary gemara location
    suggested_landmark = None
    if known_match.primary_gemara:
        suggested_landmark = known_match.primary_gemara[0].ref
    
    # Use Gemini enrichment if available for additional fields
    query_type = QueryType.TOPIC
    foundation_type = FoundationType.GEMARA
    breadth = Breadth.STANDARD
    trickle_direction = TrickleDirection.UP
    is_nuance = False
    nuance_description = ""

    # V6 FIX: Use rishonim_who_discuss from known_sugyos as default target_authors
    # This ensures we search for the specific commentators who discuss this sugya
    target_authors = list(known_match.rishonim_who_discuss) if known_match.rishonim_who_discuss else []
    primary_author = None

    # V6 FIX: Use gemara_keywords from known_sugyos if available
    # These are actual words that appear in the gemara text, better for filtering
    gemara_keywords = known_match.raw_data.get("gemara_keywords", []) if known_match.raw_data else []
    if gemara_keywords:
        # gemara_keywords are better for filtering - they're actual text words
        focus_terms = gemara_keywords
        topic_terms = known_match.key_terms + gemara_keywords
        logger.info(f"[V6] Using gemara_keywords for filtering: {gemara_keywords[:5]}...")
    else:
        focus_terms = known_match.key_terms
        topic_terms = known_match.key_terms

    # V6.1: Check for sub_topics that match query qualifiers
    # This handles queries like "bari vishema beissurin" where we want to narrow
    # to the specific sub-topic and its key rishonim
    sub_topics = known_match.raw_data.get("sub_topics", {}) if known_match.raw_data else {}
    query_lower = query.lower()
    matched_sub_topic = None
    for sub_topic_id, sub_topic_data in sub_topics.items():
        # Check if the sub_topic_id appears in the query
        if sub_topic_id in query_lower or sub_topic_id.replace("_", " ") in query_lower:
            matched_sub_topic = sub_topic_data
            logger.info(f"[V6.1] Matched sub_topic: {sub_topic_id}")
            break

    if matched_sub_topic:
        # Add sub_topic focus terms to our search
        sub_focus = matched_sub_topic.get("focus_terms", [])
        for term in sub_focus:
            if term not in focus_terms:
                focus_terms.append(term)
            if term not in topic_terms:
                topic_terms.append(term)

        # Add sub_topic key_rishonim as priority authors
        sub_rishonim = matched_sub_topic.get("key_rishonim", [])
        for rishon in sub_rishonim:
            if rishon not in target_authors:
                target_authors.insert(0, rishon)  # Prioritize these

        logger.info(f"[V6.1] Added sub_topic focus: {sub_focus}")
        logger.info(f"[V6.1] Prioritized rishonim for sub_topic: {sub_rishonim}")

    search_variants = None
    inyan_description = ""
    target_sources = ["gemara", "rashi", "tosafos"]
    reasoning = f"Matched known sugya: {known_match.sugya_id}"

    logger.info(f"[V6] Using rishonim_who_discuss as target_authors: {target_authors}")

    if gemini_enrichment:
        # Use Gemini's classification/enrichment but keep our refs
        query_type = _parse_enum(gemini_enrichment.get("query_type"), QueryType, QueryType.TOPIC)
        foundation_type = _parse_enum(gemini_enrichment.get("foundation_type"), FoundationType, FoundationType.GEMARA)
        breadth = _parse_enum(gemini_enrichment.get("breadth"), Breadth, Breadth.STANDARD)
        trickle_direction = _parse_enum(gemini_enrichment.get("trickle_direction"), TrickleDirection, TrickleDirection.UP)
        is_nuance = gemini_enrichment.get("is_nuance_query", False)
        nuance_description = gemini_enrichment.get("nuance_description", "")
        # V6 FIX: Merge Gemini's target_authors with known_sugyos rishonim
        # If Gemini provides specific authors, use both (deduped)
        gemini_authors = gemini_enrichment.get("target_authors", [])
        if gemini_authors:
            combined_authors = list(target_authors)  # Start with known_sugyos rishonim
            for author in gemini_authors:
                if author not in combined_authors:
                    combined_authors.append(author)
            target_authors = combined_authors
        primary_author = gemini_enrichment.get("primary_author")
        # V6 FIX: Merge Gemini's focus_terms with gemara_keywords, not replace
        gemini_focus = gemini_enrichment.get("focus_terms", [])
        if gemini_focus and gemara_keywords:
            # Combine both - gemara_keywords first (more reliable), then Gemini's
            combined_focus = list(gemara_keywords)
            for term in gemini_focus:
                if term not in combined_focus:
                    combined_focus.append(term)
            focus_terms = combined_focus
        elif gemini_focus:
            focus_terms = gemini_focus
        # else keep gemara_keywords as focus_terms

        # V4.5 FIX: Add qualifier_terms for nuanced queries like "bari vishema beissurin"
        # These terms are CRITICAL for narrowing the search beyond the base sugya
        qualifier_terms = gemini_enrichment.get("qualifier_terms", [])
        if qualifier_terms:
            logger.info(f"[V6] Adding qualifier terms to focus: {qualifier_terms}")
            for term in qualifier_terms:
                if term not in focus_terms:
                    focus_terms.append(term)
            # Also add to topic_terms for search
            for term in qualifier_terms:
                if term not in topic_terms:
                    topic_terms.append(term)

        search_variants = _parse_search_variants(gemini_enrichment.get("search_variants", {}))
        inyan_description = gemini_enrichment.get("inyan_description", "")
        target_sources = gemini_enrichment.get("target_sources", target_sources)
        reasoning = f"Known sugya: {known_match.sugya_id}. Gemini: {gemini_enrichment.get('reasoning', '')}"
    
    # Build final analysis
    analysis = QueryAnalysis(
        original_query=query,
        hebrew_terms_from_step1=hebrew_terms,
        
        query_type=query_type,
        foundation_type=foundation_type,
        breadth=breadth,
        trickle_direction=trickle_direction,
        
        is_nuance_query=is_nuance,
        nuance_description=nuance_description,
        
        target_authors=target_authors,
        primary_author=primary_author,
        
        suggested_landmark=suggested_landmark,
        landmark_confidence=LandmarkConfidence.HIGH,  # Known sugyos have HIGH confidence
        landmark_reasoning=f"From known_sugyos_db: {known_match.sugya_id}",
        
        focus_terms=focus_terms,
        topic_terms=topic_terms,
        
        ref_hints=ref_hints,
        primary_refs=primary_refs,
        contrast_refs=contrast_refs,
        suggested_refs=primary_refs + contrast_refs,
        
        search_variants=search_variants,
        inyan_description=inyan_description,
        search_topics_hebrew=known_match.key_terms,
        
        target_sources=target_sources,
        
        confidence=ConfidenceLevel.HIGH,  # Known sugyos give us HIGH confidence
        needs_clarification=False,
        
        reasoning=reasoning,
        
        # V6 fields
        known_sugya_match=known_match,
        used_known_sugyos=True,
    )
    
    logger.info(f"[V6] Built analysis from known sugya: {known_match.sugya_id}")
    logger.info(f"[V6]   Primary refs: {primary_refs}")
    logger.info(f"[V6]   Landmark: {suggested_landmark}")
    logger.info(f"[V6]   Confidence: HIGH")
    
    return analysis


# ==============================================================================
#  MAIN ANALYSIS FUNCTION
# ==============================================================================

async def analyze_with_gemini(query: str, hebrew_terms: List[str]) -> QueryAnalysis:
    """Have Gemini analyze the query with V6 known sugyos integration."""
    log_section("STEP 2: UNDERSTAND (V6) - With Known Sugyos")
    logger.info(f"Query: {query}")
    logger.info(f"Hebrew terms: {hebrew_terms}")
    
    # V5: Pre-check for vague queries
    needs_clarification, clarification_q = _detect_query_vagueness(query, hebrew_terms)
    if needs_clarification:
        logger.warning(f"Query detected as vague: {clarification_q}")
        return QueryAnalysis(
            original_query=query,
            hebrew_terms_from_step1=hebrew_terms,
            confidence=ConfidenceLevel.LOW,
            needs_clarification=True,
            clarification_question=clarification_q,
        )
    
    # ==========================================================================
    # V6: CHECK KNOWN SUGYOS DATABASE FIRST
    # ==========================================================================
    known_match = _check_known_sugyos(query, hebrew_terms)
    
    if known_match:
        # We found a match! Still call Gemini for enrichment but use known refs
        logger.info("[V6] Known sugya found - will use database refs as primary")
        
        # Get Gemini enrichment (optional - can skip for speed)
        gemini_enrichment = None
        try:
            log_subsection("CALLING GEMINI FOR ENRICHMENT")

            # Configure Gemini
            genai.configure(api_key=settings.gemini_api_key)

            # V4.5: Enhanced prompt to detect qualifiers/nuances beyond the main sugya
            enrich_prompt = f"""You are a Torah learning assistant analyzing a query. We matched a known sugya, but check for QUALIFIERS or SUB-TOPICS.

QUERY: {query}
HEBREW TERMS: {hebrew_terms}
KNOWN TOPIC: {known_match.sugya_id}
KNOWN KEY TERMS: {known_match.key_terms}

IMPORTANT: Look for qualifiers that narrow the topic. For example:
- "bari vishema beissurin" = bari vishema specifically in ISSURIN (prohibitions) vs mammon
- "chezkas haguf ledina" = chezkas haguf specifically for practical HALACHA
- "migu lehosif" = migu used to ADD claims

If the query has qualifiers beyond the base sugya:
1. Set is_nuance_query=true
2. Describe the nuance in nuance_description
3. Add the qualifier terms to focus_terms (in Hebrew AND transliteration)
4. Add search_variants that include the qualifier

Return ONLY valid JSON (no markdown code blocks, no explanation) with these fields:
query_type, foundation_type, breadth, trickle_direction,
is_nuance_query, nuance_description, target_authors, primary_author, focus_terms,
search_variants, inyan_description, target_sources, qualifier_terms, reasoning.

RESPOND WITH ONLY THE JSON OBJECT, NO OTHER TEXT."""

            model_name = getattr(settings, "gemini_model", "gemini-2.0-flash")
            model = genai.GenerativeModel(
                model_name=model_name,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=1500,
                    temperature=0.1,
                )
            )

            response = model.generate_content(enrich_prompt)

            # Track token usage
            if TOKEN_TRACKING_AVAILABLE and hasattr(response, 'usage_metadata'):
                tracker = get_global_tracker(model_name)
                tracker.record_from_response(response, "Step 2: Enrichment")

            raw_text = response.text.strip()
            json_text = raw_text
            if "```json" in raw_text:
                json_text = raw_text.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_text:
                json_text = raw_text.split("```")[1].split("```")[0].strip()

            gemini_enrichment = json.loads(json_text)
            logger.info("[V8] Got Gemini enrichment")
            
        except Exception as e:
            logger.warning(f"[V8] Gemini enrichment failed (non-critical): {e}")
            gemini_enrichment = None
        
        # V4.4: Check if LLM enrichment indicates the match is bad
        # If LLM says it's "unrelated" or "wrong", fall back to full analysis
        if gemini_enrichment:
            reasoning = gemini_enrichment.get("reasoning", "").lower()
            bad_match_indicators = ["unrelated", "not related", "wrong topic", "incorrect match",
                                    "different topic", "no connection", "does not match",
                                    "completely unrelated", "nothing to do with"]

            if any(indicator in reasoning for indicator in bad_match_indicators):
                logger.warning(f"[V6] Claude indicates known_sugya match is BAD - falling back to full analysis")
                logger.warning(f"[V6]   Reason: {reasoning[:100]}...")
                # Fall through to full Claude analysis below instead of using known_sugyos
                known_match = None  # Clear the match so we use full analysis

        # Only use known_sugya if it's still valid after Claude check
        if known_match:
            # Build analysis from known sugya + Claude enrichment
            analysis = _build_analysis_from_known_sugya(query, hebrew_terms, known_match, gemini_enrichment)

            log_subsection("ANALYSIS RESULTS (FROM KNOWN SUGYOS)")
            _log_analysis_results(analysis)

            return analysis

        # If we get here, Claude indicated the match was bad - continue to full analysis
    
    # ==========================================================================
    # NO KNOWN SUGYA - FALL BACK TO FULL GEMINI ANALYSIS (V8 behavior)
    # ==========================================================================
    log_subsection("CALLING GEMINI API (FULL ANALYSIS)")

    # Build the full prompt with system context included (Gemini doesn't have separate system prompt)
    full_prompt = f"""{GEMINI_SYSTEM_PROMPT_V8}

---

Now analyze this Torah query and tell me EXACTLY where to look.

QUERY: {query}
HEBREW TERMS DETECTED: {hebrew_terms}

Remember:
- SHITTAH queries (asking for one author's view) ARE nuance queries - set is_nuance_query=true
- COMPARISON queries ARE nuance queries - set is_nuance_query=true
- RAN writes on RIF, not directly on gemara - use "Ran on Rif Pesachim" format
- NO RANGE REFS like "2a-6b" - give specific refs
- Include target_segments with starting words of relevant discussion when possible
- If query is unclear, set needs_clarification=true

Return ONLY valid JSON (no markdown code blocks, no explanation before or after the JSON).
RESPOND WITH ONLY THE JSON OBJECT."""

    try:
        import time
        start_time = time.time()

        # Configure Gemini
        genai.configure(api_key=settings.gemini_api_key)

        model_name = getattr(settings, "gemini_model", "gemini-2.0-flash")
        max_tokens = min(getattr(settings, "gemini_max_tokens", 4000), 4000)
        model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=0.1,
            )
        )

        response = model.generate_content(full_prompt)

        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.info(f"Gemini response received in {elapsed_ms}ms")

        # Track token usage
        if TOKEN_TRACKING_AVAILABLE and hasattr(response, 'usage_metadata'):
            tracker = get_global_tracker(model_name)
            tracker.record_from_response(response, "Step 2: Understanding")

        raw_text = response.text.strip()
        logger.info(f"Response length: {len(raw_text)} chars")
        logger.debug(f"Raw response:\n{raw_text}")
        
        log_subsection("PARSING GEMINI RESPONSE")
        
        # Parse JSON
        json_text = raw_text
        if "```json" in raw_text:
            json_text = raw_text.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_text:
            json_text = raw_text.split("```")[1].split("```")[0].strip()
        
        try:
            data = json.loads(json_text)
        except json.JSONDecodeError:
            idx = json_text.rfind("}")
            if idx != -1:
                data = json.loads(json_text[:idx+1])
            else:
                raise
        
        logger.info("Parsed JSON successfully")
        
        # Parse ref hints
        ref_hints = []
        primary_refs_list = []
        contrast_refs_list = []
        
        for ref_data in data.get("primary_refs", []):
            if isinstance(ref_data, dict):
                hint = _parse_ref_hint(ref_data)
                hint.is_primary = True
                hint.source = "gemini"
                ref_hints.append(hint)
                primary_refs_list.append(hint.ref)
            elif isinstance(ref_data, str):
                ref_hints.append(RefHint(ref=ref_data, is_primary=True, source="gemini"))
                primary_refs_list.append(ref_data)
        
        for ref_data in data.get("contrast_refs", []):
            if isinstance(ref_data, dict):
                hint = _parse_ref_hint(ref_data)
                hint.is_primary = False
                hint.source = "gemini"
                ref_hints.append(hint)
                contrast_refs_list.append(hint.ref)
            elif isinstance(ref_data, str):
                ref_hints.append(RefHint(ref=ref_data, is_primary=False, source="gemini"))
                contrast_refs_list.append(ref_data)
        
        if not ref_hints:
            for ref_data in data.get("suggested_refs", []):
                if isinstance(ref_data, dict):
                    hint = _parse_ref_hint(ref_data)
                    hint.source = "gemini"
                    ref_hints.append(hint)
                    primary_refs_list.append(hint.ref)
                elif isinstance(ref_data, str):
                    ref_hints.append(RefHint(ref=ref_data, source="gemini"))
                    primary_refs_list.append(ref_data)
        
        # Validate and fix refs
        primary_refs_list = _validate_and_fix_refs(primary_refs_list)
        contrast_refs_list = _validate_and_fix_refs(contrast_refs_list)
        
        suggested_landmark = data.get("suggested_landmark")
        if suggested_landmark:
            fixed = _validate_and_fix_refs([suggested_landmark])
            suggested_landmark = fixed[0] if fixed else suggested_landmark
        
        # Force nuance for shittah/comparison/machlokes
        query_type = _parse_enum(data.get("query_type"), QueryType, QueryType.UNKNOWN)
        is_nuance = data.get("is_nuance_query", False)
        is_definition = data.get("is_definition_query", False)

        # Auto-detect definition queries based on query_type
        if query_type.value == "definition" or data.get("query_type") == "definition":
            is_definition = True
            logger.info(f"  Detected definition query - will limit scope")

        if query_type in [QueryType.SHITTAH, QueryType.COMPARISON, QueryType.MACHLOKES]:
            if not is_nuance:
                logger.warning(f"Forcing is_nuance_query=true for {query_type.value} query")
                is_nuance = True
        
        # Build QueryAnalysis
        analysis = QueryAnalysis(
            original_query=query,
            hebrew_terms_from_step1=hebrew_terms,
            
            query_type=query_type,
            foundation_type=_parse_enum(data.get("foundation_type"), FoundationType, FoundationType.UNKNOWN),
            breadth=_parse_enum(data.get("breadth"), Breadth, Breadth.STANDARD),
            trickle_direction=_parse_enum(data.get("trickle_direction"), TrickleDirection, TrickleDirection.UP),
            
            is_nuance_query=is_nuance,
            is_definition_query=is_definition,
            nuance_description=data.get("nuance_description", ""),
            
            target_authors=data.get("target_authors", []),
            primary_author=data.get("primary_author"),
            
            suggested_landmark=suggested_landmark,
            landmark_confidence=_parse_enum(data.get("landmark_confidence"), LandmarkConfidence, LandmarkConfidence.NONE),
            landmark_reasoning=data.get("landmark_reasoning", ""),
            
            focus_terms=data.get("focus_terms", []),
            topic_terms=data.get("topic_terms", []),
            
            ref_hints=ref_hints,
            primary_refs=primary_refs_list,
            contrast_refs=contrast_refs_list,
            suggested_refs=primary_refs_list + contrast_refs_list,
            
            search_variants=_parse_search_variants(data.get("search_variants", {})),
            inyan_description=data.get("inyan_description", ""),
            search_topics_hebrew=data.get("search_topics_hebrew", hebrew_terms),
            
            target_sources=data.get("target_sources", ["gemara", "rashi", "tosafos"]),
            target_simanim=data.get("target_simanim", []),
            target_chelek=data.get("target_chelek"),
            
            confidence=_parse_enum(data.get("confidence"), ConfidenceLevel, ConfidenceLevel.MEDIUM),
            needs_clarification=data.get("needs_clarification", False),
            clarification_question=data.get("clarification_question"),
            clarification_options=data.get("clarification_options", []),
            reasoning=data.get("reasoning", ""),

            # V6: No known sugya match
            known_sugya_match=None,
            used_known_sugyos=False,

            # V7: Possible interpretations from LLM (for clarification without extra API call)
            possible_interpretations=data.get("possible_interpretations", []),
        )
        
        log_subsection("ANALYSIS RESULTS (FROM GEMINI)")
        _log_analysis_results(analysis)
        
        return analysis
        
    except Exception as e:
        logger.error(f"[UNDERSTAND V8] Gemini error: {e}")
        import traceback
        traceback.print_exc()
        return QueryAnalysis(
            original_query=query,
            hebrew_terms_from_step1=hebrew_terms,
            query_type=QueryType.UNKNOWN,
            confidence=ConfidenceLevel.LOW,
            needs_clarification=True,
            clarification_question="I encountered an error analyzing your query. Could you rephrase it?",
            reasoning=f"Error: {e}"
        )


def _log_analysis_results(analysis: QueryAnalysis) -> None:
    """Log the analysis results in a readable format."""
    logger.info(f"Query Type: {analysis.query_type.value}")
    logger.info(f"Foundation Type: {analysis.foundation_type.value}")
    logger.info(f"Breadth: {analysis.breadth.value}")
    logger.info(f"Trickle Direction: {analysis.trickle_direction.value}")
    logger.info(f"Confidence: {analysis.confidence.value}")
    
    # V6: Known sugyos info
    if analysis.used_known_sugyos:
        logger.info("")
        logger.info("📚 USED KNOWN SUGYOS DATABASE")
        if analysis.known_sugya_match:
            logger.info(f"  Sugya ID: {analysis.known_sugya_match.sugya_id}")
            logger.info(f"  Match Reason: {analysis.known_sugya_match.match_reason}")
    
    # V5: Nuance info
    if analysis.is_nuance_query:
        logger.info("")
        logger.info("🎯 NUANCE QUERY DETECTED")
        logger.info(f"  Nuance: {analysis.nuance_description}")
        logger.info(f"  Landmark: {analysis.suggested_landmark} [{analysis.landmark_confidence.value}]")
        if analysis.landmark_reasoning:
            logger.info(f"  Landmark Reason: {analysis.landmark_reasoning[:80]}...")
        logger.info(f"  Focus Terms: {analysis.focus_terms}")
        logger.info(f"  Topic Terms: {analysis.topic_terms}")
        
        if analysis.target_authors:
            logger.info(f"  Target Authors: {analysis.target_authors}")
        if analysis.primary_author:
            logger.info(f"  Primary Author: {analysis.primary_author}")
    
    # Refs
    if analysis.primary_refs:
        logger.info("")
        logger.info(f"PRIMARY REFS ({len(analysis.primary_refs)}):")
        for hint in analysis.ref_hints:
            if hint.is_primary:
                conf = hint.confidence.value if hasattr(hint.confidence, 'value') else hint.confidence
                src = f" [from {hint.source}]" if hint.source != "gemini" else ""
                logger.info(f"  • {hint.ref} [{conf}]{src}")
                if hint.verification_keywords:
                    logger.info(f"    Keywords: {hint.verification_keywords}")
    
    if analysis.contrast_refs:
        logger.info("")
        logger.info(f"CONTRAST REFS ({len(analysis.contrast_refs)}):")
        for hint in analysis.ref_hints:
            if not hint.is_primary:
                conf = hint.confidence.value if hasattr(hint.confidence, 'value') else hint.confidence
                logger.info(f"  • {hint.ref} [{conf}] (context only)")
    
    logger.info("")
    logger.info(f"Target Sources: {analysis.target_sources}")
    
    if analysis.inyan_description:
        logger.info("")
        logger.info(f"Inyan: {analysis.inyan_description}")


# ==============================================================================
#  V7: CLARIFICATION INTEGRATION
# ==============================================================================

async def _check_for_clarification(
    analysis: QueryAnalysis,
    query: str,
    hebrew_terms: List[str],
    known_sugya_data: Optional[Dict] = None,
    skip_clarification: bool = False,
) -> QueryAnalysis:
    """
    V7: Check if clarification is needed and populate options if so.

    This is called after initial analysis to determine if we should
    ask the user for clarification before proceeding to search.
    """
    if skip_clarification:
        logger.info("[CLARIFICATION] Skipping clarification check (user already clarified)")
        return analysis

    if not CLARIFICATION_AVAILABLE:
        logger.debug("[CLARIFICATION] Module not available")
        return analysis

    # Don't skip based on confidence alone - let check_and_generate_clarification decide
    # It considers query type (machlokes queries need clarification even with high confidence)
    logger.info(f"[CLARIFICATION] Checking if clarification needed for query: {query[:50]}...")

    # Get known sugya raw data if available
    raw_sugya_data = None
    if analysis.known_sugya_match and hasattr(analysis.known_sugya_match, 'raw_data'):
        raw_sugya_data = analysis.known_sugya_match.raw_data
    elif known_sugya_data:
        raw_sugya_data = known_sugya_data

    # Determine topic for context
    topic = ""
    if analysis.known_sugya_match:
        topic = getattr(analysis.known_sugya_match, 'sugya_id', '')
    elif analysis.inyan_description:
        topic = analysis.inyan_description[:50]

    # Check if clarification is needed and generate options
    # V7: Pass possible_interpretations from Step 2 Gemini call to avoid extra API call
    clarification_result = await check_and_generate_clarification(
        query=query,
        hebrew_terms=hebrew_terms,
        confidence=analysis.confidence.value if hasattr(analysis.confidence, 'value') else str(analysis.confidence),
        landmark_confidence=analysis.landmark_confidence.value if hasattr(analysis.landmark_confidence, 'value') else str(analysis.landmark_confidence),
        query_type=analysis.query_type.value if hasattr(analysis.query_type, 'value') else str(analysis.query_type),
        topic=topic,
        known_sugya_data=raw_sugya_data,
        context=analysis.reasoning,
        clarification_question=analysis.clarification_question,
        clarification_options=analysis.clarification_options,
        possible_interpretations=analysis.possible_interpretations,  # V7: From Step 2 Gemini call
    )

    if clarification_result and clarification_result.needs_clarification:
        logger.info(f"[CLARIFICATION] Clarification needed: {clarification_result.reason}")
        logger.info(f"[CLARIFICATION] Question: {clarification_result.question}")
        logger.info(f"[CLARIFICATION] Options: {[opt.label for opt in clarification_result.options]}")

        # Update analysis with clarification info
        analysis.needs_clarification = True
        analysis.clarification_question = clarification_result.question
        analysis.clarification_options = [
            opt.label for opt in clarification_result.options
        ]

        # Store session for later retrieval
        store_clarification_session(
            query_id=clarification_result.query_id,
            original_query=query,
            hebrew_terms=hebrew_terms,
            options=clarification_result.options,
            analysis=analysis,
            partial_analysis={
                "query_type": analysis.query_type.value,
                "primary_refs": analysis.primary_refs,
                "topic_terms": analysis.topic_terms,
            }
        )

        # Store query_id in analysis for API to return
        # We'll use reasoning to pass this (not ideal but works with existing structure)
        if clarification_result.query_id:
            analysis.reasoning = f"[CLARIFY:{clarification_result.query_id}] {analysis.reasoning}"

    return analysis


# ==============================================================================
#  MAIN ENTRY POINT
# ==============================================================================

async def understand(
    hebrew_terms: List[str] = None,
    query: str = None,
    decipher_result: "DecipherResult" = None,
    skip_clarification: bool = False,
) -> QueryAnalysis:
    """
    Main entry point for Step 2: UNDERSTAND (V7 with known sugyos + clarification).

    Args:
        hebrew_terms: List of Hebrew terms from Step 1
        query: Original query string
        decipher_result: Optional DecipherResult from Step 1
        skip_clarification: If True, don't check for clarification (used when resuming after user clarified)

    Returns:
        QueryAnalysis with interpretation. If needs_clarification=True, the caller
        should present clarification_options to the user before proceeding to Step 3.
    """
    # Handle different input formats
    if decipher_result is not None:
        if hebrew_terms is None:
            hebrew_terms = decipher_result.hebrew_terms or []
            if hasattr(decipher_result, 'hebrew_term') and decipher_result.hebrew_term:
                if decipher_result.hebrew_term not in hebrew_terms:
                    hebrew_terms = [decipher_result.hebrew_term] + list(hebrew_terms)
        
        if query is None and hasattr(decipher_result, 'original_query'):
            query = decipher_result.original_query
    
    # Ensure lists
    if hebrew_terms is None:
        hebrew_terms = []
    if not isinstance(hebrew_terms, list):
        hebrew_terms = list(hebrew_terms)
    
    # Validation
    if not hebrew_terms and not query:
        logger.warning("[UNDERSTAND V6] No input provided")
        return QueryAnalysis(
            original_query="",
            confidence=ConfidenceLevel.LOW,
            needs_clarification=True,
            clarification_question="What topic would you like to explore?",
        )
    
    if not query:
        query = " ".join(hebrew_terms)
    
    analysis = await analyze_with_gemini(query, hebrew_terms)

    # V7: Check if clarification is needed before proceeding
    analysis = await _check_for_clarification(
        analysis=analysis,
        query=query,
        hebrew_terms=hebrew_terms,
        known_sugya_data=analysis.known_sugya_match.raw_data if analysis.known_sugya_match and hasattr(analysis.known_sugya_match, 'raw_data') else None,
        skip_clarification=skip_clarification,
    )

    log_section("STEP 2 COMPLETE")
    logger.info(f"Query type: {analysis.query_type.value}")
    logger.info(f"Is nuance: {analysis.is_nuance_query}")
    logger.info(f"Used known sugyos: {analysis.used_known_sugyos}")
    logger.info(f"Landmark: {analysis.suggested_landmark}")
    logger.info(f"Primary refs: {len(analysis.primary_refs)}")
    logger.info(f"Contrast refs: {len(analysis.contrast_refs)}")
    logger.info(f"Confidence: {analysis.confidence.value}")
    logger.info(f"Needs clarification: {analysis.needs_clarification}")
    if analysis.needs_clarification:
        logger.info(f"Clarification options: {analysis.clarification_options}")

    return analysis


# Aliases
run_step_two = understand
analyze = understand


__all__ = [
    'understand',
    'run_step_two',
    'analyze',
    'analyze_with_gemini',
    'QueryAnalysis',
    'RefHint',
    'SearchVariants',
    'QueryType',
    'FoundationType',
    'TrickleDirection',
    'Breadth',
    'ConfidenceLevel',
    'LandmarkConfidence',
    'RefConfidence',
]
