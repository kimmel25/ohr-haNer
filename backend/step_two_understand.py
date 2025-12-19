"""
Step 2: UNDERSTAND - The Brain of Ohr Haner
============================================

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
    TOPIC = "topic" #general inyan/topic    
    QUESTION = "question" #specific question with a specific answer
    SOURCE_REQUEST = "source_request" #asking for sources on a topic
    COMPARISON = "comparison" #comparing opinions, like rashi vs tosfos... rashba vs ramban etc.
    SHITTAH = "shittah" #asking for a specific meforshim's shittah on an inyan
    SUGYA = "sugya" #asking about a specific sugya and its complex web
    PASUK = "pasuk" #asking about a specific pasuk or set of pesukim
    HALACHA = "halacha" #asking about a specific halacha lemaysa or halachic topic. psak din
    MACHLOKES = "machlokes" #asking about a machlokes/dispute between rishonim/achronim
    MACHLOKET = "machlokes"  # Alias for backwards compatibility
    UNKNOWN = "unknown" #if unknown we should ask the user for clarification


class Realm(str, Enum):
    """What realm of Torah is this query about?"""
    CHUMASH = "chumash"
    MISHNAH = "mishnah"
    TANNAIC = "tannaic" # includes tosefta, sifra, sifre, midrashim
    GEMARA = "gemara"   #stam gemara is bavli
    YERUSHALMI = "yerushalmi"   #only if clear this is what is needed
    HALACHA = "halacha"     #psak din   
    GENERAL = "general"
    UNKNOWN = "unknown"
    MULTIPLE = "multiple" #if the query spans multiple realms. not sure how to implement this



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
        """Best-effort construction from Claude JSON."""
        if not isinstance(raw, dict):
            return cls()

        # Map common variations to field names
        field_map = {
            "psukim": ["psukim", "pesukim", "tanach", "nach", "torah"],
            "mishnayos": ["mishnah", "mishna", "mishnayos", "mishnayot", "mishnayis"],
            "tosefta": ["tosefta"],
            "gemara_bavli": ["gemara", "bavli", "gemara_bavli", "talmud"],
            "gemara_yerushalmi": ["gemara_yerushalmi", "yerushalmi"],
            "midrash": ["midrash", "midrashim"],
            "rashi": ["rashi", "reb shlomo yitzchaki", "kuntres", "hakuntres"],
            "tosfos": ["tosfos", "tosafot", "toysfes", "tos"],
            "rishonim": ["rishonim", "rishon", "rishonim_meforshim", "rishoynim"],
            "rambam": ["rambam", "maimonides", "moshe ben maimon"],
            "tur": ["tur", "toor", "tuur"],
            "shulchan_aruch": ["shulchan_aruch", "shulchan aruch", "shulchan_arukh", "shulchan arukh"],
            "nosei_keilim_rambam": ["nosei_keilim_rambam", "nosei keilim", "rambam nosei keilim"],
            "nosei_keilim_tur": ["nosei_keilim_tur", "nosei keilim tur", "tur nosei keilim"],
            "nosei_keilim_sa": ["nosei_keilim_sa" , "nosei keilim sa", "shulchan aruch nosei keilim", "nosei keilim shulchan aruch"],
            "acharonim": ["acharonim", "achroynim"],
        }

        kwargs: Dict[str, bool] = {}
        for k, v in raw.items():
            k_norm = str(k).strip().lower().replace(" ", "_").replace("-", "_")
            # Find matching field
            for field_name, aliases in field_map.items():
                if k_norm in aliases:
                    kwargs[field_name] = bool(v)
                    break

        return cls(**kwargs)


@dataclass 
class QueryAnalysis:
    """
    The complete analysis - Claude's "datatype" that drives Step 3.
    
    CRITICAL DISTINCTION:
    - search_topics: The INYAN to search for
    - target_authors: WHOSE COMMENTARY to fetch
    - target_masechtos: WHERE to look
    """
    original_query: str
    hebrew_terms_from_step1: List[str]
    
    query_type: QueryType
    realm: Realm
    breadth: Breadth
    search_method: SearchMethod
    
    # WHAT to search for
    search_topics: List[str] = field(default_factory=list)
    search_topics_hebrew: List[str] = field(default_factory=list)
    
    # WHERE to look - expanded for different realms and structures
    target_masechtos: List[str] = field(default_factory=list)  # Gemara/Mishnah
    target_perakim: List[str] = field(default_factory=list)    # Chumash/Mishnah chapters
    target_dapim: List[str] = field(default_factory=list)      # Gemara pages (e.g., "4b")
    target_simanim: List[str] = field(default_factory=list)    # Shulchan Aruch/Tur simanim
    target_sefarim: List[str] = field(default_factory=list)    # General sefarim names
    target_refs: List[str] = field(default_factory=list)       # NEW: Freeform references for any structure
    
    # WHOSE commentary to fetch
    target_authors: List[str] = field(default_factory=list)
    
    # Which source layers
    source_categories: SourceCategories = field(default_factory=SourceCategories)
    
    # Confidence & clarification
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    needs_clarification: bool = False
    clarification_question: Optional[str] = None
    clarification_options: List[str] = field(default_factory=list)
    
    # Reasoning
    reasoning: str = ""
    search_description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = asdict(self)
        result['query_type'] = self.query_type.value
        result['realm'] = self.realm.value
        result['breadth'] = self.breadth.value
        result['search_method'] = self.search_method.value
        result['confidence'] = self.confidence.value
        return result


# ==============================================================================
#  HELPERS
# ==============================================================================

def _load_author_kb():
    """Load author helpers."""
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
    # Try to load from smart_gather first (has comprehensive list)
    try:
        from smart_gather import META_TERMS_HEBREW
        return term in META_TERMS_HEBREW
    except Exception:
        pass
    
    # Fallback: our own comprehensive list
    FALLBACK_META_TERMS = {
        # Query structure terms
        "שיטה", "שיטות", "שיטת",
        "דעה", "דעות", "דעת",
        "סברא", "סברה", "סברת",
        "מחלוקת", "מחלוקות",
        "טעם", "טעמי", "טעמים",
        "כלל", "כללי", "כללים",
        # Comparison terms  
        "הבדל", "הבדלים", "חילוק", "חילוקים",
        "דומה", "שונה",
        # Question words
        "מהו", "מהי", "מה", "למה", "מדוע", "איך", "כיצד",
        "האם", "אם",
        # Source type terms (not topics themselves)
        "מקור", "מקורות", "ראיה", "ראיות",
        "פסוק", "גמרא", "משנה",  # When used as "show me the gemara" not as topic
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
            # Convert to canonical English
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

    # Deduplicate
    def dedup(seq):
        seen = set()
        return [x for x in seq if not (x in seen or seen.add(x))]

    return dedup(topics), dedup(authors)


# ==============================================================================
#  CLAUDE ANALYSIS
# ==============================================================================

#some issues with below: 
# can claude really use an example and apply it correctly every time? what if it hallucinates or misinterprets?
# do we need more info?
# how does it know how to answer questions 1-4? do we need to give it more guidance/examples?
# query type is not shittah, its obviosuly comparison, you can see that from "and how is it different", or/amd the other meforshim mentiond
# why trickle up? how should it know that from the query? do we need to give it more guidance/examples?
# target dapim/perakim? lets say the query is chumash, or mishnayos or mechaber, there is no dapim or prakim
# 
CLAUDE_SYSTEM_PROMPT = """You are a Torah learning assistant analyzing user queries.

