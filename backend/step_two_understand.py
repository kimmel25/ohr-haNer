"""
Step 2: UNDERSTAND - V6 with Known Sugyos Database
===================================================

V6 CHANGES FROM V5:
1. KNOWN SUGYOS DATABASE CHECK - Check database FIRST before Claude
2. If known sugya found, use those exact locations as primary refs with HIGH confidence
3. Claude still provides analysis but known refs take priority
4. Solves "Primary Sources Issue" where system returned Rishonim instead of Gemara

PIPELINE LOGIC:
1. Receive query + hebrew_terms from Step 1
2. Check known_sugyos database for matches
3. If MATCH FOUND:
   - Use known gemara locations as primary_refs
   - Set confidence HIGH
   - Use key_terms for validation
   - Claude enriches with search_variants, target_authors, etc.
4. If NO MATCH:
   - Fall back to full Claude analysis (same as V5)
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

from anthropic import Anthropic

# Initialize logging
try:
    from logging.logging_config import setup_logging
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
        anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "")
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
    """How confident is Claude about the suggested landmark?"""
    HIGH = "high"          # Claude is very sure this is THE source
    MEDIUM = "medium"      # Claude thinks this is likely the main source
    GUESSING = "guessing"  # Claude isn't sure but giving a best guess
    NONE = "none"          # Claude doesn't know a landmark for this


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
    """A suggested reference from Claude with verification info."""
    ref: str
    confidence: RefConfidence = RefConfidence.POSSIBLE
    verification_keywords: List[str] = field(default_factory=list)
    reasoning: str = ""
    buffer_size: int = 1
    is_primary: bool = True  # Primary refs get expanded, contrast refs don't
    # V5: Segment-level targeting
    target_segments: List[str] = field(default_factory=list)  # Specific lines/segments to focus on
    # V6: Source of ref
    source: str = "claude"  # "claude" or "known_sugyos_db"


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
    
    # What Claude understands about the query
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
    
    # Claude's reasoning
    reasoning: str = ""
    
    # V6: Known sugyos database match info
    known_sugya_match: Optional[Any] = None  # KnownSugyaMatch if found
    used_known_sugyos: bool = False          # Did we use the database?


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
        source=ref_data.get("source", "claude"),
    )


def _parse_search_variants(data: dict) -> SearchVariants:
    """Parse SearchVariants from JSON data."""
    # Claude occasionally returns a list instead of an object.
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


def _validate_and_fix_refs(refs: List[str]) -> List[str]:
    """V5: Validate and fix common ref format issues."""
    fixed_refs = []
    
    for ref in refs:
        if not ref:
            continue
        
        # Check for range refs like "2a-6b" and split them
        range_match = None
        import re
        range_pattern = r'(.+?)\s+(\d+[ab])\s*-\s*(\d+[ab])'
        match = re.match(range_pattern, ref)
        if match:
            base = match.group(1)
            start = match.group(2)
            # Just take the start of the range
            fixed_refs.append(f"{base} {start}".strip())
            logger.warning(f"  Converted range ref '{ref}' to '{base} {start}'")
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
    
    return fixed_refs


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
#  CLAUDE SYSTEM PROMPT - V6 (same as V5)
# ==============================================================================

CLAUDE_SYSTEM_PROMPT_V6 = """You are an expert Torah learning assistant for Ohr Haner, a marei mekomos (source finder) system.

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
  "query_type": "topic|nuance|shittah|comparison|machlokes|question|source_request|sugya|pasuk|halacha|unknown",
  "foundation_type": "gemara|mishna|chumash|halacha_sa|halacha_rambam|midrash|rishon|unknown",
  "breadth": "narrow|standard|wide|exhaustive",
  "trickle_direction": "up|down|both|none",
  
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
  "reasoning": "Your reasoning"
}
```
"""


# ==============================================================================
#  V6: KNOWN SUGYOS DATABASE CHECK
# ==============================================================================

def _check_known_sugyos(query: str, hebrew_terms: List[str]) -> Optional[Any]:
    """
    V6: Check if query matches a known sugya in the database.
    Returns KnownSugyaMatch if found, None otherwise.
    """
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
    claude_enrichment: Optional[Dict] = None
) -> QueryAnalysis:
    """
    V6: Build QueryAnalysis using known sugya data as foundation.
    Claude enrichment provides additional context but known refs take priority.
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
    
    # Use Claude enrichment if available for additional fields
    query_type = QueryType.TOPIC
    foundation_type = FoundationType.GEMARA
    breadth = Breadth.STANDARD
    trickle_direction = TrickleDirection.UP
    is_nuance = False
    nuance_description = ""
    target_authors = []
    primary_author = None
    focus_terms = []
    topic_terms = known_match.key_terms
    search_variants = None
    inyan_description = ""
    target_sources = ["gemara", "rashi", "tosafos"]
    reasoning = f"Matched known sugya: {known_match.sugya_id}"
    
    if claude_enrichment:
        # Use Claude's classification/enrichment but keep our refs
        query_type = _parse_enum(claude_enrichment.get("query_type"), QueryType, QueryType.TOPIC)
        foundation_type = _parse_enum(claude_enrichment.get("foundation_type"), FoundationType, FoundationType.GEMARA)
        breadth = _parse_enum(claude_enrichment.get("breadth"), Breadth, Breadth.STANDARD)
        trickle_direction = _parse_enum(claude_enrichment.get("trickle_direction"), TrickleDirection, TrickleDirection.UP)
        is_nuance = claude_enrichment.get("is_nuance_query", False)
        nuance_description = claude_enrichment.get("nuance_description", "")
        target_authors = claude_enrichment.get("target_authors", [])
        primary_author = claude_enrichment.get("primary_author")
        focus_terms = claude_enrichment.get("focus_terms", [])
        search_variants = _parse_search_variants(claude_enrichment.get("search_variants", {}))
        inyan_description = claude_enrichment.get("inyan_description", "")
        target_sources = claude_enrichment.get("target_sources", target_sources)
        reasoning = f"Known sugya: {known_match.sugya_id}. Claude: {claude_enrichment.get('reasoning', '')}"
    
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

async def analyze_with_claude(query: str, hebrew_terms: List[str]) -> QueryAnalysis:
    """Have Claude analyze the query with V6 known sugyos integration."""
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
        # We found a match! Still call Claude for enrichment but use known refs
        logger.info("[V6] Known sugya found - will use database refs as primary")
        
        # Get Claude enrichment (optional - can skip for speed)
        claude_enrichment = None
        try:
            log_subsection("CALLING CLAUDE FOR ENRICHMENT")
            
            client = Anthropic(api_key=settings.anthropic_api_key)
            
            # Simpler prompt since we already have the refs
            enrich_prompt = f"""Analyze this Torah query. We already know the main sources.
Just provide classification and search variants.

QUERY: {query}
HEBREW TERMS: {hebrew_terms}
KNOWN TOPIC: {known_match.sugya_id}
KNOWN KEY TERMS: {known_match.key_terms}

Return ONLY valid JSON with: query_type, foundation_type, breadth, trickle_direction, 
is_nuance_query, nuance_description, target_authors, primary_author, focus_terms, 
search_variants, inyan_description, target_sources, reasoning."""
            
            response = client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=1500,
                temperature=0,
                system="You are a Torah learning assistant. Provide query classification as JSON.",
                messages=[{"role": "user", "content": enrich_prompt}]
            )
            
            raw_text = response.content[0].text.strip()
            json_text = raw_text
            if "```json" in raw_text:
                json_text = raw_text.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_text:
                json_text = raw_text.split("```")[1].split("```")[0].strip()
            
            claude_enrichment = json.loads(json_text)
            logger.info("[V6] Got Claude enrichment")
            
        except Exception as e:
            logger.warning(f"[V6] Claude enrichment failed (non-critical): {e}")
            claude_enrichment = None
        
        # Build analysis from known sugya + Claude enrichment
        analysis = _build_analysis_from_known_sugya(query, hebrew_terms, known_match, claude_enrichment)
        
        log_subsection("ANALYSIS RESULTS (FROM KNOWN SUGYOS)")
        _log_analysis_results(analysis)
        
        return analysis
    
    # ==========================================================================
    # NO KNOWN SUGYA - FALL BACK TO FULL CLAUDE ANALYSIS (V5 behavior)
    # ==========================================================================
    log_subsection("CALLING CLAUDE API (FULL ANALYSIS)")
    
    user_prompt = f"""Analyze this Torah query and tell me EXACTLY where to look.

QUERY: {query}
HEBREW TERMS DETECTED: {hebrew_terms}

Remember:
- SHITTAH queries (asking for one author's view) ARE nuance queries - set is_nuance_query=true
- COMPARISON queries ARE nuance queries - set is_nuance_query=true  
- RAN writes on RIF, not directly on gemara - use "Ran on Rif Pesachim" format
- NO RANGE REFS like "2a-6b" - give specific refs
- Include target_segments with starting words of relevant discussion when possible
- If query is unclear, set needs_clarification=true

Return ONLY valid JSON."""

    try:
        import time
        start_time = time.time()
        
        client = Anthropic(api_key=settings.anthropic_api_key)
        
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=3000,
            temperature=0,
            system=CLAUDE_SYSTEM_PROMPT_V6,
            messages=[{"role": "user", "content": user_prompt}]
        )
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.info(f"Claude response received in {elapsed_ms}ms")
        
        raw_text = response.content[0].text.strip()
        logger.info(f"Response length: {len(raw_text)} chars")
        logger.debug(f"Raw response:\n{raw_text}")
        
        log_subsection("PARSING CLAUDE RESPONSE")
        
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
                hint.source = "claude"
                ref_hints.append(hint)
                primary_refs_list.append(hint.ref)
            elif isinstance(ref_data, str):
                ref_hints.append(RefHint(ref=ref_data, is_primary=True, source="claude"))
                primary_refs_list.append(ref_data)
        
        for ref_data in data.get("contrast_refs", []):
            if isinstance(ref_data, dict):
                hint = _parse_ref_hint(ref_data)
                hint.is_primary = False
                hint.source = "claude"
                ref_hints.append(hint)
                contrast_refs_list.append(hint.ref)
            elif isinstance(ref_data, str):
                ref_hints.append(RefHint(ref=ref_data, is_primary=False, source="claude"))
                contrast_refs_list.append(ref_data)
        
        if not ref_hints:
            for ref_data in data.get("suggested_refs", []):
                if isinstance(ref_data, dict):
                    hint = _parse_ref_hint(ref_data)
                    hint.source = "claude"
                    ref_hints.append(hint)
                    primary_refs_list.append(hint.ref)
                elif isinstance(ref_data, str):
                    ref_hints.append(RefHint(ref=ref_data, source="claude"))
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
        )
        
        log_subsection("ANALYSIS RESULTS (FROM CLAUDE)")
        _log_analysis_results(analysis)
        
        return analysis
        
    except Exception as e:
        logger.error(f"[UNDERSTAND V6] Claude error: {e}")
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
                src = f" [from {hint.source}]" if hint.source != "claude" else ""
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
#  MAIN ENTRY POINT
# ==============================================================================

async def understand(
    hebrew_terms: List[str] = None,
    query: str = None,
    decipher_result: "DecipherResult" = None
) -> QueryAnalysis:
    """
    Main entry point for Step 2: UNDERSTAND (V6 with known sugyos).
    
    Args:
        hebrew_terms: List of Hebrew terms from Step 1
        query: Original query string
        decipher_result: Optional DecipherResult from Step 1
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
    
    analysis = await analyze_with_claude(query, hebrew_terms)
    
    log_section("STEP 2 COMPLETE")
    logger.info(f"Query type: {analysis.query_type.value}")
    logger.info(f"Is nuance: {analysis.is_nuance_query}")
    logger.info(f"Used known sugyos: {analysis.used_known_sugyos}")
    logger.info(f"Landmark: {analysis.suggested_landmark}")
    logger.info(f"Primary refs: {len(analysis.primary_refs)}")
    logger.info(f"Contrast refs: {len(analysis.contrast_refs)}")
    logger.info(f"Confidence: {analysis.confidence.value}")
    
    return analysis


# Aliases
run_step_two = understand
analyze = understand


__all__ = [
    'understand',
    'run_step_two',
    'analyze',
    'analyze_with_claude',
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