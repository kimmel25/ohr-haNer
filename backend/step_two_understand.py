"""
Step 2: UNDERSTAND - Query Analysis and Strategy Determination
COMPLETE VERSION WITH MASTER KB INTEGRATION BUILT-IN
=====================================================
This file includes ALL Master KB enhancements.
Simply replace your existing step_two_understand.py with this file.

FIXES IN THIS VERSION:
- Added explicit instructions to prefer Bavli over Yerushalmi
- Added validation for constructed refs
- Better guidance for comparison queries
"""

import logging
import json
import re
from typing import Dict, List, Optional
from anthropic import Anthropic
from pydantic import ValidationError

# Core models
from models import (
    SearchStrategy,
    QueryType,
    FetchStrategy,
    ConfidenceLevel,
)

# Configuration
from config import get_settings

# Sefaria tools
from tools.sefaria_client import get_sefaria_client

# MASTER KB INTEGRATION - Helper functions
from phase2_integration_helpers import (
    should_use_smart_gather,
    execute_smart_gather,
    format_for_claude,
    get_author_handling_instructions,
    debug_author_detection,
    log_integration_status,
)

logger = logging.getLogger(__name__)
settings = get_settings()

# ==========================================
# TRADITIONAL SEFARIA GATHERING (for concepts only)
# ==========================================

async def gather_sefaria_data(term: str) -> Dict:
    """
    Traditional Sefaria data gathering for a single term.
    Used only for concept queries (no authors detected).
    
    Args:
        term: Hebrew term to search
    
    Returns:
        Dictionary with search results
    """
    try:
        client = get_sefaria_client()
        # sefaria_client.search() returns a SearchResults dataclass, NOT a dict
        result = await client.search(term, size=100)
        
        # FIX: Use attribute access instead of .get() - SearchResults is a dataclass
        total_hits = result.total_hits
        hits = result.hits  # List of SearchHit dataclass objects
        
        # Extract top refs
        # FIX: SearchHit is a dataclass, use attribute access
        top_refs = [hit.ref for hit in hits[:20]]
        
        # Extract categories
        categories = {}
        for hit in hits:
            # FIX: Use attribute access - SearchHit is a dataclass
            cat = hit.category
            categories[cat] = categories.get(cat, 0) + 1
        
        return {
            'total_hits': total_hits,
            'top_refs': top_refs,
            'categories': categories,
            'search_success': True
        }
        
    except Exception as e:
        logger.error(f"[GATHER] Error searching for '{term}': {e}")
        return {
            'search_success': False,
            'error': str(e)
        }

# ==========================================
# CLAUDE ANALYSIS
# ==========================================

