"""
Step 2: UNDERSTAND - The Brain of Ohr Haner (V6 Enhanced)
==========================================================

V6 CHANGES:
1. Updated search method selection - comparison/shittah/machlokes queries use trickle_down
2. Fixed parameter naming consistency with console_full_pipeline.py
3. Better Claude prompting for search method selection

Claude analyzes the query and creates a detailed "datatype" that tells Step 3:
- WHERE to look (which masechtos)
- WHAT to search for (the inyan/topic - NOT author names)
- WHICH commentaries to fetch (based on authors mentioned)
- HOW to search (trickle-up vs trickle-down)
"""

import logging
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
import importlib.util
import re

from anthropic import Anthropic

from models import DecipherResult, ConfidenceLevel
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


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
    try:
        from torah_authors_master import is_author, get_author_matches
        return is_author, get_author_matches
    except Exception:
        try:
            here = Path(__file__).resolve().parent
            path = here / "torah_authors_master.py"
            if not path.exists():
                return None, None
            spec = importlib.util.spec_from_file_location("_torah_authors", str(path))
            if spec is None or spec.loader is None:
                return None, None
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return getattr(mod, "is_author", None), getattr(mod, "get_author_matches", None)
        except Exception:
            return None, None


def _is_meta_term(term: str) -> bool:
    """Check if term is a meta-term (not a search topic)."""
    try:
        from smart_gather import META_TERMS_HEBREW
        return term in META_TERMS_HEBREW
    except Exception:
        pass
    
    FALLBACK_META_TERMS = {
        "שיטה", "שיטות", "שיטת",
        "דעה", "דעות", "דעת",
        "סברא", "סברה", "סברת",
        "מחלוקת", "מחלוקות",
        "טעם", "טעמי", "טעמים",
        "כלל", "כללי", "כללים",
        "הבדל", "הבדלים", "חילוק", "חילוקים",
        "דומה", "שונה",
        "מהו", "מהי", "מה", "למה", "מדוע", "איך", "כיצד",
        "האם", "אם",
        "מקור", "מקורות", "ראיה", "ראיות",
        "פסוק", "גמרא", "משנה",
    }
    return term in FALLBACK_META_TERMS


def _split_terms_into_topics_and_authors(hebrew_terms: List[str]) -> tuple[list[str], list[str]]:
    """Return (topics_hebrew, authors_en)."""
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
#  CLAUDE ANALYSIS (V6 Updated)
# ==============================================================================

