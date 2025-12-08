"""
Step 2: UNDERSTAND - Query Analysis & Strategy
==============================================

This step takes the Hebrew term from Step 1 and:
1. GATHER: Query Sefaria to see where it appears
2. ANALYZE: Use Claude to understand what the user likely wants
3. DECIDE: Create a search strategy

Key principle: "Think first, ask later"
- We make an intelligent guess based on Torah knowledge
- User sees results immediately
- They can refine if we guessed wrong

NO upfront questions that might gaslight users into specific sugyos.
"""

import asyncio
import json
import os
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

# Claude client
from anthropic import Anthropic

logger = logging.getLogger(__name__)


# ==========================================
#  DATA STRUCTURES
# ==========================================

class QueryType(Enum):
    """Types of Torah queries we can handle."""
    SUGYA_CONCEPT = "sugya_concept"      # A concept discussed in a specific sugya (חזקת הגוף)
    HALACHA_TERM = "halacha_term"        # A halachic term (מיגו, ברירה)
    DAF_REFERENCE = "daf_reference"       # Direct reference (כתובות ט)
    MASECHTA = "masechta"                 # Just a masechta name (כתובות)
    PERSON = "person"                      # A tanna/amora (רבא, רב הונא)
    PASUK = "pasuk"                        # Torah verse reference
    KLAL = "klal"                          # A כלל or principle (אין אדם מקנה...)
    AMBIGUOUS = "ambiguous"                # Needs clarification
    UNKNOWN = "unknown"                    # Couldn't determine


class FetchStrategy(Enum):
    """How to fetch and organize sources."""
    TRICKLE_UP = "trickle_up"      # Start from primary source, go up through layers
    TRICKLE_DOWN = "trickle_down"  # Start from halacha, trace back to source
    DIRECT = "direct"              # Just fetch the specific reference
    SURVEY = "survey"              # Show across multiple sugyos


@dataclass
class RelatedSugya:
    """A sugya related to the main one."""
    ref: str
    he_ref: str
    connection: str        # How it relates (e.g., "also discusses", "contrasts with")
    importance: str        # "primary", "secondary", "tangential"


@dataclass
class SearchStrategy:
    """
    The output of Step 2 - tells Step 3 what to do.
    """
    # What type of query is this?
    query_type: QueryType
    
    # The main source to focus on
    primary_source: Optional[str] = None      # e.g., "Ketubot 9a"
    primary_source_he: Optional[str] = None   # e.g., "כתובות ט׳ א"
    
    # Why we chose this source
    reasoning: str = ""
    
    # Other relevant sugyos (per your request - include if Claude thinks important)
    related_sugyos: List[RelatedSugya] = field(default_factory=list)
    
    # How to fetch sources
    fetch_strategy: FetchStrategy = FetchStrategy.TRICKLE_UP
    
    # How deep to go (Claude decides based on query)
    # "basic" = Gemara only
    # "standard" = + Rashi/Tosfos + Mishna/Chumash if applicable
    # "expanded" = + key Rishonim
    # "full" = everything available
    depth: str = "standard"
    
    # Confidence in our interpretation
    confidence: str = "high"  # "high", "medium", "low"
    
    # If low confidence, what to ask the user
    clarification_prompt: Optional[str] = None
    
    # Metadata
    sefaria_hits: int = 0
    hits_by_masechta: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "query_type": self.query_type.value,
            "primary_source": self.primary_source,
            "primary_source_he": self.primary_source_he,
            "reasoning": self.reasoning,
            "related_sugyos": [
                {
                    "ref": s.ref,
                    "he_ref": s.he_ref,
                    "connection": s.connection,
                    "importance": s.importance
                }
                for s in self.related_sugyos
            ],
            "fetch_strategy": self.fetch_strategy.value,
            "depth": self.depth,
            "confidence": self.confidence,
            "clarification_prompt": self.clarification_prompt,
            "sefaria_hits": self.sefaria_hits,
            "hits_by_masechta": self.hits_by_masechta
        }


# ==========================================
#  SEFARIA DATA GATHERING
# ==========================================