Create a detailed search plan that tells the system:
1. WHAT to search for (the inyan/topic - NOT author names)
2. WHERE to look (which masechtos/sefarim)  
3. WHOSE commentary to fetch (which meforshim)
4. HOW to search (trickle-up or trickle-down)

CRITICAL RULES:
- "search_topics" = the CONCEPT/INYAN only. Never put author names here.
- "target_authors" = whose COMMENTARY to fetch on that topic.
- If comparing multiple shittos, query_type should be "comparison" or "machlokes"
- If asking ONE author's view, query_type is "shittah"

SEARCH METHOD GUIDE:
- trickle_up: Start from base sources (gemara), then get commentaries. 
  USE WHEN: Looking for meforshim on a sugya, standard research.
- trickle_down: Start from later sources (halacha sefarim), trace back.
  USE WHEN: Starting from a halacha question, want to find source in gemara.
- hybrid: Both methods, find overlap.
  USE WHEN: Comprehensive research, or unsure where topic is discussed.
- direct: Go straight to specific ref.
  USE WHEN: User gives specific daf/source.

REALM DETERMINES STRUCTURE - Choose appropriate location fields:
- gemara/yerushalmi: Use target_masechtos + target_dapim (e.g., "Pesachim", "4b")
- chumash: Use target_perakim for parsha/perek (e.g., "Genesis 1", "Bereishis")
- mishnah: Use target_masechtos + target_perakim (e.g., "Berachos", "1")
- halacha: Use target_simanim for Shulchan Aruch/Tur (e.g., "Orach Chaim 1")
- OTHER SEFARIM: Use target_sefarim for book names + target_refs for any structure
  Examples:
  * Sefer HaChinuch: target_sefarim=["Sefer HaChinuch"], target_refs=["Mitzvah 1"]
  * Kuzari: target_sefarim=["Kuzari"], target_refs=["Ma'amar 1, Section 1"]
  * Ramban on Torah: target_sefarim=["Ramban on Torah"], target_refs=["Bereishis 1:1"]
  * Maharal: target_sefarim=["Netzach Yisrael"], target_refs=["Chapter 3"]
  * Any sefer without standard structure: Just use target_refs with descriptive location

