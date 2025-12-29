"""
Step 2: UNDERSTAND - The Brain of Ohr Haner (V7 Enhanced)
==========================================================

V7 CHANGES:
1. Better Claude prompting for understanding complex topics
2. Added context about what KIND of search is needed based on topic
3. More detailed reasoning requirements
4. Better handling of multi-concept queries
5. Clearer guidance on when concepts have multiple meanings

The goal: Claude should UNDERSTAND what the user wants, not just keyword-match.
"""

import logging
import json
from typing import Dict, List, Optional, Any, TYPE_CHECKING
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
import importlib.util
import re

from anthropic import Anthropic

# Robust imports
try:
    from models import DecipherResult, ConfidenceLevel
except ImportError:
    # Fallback definitions
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
    # Fallback - use environment variable
    import os
    class Settings:
        anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    settings = Settings()

logger = logging.getLogger(__name__)


# ==============================================================================
#  QUERY ANALYSIS DATATYPE
# ==============================================================================

class QueryType(str, Enum):
    """What kind of query is this?"""
    TOPIC = "topic"
    QUESTION = "question"
    SOURCE_REQUEST = "source_request"
    COMPARISON = "comparison"
    SHITTAH = "shittah"
    SUGYA = "sugya"
    PASUK = "pasuk"
    CHUMASH_SUGYA = "chumash_sugya"
    HALACHA = "halacha"
    MACHLOKES = "machlokes"
    MACHLOKET = "machlokes"  # Alias
    UNKNOWN = "unknown"


class Realm(str, Enum):
    """What realm of Torah is this query about?"""
    CHUMASH = "chumash"
    MISHNAH = "mishnah"
    TANNAIC = "tannaic"
    GEMARA = "gemara"
    YERUSHALMI = "yerushalmi"
    HALACHA = "halacha"
    GENERAL = "general"
    UNKNOWN = "unknown"
    MULTIPLE = "multiple"


class Breadth(str, Enum):
    """How wide should the search be?"""
    NARROW = "narrow"
    STANDARD = "standard"
    WIDE = "wide"
    EXHAUSTIVE = "exhaustive"


class SearchMethod(str, Enum):
    """Which search methodology to use?"""
    TRICKLE_UP = "trickle_up"
    TRICKLE_DOWN = "trickle_down"
    HYBRID = "hybrid"
    DIRECT = "direct"


@dataclass
class SourceCategories:
    """Which categories of sources to include."""
    psukim: bool = False
    mishnayos: bool = False
    tosefta: bool = False
    gemara_bavli: bool = True
    gemara_yerushalmi: bool = False
    midrash: bool = False
    rashi: bool = True
    tosfos: bool = True
    rishonim: bool = False
    rambam: bool = False
    tur: bool = False
    shulchan_aruch: bool = False
    nosei_keilim_rambam: bool = False
    nosei_keilim_tur: bool = False
    nosei_keilim_sa: bool = False
    acharonim: bool = False

    @classmethod
    def from_dict(cls, raw: Any) -> "SourceCategories":
        if isinstance(raw, cls):
            return raw
        if isinstance(raw, dict):
            return cls(**{k: v for k, v in raw.items() if hasattr(cls, k)})
        return cls()


@dataclass
class QueryAnalysis:
    """Complete analysis of a Torah query."""
    original_query: str
    hebrew_terms_from_step1: Any = None
    
    query_type: QueryType = QueryType.UNKNOWN
    realm: Realm = Realm.UNKNOWN
    breadth: Breadth = Breadth.STANDARD
    search_method: SearchMethod = SearchMethod.HYBRID
    
    search_topics: List[str] = field(default_factory=list)
    search_topics_hebrew: List[str] = field(default_factory=list)
    
    # V7: Add conceptual understanding fields
    inyan_description: str = ""  # What is this inyan about?
    related_concepts: List[str] = field(default_factory=list)  # Related ideas to search
    potential_masechtos: List[str] = field(default_factory=list)  # Where might this appear?
    
    target_masechtos: List[str] = field(default_factory=list)
    target_perakim: List[str] = field(default_factory=list)
    target_dapim: List[str] = field(default_factory=list)
    target_simanim: List[str] = field(default_factory=list)
    target_sefarim: List[str] = field(default_factory=list)
    target_refs: List[str] = field(default_factory=list)
    target_authors: List[str] = field(default_factory=list)
    
    source_categories: SourceCategories = field(default_factory=SourceCategories)
    
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    needs_clarification: bool = False
    clarification_question: Optional[str] = None
    clarification_options: List[str] = field(default_factory=list)
    
    reasoning: str = ""
    search_description: str = ""


