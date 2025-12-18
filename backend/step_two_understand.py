"""
Step 2: UNDERSTAND - The Brain of Ohr Haner
============================================

Claude analyzes the query and creates a detailed "datatype" that 
PROGRAMMATICALLY tells Step 3:
- WHERE to look (which masechtos)
- WHAT to search for (the inyan/topic - NOT author names)
- WHICH commentaries to fetch (based on authors mentioned)
- HOW to search (trickle-up vs trickle-down)

From Architecture:
- "This part needs to be perfect, its the brain of the project"
- "Claude in its datatype should have a nice idea where to look"
- "This should not be key word searching"

NO SEFARIA SEARCHES HERE. This step is pure understanding.
"""

import logging
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from enum import Enum

from anthropic import Anthropic

from models import DecipherResult, ConfidenceLevel
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# ==============================================================================
#  QUERY ANALYSIS DATATYPE - The "Brain Output"
# ==============================================================================

class QueryType(str, Enum):
    """What kind of query is this?"""
    TOPIC = "topic"                    # General topic exploration
    QUESTION = "question"              # Specific question needing answer
    SOURCE_REQUEST = "source_request"  # "Show me the gemara on X"
    COMPARISON = "comparison"          # "What's the difference between X and Y"
    SHITTAH = "shittah"               # "What is Rashi's shittah on X"
    SUGYA = "sugya"                   # Wants a full sugya breakdown
    PASUK = "pasuk"                   # Looking for peirushim on a pasuk
    HALACHA = "halacha"               # Looking for halachic ruling
    MACHLOKET = "machloket"           # Looking for a dispute/argument
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
    """Which categories of sources to include at each layer."""
    # Layer 1: Tanach
    psukim: bool = False
    
    # Layer 2: Mishna era
    mishnayos: bool = False
    tosefta: bool = False
    
    # Layer 3: Gemara
    gemara_bavli: bool = True
    gemara_yerushalmi: bool = False
    midrash: bool = False
    
    # Layer 4: Basic meforshim (almost always wanted)
    rashi: bool = True
    tosfos: bool = True
    
    # Layer 5: Other Rishonim
    rishonim: bool = False  # Ran, Rashba, Ritva, Ramban, Rosh, etc.
    rambam: bool = False
    
    # Layer 6: Halacha codes
    tur: bool = False
    shulchan_aruch: bool = False
    
    # Layer 7: Nosei Keilim
    nosei_keilim_rambam: bool = False   # Maggid Mishna, Kesef Mishna, etc.
    nosei_keilim_tur: bool = False      # Bach, Beis Yosef, etc.
    nosei_keilim_sa: bool = False       # Shach, Taz, etc.
    
    # Layer 8: Acharonim
    acharonim: bool = False  # Pnei Yehoshua, Ketzos, etc.


@dataclass 
class QueryAnalysis:
    """
    The complete analysis - Claude's "datatype" that drives Step 3.
    
    CRITICAL DISTINCTION:
    - search_topics: The INYAN to search for (e.g., "ביטול חמץ")
    - target_authors: WHOSE COMMENTARY to fetch (e.g., ["Ran", "Rashi"])
    - target_masechtos: WHERE to look (e.g., ["Pesachim"])
    
    search_topics gets searched. target_authors determines which 
    commentaries to fetch ON whatever base sources are found.
    """
    # Original input (for reference)
    original_query: str
    hebrew_terms_from_step1: List[str]  # Raw terms - for logging only
    
    # Query classification
    query_type: QueryType
    realm: Realm
    breadth: Breadth
    search_method: SearchMethod
    
    # === THE CRITICAL FIELDS ===
    
    # WHAT to search for - the actual INYAN/concept (NOT author names!)
    # This is what gets passed to Sefaria search
    search_topics: List[str] = field(default_factory=list)
    search_topics_hebrew: List[str] = field(default_factory=list)
    
    # WHERE to look - which masechtos/seforim to search in
    target_masechtos: List[str] = field(default_factory=list)
    target_perakim: List[str] = field(default_factory=list)  # If known
    target_dapim: List[str] = field(default_factory=list)    # If known (e.g., "Pesachim 4b")
    
    # WHOSE commentary to fetch - determines which meforshim to get
    # These are NOT search terms - they tell us which refs to construct
    target_authors: List[str] = field(default_factory=list)
    
    # Which source layers to include
    source_categories: SourceCategories = field(default_factory=SourceCategories)
    
    # === CONFIDENCE & CLARIFICATION ===
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    needs_clarification: bool = False
    clarification_question: Optional[str] = None
    clarification_options: List[str] = field(default_factory=list)
    
    # Claude's reasoning (for debugging/display)
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
#  CLAUDE ANALYSIS
# ==============================================================================