EXAMPLES:

Query: "what is the rans shittah in bittul chometz"
{
    "query_type": "shittah",
    "realm": "gemara",
    "search_method": "trickle_up",
    "search_topics": ["bittul chometz"],
    "search_topics_hebrew": ["ביטול חמץ"],
    "target_masechtos": ["Pesachim"],
    "target_dapim": [],
    "target_authors": ["Ran"],
    "reasoning": "User wants ONE author's (Ran) approach to bittul chometz"
}

Query: "what is the rans shittah in bittul chometz and how is it different from rashis"
{
    "query_type": "comparison",
    "realm": "gemara", 
    "search_method": "trickle_up",
    "search_topics": ["bittul chometz"],
    "search_topics_hebrew": ["ביטול חמץ"],
    "target_masechtos": ["Pesachim"],
    "target_authors": ["Ran", "Rashi"],
    "reasoning": "User wants to COMPARE Ran vs Rashi - this is comparison, not just shittah"
}

Query: "where does the mechaber discuss carrying on shabbos"
{
    "query_type": "source_request",
    "realm": "halacha",
    "search_method": "direct",
    "search_topics": ["carrying on shabbos", "hotza'ah"],
    "search_topics_hebrew": ["הוצאה", "טלטול בשבת"],
    "target_masechtos": [],
    "target_sefarim": ["Shulchan Aruch Orach Chaim"],
    "target_simanim": ["301-350"],
    "target_authors": ["Mechaber"],
    "reasoning": "User asking for location in Shulchan Aruch - use simanim not dapim"
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
    "reasoning": "Direct pasuk request - no masechtos or dapim needed"
}

Query: "what does the kuzari say about loving hashem"
{
    "query_type": "topic",
    "realm": "hashkafa",
    "search_method": "direct",
    "search_topics": ["loving hashem", "ahavas hashem"],
    "search_topics_hebrew": ["אהבת ה'", "אהבה"],
    "target_sefarim": ["Kuzari"],
    "target_refs": [],
    "target_authors": ["Reb Yehuda HaLevi"],
    "reasoning": "Kuzari doesn't use standard structure - will search by topic in the sefer"
}

Query: "find me the maharals discussion of free will in derech chaim"
{
    "query_type": "topic",
    "realm": "hashkafa",
    "search_method": "direct",
    "search_topics": ["free will", "bechira"],
    "search_topics_hebrew": ["בחירה", "בחירה חפשית"],
    "target_sefarim": ["Derech Chaim"],
    "target_refs": [],
    "target_authors": ["Maharal"],
    "reasoning": "Sefer without standard structure - search by topic within the sefer"
}

Return ONLY valid JSON with this structure."""


async def analyze_with_claude(query: str, hebrew_terms: List[str]) -> QueryAnalysis:
    """Have Claude analyze the query and produce the search plan."""
    logger.info("[UNDERSTAND] Sending query to Claude")
    
    user_prompt = f"""Analyze this Torah query:

Query: {query}
Hebrew Terms: {hebrew_terms}