# V6: Updated system prompt with better search method guidance
CLAUDE_SYSTEM_PROMPT = """You are a Torah learning assistant analyzing user queries.

Create a detailed search plan that tells the system:
1. WHAT to search for (the inyan/topic - NOT author names)
2. WHERE to look (which masechtos/sefarim)  
3. WHOSE commentary to fetch (which meforshim)
4. HOW to search (trickle-up vs trickle-down)

CRITICAL RULES:
- "search_topics" = the CONCEPT/INYAN only. Never put author names here.
- "target_authors" = whose COMMENTARY to fetch on that topic.
- If comparing multiple shittos, query_type should be "comparison" or "machlokes"
- If asking ONE author's view, query_type is "shittah"

SEARCH METHOD GUIDE (V6 - IMPORTANT):
- trickle_down: Search ACHRONIM first to discover which dapim discuss the topic, then fetch rishonim.
  USE WHEN: 
    * Comparing shittos (comparison, machlokes)
    * Asking for a specific shittah 
    * Complex conceptual questions
    * When the gemara might use different language than the query
  WHY: Achronim synthesize and discuss concepts - they're "semantic indices" that help find relevant sugyos.

- trickle_up: Start from base sources (gemara), then get commentaries. 
  USE WHEN: 
    * Simple lookups ("show me Rashi on daf X")
    * When you know the exact location
    * Standard reference requests

- hybrid: Both methods, find overlap.
  USE WHEN: Comprehensive research needed.

- direct: Go straight to specific ref.
  USE WHEN: User gives specific daf/source.

REALM DETERMINES STRUCTURE - Choose appropriate location fields:
- gemara/yerushalmi: Use target_masechtos + target_dapim
- chumash: Use target_perakim for parsha/perek
- mishnah: Use target_masechtos + target_perakim
- halacha: Use target_simanim for Shulchan Aruch/Tur
- OTHER SEFARIM: Use target_sefarim + target_refs

EXAMPLES:

Query: "what is the rans shittah in bittul chometz"
{
    "query_type": "shittah",
    "realm": "gemara",
    "search_method": "trickle_down",
    "search_topics": ["bittul chometz"],
    "search_topics_hebrew": ["ביטול חמץ"],
    "target_masechtos": ["Pesachim"],
    "target_dapim": [],
    "target_authors": ["Ran"],
    "reasoning": "Shittah question - use trickle_down to find where Ran discusses bittul chometz via achronim"
}

Query: "what is the rans shittah in bittul chometz and how is it different from rashis"
{
    "query_type": "comparison",
    "realm": "gemara", 
    "search_method": "trickle_down",
    "search_topics": ["bittul chometz"],
    "search_topics_hebrew": ["ביטול חמץ"],
    "target_masechtos": ["Pesachim"],
    "target_authors": ["Ran", "Rashi", "Tosafos"],
    "reasoning": "Comparison of multiple shittos - MUST use trickle_down to discover all relevant dapim"
}

Query: "show me rashi on pesachim 4b"
{
    "query_type": "source_request",
    "realm": "gemara",
    "search_method": "direct",
    "search_topics": [],
    "target_masechtos": ["Pesachim"],
    "target_dapim": ["4b"],
    "target_authors": ["Rashi"],
    "reasoning": "Direct request for specific location - use direct fetch"
}

Query: "where does the mechaber discuss carrying on shabbos"
{
    "query_type": "source_request",
    "realm": "halacha",
    "search_method": "direct",
    "search_topics": ["carrying on shabbos", "hotza'ah"],
    "search_topics_hebrew": ["הוצאה", "טלטול בשבת"],
    "target_sefarim": ["Shulchan Aruch Orach Chaim"],
    "target_simanim": ["301-350"],
    "target_authors": ["Mechaber"],
    "reasoning": "User asking for location in Shulchan Aruch"
}

Query: "explain rashi on bereishis 1:1"
{
    "query_type": "pasuk",
    "realm": "chumash",
    "search_method": "direct",
    "search_topics": ["bereishis creation"],
    "search_topics_hebrew": ["בראשית", "בריאה"],
    "target_perakim": ["Genesis 1"],
    "target_refs": ["Bereishis 1:1"],
    "target_authors": ["Rashi"],
    "reasoning": "Direct pasuk request"
}

Return ONLY valid JSON with this structure."""