async def gather_sefaria_data(hebrew_term: str) -> Dict:
    """
    Phase 1: GATHER - Query Sefaria to understand where term appears.
    
    Returns raw data for Claude to analyze.
    """
    logger.info(f"[GATHER] Querying Sefaria for: {hebrew_term}")
    
    # Import here to avoid circular imports
    try:
        from tools.sefaria_client import get_sefaria_client, SearchResults
        client = get_sefaria_client()
        
        # Search for the term
        results = await client.search(hebrew_term, size=100)
        
        return {
            "query": hebrew_term,
            "total_hits": results.total_hits,
            "hits_by_category": results.hits_by_category,
            "hits_by_masechta": results.hits_by_masechta,
            "top_refs": results.top_refs[:10],
            "sample_hits": [
                {
                    "ref": h.ref,
                    "he_ref": h.he_ref,
                    "category": h.category,
                    "snippet": h.text_snippet[:200] if h.text_snippet else ""
                }
                for h in results.hits[:15]
            ]
        }
    except Exception as e:
        logger.error(f"[GATHER] Sefaria error: {e}")
        # Return empty data - Claude will work with what we have
        return {
            "query": hebrew_term,
            "total_hits": 0,
            "hits_by_category": {},
            "hits_by_masechta": {},
            "top_refs": [],
            "sample_hits": [],
            "error": str(e)
        }


# ==========================================
#  CLAUDE ANALYSIS
# ==========================================

# Initialize Claude client
_claude_client = None

def get_claude_client() -> Anthropic:
    """Get Claude client instance."""
    global _claude_client
    if _claude_client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        _claude_client = Anthropic(api_key=api_key)
    return _claude_client


ANALYSIS_SYSTEM_PROMPT = """You are a Torah scholar assistant helping to understand what a user is looking for when they search for a Hebrew term.

Your job: Given a Hebrew term and data about where it appears in Sefaria's corpus, determine:
1. What type of query is this?
2. What is the user most likely looking for?
3. What is the primary source (locus classicus) for this term?
4. Are there other important sugyos the user should know about?

IMPORTANT PRINCIPLES:
- Think like a chavrusa helping a fellow learner
- When a bachur asks about "חזקת הגוף", 80% of the time he means the sugya in Kesubos 9a
- Don't overthink - make a reasonable guess based on typical yeshiva learning
- If there are multiple important sugyos, note them but pick the most common one as primary
- Use yeshivish transliteration (sav not tav): Kesubos, Tosfos, etc.

QUERY TYPES:
- sugya_concept: A concept tied to a specific sugya (חזקת הגוף → Kesubos 9a)
- halacha_term: A halachic mechanism used across sugyos (מיגו, ברירה)
- daf_reference: User gave a specific daf (כתובות ט)
- masechta: Just a masechta name
- person: A tanna or amora
- pasuk: A פסוק reference
- klal: A broad principle (אין אדם מקנה דבר שלא בא לעולם)
- ambiguous: Could mean multiple things, genuinely unclear
- unknown: Can't determine

DEPTH GUIDANCE:
- "basic": Simple factual queries, just show the Gemara
- "standard": Most queries - Gemara + Rashi + Tosfos + relevant Mishna/Chumash
- "expanded": Complex concepts - add key Rishonim (Rambam, Rashba, Ritva)
- "full": Comprehensive research - everything available

Respond in JSON format only."""


ANALYSIS_USER_TEMPLATE = """The user searched for: "{hebrew_term}"

Here's what Sefaria found:
- Total hits: {total_hits}
- Hits by category: {hits_by_category}
- Hits by masechta: {hits_by_masechta}
- Top references: {top_refs}

Sample text snippets:
{sample_snippets}

Based on this, analyze:
1. What is the user most likely looking for?
2. What is the primary source for this term?
3. Are there other important related sugyos?
4. How deep should we go (basic/standard/expanded/full)?
5. How confident are you in this interpretation?

If you're not confident, suggest a brief clarifying question (but prefer making a reasonable guess).

Respond with this exact JSON structure:
{{
    "query_type": "sugya_concept|halacha_term|daf_reference|masechta|person|pasuk|klal|ambiguous|unknown",
    "primary_source": "The main Gemara reference (e.g., Kesubos 9a) or null if unclear",
    "primary_source_he": "Hebrew reference (e.g., כתובות ט׳ א) or null",
    "reasoning": "Brief explanation of why you chose this interpretation",
    "related_sugyos": [
        {{
            "ref": "Another important reference",
            "he_ref": "Hebrew version",
            "connection": "How it relates to the primary",
            "importance": "primary|secondary|tangential"
        }}
    ],
    "depth": "basic|standard|expanded|full",
    "confidence": "high|medium|low",
    "clarification_prompt": "Optional question if confidence is low, otherwise null"
}}"""


