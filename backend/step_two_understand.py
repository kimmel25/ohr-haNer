"""
Step 2: UNDERSTAND - V2 Complete Rewrite
=========================================

V2 PHILOSOPHY:
Claude is the brain. We trust Claude to identify specific refs, not just masechtos.
If Claude doesn't know, it says so and we ask for clarification.

KEY CHANGES FROM V1:
1. Claude outputs SPECIFIC REFS (e.g., "Ketubot 12b") not just masechtos
2. Claude specifies exactly which commentaries user wants
3. Claude indicates foundation type (gemara/mishna/chumash/halacha)
4. Claude specifies trickle direction (up for commentaries, down for earlier sources)
5. If Claude is unsure, it MUST say needs_clarification=True

OUTPUT FLOW:
- suggested_refs: ["Ketubot 12b", "Bava Kamma 46b"] - Claude's best guesses
- foundation_type: "gemara" | "mishna" | "chumash" | "halacha" | "midrash"
- target_sources: ["gemara", "rashi", "tosafos", "ran", "ketzos"] - exactly what to fetch
- trickle_direction: "up" | "down" | "both" | "none"
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
    # Fallback to basic logging
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
    TOPIC = "topic"                    # General exploration
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
    HALACHA_SA = "halacha_sa"         # Shulchan Aruch based
    HALACHA_RAMBAM = "halacha_rambam" # Rambam based
    MIDRASH = "midrash"
    UNKNOWN = "unknown"


class TrickleDirection(str, Enum):
    """Which direction to fetch sources?"""
    UP = "up"       # Get later sources (commentaries on the foundation)
    DOWN = "down"   # Get earlier sources (what the foundation is based on)
    BOTH = "both"   # Both directions
    NONE = "none"   # Just the foundation, no trickle


class Breadth(str, Enum):
    """How wide should the search be?"""
    NARROW = "narrow"       # Just main sugya
    STANDARD = "standard"   # Main sugya + key related
    WIDE = "wide"           # Multiple sugyos
    EXHAUSTIVE = "exhaustive"  # Everything


# ==============================================================================
#  DATA STRUCTURES
# ==============================================================================

@dataclass
class QueryAnalysis:
    """Complete analysis of a Torah query - V2."""
    original_query: str
    hebrew_terms_from_step1: List[str] = field(default_factory=list)
    
    # Classification
    query_type: QueryType = QueryType.UNKNOWN
    foundation_type: FoundationType = FoundationType.UNKNOWN
    breadth: Breadth = Breadth.STANDARD
    trickle_direction: TrickleDirection = TrickleDirection.UP
    
    # THE KEY OUTPUT: Specific refs Claude thinks are relevant
    suggested_refs: List[str] = field(default_factory=list)
    
    # What Claude understands about the query
    inyan_description: str = ""
    search_topics_hebrew: List[str] = field(default_factory=list)
    
    # Exactly which sources to fetch
    target_sources: List[str] = field(default_factory=list)
    # e.g., ["gemara", "rashi", "tosafos", "ran", "rashba", "ritva", "rambam", "ketzos"]
    
    # For halacha queries
    target_simanim: List[str] = field(default_factory=list)
    
    # Confidence and clarification
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    needs_clarification: bool = False
    clarification_question: Optional[str] = None
    clarification_options: List[str] = field(default_factory=list)
    
    # Claude's reasoning
    reasoning: str = ""


# ==============================================================================
#  CLAUDE SYSTEM PROMPT - V2
# ==============================================================================

CLAUDE_SYSTEM_PROMPT_V2 = """You are an expert Torah learning assistant for Ohr Haner, a marei mekomos (source finder) system.

YOUR JOB: Understand what the user wants and tell us EXACTLY where to look.

## CRITICAL RULES

1. **GIVE SPECIFIC REFS**: Don't say "Ketubot" - say "Ketubot 12b". Don't say "Bava Kamma" - say "Bava Kamma 46a".
   If you know the daf, give it. If you're not 100% sure but have a good idea, give your best guess.
   We will verify your guess - it's better to guess than to be vague.

2. **BE HONEST ABOUT UNCERTAINTY**: If you truly don't know where something is discussed, set needs_clarification=true.
   Don't make up random refs. But if you have a reasonable guess, give it.