async def analyze_with_claude(query: str, hebrew_terms: List[str]) -> QueryAnalysis:
    """Have Claude analyze the query and produce the search plan."""
    logger.info("[UNDERSTAND] Sending query to Claude")
    
    # Pre-split terms for context
    topics_hebrew, authors = _split_terms_into_topics_and_authors(hebrew_terms)
    
    user_prompt = f"""Analyze this Torah query:

Query: {query}
Hebrew Terms: {hebrew_terms}
Extracted Topics: {topics_hebrew}
Detected Authors: {authors}

Create a search plan. Remember:
- search_topics = the INYAN to search for (use the Extracted Topics above)
- target_authors = whose COMMENTARY to fetch (use the Detected Authors above, plus any others implied)
- For comparison/shittah/machlokes queries, use trickle_down method

Return ONLY valid JSON."""

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
            max_tokens=2000,
            temperature=0,
            system=CLAUDE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}]
        )
        
        raw_text = response.content[0].text.strip()
        logger.info(f"[UNDERSTAND] Claude raw response:\n{raw_text}")
        
        # Parse JSON from response
        json_text = raw_text
        if "```json" in raw_text:
            json_text = raw_text.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_text:
            json_text = raw_text.split("```")[1].split("```")[0].strip()
        
        # Progressive trimming for JSON parsing
        parsed = None
        attempts = [
            json_text,
            json_text.rstrip("}") + "}",
            json_text.rstrip("}").rstrip(",").rstrip() + "}",
        ]
        
        for attempt in attempts:
            try:
                parsed = json.loads(attempt)
                break
            except json.JSONDecodeError:
                continue
        
        if not parsed:
            logger.warning(f"[UNDERSTAND] Could not parse JSON, using fallback")
            return _create_fallback_analysis(query, hebrew_terms, topics_hebrew, authors, "JSON parse failed")
        
        logger.info(f"[UNDERSTAND] Claude parsed JSON:\n{json.dumps(parsed, indent=2, ensure_ascii=False)}")
        
        # Build QueryAnalysis from parsed JSON
        query_type = QueryType.UNKNOWN
        try:
            query_type = QueryType(parsed.get("query_type", "unknown"))
        except ValueError:
            pass
        
        realm = Realm.UNKNOWN
        try:
            realm = Realm(parsed.get("realm", "unknown"))
        except ValueError:
            pass
        
        search_method = SearchMethod.HYBRID
        try:
            search_method = SearchMethod(parsed.get("search_method", "hybrid"))
        except ValueError:
            pass
        
        # V6: Force trickle_down for comparison/shittah/machlokes
        if query_type in (QueryType.COMPARISON, QueryType.MACHLOKES, QueryType.SHITTAH, QueryType.SUGYA):
            if search_method != SearchMethod.TRICKLE_DOWN:
                logger.info(f"[V6] Forcing trickle_down for query_type={query_type}")
                search_method = SearchMethod.TRICKLE_DOWN
        
        # Build source categories
        source_cats = SourceCategories()
        for author in parsed.get("target_authors", []):
            author_lower = author.lower()
            if author_lower == "rashi":
                source_cats.rashi = True
            elif author_lower in ("tosafos", "tosafot", "tosfos"):
                source_cats.tosfos = True
            elif author_lower in ("rambam", "maimonides"):
                source_cats.rambam = True
            elif author_lower in RISHONIM_SET:
                source_cats.rishonim = True
            elif author_lower in ACHARONIM_SET:
                source_cats.acharonim = True
        
        # Enable gemara for gemara realm
        if realm == Realm.GEMARA:
            source_cats.gemara_bavli = True
        
        analysis = QueryAnalysis(
            original_query=query,
            hebrew_terms_from_step1=hebrew_terms,
            query_type=query_type,
            realm=realm,
            breadth=Breadth.STANDARD,
            search_method=search_method,
            search_topics=parsed.get("search_topics", topics_hebrew),
            search_topics_hebrew=parsed.get("search_topics_hebrew", topics_hebrew),
            target_masechtos=parsed.get("target_masechtos", []),
            target_perakim=parsed.get("target_perakim", []),
            target_dapim=parsed.get("target_dapim", []),
            target_simanim=parsed.get("target_simanim", []),
            target_sefarim=parsed.get("target_sefarim", []),
            target_refs=parsed.get("target_refs", []),
            target_authors=parsed.get("target_authors", authors),
            source_categories=source_cats,
            confidence=_parse_confidence(parsed.get("confidence", "medium")),
            needs_clarification=parsed.get("needs_clarification", False),
            clarification_question=parsed.get("clarification_question"),
            clarification_options=parsed.get("clarification_options", []),
            reasoning=parsed.get("reasoning", ""),
            search_description=parsed.get("search_description", "")
        )
        
        logger.info(f"[UNDERSTAND] Final QueryAnalysis:\n{json.dumps(asdict(analysis), indent=2, ensure_ascii=False, default=str)}")
        logger.info(f"[UNDERSTAND] Reasoning: {analysis.reasoning}")
        logger.info(f"[UNDERSTAND] Search Description: {analysis.search_description or '<none>'}")
        
        return analysis
        
    except Exception as e:
        logger.error(f"[UNDERSTAND] Claude analysis failed: {e}", exc_info=True)
        return _create_fallback_analysis(query, hebrew_terms, topics_hebrew, authors, str(e))


# Known author sets for classification
RISHONIM_SET = {
    'ran', 'rashba', 'ritva', 'ramban', 'rosh', 'meiri', 'ra\'ah',
    'nimukei yosef', 'mordechai', 'rashbam', 'rabbeinu chananel',
}

ACHARONIM_SET = {
    'pnei yehoshua', 'maharsha', 'sfas emes', 'rav akiva eiger',
    'ketzos', 'nesivos', 'mishna berura', 'aruch hashulchan',
}


