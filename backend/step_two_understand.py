"""
Step 2: UNDERSTAND - V4 with Nuance Detection
=============================================

V4 PHILOSOPHY:
Claude is the brain. We trust Claude to identify:
1. GENERAL queries: "bari vishema" → multiple foundations, wide expansion
2. NUANCE queries: "bari vishema beissurin" → specific landmark, narrow expansion

KEY V4 ADDITIONS:
1. NUANCE DETECTION: Identify when query has a specific qualifier
2. FOCUS TERMS: Behavioral markers that distinguish the nuance (e.g., "מותרת", "לאוסרה")
3. TOPIC TERMS: Generic terms for the broad topic (e.g., "ברי ושמא")
4. SUGGESTED LANDMARK: Claude's best guess for THE source for this nuance
5. LANDMARK CONFIDENCE: How sure is Claude (high/medium/guessing/none)
6. PRIMARY vs CONTRAST REFS: What to expand vs. just include for context

OUTPUT FLOW FOR NUANCE QUERIES:
- suggested_landmark: "Rosh on Ketubot 1:18" - THE source
- landmark_confidence: "high" | "medium" | "guessing" | "none"
- focus_terms: ["מותרת", "אסורה", "לאוסרה", "שויא אנפשיה", "חתיכה דאיסורא"]
- topic_terms: ["ברי ושמא", "ברי עדיף", "שמא"]
- primary_refs: Refs that directly discuss the nuance (expand these)
- contrast_refs: Refs for comparison/context only (don't expand)
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
    RISHON = "rishon"                  # V4: For nuance queries where landmark is a rishon
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
    is_primary: bool = True  # V4: Primary refs get expanded, contrast refs don't


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
    """Complete analysis of a Torah query - V4 with nuance support."""
    original_query: str
    hebrew_terms_from_step1: List[str] = field(default_factory=list)
    
    # Classification
    query_type: QueryType = QueryType.UNKNOWN
    foundation_type: FoundationType = FoundationType.UNKNOWN
    breadth: Breadth = Breadth.STANDARD
    trickle_direction: TrickleDirection = TrickleDirection.UP
    
    # V4: NUANCE DETECTION
    is_nuance_query: bool = False
    nuance_description: str = ""  # What specific nuance is being asked about
    
    # V4: LANDMARK (THE source for nuance queries)
    suggested_landmark: Optional[str] = None
    landmark_confidence: LandmarkConfidence = LandmarkConfidence.NONE
    landmark_reasoning: str = ""
    
    # V4: FOCUS vs TOPIC TERMS
    focus_terms: List[str] = field(default_factory=list)  # Nuance-specific markers
    topic_terms: List[str] = field(default_factory=list)  # General topic terms
    
    # V4: PRIMARY vs CONTRAST REFS
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
#  CLAUDE SYSTEM PROMPT - V4 with NUANCE DETECTION
# ==============================================================================

CLAUDE_SYSTEM_PROMPT_V4 = """You are an expert Torah learning assistant for Ohr Haner, a marei mekomos (source finder) system.

YOUR JOB: Understand what the user wants and tell us EXACTLY where to look.

## CRITICAL: NUANCE DETECTION

Many Torah queries are not just "tell me about X" but "tell me about the SPECIFIC ASPECT of X".

Examples:
- "bari vishema" → GENERAL topic, wants multiple sugyos
- "bari vishema beissurin" → NUANCE query, wants the specific discussion of whether bari v'shema applies to issurin

When you detect a NUANCE query:
1. Set query_type = "nuance"
2. Identify the LANDMARK source - the famous source that discusses this specific nuance
3. Provide FOCUS TERMS - behavioral/halachic markers that distinguish this nuance
4. Separate PRIMARY refs (expand these) from CONTRAST refs (context only)

## FOCUS TERMS vs TOPIC TERMS

TOPIC TERMS are generic words for the broad topic:
- For bari v'shema: ["ברי ושמא", "ברי עדיף", "שמא"]
- These appear in many sugyos

FOCUS TERMS are specific markers for the nuance:
- For bari v'shema BEISSURIN: ["מותרת", "אסורה", "לאוסרה", "שויא אנפשיה", "חתיכה דאיסורא"]
- These appear specifically in the issur-application discussion
- The key is finding phrases that distinguish the nuance from the general topic

## LANDMARK SOURCES

For nuance queries, there's usually ONE or TWO sources that are THE famous discussion.
- For bari v'shema beissurin: Rosh on Ketubot 1:18 is THE landmark
- The landmark might be a gemara, rishon, or even acharon depending on the topic