async def analyze_with_claude(
    query: str,
    hebrew_terms: List[str],
    sefaria_data: Dict
) -> SearchStrategy:
    """
    Use Claude to analyze the query and determine search strategy.
    
    Args:
        query: Original user query
        hebrew_terms: List of Hebrew terms
        sefaria_data: Data from Sefaria (smart or traditional)
    
    Returns:
        SearchStrategy object
    """
    logger.info("[ANALYZE] Sending to Claude for analysis")
    
    # Format Sefaria data using Master KB formatter
    sefaria_context = format_for_claude(sefaria_data)
    
    # Build user prompt
    user_prompt = f"""
Analyze this Torah learning query and determine the search strategy.

Original Query: {query}
Hebrew Terms: {hebrew_terms}

Sefaria Data:
{sefaria_context}

Based on this information, determine:
1. query_type - What kind of query is this?
2. fetch_strategy - How should we fetch sources?
3. primary_sources - Which sources should we fetch?
4. related_sugyot - Any related sugyot to consider?
5. confidence - How confident are you?
6. clarification_prompt - Any clarification needed?

Return ONLY a JSON object with this structure:
{{
  "query_type": "sugya_concept" | "halacha_term" | "daf_reference" | "masechta" | "person" | "pasuk" | "klal" | "comparison" | "ambiguous" | "unknown",
  "fetch_strategy": "trickle_up" | "trickle_down" | "direct" | "survey" | "multi_term",
  "primary_sources": ["source1", "source2"],
  "related_sugyot": ["sugya1", "sugya2"] or null,
  "confidence": "high" | "medium" | "low",
  "clarification_prompt": "question for user" or null,
  "reasoning": "brief explanation"
}}
"""

    # Build system prompt with Master KB author handling
    # FIXED: Added explicit Bavli preference and ref validation instructions
    system_prompt = f"""You are a Torah scholar assistant specializing in understanding Torah learning queries.

Your task is to analyze the query and Sefaria data to determine the best search strategy.

Query Types:
- sugya_concept: Asking about a concept in a specific sugya (e.g., "chazakah in Bava Metzia")
- halacha_term: Asking about a halachic term across sources (e.g., "what is migo")
- daf_reference: Direct daf reference (e.g., "Ketubot 7b")
- masechta: Just masechta name (e.g., "Pesachim")
- person: Asking about a Tanna/Amora (e.g., "Rabbi Akiva")
- pasuk: Torah verse reference
- klal: General principle (e.g., "ein adam makneh")
- comparison: Comparing multiple authorities/views (e.g., "Ran vs Tosafot")
- ambiguous: Multiple possible interpretations
- unknown: Cannot determine

Fetch Strategies:
- trickle_up: Start from Gemara and go up through commentaries
- trickle_down: Start from later authorities and trace back
- direct: Direct fetch of specific reference (use for clarification needed)
- survey: Broad survey across sources
- multi_term: Multiple terms need separate handling

{get_author_handling_instructions()}

CRITICAL GUIDELINES FOR PRIMARY_SOURCES:

1. **BAVLI ONLY**: The Rishonim (Rashi, Tosafot, Ran, Rashba, Ritva, Meiri) wrote commentaries on the BAVLI (Babylonian Talmud), NOT on the Yerushalmi (Jerusalem Talmud).
   - CORRECT: "Ran on Pesachim 4b", "Tosafot on Bava Metzia 10a"
   - WRONG: "Ran on Jerusalem Talmud Pesachim" (DOES NOT EXIST!)
   - WRONG: "Tosafot on Yerushalmi" (DOES NOT EXIST!)

2. **USE PROVIDED REFS**: If the Sefaria data shows a "constructed_ref" for an author, USE THAT EXACT REF. Do not invent your own.

3. **DAF FORMAT**: Bavli uses daf format like "4b", "10a". Yerushalmi uses perek:halacha format like "2:2:6:2".
   - If you see a ref with format like "2:2:6:2", it's Yerushalmi - DO NOT use it for Rishonim.
   - If you see a ref with format like "4b", it's Bavli - this is correct.

4. **PRIMARY SUGYA**: Look at the "Primary sugya" in the Sefaria data. Use this masechta+daf for constructing commentary refs.

5. **VALIDATE BEFORE OUTPUT**: Before returning primary_sources, verify:
   - No "Jerusalem Talmud" or "Yerushalmi" in any source
   - Commentary refs follow the pattern "Author on Masechta Daf" (e.g., "Ran on Pesachim 4b")
   - All refs are from BAVLI

6. For concept queries: Use the primary_sugya from Sefaria data (ensure it's Bavli)
7. For author queries: Use the constructed Commentary reference (e.g., "Ran on Pesachim 4b")
8. For comparison queries: Include all relevant author references, all based on the SAME Bavli sugya
9. Always prefer actual Torah sources over dictionaries or modern works
10. If uncertain, set confidence to "low" and provide clarification_prompt
11. Keep reasoning brief (1-2 sentences)

Return ONLY valid JSON, no preamble or markdown.
"""

    try:
        # Call Claude
        client = Anthropic(api_key=settings.anthropic_api_key)
        
        response = client.messages.create(
            model=settings.claude_model,
            max_tokens=2000,
            temperature=0,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )
        
        # Extract response
        response_text = response.content[0].text
        
        # Clean and parse JSON
        response_text = response_text.strip()
        # Remove markdown code fences if present
        response_text = re.sub(r'^```json\s*', '', response_text)
        response_text = re.sub(r'\s*```$', '', response_text)
        
        # Parse JSON
        strategy_dict = json.loads(response_text)
        
        # VALIDATION: Check for Yerushalmi refs and fix them
        primary_sources = strategy_dict.get('primary_sources', [])
        validated_sources = []
        for source in primary_sources:
            if 'Jerusalem Talmud' in source or 'Yerushalmi' in source:
                logger.warning(f"[ANALYZE] Removing invalid Yerushalmi ref: {source}")
                # Try to fix it by extracting just the masechta
                # This is a safety net - ideally Claude shouldn't generate these
                continue
            validated_sources.append(source)
        
        strategy_dict['primary_sources'] = validated_sources
        
        # Convert to SearchStrategy
        strategy = SearchStrategy(**strategy_dict)
        
        logger.info(f"[ANALYZE] Claude analysis complete:")
        logger.info(f"  Query type: {strategy.query_type}")
        logger.info(f"  Fetch strategy: {strategy.fetch_strategy}")
        logger.info(f"  Primary sources: {strategy.primary_sources[:3] if strategy.primary_sources else []}")
        logger.info(f"  Confidence: {strategy.confidence}")
        
        return strategy
        
    except json.JSONDecodeError as e:
        logger.error(f"[ANALYZE] JSON parse error: {e}")
        logger.error(f"[ANALYZE] Raw response: {response_text[:500]}")
        
        return SearchStrategy(
            query_type=QueryType.AMBIGUOUS,
            fetch_strategy=FetchStrategy.DIRECT,
            primary_sources=[],
            confidence=ConfidenceLevel.LOW,
            clarification_prompt="I had trouble understanding your query. Could you rephrase it?",
            reasoning="Failed to validate query analysis"
        )
        
    except ValidationError as e:
        logger.error(f"[ANALYZE] Strategy validation error: {e}")
        
        return SearchStrategy(
            query_type=QueryType.AMBIGUOUS,
            fetch_strategy=FetchStrategy.DIRECT,
            primary_sources=[],
            confidence=ConfidenceLevel.LOW,
            clarification_prompt="I had trouble understanding your query. Could you rephrase it?",
            reasoning="Failed to validate query analysis"
        )
        
    except Exception as e:
        logger.error(f"[ANALYZE] Error during Claude analysis: {e}")
        
        return SearchStrategy(
            query_type=QueryType.UNKNOWN,
            fetch_strategy=FetchStrategy.DIRECT,
            primary_sources=[],
            confidence=ConfidenceLevel.LOW,
            clarification_prompt="I encountered an error. Could you try rephrasing your query?",
            reasoning=f"Error during analysis: {str(e)}"
        )