CLAUDE_SYSTEM_PROMPT = """You are a Torah learning assistant analyzing user queries.

Your job is to create a detailed search plan that tells the system:
1. WHAT to search for (the inyan/topic - NOT author names)
2. WHERE to look (which masechtos)  
3. WHOSE commentary to fetch (which meforshim)
4. HOW to search (trickle-up or trickle-down)

CRITICAL DISTINCTION:
- "search_topics" = The actual CONCEPT being asked about (e.g., "bittul chometz", "chezkas haguf")
- "target_authors" = Whose COMMENTARY to fetch (e.g., "Ran", "Rashi", "Tosfos")

Example: "What is the Ran's shittah on bittul chometz"
- search_topics: ["bittul chometz", "ביטול חמץ"] ← This gets searched
- target_authors: ["Ran", "Rashi", "Tosfos"] ← Fetch their commentary on found sources
- target_masechtos: ["Pesachim"] ← Where to look

DO NOT put author names in search_topics! They are NOT the inyan.
Words like "shittah", "pshat", "svara" are meta-terms - also NOT search topics.

QUERY TYPES:
- topic: General exploration (e.g., "bittul chometz")
- question: Specific question (e.g., "why do we do bittul")  
- comparison: Comparing views (e.g., "Rashi vs Tosfos on X")
- shittah: Someone's opinion (e.g., "what is the Ran's shittah")
- sugya: Full sugya breakdown
- machloket: Looking for a dispute
- halacha: Practical ruling
- pasuk: Peirushim on a verse

SEARCH METHODS:
- trickle_up: Start from psukim → mishna → gemara → rishonim → acharonim
  Best for: Understanding foundations, simple topics
- trickle_down: Start from acharonim → trace citations back to gemara
  Best for: Complex topics, finding where something is discussed
- hybrid: Both methods, find commonalities
- direct: When user specifies exact location

SOURCE CATEGORIES (mark true/false):
- psukim, mishnayos, tosefta
- gemara_bavli (usually true), gemara_yerushalmi, midrash  
- rashi (usually true), tosfos (usually true)
- rishonim (other Rishonim like Ran, Rashba, etc.)
- rambam, tur, shulchan_aruch
- nosei_keilim_rambam, nosei_keilim_tur, nosei_keilim_sa
- acharonim

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
        "psukim": false,
        "mishnayos": false,
        "tosefta": false,
        "gemara_bavli": true,
        "gemara_yerushalmi": false,
        "midrash": false,
        "rashi": true,
        "tosfos": true,
        "rishonim": true,
        "rambam": false,
        "tur": false,
        "shulchan_aruch": false,
        "nosei_keilim_rambam": false,
        "nosei_keilim_tur": false,
        "nosei_keilim_sa": false,
        "acharonim": false
    },
    
    "confidence": "high",
    "needs_clarification": false,
    "clarification_question": null,
    "clarification_options": [],
    
    "reasoning": "User wants to understand the Ran's approach to bittul chometz compared to Rashi and Tosfos. This is discussed in Pesachim perek 1.",
    "search_description": "Searching for bittul chometz in Pesachim, fetching Ran, Rashi, and Tosfos"
}
"""