# ==============================================================================
#  HELPER FUNCTIONS
# ==============================================================================

def _load_author_kb():
    """Try to load is_author / get_author_matches from torah_authors_master."""
    is_author = None
    get_author_matches = None

    try:
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
                    is_author = getattr(mod, "is_author", None)
                    get_author_matches = getattr(mod, "get_author_matches", None)
                    break
    except Exception as e:
        logger.debug(f"Could not load author KB: {e}")

    return is_author, get_author_matches


_META_TERMS = {"את", "על", "של", "עם", "או", "אל", "לא", "כי", "כל", "זה", "זו", "אם"}


def _is_meta_term(t: str) -> bool:
    return t in _META_TERMS or len(t) <= 1


def _split_terms_into_topics_and_authors(hebrew_terms: List[str]) -> tuple:
    """Split terms into topics (the INYAN) and authors (whose commentary)."""
    is_author, get_author_matches = _load_author_kb()

    topics: List[str] = []
    authors: List[str] = []
    
    for t in hebrew_terms:
        t = str(t).strip()
        if not t or _is_meta_term(t):
            continue

        is_auth = False
        if callable(is_author):
            try:
                is_auth = bool(is_author(t))
            except Exception:
                pass

        if is_auth:
            en = None
            if callable(get_author_matches):
                try:
                    matches = get_author_matches(t) or []
                    if matches:
                        en = matches[0].get("primary_name_en")
                except Exception:
                    pass
            authors.append(en or t)
        else:
            topics.append(t)

    def dedup(seq):
        seen = set()
        return [x for x in seq if not (x in seen or seen.add(x))]

    return dedup(topics), dedup(authors)


# ==============================================================================
#  CLAUDE ANALYSIS (V7 Enhanced)
# ==============================================================================