3. **UNDERSTAND THE QUERY TYPE**:
   - "migu" → topic exploration, gemara-based, wants rishonim
   - "chezkas haguf vs chezkas mammon" → comparison, wants to see both concepts
   - "show me rashi on pesachim 4b" → direct source request
   - "where does the mechaber discuss X" → halacha query
   - "peirushim on bereishis 1:1" → chumash query

4. **SPECIFY EXACTLY WHAT TO FETCH**:
   The target_sources list should contain exactly what the user wants:
   - For a basic gemara query: ["gemara", "rashi", "tosafos"]
   - For rishonim exploration: ["gemara", "rashi", "tosafos", "ran", "rashba", "ritva", "ramban"]
   - For halacha with acharonim: ["shulchan_aruch", "mishnah_berurah", "taz", "magen_avraham"]
   - For a comparison: Include the specific meforshim who discuss the comparison

5. **SEFARIA SPELLING**: Use Sefaria's exact spellings:
   - Ketubot (not Kesubos)
   - Shabbat (not Shabbos)
   - Berakhot (not Berachos)
   - Bava Batra (not Basra)
   - etc.

## OUTPUT FORMAT

Return ONLY valid JSON:
{
    "query_type": "topic|question|source_request|comparison|shittah|sugya|pasuk|chumash_sugya|halacha|machlokes",
    "foundation_type": "gemara|mishna|chumash|halacha_sa|halacha_rambam|midrash",
    "breadth": "narrow|standard|wide|exhaustive",
    "trickle_direction": "up|down|both|none",
    
    "suggested_refs": ["Ketubot 12b", "Bava Kamma 46a"],
    
    "inyan_description": "Clear explanation of what this topic is about",
    "search_topics_hebrew": ["חזקת הגוף", "חזקת ממון"],
    
    "target_sources": ["gemara", "rashi", "tosafos", "ran", "ketzos"],
    "target_simanim": [],
    
    "confidence": "high|medium|low",
    "needs_clarification": false,
    "clarification_question": null,
    "clarification_options": [],
    
    "reasoning": "Detailed explanation of why you chose these refs and sources"
}

## EXAMPLES

### Example 1: Topic Query
Query: "migu"
{
    "query_type": "topic",
    "foundation_type": "gemara",
    "breadth": "standard",
    "trickle_direction": "up",
    "suggested_refs": ["Ketubot 12b", "Bava Metzia 3a", "Bava Kamma 46a", "Kiddushin 43a"],
    "inyan_description": "The concept of migu - since he could have made a better claim, we believe his current claim",
    "search_topics_hebrew": ["מיגו"],
    "target_sources": ["gemara", "rashi", "tosafos", "ran", "rashba"],
    "confidence": "high",
    "needs_clarification": false,
    "reasoning": "Migu is discussed in several key sugyos. Ketubot 12b is the classic case with the 'pesach pasuach' migu. BM 3a discusses migu lhotzi. BK 46a has the case of the ox. These are the main sugyos - user probably wants basic rishonim."
}

### Example 2: Comparison Query
Query: "chezkas haguf vs chezkas mammon"
{
    "query_type": "comparison",
    "foundation_type": "gemara",
    "breadth": "wide",
    "trickle_direction": "up",
    "suggested_refs": ["Ketubot 12b", "Ketubot 75b-76a", "Bava Kamma 46b"],
    "inyan_description": "The fundamental distinction between chezkas haguf (bodily/status presumption) and chezkas mammon (monetary possession presumption)",
    "search_topics_hebrew": ["חזקת הגוף", "חזקת ממון"],
    "target_sources": ["gemara", "rashi", "tosafos", "rashba", "ritva", "ketzos", "nesivos"],
    "confidence": "high",
    "needs_clarification": false,
    "reasoning": "Ketubot 12b discusses the classic case where chezkas haguf conflicts with chezkas mammon regarding a woman's virginity claim. Ketubot 75b-76a discusses mum claims. BK 46b has the shor tam case. The Ketzos and Nesivos have famous discussions on this topic."
}