If you know a landmark:
- Set suggested_landmark to the exact ref
- Set landmark_confidence to how sure you are:
  - "high" = you're very confident this is THE source
  - "medium" = you think this is probably it
  - "guessing" = you're not sure but giving a best guess
  - "none" = you don't know a specific landmark

## PRIMARY vs CONTRAST REFS

PRIMARY refs directly discuss the nuance - Step 3 will expand these (fetch commentaries).
CONTRAST refs provide context but don't address the nuance - Step 3 includes them but doesn't expand.

For "bari vishema beissurin":
- PRIMARY: Ketubot 12b (the sugya), Rosh Ketubot 1:18 (the landmark)
- CONTRAST: Bava Kamma 46a (mamon application - shows what bari v'shema looks like WITHOUT issur)

## OUTPUT FORMAT

Return ONLY valid JSON:
```json
{
    "query_type": "topic|nuance|question|source_request|comparison|shittah|sugya|pasuk|halacha|machlokes",
    "foundation_type": "gemara|mishna|chumash|halacha_sa|halacha_rambam|midrash|rishon",
    "breadth": "narrow|standard|wide|exhaustive",
    "trickle_direction": "up|down|both|none",
    
    "is_nuance_query": true,
    "nuance_description": "Whether bari v'shema applies to issurin, not just mamon",
    
    "suggested_landmark": "Rosh on Ketubot 1:18",
    "landmark_confidence": "high|medium|guessing|none",
    "landmark_reasoning": "The Rosh explicitly discusses whether the principle applies in issur contexts",
    
    "focus_terms": ["מותרת", "אסורה", "לאוסרה", "שויא אנפשיה", "חתיכה דאיסורא"],
    "topic_terms": ["ברי ושמא", "ברי עדיף", "ברי", "שמא"],
    
    "primary_refs": [
        {
            "ref": "Ketubot 12b",
            "confidence": "certain",
            "verification_keywords": ["ברי", "שמא", "ברי עדיף"],
            "reasoning": "Main sugya for bari v'shema",
            "buffer_size": 2
        }
    ],
    "contrast_refs": [
        {
            "ref": "Bava Kamma 46a",
            "confidence": "likely",
            "verification_keywords": ["ברי", "שמא", "ממון"],
            "reasoning": "Mamon application - contrast to issur",
            "buffer_size": 1
        }
    ],
    
    "search_variants": {
        "primary_hebrew": ["ברי ושמא", "ברי עדיף"],
        "aramaic_forms": ["ברי עדיף משמא"],
        "gemara_language": ["ברי ושמא ברי עדיף"],
        "root_words": ["ברי", "שמא"],
        "related_terms": ["טענת ברי", "טענת שמא"]
    },
    
    "inyan_description": "Clear explanation of what this query is asking about",
    "target_sources": ["gemara", "rashi", "tosafos", "rosh", "rashba", "ritva"],
    "target_simanim": [],
    "target_chelek": null,
    
    "confidence": "high|medium|low",
    "needs_clarification": false,
    "clarification_question": null,
    "clarification_options": [],
    "reasoning": "Your reasoning process"
}
```

## IMPORTANT RULES

1. **DETECT NUANCE**: If the query has a qualifier (beissurin, b'karka, b'get, l'chumra, etc.), treat as nuance
2. **GIVE SPECIFIC REFS**: Don't say "Ketubot" - say "Ketubot 12b"
3. **LANDMARKS FOR NUANCE**: Try to identify THE famous source for nuance queries
4. **FOCUS TERMS**: These should be phrases that DISTINGUISH the nuance, not generic topic words
5. **SEFARIA SPELLING**: Use Ketubot (not Kesubos), Shabbat (not Shabbos), etc.
6. **HONEST UNCERTAINTY**: If you don't know a landmark, set landmark_confidence="none"
"""


# ==============================================================================
#  HELPER FUNCTIONS
# ==============================================================================

def _load_author_kb():
    """Try to load author detection from torah_authors_master."""
    try:
        from pathlib import Path
        import importlib.util
        
        module_paths = [
            Path(__file__).parent / "tools" / "torah_authors_master.py",
            Path(__file__).parent / "torah_authors_master.py"
        ]
        for mp in module_paths:
            if mp.exists():
                spec = importlib.util.spec_from_file_location("torah_authors_master", mp)
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    return getattr(mod, "is_author", None), getattr(mod, "get_author_matches", None)
    except Exception as e:
        logger.debug(f"Could not load author KB: {e}")
    return None, None


def _parse_enum(value: Any, enum_class, default):
    """Safely parse an enum value."""
    if value is None:
        return default
    try:
        return enum_class(value)
    except (ValueError, KeyError):
        try:
            return enum_class(str(value).lower())
        except:
            return default


def _parse_ref_hint(ref_data: Dict) -> RefHint:
    """Parse a ref hint from Claude's JSON response."""
    return RefHint(
        ref=ref_data.get("ref", ""),
        confidence=_parse_enum(ref_data.get("confidence"), RefConfidence, RefConfidence.POSSIBLE),
        verification_keywords=ref_data.get("verification_keywords", []),
        reasoning=ref_data.get("reasoning", ""),
        buffer_size=ref_data.get("buffer_size", 1),
        is_primary=True
    )


def _parse_search_variants(data: Dict) -> Optional[SearchVariants]:
    """Parse search variants from Claude's response."""
    if not data:
        return None
    return SearchVariants(
        primary_hebrew=data.get("primary_hebrew", []),
        aramaic_forms=data.get("aramaic_forms", []),
        gemara_language=data.get("gemara_language", []),
        root_words=data.get("root_words", []),
        related_terms=data.get("related_terms", [])
    )


# ==============================================================================
#  MAIN ANALYSIS FUNCTION
# ==============================================================================

async def analyze_with_claude(query: str, hebrew_terms: List[str]) -> QueryAnalysis:
    """Have Claude analyze the query with nuance detection."""
    log_section("STEP 2: UNDERSTAND (V4) - Nuance Detection")
    logger.info(f"Query: {query}")
    logger.info(f"Hebrew terms: {hebrew_terms}")
    
    log_subsection("CALLING CLAUDE API")
    
    # Build user prompt
    user_prompt = f"""Analyze this Torah query and tell me EXACTLY where to look.

QUERY: {query}
HEBREW TERMS DETECTED: {hebrew_terms}

Remember:
- DETECT if this is a NUANCE query (specific sub-topic) vs GENERAL topic
- For nuance queries: identify the LANDMARK source and FOCUS TERMS
- Give SPECIFIC refs (e.g., "Ketubot 12b" not just "Ketubot")
- Separate PRIMARY refs (to expand) from CONTRAST refs (for context only)
- If you're not sure about a landmark, set landmark_confidence appropriately

Return ONLY valid JSON."""

    try:
        import time
        start_time = time.time()
        
        client = Anthropic(api_key=settings.anthropic_api_key)
        
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=3000,
            temperature=0,
            system=CLAUDE_SYSTEM_PROMPT_V4,
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
        
        logger.debug(f"Extracted JSON length: {len(json_text)} chars")
        
        try:
            data = json.loads(json_text)
        except json.JSONDecodeError:
            idx = json_text.rfind("}")
            if idx != -1:
                data = json.loads(json_text[:idx+1])
            else:
                raise
        
        logger.info("Parsed JSON successfully")
        logger.debug(f"Keys in response: {list(data.keys())}")
        
        # Parse ref hints from primary_refs and contrast_refs
        ref_hints = []
        primary_refs_list = []
        contrast_refs_list = []
        
        # Parse primary refs
        for ref_data in data.get("primary_refs", []):
            if isinstance(ref_data, dict):
                hint = _parse_ref_hint(ref_data)
                hint.is_primary = True
                ref_hints.append(hint)
                primary_refs_list.append(hint.ref)
            elif isinstance(ref_data, str):
                ref_hints.append(RefHint(ref=ref_data, is_primary=True))
                primary_refs_list.append(ref_data)
        
        # Parse contrast refs
        for ref_data in data.get("contrast_refs", []):
            if isinstance(ref_data, dict):
                hint = _parse_ref_hint(ref_data)
                hint.is_primary = False
                ref_hints.append(hint)
                contrast_refs_list.append(hint.ref)
            elif isinstance(ref_data, str):
                ref_hints.append(RefHint(ref=ref_data, is_primary=False))
                contrast_refs_list.append(ref_data)
        
        # Fallback: if no primary/contrast refs, use suggested_refs
        if not ref_hints:
            for ref_data in data.get("suggested_refs", []):
                if isinstance(ref_data, dict):
                    hint = _parse_ref_hint(ref_data)
                    ref_hints.append(hint)
                    primary_refs_list.append(hint.ref)
                elif isinstance(ref_data, str):
                    ref_hints.append(RefHint(ref=ref_data))
                    primary_refs_list.append(ref_data)
        
        # Build QueryAnalysis
        analysis = QueryAnalysis(
            original_query=query,
            hebrew_terms_from_step1=hebrew_terms,
            
            # Classification
            query_type=_parse_enum(data.get("query_type"), QueryType, QueryType.UNKNOWN),
            foundation_type=_parse_enum(data.get("foundation_type"), FoundationType, FoundationType.UNKNOWN),
            breadth=_parse_enum(data.get("breadth"), Breadth, Breadth.STANDARD),
            trickle_direction=_parse_enum(data.get("trickle_direction"), TrickleDirection, TrickleDirection.UP),
            
            # V4: Nuance detection
            is_nuance_query=data.get("is_nuance_query", False),
            nuance_description=data.get("nuance_description", ""),
            
            # V4: Landmark
            suggested_landmark=data.get("suggested_landmark"),
            landmark_confidence=_parse_enum(data.get("landmark_confidence"), LandmarkConfidence, LandmarkConfidence.NONE),
            landmark_reasoning=data.get("landmark_reasoning", ""),
            
            # V4: Focus vs Topic terms
            focus_terms=data.get("focus_terms", []),
            topic_terms=data.get("topic_terms", []),
            
            # V4: Refs
            ref_hints=ref_hints,
            primary_refs=primary_refs_list,
            contrast_refs=contrast_refs_list,
            suggested_refs=primary_refs_list + contrast_refs_list,  # For backward compatibility
            
            # Search variants
            search_variants=_parse_search_variants(data.get("search_variants", {})),
            inyan_description=data.get("inyan_description", ""),
            search_topics_hebrew=data.get("search_topics_hebrew", hebrew_terms),
            
            # Target sources
            target_sources=data.get("target_sources", ["gemara", "rashi", "tosafos"]),
            target_simanim=data.get("target_simanim", []),
            target_chelek=data.get("target_chelek"),
            
            # Confidence and clarification
            confidence=_parse_enum(data.get("confidence"), ConfidenceLevel, ConfidenceLevel.MEDIUM),
            needs_clarification=data.get("needs_clarification", False),
            clarification_question=data.get("clarification_question"),
            clarification_options=data.get("clarification_options", []),
            reasoning=data.get("reasoning", ""),
        )
        
        # Log results
        log_subsection("ANALYSIS RESULTS")
        _log_analysis_results(analysis)
        
        return analysis
        
    except Exception as e:
        logger.error(f"[UNDERSTAND V4] Claude error: {e}")
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
    
    # V4: Nuance info
    if analysis.is_nuance_query:
        logger.info("")
        logger.info("🎯 NUANCE QUERY DETECTED")
        logger.info(f"  Nuance: {analysis.nuance_description}")
        logger.info(f"  Landmark: {analysis.suggested_landmark} [{analysis.landmark_confidence.value}]")
        if analysis.landmark_reasoning:
            logger.info(f"  Landmark Reason: {analysis.landmark_reasoning[:80]}...")
        logger.info(f"  Focus Terms: {analysis.focus_terms}")
        logger.info(f"  Topic Terms: {analysis.topic_terms}")
    
    # Refs
    if analysis.primary_refs:
        logger.info("")
        logger.info(f"PRIMARY REFS ({len(analysis.primary_refs)}):")
        for hint in analysis.ref_hints:
            if hint.is_primary:
                conf = hint.confidence.value if hasattr(hint.confidence, 'value') else hint.confidence
                logger.info(f"  • {hint.ref} [{conf}]")
                if hint.verification_keywords:
                    logger.info(f"    Keywords: {hint.verification_keywords}")
    
    if analysis.contrast_refs:
        logger.info("")
        logger.info(f"CONTRAST REFS ({len(analysis.contrast_refs)}):")
        for hint in analysis.ref_hints:
            if not hint.is_primary:
                conf = hint.confidence.value if hasattr(hint.confidence, 'value') else hint.confidence
                logger.info(f"  • {hint.ref} [{conf}] (context only)")
    
    # Search variants
    if analysis.search_variants:
        logger.info("")
        logger.info("SEARCH VARIANTS:")
        sv = analysis.search_variants
        if sv.primary_hebrew:
            logger.info(f"  Primary Hebrew: {sv.primary_hebrew}")
        if sv.aramaic_forms:
            logger.info(f"  Aramaic Forms: {sv.aramaic_forms}")
        if sv.gemara_language:
            logger.info(f"  Gemara Language: {sv.gemara_language}")
    
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
    Main entry point for Step 2: UNDERSTAND (V4 with nuance detection).
    
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
        logger.warning("[UNDERSTAND V4] No input provided")
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
    logger.info(f"Landmark: {analysis.suggested_landmark}")
    logger.info(f"Primary refs: {len(analysis.primary_refs)}")
    logger.info(f"Contrast refs: {len(analysis.contrast_refs)}")
    logger.info(f"Needs clarification: {analysis.needs_clarification}")
    
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