# V7: Much more detailed system prompt with conceptual understanding
CLAUDE_SYSTEM_PROMPT_V7 = """You are an expert Torah learning assistant analyzing user queries for Ohr Haner, a marei mekomos (source finding) system.

YOUR ROLE:
You are like a knowledgeable chavrusa who understands what the user is REALLY looking for, not just matching keywords. Your job is to create a search plan that will find the right sources.

STEP-BY-STEP ANALYSIS:

1. UNDERSTAND THE INYAN (Concept)
   - What is the user actually asking about?
   - Is this a specific halachic concept, a sugya, a comparison, or something else?
   - Are there multiple meanings of the same word? (e.g., "חזקה" can mean many things)

2. IDENTIFY THE TYPE
   - topic: General exploration of a concept
   - comparison: Comparing two or more shittos/approaches
   - machlokes: Looking for disagreements
   - shittah: One specific author's view
   - sugya: Full sugya with all components
   - halacha: Practical halachic ruling
   - pasuk: Chumash-related
   - source_request: Specific source lookup

3. DETERMINE WHERE TO LOOK
   Think about which masechtos would logically discuss this topic:
   - Monetary law → Bava Kamma, Bava Metzia, Bava Batra, Choshen Mishpat
   - Marriage/divorce → Ketubot, Kiddushin, Gittin, Even HaEzer, Ishut/Ishus
   - Holidays → Shabbat, Eruvin, Psachim, Orach Chaim, Zmanim
   - Kashrus → Chullin, Zvachim, Yoreh Deah
   - etc.

4. CHOOSE SEARCH METHOD
   - trickle_down: For complex queries, comparisons, conceptual questions
     * Search Shulchan Aruch, Tur, and Rambam with nosei keilim and other Achronim (Mishnah Berurah, Ketzos, Nesivos, etc.) first
     * They cite the relevant gemaras, and Rishonim, helping us find the right dapim
     * USE THIS for multi-concept queries like "chezkas haguf vs chezkas mammon"
   
   - trickle_up: For simple, single-topic queries
     * Start from pasuk/mishna/gemara and work up
     * Good for direct lookups
   
   - direct: When user gives specific location
   - hybrid: can use each to confirm

IMPORTANT WARNINGS:

1. MULTIPLE MEANINGS: Many Torah terms have multiple meanings in different contexts!
    For example but absolutley not limited too...
   - "חזקה" could mean:
     * חזקת הגוף (bodily/status presumption)
     * חזקת ממון (monetary possession presumption)  
     * חזקה של ג' שנים (3-year land possession)
     * חזקת כשרות (presumption of observance)
   - Make sure you identify WHICH meaning the user wants!

2. TOPIC vs AUTHOR: 
   - search_topics = the CONCEPT being discussed (never put author names here)
   - target_authors = whose COMMENTARY to fetch

3. BE COMPREHENSIVE:
   - If a topic could appear in multiple masechtos, list them all
   - Don't guess too narrowly - let the search find the right places

4. SEFARIA SPELLING (CRITICAL):
   Use Sefaria's EXACT masechta spellings in all output fields (target_masechtos, potential_masechtos, target_dapim, reasoning):
   - Ketubot (NOT Kesubos)
   - Shabbat (NOT Shabbos)  
   - Berakhot (NOT Berachos)
   - Yevamot (NOT Yevamos)
   - Bava Batra (NOT Bava Basra)
   - Makkot (NOT Makkos)
   - Shevuot (NOT Shevuos)
   - Horayot (NOT Horayos)
   - Menachot (NOT Menachos)
   - Bekhorot (NOT Bechoros)
   - Keritot (NOT Kerisos)
   - Taanit (NOT Taanis)
   - Chullin, Gittin, Kiddushin, Sanhedrin, Nazir, Sotah are spelled correctly as-is

OUTPUT FORMAT:
Return a JSON object with:
{
    "query_type": "comparison|topic|shittah|sugya|halacha|pasuk|machlokes|source_request",
    "realm": "gemara|chumash|mishnah|halacha|general",
    "breadth": "narrow|standard|wide|exhaustive",
    "search_method": "trickle_down|trickle_up|hybrid|direct",
    
    "inyan_description": "A clear description of what this inyan is about",
    "search_topics": ["English topic 1", "English topic 2"],
    "search_topics_hebrew": ["Hebrew topic 1", "Hebrew topic 2"],
    "related_concepts": ["Related concept that might help find sources"],
    
    "potential_masechtos": ["Where this topic would logically appear"],
    "target_masechtos": ["Specific masechtos to search"],
    "target_dapim": [],
    "target_simanim": [],
    "target_authors": ["Whose commentary to fetch"],
    
    "reasoning": "Detailed explanation of your understanding and search strategy",
    "confidence": "high|medium|low",
    "needs_clarification": false,
    "clarification_question": null
}

EXAMPLES:

Query: "chezkas haguf chezkas mammon"
{
    "query_type": "comparison",
    "realm": "gemara",
    "breadth": "wide",
    "search_method": "trickle_down",
    "inyan_description": "The distinction between chezkas haguf (presumption about a person's status, like assuming someone is alive or a woman hasn't given birth) and chezkas mammon (presumption favoring the current possessor of money/property). This is a fundamental concept in dinei mamonos.",
    "search_topics": ["chezkas haguf", "chezkas mammon", "types of chazakah in monetary law"],
    "search_topics_hebrew": ["חזקת הגוף", "חזקת ממון", "חזקה"],
    "related_concepts": ["המוציא מחבירו עליו הראיה", "ספק ממון", "אוקי ממונא בחזקתיה"],
    "potential_masechtos": ["Ketubot", "Bava Kamma", "Bava Batra", "Bava Metzia", "Sanhedrin"],
    "target_masechtos": ["Ketubot", "Bava Kamma", "Bava Batra"],
    "target_dapim": [],
    "target_simanim": [],
    "target_authors": ["Rashi", "Tosafos", "Ketzos HaChoshen", "Nesivos HaMishpat"],
    "reasoning": "This is a conceptual comparison between two fundamental types of presumption in monetary law. Ketubot discusses this in the context of marriage claims (12a, 75a), Bava Kamma in the context of damages (46a - shor tam). Using trickle_down because achronim like Ketzos systematically analyze these categories and will point us to the right gemaras.",
    "confidence": "high",
    "needs_clarification": false
}

Query: "migu"
{
    "query_type": "topic",
    "realm": "gemara",
    "breadth": "standard",
    "search_method": "trickle_down",
    "inyan_description": "The concept of migu - 'since he could have made a better claim, we believe his current claim'. A fundamental principle in monetary and testimony law.",
    "search_topics": ["migu"],
    "search_topics_hebrew": ["מיגו"],
    "related_concepts": ["נאמנות", "טענה", "פה שאסר"],
    "potential_masechtos": ["Ketubot", "Bava Kamma", "Bava Metzia", "Bava Batra", "Kiddushin"],
    "target_masechtos": ["Ketubot", "Bava Kamma", "Bava Metzia"],
    "target_dapim": [],
    "target_authors": ["Rashi", "Tosafos", "Ketzos"],
    "reasoning": "Single-topic query about a fundamental gemara concept. Trickle-down will help find the main sugyos where migu is discussed via the nosei keilim.",
    "confidence": "high"
}

Query: "show me rashi on pesachim 4b"
{
    "query_type": "source_request",
    "realm": "gemara",
    "search_method": "direct",
    "inyan_description": "Direct request for Rashi's commentary on a specific daf",
    "search_topics": [],
    "search_topics_hebrew": [],
    "target_masechtos": ["Pesachim"],
    "target_dapim": ["4b"],
    "target_authors": ["Rashi"],
    "reasoning": "User specified exact location - fetch directly",
    "confidence": "high"
}

Return ONLY valid JSON, no markdown code blocks."""