### Example 3: Direct Source Request
Query: "show me rashi on pesachim 4b"
{
    "query_type": "source_request",
    "foundation_type": "gemara",
    "breadth": "narrow",
    "trickle_direction": "none",
    "suggested_refs": ["Pesachim 4b"],
    "inyan_description": "Direct request for Rashi on Pesachim 4b",
    "search_topics_hebrew": [],
    "target_sources": ["gemara", "rashi"],
    "confidence": "high",
    "needs_clarification": false,
    "reasoning": "User explicitly requested Rashi on Pesachim 4b. Direct fetch."
}

### Example 4: Halacha Query
Query: "hilchos carrying on shabbos"
{
    "query_type": "halacha",
    "foundation_type": "halacha_sa",
    "breadth": "wide",
    "trickle_direction": "both",
    "suggested_refs": ["Shulchan Arukh, Orach Chaim 301", "Shulchan Arukh, Orach Chaim 308", "Shabbat 96b", "Shabbat 73b"],
    "inyan_description": "Laws of carrying on Shabbos - hotza'ah melacha",
    "search_topics_hebrew": ["הוצאה", "טלטול", "רשויות"],
    "target_sources": ["shulchan_aruch", "mishnah_berurah", "gemara", "rashi"],
    "target_simanim": ["301", "308", "345-346"],
    "confidence": "medium",
    "needs_clarification": false,
    "reasoning": "Carrying on Shabbos is spread across many simanim in OC. Main simanim are 301 (general), 308 (muktza related), 345-346 (reshuyos). Gemara sources in Shabbat perek HaZoreik."
}

### Example 5: Uncertain - Needs Clarification
Query: "the shittah about the thing with the food"
{
    "query_type": "unknown",
    "foundation_type": "unknown",
    "breadth": "standard",
    "trickle_direction": "up",
    "suggested_refs": [],
    "inyan_description": "",
    "search_topics_hebrew": [],
    "target_sources": [],
    "confidence": "low",
    "needs_clarification": true,
    "clarification_question": "I need more information to help you. Could you tell me:",
    "clarification_options": [
        "Which topic area? (Shabbos, Kashrus, Monetary law, etc.)",
        "Which specific concept about food?",
        "Whose shittah are you looking for?"
    ],
    "reasoning": "Query is too vague. Could be about brachos, kashrus, maaser, etc. Need clarification."
}

### Example 6: Chumash Query  
Query: "meforshim on bereishis 1:1"
{
    "query_type": "pasuk",
    "foundation_type": "chumash",
    "breadth": "standard",
    "trickle_direction": "up",
    "suggested_refs": ["Genesis 1:1"],
    "inyan_description": "Commentaries on the first verse of the Torah",
    "search_topics_hebrew": ["בראשית"],
    "target_sources": ["chumash", "rashi", "ramban", "ibn_ezra", "sforno", "ohr_hachaim"],
    "confidence": "high",
    "needs_clarification": false,
    "reasoning": "Direct pasuk request. User wants standard chumash meforshim."
}

Return ONLY the JSON, no markdown code blocks or extra text."""


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


# ==============================================================================
#  MAIN ANALYSIS FUNCTION
# ==============================================================================

async def analyze_with_claude(query: str, hebrew_terms: List[str]) -> QueryAnalysis:
    """Have Claude analyze the query and return specific refs."""
    logger.info("[UNDERSTAND V2] Sending query to Claude")
    
    # Build user prompt
    user_prompt = f"""Analyze this Torah query and tell me EXACTLY where to look.

QUERY: {query}
HEBREW TERMS DETECTED: {hebrew_terms}

Remember:
- Give SPECIFIC refs (e.g., "Ketubot 12b" not just "Ketubot")
- If you're not sure, give your best guess - we'll verify
- If you truly don't know, set needs_clarification=true
- List exactly which meforshim/sources to fetch in target_sources