Create a search plan. Remember:
- search_topics = the INYAN to search for
- target_authors = whose COMMENTARY to fetch
- Use appropriate location fields based on realm (see REALM DETERMINES STRUCTURE guide)

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
            model=settings.claude_model,
            max_tokens=2000,
            temperature=0,
            system=CLAUDE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}]
        )
        
        # Extract and log raw Claude response
        response_text = ""
        try:
            content = getattr(response, "content", None)
            if isinstance(content, (list, tuple)) and len(content) > 0:
                parts = []
                for item in content:
                    if hasattr(item, "text"):
                        parts.append(item.text)
                    elif isinstance(item, dict) and "text" in item:
                        parts.append(item["text"])
                    else:
                        parts.append(str(item))
                response_text = "\n".join(parts).strip()
            elif hasattr(response, "text"):
                response_text = response.text.strip()
            else:
                response_text = str(response)
        except Exception as e:
            logger.debug(f"[UNDERSTAND] Could not extract Anthropic response text: {e}")
            response_text = str(response)

        logger.info("[UNDERSTAND] Claude raw response:\n%s", response_text)

        # Clean markdown fences
        if response_text.startswith("```"):
            try:
                inner = response_text.split("```", 2)[1]
                if inner.strip().lower().startswith("json"):
                    inner = inner.split(None, 1)[1] if len(inner.split(None, 1)) > 1 else ""
                response_text = inner.strip()
            except Exception:
                pass

        # Parse JSON and log it
        try:
            result = json.loads(response_text)
            logger.info("[UNDERSTAND] Claude parsed JSON:\n%s", json.dumps(result, ensure_ascii=False, indent=2))
        except Exception as e:
            logger.error("[UNDERSTAND] Failed to parse JSON from Claude response: %s", e)
            logger.debug("[UNDERSTAND] Response that failed JSON parse:\n%s", response_text)
            raise

        # Build analysis
        analysis = QueryAnalysis(
            original_query=query,
            hebrew_terms_from_step1=hebrew_terms,
            query_type=QueryType(result.get("query_type", "unknown")),
            realm=Realm(result.get("realm", "unknown")),
            breadth=Breadth(result.get("breadth", "standard")),
            search_method=SearchMethod(result.get("search_method", "trickle_up")),
            search_topics=[str(t) for t in (result.get("search_topics") or [])],
            search_topics_hebrew=[str(t) for t in (result.get("search_topics_hebrew") or [])],
            target_masechtos=[str(m) for m in (result.get("target_masechtos") or [])],
            target_perakim=[str(p) for p in (result.get("target_perakim") or [])],
            target_dapim=[str(d) for d in (result.get("target_dapim") or [])],
            target_simanim=[str(s) for s in (result.get("target_simanim") or [])],
            target_sefarim=[str(s) for s in (result.get("target_sefarim") or [])],
            target_refs=[str(r) for r in (result.get("target_refs") or [])],
            target_authors=[str(a) for a in (result.get("target_authors") or [])],
            source_categories=SourceCategories.from_dict(result.get("source_categories", {})),
            confidence=_parse_confidence(result.get("confidence", "medium")),
            needs_clarification=bool(result.get("needs_clarification", False)),
            clarification_question=result.get("clarification_question"),
            clarification_options=[str(o) for o in (result.get("clarification_options") or [])],
            reasoning=str(result.get("reasoning", "")),
            search_description=str(result.get("search_description", "")),
        )

        # Post-clean: ensure authors/meta terms don't leak into search_topics
        step1_topics, step1_authors = _split_terms_into_topics_and_authors(hebrew_terms)
        
        if not analysis.search_topics_hebrew:
            analysis.search_topics_hebrew = step1_topics

        cleaned = [t for t in analysis.search_topics_hebrew if t and not _is_meta_term(t)]
        is_author, _ = _load_author_kb()
        if callable(is_author):
            cleaned = [t for t in cleaned if not bool(is_author(t))]
        analysis.search_topics_hebrew = cleaned

        if not analysis.target_authors and step1_authors:
            analysis.target_authors = step1_authors

        if analysis.target_authors and any(a.lower() not in {"rashi", "tosfos", "tosafot"} for a in analysis.target_authors):
            analysis.source_categories.rishonim = True
        
        # Log final QueryAnalysis as dict
        logger.info("[UNDERSTAND] Final QueryAnalysis:\n%s", json.dumps(analysis.to_dict(), ensure_ascii=False, indent=2))
        logger.info("[UNDERSTAND] Reasoning: %s", analysis.reasoning or "<none>")
        logger.info("[UNDERSTAND] Search Description: %s", analysis.search_description or "<none>")
        
        return analysis
        
    except Exception as e:
        logger.error(f"[UNDERSTAND] Error: {e}")
        return _fallback_analysis(query, hebrew_terms, str(e))


def _fallback_analysis(query: str, hebrew_terms: List[str], error: str) -> QueryAnalysis:
    """Create a low-confidence fallback analysis."""
    topics, authors = _split_terms_into_topics_and_authors(hebrew_terms)
    return QueryAnalysis(
        original_query=query,
        hebrew_terms_from_step1=hebrew_terms,
        query_type=QueryType.UNKNOWN,
        realm=Realm.UNKNOWN,
        breadth=Breadth.STANDARD,
        search_method=SearchMethod.HYBRID,
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
        (["רן", "ביטול חמץ", "תוספות", "רש\"י"], 
         "what is the rans shittah in bittul chometz"),
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