async def analyze_with_claude(hebrew_term: str, sefaria_data: Dict) -> SearchStrategy:
    """
    Phase 2: ANALYZE - Have Claude interpret the query.
    
    Claude looks at the Sefaria data and uses Torah knowledge to determine
    what the user is most likely looking for.
    """
    logger.info(f"[ANALYZE] Claude analyzing: {hebrew_term}")
    
    client = get_claude_client()
    
    # Format sample snippets
    sample_snippets = ""
    for i, hit in enumerate(sefaria_data.get("sample_hits", [])[:8], 1):
        sample_snippets += f"{i}. {hit['ref']}: {hit['snippet'][:150]}...\n"
    
    if not sample_snippets:
        sample_snippets = "(No sample text available)"
    
    # Build the prompt
    user_message = ANALYSIS_USER_TEMPLATE.format(
        hebrew_term=hebrew_term,
        total_hits=sefaria_data.get("total_hits", 0),
        hits_by_category=json.dumps(sefaria_data.get("hits_by_category", {}), ensure_ascii=False),
        hits_by_masechta=json.dumps(sefaria_data.get("hits_by_masechta", {}), ensure_ascii=False),
        top_refs=sefaria_data.get("top_refs", [])[:10],
        sample_snippets=sample_snippets
    )
    
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            system=ANALYSIS_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}]
        )
        
        response_text = response.content[0].text
        logger.debug(f"[ANALYZE] Claude response: {response_text[:300]}...")
        
        # Parse JSON response
        analysis = _parse_claude_response(response_text)
        
        # Build SearchStrategy from analysis
        strategy = SearchStrategy(
            query_type=QueryType(analysis.get("query_type", "unknown")),
            primary_source=analysis.get("primary_source"),
            primary_source_he=analysis.get("primary_source_he"),
            reasoning=analysis.get("reasoning", ""),
            fetch_strategy=FetchStrategy.TRICKLE_UP,  # Default for most queries
            depth=analysis.get("depth", "standard"),
            confidence=analysis.get("confidence", "medium"),
            clarification_prompt=analysis.get("clarification_prompt"),
            sefaria_hits=sefaria_data.get("total_hits", 0),
            hits_by_masechta=sefaria_data.get("hits_by_masechta", {})
        )
        
        # Add related sugyos
        for sugya in analysis.get("related_sugyos", []):
            strategy.related_sugyos.append(RelatedSugya(
                ref=sugya.get("ref", ""),
                he_ref=sugya.get("he_ref", ""),
                connection=sugya.get("connection", ""),
                importance=sugya.get("importance", "secondary")
            ))
        
        # Adjust fetch strategy based on query type
        if strategy.query_type == QueryType.DAF_REFERENCE:
            strategy.fetch_strategy = FetchStrategy.DIRECT
        elif strategy.query_type == QueryType.HALACHA_TERM:
            strategy.fetch_strategy = FetchStrategy.SURVEY
        elif strategy.query_type == QueryType.KLAL:
            strategy.fetch_strategy = FetchStrategy.TRICKLE_UP
            strategy.depth = "expanded"  # Klals usually need more context
        
        logger.info(f"[ANALYZE] Result: type={strategy.query_type.value}, "
                   f"primary={strategy.primary_source}, confidence={strategy.confidence}")
        
        return strategy
        
    except Exception as e:
        logger.error(f"[ANALYZE] Claude error: {e}", exc_info=True)
        
        # Return a basic strategy based on Sefaria data alone
        return _fallback_strategy(hebrew_term, sefaria_data)


def _parse_claude_response(response_text: str) -> Dict:
    """Parse JSON from Claude's response."""
    try:
        # Handle markdown code fences
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        
        response_text = response_text.strip()
        
        # Find JSON object
        if not response_text.startswith("{"):
            brace_index = response_text.find("{")
            if brace_index != -1:
                response_text = response_text[brace_index:]
        
        return json.loads(response_text)
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Claude JSON: {e}")
        logger.error(f"Response: {response_text[:500]}")
        return {}