Return ONLY valid JSON."""

    try:
        client = Anthropic(api_key=settings.anthropic_api_key)
        
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2000,
            temperature=0,
            system=CLAUDE_SYSTEM_PROMPT_V2,
            messages=[{"role": "user", "content": user_prompt}]
        )
        
        raw_text = response.content[0].text.strip()
        logger.info(f"[UNDERSTAND V2] Claude response:\n{raw_text}")
        
        # Parse JSON
        json_text = raw_text
        if "```json" in raw_text:
            json_text = raw_text.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_text:
            json_text = raw_text.split("```")[1].split("```")[0].strip()
        
        # Try to parse
        try:
            data = json.loads(json_text)
        except json.JSONDecodeError:
            # Try trimming after last }
            idx = json_text.rfind("}")
            if idx != -1:
                data = json.loads(json_text[:idx+1])
            else:
                raise
        
        # Build QueryAnalysis
        analysis = QueryAnalysis(
            original_query=query,
            hebrew_terms_from_step1=hebrew_terms,
            query_type=_parse_enum(data.get("query_type"), QueryType, QueryType.UNKNOWN),
            foundation_type=_parse_enum(data.get("foundation_type"), FoundationType, FoundationType.UNKNOWN),
            breadth=_parse_enum(data.get("breadth"), Breadth, Breadth.STANDARD),
            trickle_direction=_parse_enum(data.get("trickle_direction"), TrickleDirection, TrickleDirection.UP),
            suggested_refs=data.get("suggested_refs", []),
            inyan_description=data.get("inyan_description", ""),
            search_topics_hebrew=data.get("search_topics_hebrew", hebrew_terms),
            target_sources=data.get("target_sources", ["gemara", "rashi", "tosafos"]),
            target_simanim=data.get("target_simanim", []),
            confidence=_parse_enum(data.get("confidence"), ConfidenceLevel, ConfidenceLevel.MEDIUM),
            needs_clarification=data.get("needs_clarification", False),
            clarification_question=data.get("clarification_question"),
            clarification_options=data.get("clarification_options", []),
            reasoning=data.get("reasoning", ""),
        )
        
        logger.info(f"[UNDERSTAND V2] Analysis complete:")
        logger.info(f"  Type: {analysis.query_type}")
        logger.info(f"  Foundation: {analysis.foundation_type}")
        logger.info(f"  Suggested refs: {analysis.suggested_refs}")
        logger.info(f"  Target sources: {analysis.target_sources}")
        logger.info(f"  Confidence: {analysis.confidence}")
        
        return analysis
        
    except Exception as e:
        logger.error(f"[UNDERSTAND V2] Claude error: {e}")
        return QueryAnalysis(
            original_query=query,
            hebrew_terms_from_step1=hebrew_terms,
            query_type=QueryType.UNKNOWN,
            confidence=ConfidenceLevel.LOW,
            needs_clarification=True,
            clarification_question="I encountered an error analyzing your query. Could you rephrase it?",
            reasoning=f"Error: {e}"
        )


# ==============================================================================
#  MAIN ENTRY POINT
# ==============================================================================

async def understand(
    hebrew_terms: List[str] = None,
    query: str = None,
    decipher_result: "DecipherResult" = None
) -> QueryAnalysis:
    """
    Main entry point for Step 2: UNDERSTAND (V2).
    
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
        logger.warning("[UNDERSTAND V2] No input provided")
        return QueryAnalysis(
            original_query="",
            confidence=ConfidenceLevel.LOW,
            needs_clarification=True,
            clarification_question="What topic would you like to explore?",
        )
    
    if not query:
        query = " ".join(hebrew_terms)
    
    logger.info("=" * 70)
    logger.info("[STEP 2: UNDERSTAND V2]")
    logger.info(f"  Query: {query}")
    logger.info(f"  Hebrew terms: {hebrew_terms}")
    logger.info("=" * 70)
    
    analysis = await analyze_with_claude(query, hebrew_terms)
    
    logger.info("=" * 70)
    logger.info("[STEP 2 COMPLETE]")
    logger.info(f"  Suggested refs: {analysis.suggested_refs}")
    logger.info(f"  Needs clarification: {analysis.needs_clarification}")
    logger.info("=" * 70)
    
    return analysis


# Aliases
run_step_two = understand


__all__ = [
    'understand',
    'run_step_two',
    'analyze_with_claude',
    'QueryAnalysis',
    'QueryType',
    'FoundationType',
    'TrickleDirection',
    'Breadth',
    'ConfidenceLevel',
]