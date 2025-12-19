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
    TOPIC = "topic"
    QUESTION = "question"
    SOURCE_REQUEST = "source_request"
    COMPARISON = "comparison"
    SHITTAH = "shittah"
    SUGYA = "sugya"
    PASUK = "pasuk"
    HALACHA = "halacha"
    MACHLOKET = "machloket"
    UNKNOWN = "unknown"


class Realm(str, Enum):
    """What realm of Torah is this query about?"""
    GEMARA = "gemara"
    CHUMASH = "chumash"
    HALACHA = "halacha"
    HASHKAFA = "hashkafa"
    GENERAL = "general"
    UNKNOWN = "unknown"


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
            "psukim": ["psukim", "pesukim", "tanach"],
            "mishnayos": ["mishnah", "mishna", "mishnayos"],
            "tosefta": ["tosefta"],
            "gemara_bavli": ["gemara", "bavli", "gemara_bavli"],
            "gemara_yerushalmi": ["gemara_yerushalmi", "yerushalmi"],
            "midrash": ["midrash"],
            "rashi": ["rashi"],
            "tosfos": ["tosfos", "tosafot"],
            "rishonim": ["rishonim"],
            "rambam": ["rambam"],
            "tur": ["tur"],
            "shulchan_aruch": ["shulchan_aruch"],
            "nosei_keilim_rambam": ["nosei_keilim_rambam"],
            "nosei_keilim_tur": ["nosei_keilim_tur"],
            "nosei_keilim_sa": ["nosei_keilim_sa"],
            "acharonim": ["acharonim"],
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
    
    # WHERE to look
    target_masechtos: List[str] = field(default_factory=list)
    target_perakim: List[str] = field(default_factory=list)
    target_dapim: List[str] = field(default_factory=list)
    
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
    try:
        from smart_gather import META_TERMS_HEBREW
        return term in META_TERMS_HEBREW
    except Exception:
        return term in {"שיטה", "שיטות", "דעה", "דעות", "סברא", "סברה", "מחלוקת", "טעם", "כלל"}


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

CLAUDE_SYSTEM_PROMPT = """You are a Torah learning assistant analyzing user queries.

Create a detailed search plan that tells the system:
1. WHAT to search for (the inyan/topic - NOT author names)
2. WHERE to look (which masechtos)  
3. WHOSE commentary to fetch (which meforshim)
4. HOW to search (trickle-up or trickle-down)

CRITICAL: "search_topics" = the CONCEPT. "target_authors" = whose COMMENTARY to fetch.

Example: "What is the Ran's shittah on bittul chometz"
- search_topics: ["bittul chometz", "ביטול חמץ"]
- target_authors: ["Ran", "Rashi", "Tosfos"]
- target_masechtos: ["Pesachim"]

Return JSON with this structure:
{
    "query_type": "shittah",
    "realm": "gemara",
    "breadth": "standard",
    "search_method": "trickle_up",
    "search_topics": ["bittul chometz"],
    "search_topics_hebrew": ["ביטול חמץ"],
    "target_masechtos": ["Pesachim"],
    "target_perakim": [],
    "target_dapim": [],
    "target_authors": ["Ran", "Rashi", "Tosfos"],
    "source_categories": {
        "gemara_bavli": true,
        "rashi": true,
        "tosfos": true,
        "rishonim": true
    },
    "confidence": "high",
    "needs_clarification": false,
    "reasoning": "User wants Ran's approach to bittul chometz compared to Rashi and Tosfos.",
    "search_description": "Searching for bittul chometz in Pesachim"
}
"""


async def analyze_with_claude(query: str, hebrew_terms: List[str]) -> QueryAnalysis:
    """Have Claude analyze the query and produce the search plan."""
    logger.info("[UNDERSTAND] Sending query to Claude")
    
    user_prompt = f"""Analyze this Torah query:

Query: {query}
Hebrew Terms: {hebrew_terms}

Create a search plan. Remember:
- search_topics = the INYAN to search for
- target_authors = whose COMMENTARY to fetch

Return ONLY valid JSON."""

    try:
        client = Anthropic(api_key=settings.anthropic_api_key)
        
        response = client.messages.create(
            model=settings.claude_model,
            max_tokens=2000,
            temperature=0,
            system=CLAUDE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}]
        )
        
        response_text = response.content[0].text.strip()
        
        # Clean markdown fences
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.strip()
        
        # Parse JSON
        result = json.loads(response_text)
        
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
            target_authors=[str(a) for a in (result.get("target_authors") or [])],
            source_categories=SourceCategories.from_dict(result.get("source_categories", {})),
            confidence=ConfidenceLevel(result.get("confidence", "medium")),
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

        # Remove meta terms and authors from topics
        cleaned = [t for t in analysis.search_topics_hebrew if t and not _is_meta_term(t)]
        is_author, _ = _load_author_kb()
        if callable(is_author):
            cleaned = [t for t in cleaned if not bool(is_author(t))]
        analysis.search_topics_hebrew = cleaned

        # Use Step 1 authors if Claude didn't provide them
        if not analysis.target_authors and step1_authors:
            analysis.target_authors = step1_authors

        # Enable rishonim layer if needed
        if analysis.target_authors and any(a.lower() not in {"rashi", "tosfos", "tosafot"} for a in analysis.target_authors):
            analysis.source_categories.rishonim = True
        
        logger.info(f"[UNDERSTAND] Analysis complete:")
        logger.info(f"  INYAN: {analysis.search_topics_hebrew}")
        logger.info(f"  WHERE: {analysis.target_masechtos}")
        logger.info(f"  WHOSE: {analysis.target_authors}")
        
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