def _create_fallback_analysis(
    query: str,
    hebrew_terms: List[str],
    topics: List[str],
    authors: List[str],
    error: str
) -> QueryAnalysis:
    """Create fallback analysis when Claude fails."""
    logger.warning(f"[UNDERSTAND] Using fallback analysis due to: {error}")
    
    # Default to trickle_down for comparison-like queries
    search_method = SearchMethod.TRICKLE_DOWN if len(authors) > 1 else SearchMethod.HYBRID
    
    return QueryAnalysis(
        original_query=query,
        hebrew_terms_from_step1=hebrew_terms,
        query_type=QueryType.UNKNOWN,
        realm=Realm.GEMARA,  # Default to gemara
        breadth=Breadth.STANDARD,
        search_method=search_method,
        search_topics=topics or hebrew_terms,
        search_topics_hebrew=topics or hebrew_terms,
        target_authors=authors,
        source_categories=SourceCategories(),
        confidence=ConfidenceLevel.LOW,
        needs_clarification=True,
        clarification_question="I had trouble understanding your query. Could you rephrase it?",
        reasoning=f"Fallback due to error: {error}"
    )


# ==============================================================================
#  MAIN ENTRY POINT
# ==============================================================================

async def understand(
    hebrew_terms: List[str] = None,
    query: str = None,
    decipher_result: DecipherResult = None,
) -> QueryAnalysis:
    """
    Step 2: UNDERSTAND - Analyze the query with Claude.
    
    Creates QueryAnalysis that tells Step 3:
    - WHAT to search (search_topics)
    - WHERE to look (target_masechtos)
    - WHOSE commentary to fetch (target_authors)
    - HOW to search (search_method)
    
    V6: Fixed parameter naming to match console_full_pipeline.py
    """
    # Extract from decipher_result if provided
    if decipher_result:
        if hasattr(decipher_result, 'hebrew_terms') and decipher_result.hebrew_terms:
            hebrew_terms = decipher_result.hebrew_terms
        elif hasattr(decipher_result, 'hebrew_term') and decipher_result.hebrew_term:
            hebrew_terms = [decipher_result.hebrew_term]
        
        if hasattr(decipher_result, 'original_query') and decipher_result.original_query:
            query = decipher_result.original_query
    
    # Validation
    if not hebrew_terms:
        logger.warning("[UNDERSTAND] No Hebrew terms provided")
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
    logger.info("[STEP 2: UNDERSTAND] Analyzing query")
    logger.info(f"  Query: {query}")
    logger.info(f"  Hebrew terms: {hebrew_terms}")
    
    analysis = await analyze_with_claude(query, hebrew_terms)
    
    logger.info("=" * 70)
    logger.info("[STEP 2: UNDERSTAND] Complete")
    logger.info(f"  INYAN: {analysis.search_topics_hebrew}")
    logger.info(f"  WHERE: {analysis.target_masechtos}")
    logger.info(f"  WHOSE: {analysis.target_authors}")
    logger.info(f"  METHOD: {analysis.search_method}")
    logger.info("=" * 70)
    
    return analysis


# Aliases
run_step_two = understand


# ==============================================================================
#  TESTING
# ==============================================================================

async def test_step_two():
    """Test Step 2."""
    print("=" * 70)
    print("STEP 2 TEST: UNDERSTAND")
    print("=" * 70)
    
    test_cases = [
        (["רן", "ביטול חמץ", "תוספות", 'רש"י'], 
         "what is the rans shittah in bittul chometz and how is it different than tosfos and rashis"),
    ]
    
    for hebrew_terms, query in test_cases:
        print(f"\nQuery: {query}")
        print(f"Hebrew terms: {hebrew_terms}")
        
        analysis = await understand(hebrew_terms=hebrew_terms, query=query)
        
        print(f"\nAnalysis:")
        print(f"  INYAN: {analysis.search_topics_hebrew}")
        print(f"  WHERE: {analysis.target_masechtos}")
        print(f"  WHOSE: {analysis.target_authors}")
        print(f"  Method: {analysis.search_method.value}")


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)-8s | %(message)s')
    asyncio.run(test_step_two())