def _fallback_strategy(hebrew_term: str, sefaria_data: Dict) -> SearchStrategy:
    """
    Create a basic strategy when Claude analysis fails.
    Uses Sefaria data to make reasonable guesses.
    """
    logger.info("[ANALYZE] Using fallback strategy")
    
    # Find the masechta with most hits
    hits_by_masechta = sefaria_data.get("hits_by_masechta", {})
    primary_masechta = None
    if hits_by_masechta:
        primary_masechta = max(hits_by_masechta.items(), key=lambda x: x[1])[0]
    
    # Use top ref if available
    top_refs = sefaria_data.get("top_refs", [])
    primary_source = top_refs[0] if top_refs else None
    
    return SearchStrategy(
        query_type=QueryType.SUGYA_CONCEPT,
        primary_source=primary_source,
        reasoning="Based on Sefaria search results (Claude analysis unavailable)",
        fetch_strategy=FetchStrategy.TRICKLE_UP,
        depth="standard",
        confidence="low",
        clarification_prompt=f"I found this term in multiple places. Could you tell me more about what you're looking for?",
        sefaria_hits=sefaria_data.get("total_hits", 0),
        hits_by_masechta=hits_by_masechta
    )


# ==========================================
#  MAIN STEP 2 FUNCTION
# ==========================================

async def understand(hebrew_term: str, original_query: str = None) -> SearchStrategy:
    """
    Main entry point for Step 2: UNDERSTAND
    
    Takes the Hebrew term from Step 1 and figures out what the user wants.
    
    Args:
        hebrew_term: Hebrew term from Step 1 (e.g., "חזקת הגוף")
        original_query: Original transliteration (e.g., "chezkas haguf") for context
    
    Returns:
        SearchStrategy telling Step 3 what to do
    """
    logger.info("=" * 80)
    logger.info("STEP 2: UNDERSTAND")
    logger.info("=" * 80)
    logger.info(f"  Hebrew term: {hebrew_term}")
    if original_query:
        logger.info(f"  Original query: {original_query}")
    
    # Phase 1: GATHER - Get Sefaria data
    logger.info("\n[Phase 1: GATHER]")
    sefaria_data = await gather_sefaria_data(hebrew_term)
    
    logger.info(f"  Sefaria hits: {sefaria_data.get('total_hits', 0)}")
    logger.info(f"  By masechta: {sefaria_data.get('hits_by_masechta', {})}")
    
    # Phase 2: ANALYZE - Have Claude interpret
    logger.info("\n[Phase 2: ANALYZE]")
    strategy = await analyze_with_claude(hebrew_term, sefaria_data)
    
    # Phase 3: DECIDE (implicit in strategy creation)
    logger.info("\n[Phase 3: DECIDE]")
    logger.info(f"  Query type: {strategy.query_type.value}")
    logger.info(f"  Primary source: {strategy.primary_source}")
    logger.info(f"  Fetch strategy: {strategy.fetch_strategy.value}")
    logger.info(f"  Depth: {strategy.depth}")
    logger.info(f"  Confidence: {strategy.confidence}")
    
    if strategy.related_sugyos:
        logger.info(f"  Related sugyos: {len(strategy.related_sugyos)}")
        for s in strategy.related_sugyos:
            logger.info(f"    - {s.ref} ({s.importance}): {s.connection}")
    
    if strategy.clarification_prompt:
        logger.info(f"  Clarification needed: {strategy.clarification_prompt}")
    
    logger.info("=" * 80)
    
    return strategy


# ==========================================
#  TESTING
# ==========================================

async def test_understand():
    """Test the understand function."""
    
    print("=" * 70)
    print("STEP 2 TEST: UNDERSTAND")
    print("=" * 70)
    
    test_cases = [
        ("חזקת הגוף", "chezkas haguf"),
        ("מיגו", "migu"),
        ("ברי ושמא", "bari vishma"),
        ("כתובות ט", "kesubos 9"),
    ]
    
    for hebrew, original in test_cases:
        print(f"\n{'='*60}")
        print(f"Testing: {hebrew} ({original})")
        print("=" * 60)
        
        strategy = await understand(hebrew, original)
        
        print(f"\nResult:")
        print(f"  Type: {strategy.query_type.value}")
        print(f"  Primary: {strategy.primary_source}")
        print(f"  Reasoning: {strategy.reasoning[:100]}...")
        print(f"  Confidence: {strategy.confidence}")
        
        if strategy.related_sugyos:
            print(f"  Related:")
            for s in strategy.related_sugyos[:3]:
                print(f"    - {s.ref}: {s.connection}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    asyncio.run(test_understand())