async def analyze_with_claude(query: str, hebrew_terms: List[str]) -> QueryAnalysis:
    """V7: Have Claude analyze the query with deeper understanding."""
    logger.info("[UNDERSTAND V7] Sending query to Claude for analysis")
    
    # Pre-split terms for context
    topics_hebrew, authors = _split_terms_into_topics_and_authors(hebrew_terms)
    
    user_prompt = f"""Analyze this Torah query:

QUERY: {query}
HEBREW TERMS (from Step 1): {hebrew_terms}
EXTRACTED TOPICS: {topics_hebrew}
DETECTED AUTHORS: {authors}

Create a comprehensive search plan. Focus on:
1. What is the user REALLY looking for? (not just keywords)
2. Which masechtos would logically discuss this?
3. Are there multiple meanings of these terms?

Return ONLY valid JSON matching the format in the system prompt."""

    def _parse_confidence(value: Any) -> ConfidenceLevel:
        try:
            return ConfidenceLevel(value)
        except Exception:
            try:
                return ConfidenceLevel(str(value).lower())
            except Exception:
                return ConfidenceLevel.MEDIUM

    try:
        client = Anthropic(api_key=settings.anthropic_api_key)
        
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2500,
            temperature=0,
            system=CLAUDE_SYSTEM_PROMPT_V7,
            messages=[{"role": "user", "content": user_prompt}]
        )
        
        raw_text = response.content[0].text.strip()
        logger.info(f"[UNDERSTAND V7] Claude raw response:\n{raw_text}")
        
        # Parse JSON from response
        json_text = raw_text
        if "```json" in raw_text:
            json_text = raw_text.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_text:
            json_text = raw_text.split("```")[1].split("```")[0].strip()
        
        # Progressive trimming for JSON parsing
        parsed_data = None
        attempts = [json_text]
        
        # Try removing trailing content after last }
        idx = json_text.rfind("}")
        if idx != -1:
            attempts.append(json_text[:idx+1])
        
        for attempt in attempts:
            try:
                parsed_data = json.loads(attempt)
                break
            except json.JSONDecodeError:
                continue
        
        if not parsed_data:
            logger.error(f"[UNDERSTAND V7] Failed to parse JSON: {raw_text[:200]}")
            return _build_fallback_analysis(query, hebrew_terms, topics_hebrew, authors)
        
        logger.info(f"[UNDERSTAND V7] Claude parsed JSON:\n{json.dumps(parsed_data, indent=2, ensure_ascii=False)}")
        
        # Build QueryAnalysis from parsed data
        query_type_str = parsed_data.get("query_type", "unknown")
        realm_str = parsed_data.get("realm", "gemara")
        method_str = parsed_data.get("search_method", "trickle_down")
        
        # Parse enums safely
        try:
            query_type = QueryType(query_type_str)
        except ValueError:
            query_type = QueryType.UNKNOWN
        
        try:
            realm = Realm(realm_str)
        except ValueError:
            realm = Realm.GEMARA
        
        try:
            search_method = SearchMethod(method_str)
        except ValueError:
            search_method = SearchMethod.TRICKLE_DOWN
        
        # Build source categories
        cats = SourceCategories()
        if realm == Realm.GEMARA:
            cats.gemara_bavli = True
            cats.rashi = True
            cats.tosfos = True
        if query_type in [QueryType.COMPARISON, QueryType.MACHLOKES, QueryType.SUGYA]:
            cats.rishonim = True
        
        analysis = QueryAnalysis(
            original_query=query,
            hebrew_terms_from_step1=hebrew_terms,
            query_type=query_type,
            realm=realm,
            breadth=Breadth(parsed_data.get("breadth", "standard")),
            search_method=search_method,
            search_topics=parsed_data.get("search_topics", []),
            search_topics_hebrew=parsed_data.get("search_topics_hebrew", topics_hebrew),
            inyan_description=parsed_data.get("inyan_description", ""),
            related_concepts=parsed_data.get("related_concepts", []),
            potential_masechtos=parsed_data.get("potential_masechtos", []),
            target_masechtos=parsed_data.get("target_masechtos", []),
            target_perakim=parsed_data.get("target_perakim", []),
            target_dapim=parsed_data.get("target_dapim", []),
            target_simanim=parsed_data.get("target_simanim", []),
            target_sefarim=parsed_data.get("target_sefarim", []),
            target_refs=parsed_data.get("target_refs", []),
            target_authors=parsed_data.get("target_authors", authors) or authors,
            source_categories=cats,
            confidence=_parse_confidence(parsed_data.get("confidence", "medium")),
            needs_clarification=parsed_data.get("needs_clarification", False),
            clarification_question=parsed_data.get("clarification_question"),
            clarification_options=parsed_data.get("clarification_options", []),
            reasoning=parsed_data.get("reasoning", ""),
            search_description=parsed_data.get("search_description", ""),
        )
        
        logger.info(f"[UNDERSTAND V7] Final QueryAnalysis:")
        logger.info(f"  INYAN: {analysis.inyan_description[:100]}..." if analysis.inyan_description else "  INYAN: (none)")
        logger.info(f"  TOPICS: {analysis.search_topics_hebrew}")
        logger.info(f"  WHERE: {analysis.target_masechtos or analysis.potential_masechtos}")
        logger.info(f"  WHOSE: {analysis.target_authors}")
        logger.info(f"  METHOD: {analysis.search_method}")
        logger.info(f"  REASONING: {analysis.reasoning[:150]}...")
        
        return analysis
        
    except Exception as e:
        logger.error(f"[UNDERSTAND V7] Claude error: {e}")
        return _build_fallback_analysis(query, hebrew_terms, topics_hebrew, authors)