async def analyze_with_claude(
    query: str,
    hebrew_terms: List[str]
) -> QueryAnalysis:
    """
    Have Claude analyze the query and produce the search plan datatype.
    """
    logger.info("[UNDERSTAND] Sending query to Claude for analysis")
    
    user_prompt = f"""Analyze this Torah learning query:

Original Query: {query}
Hebrew Terms Identified: {hebrew_terms}

Create a detailed search plan. Remember:
- search_topics = the INYAN (concept) to search for
- target_authors = whose COMMENTARY to fetch (NOT search terms)
- target_masechtos = WHERE to look

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
        
        # Clean up JSON if wrapped in markdown
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.strip()
        
        result = json.loads(response_text)
        
        # Build SourceCategories
        cats = result.get("source_categories", {})
        source_categories = SourceCategories(
            psukim=cats.get("psukim", False),
            mishnayos=cats.get("mishnayos", False),
            tosefta=cats.get("tosefta", False),
            gemara_bavli=cats.get("gemara_bavli", True),
            gemara_yerushalmi=cats.get("gemara_yerushalmi", False),
            midrash=cats.get("midrash", False),
            rashi=cats.get("rashi", True),
            tosfos=cats.get("tosfos", True),
            rishonim=cats.get("rishonim", False),
            rambam=cats.get("rambam", False),
            tur=cats.get("tur", False),
            shulchan_aruch=cats.get("shulchan_aruch", False),
            nosei_keilim_rambam=cats.get("nosei_keilim_rambam", False),
            nosei_keilim_tur=cats.get("nosei_keilim_tur", False),
            nosei_keilim_sa=cats.get("nosei_keilim_sa", False),
            acharonim=cats.get("acharonim", False),
        )
        
        analysis = QueryAnalysis(
            original_query=query,
            hebrew_terms_from_step1=hebrew_terms,
            query_type=QueryType(result.get("query_type", "unknown")),
            realm=Realm(result.get("realm", "unknown")),
            breadth=Breadth(result.get("breadth", "standard")),
            search_method=SearchMethod(result.get("search_method", "trickle_up")),
            search_topics=result.get("search_topics", []),
            search_topics_hebrew=result.get("search_topics_hebrew", []),
            target_masechtos=result.get("target_masechtos", []),
            target_perakim=result.get("target_perakim", []),
            target_dapim=result.get("target_dapim", []),
            target_authors=result.get("target_authors", []),
            source_categories=source_categories,
            confidence=ConfidenceLevel(result.get("confidence", "medium")),
            needs_clarification=result.get("needs_clarification", False),
            clarification_question=result.get("clarification_question"),
            clarification_options=result.get("clarification_options", []),
            reasoning=result.get("reasoning", ""),
            search_description=result.get("search_description", ""),
        )
        
        # Log the analysis
        logger.info(f"[UNDERSTAND] Analysis complete:")
        logger.info(f"  Query type: {analysis.query_type.value}")
        logger.info(f"  Search topics (INYAN): {analysis.search_topics}")
        logger.info(f"  Search topics Hebrew: {analysis.search_topics_hebrew}")
        logger.info(f"  Target masechtos: {analysis.target_masechtos}")
        logger.info(f"  Target authors (for commentary): {analysis.target_authors}")
        logger.info(f"  Search method: {analysis.search_method.value}")
        logger.info(f"  Confidence: {analysis.confidence.value}")
        
        return analysis
        
    except json.JSONDecodeError as e:
        logger.error(f"[UNDERSTAND] JSON parse error: {e}")
        return _fallback_analysis(query, hebrew_terms, f"JSON parse error: {e}")
        
    except Exception as e:
        logger.error(f"[UNDERSTAND] Error: {e}")
        import traceback
        traceback.print_exc()
        return _fallback_analysis(query, hebrew_terms, str(e))


def _fallback_analysis(query: str, hebrew_terms: List[str], error: str) -> QueryAnalysis:
    """Create a low-confidence fallback analysis."""
    return QueryAnalysis(
        original_query=query,
        hebrew_terms_from_step1=hebrew_terms,
        query_type=QueryType.UNKNOWN,
        realm=Realm.UNKNOWN,
        breadth=Breadth.STANDARD,
        search_method=SearchMethod.HYBRID,
        search_topics=hebrew_terms,  # Best guess
        search_topics_hebrew=hebrew_terms,
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
    # Backward compatibility
    hebrew_term: str = None,
    original_query: str = None,
    step1_result: DecipherResult = None,
) -> QueryAnalysis:
    """
    Step 2: UNDERSTAND - Analyze the query with Claude.
    
    Creates a detailed QueryAnalysis datatype that tells Step 3:
    - WHAT to search (search_topics - the inyan)
    - WHERE to look (target_masechtos)
    - WHOSE commentary to fetch (target_authors)
    - HOW to search (search_method)
    """
    # Handle backward compatibility
    if hebrew_term is not None and hebrew_terms is None:
        hebrew_terms = [hebrew_term]
    if original_query is not None and query is None:
        query = original_query
    if step1_result is not None and decipher_result is None:
        decipher_result = step1_result
    
    # Extract from decipher_result
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
    logger.info("[STEP 2: UNDERSTAND] Analyzing query with Claude")
    logger.info("=" * 70)
    logger.info(f"  Original query: {query}")
    logger.info(f"  Hebrew terms from Step 1: {hebrew_terms}")
    
    # Have Claude analyze
    analysis = await analyze_with_claude(query, hebrew_terms)
    
    logger.info("=" * 70)
    logger.info("[STEP 2: UNDERSTAND] Complete")
    logger.info(f"  INYAN to search: {analysis.search_topics_hebrew}")
    logger.info(f"  WHERE to look: {analysis.target_masechtos}")
    logger.info(f"  WHOSE commentary: {analysis.target_authors}")
    logger.info("=" * 70)
    
    return analysis


# Alias
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
        (["רן", "שיטה", "ביטול חמץ", "תוספות", "רש\"י"], 
         "what is the rans shittah in bittul chometz and how is it different then tosfoses and rashis"),
    ]
    
    for hebrew_terms, query in test_cases:
        print(f"\nQuery: {query}")
        print(f"Hebrew terms: {hebrew_terms}")
        
        analysis = await understand(hebrew_terms=hebrew_terms, query=query)
        
        print(f"\nAnalysis:")
        print(f"  INYAN to search: {analysis.search_topics_hebrew}")
        print(f"  WHERE to look: {analysis.target_masechtos}")
        print(f"  WHOSE commentary: {analysis.target_authors}")
        print(f"  Search method: {analysis.search_method.value}")
        print(f"  Confidence: {analysis.confidence.value}")


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)-8s | %(message)s')
    asyncio.run(test_step_two())