# ==========================================
# MAIN UNDERSTAND FUNCTION
# ==========================================

async def understand(
    hebrew_terms: List[str] = None,
    query: str = None,
    decipher_result: Dict = None,
    # Backward compatibility parameters
    hebrew_term: str = None,
    original_query: str = None,
    step1_result: Dict = None,
) -> SearchStrategy:
    """
    Step 2: Understand the query and determine search strategy.
    NOW WITH MASTER KB INTEGRATION!
    
    Supports both old and new calling conventions for backward compatibility.
    
    New signature:
        understand(hebrew_terms: List[str], query: str, decipher_result: Dict)
    
    Old signature (backward compatible):
        understand(hebrew_term: str, original_query: str, step1_result: Dict)
    
    Args:
        hebrew_terms: List of Hebrew terms from Step 1 (new style)
        query: Original user query (new style)
        decipher_result: Complete result from Step 1 (new style)
        hebrew_term: Single Hebrew term (old style - backward compat)
        original_query: Original query (old style - backward compat)
        step1_result: Step 1 result (old style - backward compat)
    
    Returns:
        SearchStrategy object
    """
    # Handle backward compatibility
    if hebrew_term is not None and hebrew_terms is None:
        # Old style call with single term
        hebrew_terms = [hebrew_term]
    
    if original_query is not None and query is None:
        query = original_query
    
    if step1_result is not None and decipher_result is None:
        decipher_result = step1_result
    
    # Extract all terms from decipher_result if available
    # NOTE: step1_result/decipher_result is a Pydantic model, not a dict
    if decipher_result:
        # Try to get hebrew_terms from the result object
        if hasattr(decipher_result, 'hebrew_terms') and decipher_result.hebrew_terms:
            hebrew_terms = decipher_result.hebrew_terms
            logger.debug(f"[UNDERSTAND] Extracted {len(hebrew_terms)} terms from decipher_result")
        # Fallback: if only hebrew_term (singular) is set, use it
        elif hasattr(decipher_result, 'hebrew_term') and decipher_result.hebrew_term:
            if not hebrew_terms or hebrew_terms == [hebrew_term]:
                hebrew_terms = [decipher_result.hebrew_term]
                logger.debug(f"[UNDERSTAND] Using single term from decipher_result")
    
    # Validation
    if not hebrew_terms:
        logger.error("[UNDERSTAND] No hebrew_terms provided")
        return SearchStrategy(
            query_type=QueryType.UNKNOWN,
            fetch_strategy=FetchStrategy.DIRECT,
            primary_sources=[],
            confidence=ConfidenceLevel.LOW,
            clarification_prompt="No Hebrew terms were provided to analyze.",
            reasoning="Missing hebrew_terms parameter"
        )
    
    if not query:
        logger.error("[UNDERSTAND] No query provided")
        return SearchStrategy(
            query_type=QueryType.UNKNOWN,
            fetch_strategy=FetchStrategy.DIRECT,
            primary_sources=[],
            confidence=ConfidenceLevel.LOW,
            clarification_prompt="No query text was provided.",
            reasoning="Missing query parameter"
        )
    
    logger.info("=" * 70)
    logger.info("[UNDERSTAND] Step 2: Understanding query with Master KB")
    logger.info("=" * 70)
    logger.info(f"  Query: {query}")
    logger.info(f"  Hebrew terms: {hebrew_terms}")
    
    # Log Master KB integration status
    log_integration_status()
    
    # Debug author detection
    debug_info = debug_author_detection(hebrew_terms)
    logger.debug(f"[UNDERSTAND] Author detection results: {debug_info}")
    
    # Handle empty results (double-check after all parameter handling)
    if not hebrew_terms:
        logger.warning("[UNDERSTAND] No Hebrew terms after parameter processing")
        return SearchStrategy(
            query_type=QueryType.UNKNOWN,
            fetch_strategy=FetchStrategy.DIRECT,
            primary_sources=[],
            confidence=ConfidenceLevel.LOW,
            clarification_prompt="I couldn't identify any Hebrew terms in your query. Could you rephrase?",
            reasoning="No Hebrew terms identified"
        )
    
    # Handle single term (simple case)
    if len(hebrew_terms) == 1:
        term = hebrew_terms[0]
        logger.info(f"[UNDERSTAND] Single term query: {term}")
        
        # Check if it's an author
        if should_use_smart_gather([term]):
            logger.info("[UNDERSTAND] Single author query detected")
            
            return SearchStrategy(
                query_type=QueryType.PERSON,
                fetch_strategy=FetchStrategy.DIRECT,
                primary_sources=[],
                confidence=ConfidenceLevel.LOW,
                clarification_prompt=f"I see you're asking about {term}. Which masechta or topic would you like me to search in?",
                reasoning="Author mentioned without specific topic"
            )
        
        # Concept - do simple search
        logger.info("[UNDERSTAND] Single concept query")
        sefaria_data = {term: await gather_sefaria_data(term)}
        
        # Analyze with Claude
        strategy = await analyze_with_claude(query, hebrew_terms, sefaria_data)
        return strategy
    
    # Handle multiple terms (mixed query - the main case)
    logger.info(f"[UNDERSTAND] Mixed query with {len(hebrew_terms)} terms")
    
    # MASTER KB INTEGRATION POINT
    # Determine if we should use smart gathering
    if should_use_smart_gather(hebrew_terms):
        logger.info("[UNDERSTAND] Authors detected - using smart gathering (Master KB)")
        
        # Execute smart gathering with Master KB
        sefaria_data = await execute_smart_gather(hebrew_terms, query)
        
    else:
        logger.info("[UNDERSTAND] No authors detected - using traditional gathering")
        
        # Traditional gathering for concepts only
        sefaria_data = {}
        for term in hebrew_terms:
            logger.info(f"[GATHER] Querying Sefaria for: {term}")
            result = await gather_sefaria_data(term)
            sefaria_data[term] = result
    
    # Analyze with Claude
    strategy = await analyze_with_claude(query, hebrew_terms, sefaria_data)
    
    logger.info("=" * 70)
    logger.info(f"[UNDERSTAND] Step 2 complete: {strategy.query_type}")
    logger.info("=" * 70)
    
    return strategy

# ==========================================
# ENTRY POINT
# ==========================================

async def run_step_two(
    hebrew_terms: List[str] = None,
    query: str = None,
    decipher_result: Dict = None,
    # Backward compatibility
    hebrew_term: str = None,
    original_query: str = None,
    step1_result: Dict = None
) -> SearchStrategy:
    """
    Entry point for Step 2.
    Supports both old and new calling conventions.
    
    Args:
        hebrew_terms: List of Hebrew terms from Step 1 (new style)
        query: Original user query (new style)
        decipher_result: Complete result from Step 1 (new style)
        hebrew_term: Single Hebrew term (old style - backward compat)
        original_query: Original query (old style - backward compat)
        step1_result: Step 1 result (old style - backward compat)
    
    Returns:
        SearchStrategy object
    """
    return await understand(
        hebrew_terms=hebrew_terms,
        query=query,
        decipher_result=decipher_result,
        hebrew_term=hebrew_term,
        original_query=original_query,
        step1_result=step1_result
    )