def _build_fallback_analysis(
    query: str,
    hebrew_terms: List[str],
    topics_hebrew: List[str],
    authors: List[str]
) -> QueryAnalysis:
    """Build a fallback analysis when Claude fails."""
    logger.warning("[UNDERSTAND V7] Using fallback analysis")
    
    return QueryAnalysis(
        original_query=query,
        hebrew_terms_from_step1=hebrew_terms,
        query_type=QueryType.TOPIC,
        realm=Realm.GEMARA,
        search_method=SearchMethod.TRICKLE_DOWN,
        search_topics_hebrew=topics_hebrew,
        target_authors=authors if authors else ["Rashi", "Tosafos"],
        confidence=ConfidenceLevel.LOW,
        reasoning="Fallback analysis - Claude unavailable",
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
    Main entry point for Step 2: UNDERSTAND.
    
    Args:
        hebrew_terms: List of Hebrew terms from Step 1
        query: Original query string
        decipher_result: Optional DecipherResult from Step 1
    """
    # Handle different calling conventions
    if decipher_result is not None:
        if hebrew_terms is None:
            hebrew_terms = decipher_result.hebrew_terms or []
            if hasattr(decipher_result, 'hebrew_term') and decipher_result.hebrew_term:
                if decipher_result.hebrew_term not in hebrew_terms:
                    hebrew_terms = [decipher_result.hebrew_term] + list(hebrew_terms)
        
        if query is None and hasattr(decipher_result, 'original_query'):
            query = decipher_result.original_query
    
    # Ensure we have lists
    if hebrew_terms is None:
        hebrew_terms = []
    if not isinstance(hebrew_terms, list):
        hebrew_terms = list(hebrew_terms)
    
    # Validation
    if not hebrew_terms:
        logger.warning("[UNDERSTAND V7] No Hebrew terms provided")
        return QueryAnalysis(
            original_query=query or "",
            hebrew_terms_from_step1=[],
            query_type=QueryType.UNKNOWN,
            realm=Realm.UNKNOWN,
            breadth=Breadth.STANDARD,
            search_method=SearchMethod.HYBRID,
            source_categories=SourceCategories(),
            confidence=ConfidenceLevel.LOW,
            needs_clarification=True,
            clarification_question="I couldn't identify Hebrew terms. What topic are you looking for?",
            reasoning="No Hebrew terms from Step 1"
        )
    
    if not query:
        query = " ".join(hebrew_terms)
    
    logger.info("=" * 70)
    logger.info("[STEP 2: UNDERSTAND V7] Analyzing query")
    logger.info(f"  Query: {query}")
    logger.info(f"  Hebrew terms: {hebrew_terms}")
    logger.info("=" * 70)
    
    analysis = await analyze_with_claude(query, hebrew_terms)
    
    logger.info("=" * 70)
    logger.info("[STEP 2: UNDERSTAND V7] Complete")
    logger.info(f"  Type: {analysis.query_type}")
    logger.info(f"  Inyan: {analysis.inyan_description[:80]}..." if analysis.inyan_description else "  Inyan: (none)")
    logger.info(f"  Topics: {analysis.search_topics_hebrew}")
    logger.info(f"  Method: {analysis.search_method}")
    logger.info(f"  Confidence: {analysis.confidence}")
    logger.info("=" * 70)
    
    return analysis


# Aliases for compatibility
run_step_two = understand


__all__ = [
    'understand',
    'analyze_with_claude',
    'QueryAnalysis',
    'QueryType',
    'Realm',
    'Breadth',
    'SearchMethod',
    'SourceCategories',
]