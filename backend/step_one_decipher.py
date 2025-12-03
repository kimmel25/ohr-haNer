"""
Step 1: DECIPHER
================

Turn user's transliteration into Hebrew terms.

Three-Tool Cascade:
1. Word Dictionary (instant, learns at runtime)
2. Transliteration Map → Generate variants → Verify
3. Vector Search (BEREL) → Claude picks best

Only escalates to expensive tools if needed.
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional
import asyncio

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from tools.word_dictionary import get_dictionary
from tools.transliteration_map import (
    generate_hebrew_variants,
    transliteration_confidence,
    normalize_query
)

# Logging
from logging_config import get_logger
logger = get_logger(__name__)


# ==========================================
#  STEP 1 MAIN FUNCTION
# ==========================================

async def decipher(query: str, user_context: Optional[Dict] = None) -> Dict:
    """
    Main entry point for Step 1: DECIPHER
    
    Args:
        query: User's transliterated input (e.g., "chezkas haguf")
        user_context: Optional context from previous steps (for feedback loops)
    
    Returns:
        {
            "success": True/False,
            "hebrew_term": "חזקת הגוף",
            "confidence": "high/medium/low",
            "method": "dictionary" | "transliteration" | "vector" | "claude",
            "alternatives": [],  # if confidence not high
            "needs_clarification": False,
            "message": "..."
        }
    """
    logger.info("=" * 80)
    logger.info("STEP 1: DECIPHER")
    logger.info("=" * 80)
    logger.info(f"Query: '{query}'")
    
    # Normalize query
    query_normalized = normalize_query(query)
    logger.info(f"Normalized: '{query_normalized}'")
    
    # ========================================
    # TOOL 1: WORD DICTIONARY (INSTANT)
    # ========================================
    
    logger.info("\n[TOOL 1] Word Dictionary - Checking cache...")
    
    dictionary = get_dictionary()
    dict_result = dictionary.lookup(query_normalized)
    
    if dict_result and dict_result["confidence"] == "high":
        logger.info(f"✓ DICTIONARY HIT! {dict_result['hebrew']}")
        logger.info(f"  Confidence: {dict_result['confidence']}")
        logger.info(f"  Usage: {dict_result['usage_count']} times")
        
        return {
            "success": True,
            "hebrew_term": dict_result["hebrew"],
            "confidence": "high",
            "method": "dictionary",
            "alternatives": [],
            "needs_clarification": False,
            "message": f"Found in dictionary: {dict_result['hebrew']}"
        }
    
    logger.info("  → Dictionary miss or low confidence, continuing...")
    
    # ========================================
    # TOOL 2: TRANSLITERATION MAP
    # ========================================
    
    logger.info("\n[TOOL 2] Transliteration Map - Generating Hebrew variants...")
    
    # Generate possible Hebrew spellings
    variants = generate_hebrew_variants(query_normalized, max_variants=50)
    logger.info(f"  Generated {len(variants)} possible Hebrew spellings")
    
    if len(variants) == 0:
        logger.warning("  ✗ Could not generate any Hebrew variants")
        return {
            "success": False,
            "needs_clarification": True,
            "message": "Could not transliterate. Can you type in Hebrew or clarify?"
        }
    
    # Log first few variants for debugging
    logger.info(f"  Sample variants: {variants[:5]}")
    
    # Check variants against known sources
    # Option A: Check against Sefaria API (slow but accurate)
    # Option B: Check against local embeddings (fast)
    # For now, let's use a simple heuristic and defer to vector search
    
    translit_confidence_score = transliteration_confidence(query_normalized)
    logger.info(f"  Transliteration confidence: {translit_confidence_score}")
    
    if len(variants) == 1 and translit_confidence_score == "high":
        # Only one possible spelling and high confidence
        hebrew_term = variants[0]
        logger.info(f"✓ SINGLE HIGH-CONFIDENCE VARIANT: {hebrew_term}")
        
        # Add to dictionary for future
        dictionary.add_entry(
            query_normalized,
            hebrew_term,
            confidence="high",
            source="transliteration"
        )
        
        return {
            "success": True,
            "hebrew_term": hebrew_term,
            "confidence": "high",
            "method": "transliteration",
            "alternatives": [],
            "needs_clarification": False,
            "message": f"Transliterated to: {hebrew_term}"
        }
    
    # Multiple variants or low confidence → need verification
    logger.info(f"  → Multiple variants or low confidence, escalating to vector search...")
    
    # ========================================
    # TOOL 3: VECTOR SEARCH + CLAUDE
    # ========================================
    
    logger.info("\n[TOOL 3] Vector Search + Claude Verification...")
    
    # Import vector search (only when needed)
    try:
        from vector_search import get_engine
        vector_engine = get_engine()
        
        if not vector_engine.is_ready():
            logger.warning("  ⚠️  Vector search not ready (embeddings not created)")
            
            # Fallback: return top transliteration variants for user to choose
            return {
                "success": False,
                "needs_clarification": True,
                "alternatives": variants[:5],
                "message": "Multiple possible spellings. Which did you mean?",
                "hebrew_variants": variants[:5]
            }
        
        # Search for each variant
        logger.info(f"  Searching vector index for {len(variants[:10])} variants...")
        
        search_results = []
        for variant in variants[:10]:  # Limit to top 10 to avoid too many searches
            results = vector_engine.search(variant, top_k=3)
            if results:
                search_results.extend(results)
        
        if not search_results:
            logger.warning("  ✗ No matches found in vector search")
            return {
                "success": False,
                "needs_clarification": True,
                "message": "Could not find matching Hebrew terms. Try rephrasing?"
            }
        
        logger.info(f"  Found {len(search_results)} potential matches")
        
        # Sort by score and remove duplicates
        search_results = sorted(search_results, key=lambda x: x['score'], reverse=True)
        
        # Deduplicate by Hebrew text
        seen_hebrew = set()
        unique_results = []
        for result in search_results:
            he_text = result.get('he_text', '')
            if he_text and he_text not in seen_hebrew:
                seen_hebrew.add(he_text)
                unique_results.append(result)
        
        logger.info(f"  Top 5 unique matches:")
        for i, result in enumerate(unique_results[:5], 1):
            logger.info(f"    {i}. {result.get('ref', '')} (score: {result.get('score', 0):.3f})")
        
        # If top match has very high confidence (>0.85), use it
        if unique_results and unique_results[0]['score'] > 0.85:
            top_match = unique_results[0]
            hebrew_term = top_match['he_text'][:50]  # First 50 chars
            
            logger.info(f"✓ HIGH CONFIDENCE VECTOR MATCH: {hebrew_term}")
            
            # Add to dictionary
            dictionary.add_entry(
                query_normalized,
                hebrew_term,
                confidence="high",
                source="vector"
            )
            
            return {
                "success": True,
                "hebrew_term": hebrew_term,
                "confidence": "high",
                "method": "vector",
                "source_ref": top_match.get('ref', ''),
                "alternatives": [],
                "needs_clarification": False,
                "message": f"Found via vector search: {hebrew_term}"
            }
        
        # Medium confidence → Ask Claude to verify
        logger.info("  → Sending to Claude for verification...")
        
        claude_result = await claude_verify_candidates(
            query_normalized,
            unique_results[:10]
        )
        
        if claude_result["success"]:
            # Add to dictionary
            dictionary.add_entry(
                query_normalized,
                claude_result["hebrew_term"],
                confidence=claude_result["confidence"],
                source="claude"
            )
        
        return claude_result
        
    except ImportError as e:
        logger.error(f"  ✗ Could not import vector search: {e}")
        
        # Fallback: return variants for user choice
        return {
            "success": False,
            "needs_clarification": True,
            "alternatives": variants[:5],
            "message": "Vector search unavailable. Which spelling did you mean?",
            "hebrew_variants": variants[:5]
        }


# ==========================================
#  CLAUDE VERIFICATION
# ==========================================

async def claude_verify_candidates(
    query: str,
    candidates: List[Dict]
) -> Dict:
    """
    Have Claude review vector search candidates and pick the best match.
    
    This is the most expensive step, only called when necessary.
    """
    logger.info("  [CLAUDE] Verifying candidates...")
    
    # Import Claude (only when needed)
    from anthropic import Anthropic
    import os
    
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("  ✗ ANTHROPIC_API_KEY not set")
        return {
            "success": False,
            "needs_clarification": True,
            "message": "Claude API unavailable"
        }
    
    client = Anthropic(api_key=api_key)
    
    # Format candidates for Claude
    candidates_text = "\n\n".join([
        f"[Candidate {i+1}]\n"
        f"Source: {c.get('ref', '')}\n"
        f"Hebrew: {c.get('he_text', '')[:200]}\n"
        f"Score: {c.get('score', 0):.3f}"
        for i, c in enumerate(candidates[:10])
    ])
    
    system_prompt = """You are a Torah scholar assistant helping identify Hebrew/Aramaic terms from transliterations.

Review the candidates from vector search and pick the best match for the user's query.

IMPORTANT:
- Match phonetically (ch=ח, sh=ש, tz=צ, s=ת in yeshivish)
- Consider context and meaning
- Be confident when there's a clear match
- Admit uncertainty if candidates don't match well

Return JSON:
{
  "matched": true/false,
  "hebrew_term": "The Hebrew/Aramaic term (first 50 chars)",
  "source_ref": "Where it appears",
  "confidence": "high/medium/low",
  "explanation": "Why this is the best match"
}"""

    user_message = f"""User's transliteration: "{query}"

Here are the top candidates from vector search:

{candidates_text}

Which candidate best matches the user's query?"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=800,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}]
        )
        
        response_text = response.content[0].text
        logger.info(f"  [CLAUDE] Response: {response_text[:200]}...")
        
        # Parse JSON
        import json
        import re
        
        # Extract JSON (handle markdown fences)
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        
        response_text = response_text.strip()
        if not response_text.startswith("{"):
            brace_idx = response_text.find("{")
            if brace_idx != -1:
                response_text = response_text[brace_idx:]
        
        result = json.loads(response_text)
        
        if result.get("matched"):
            logger.info(f"  ✓ CLAUDE MATCHED: {result.get('hebrew_term', '')}")
            
            return {
                "success": True,
                "hebrew_term": result.get("hebrew_term", ""),
                "confidence": result.get("confidence", "medium"),
                "method": "claude",
                "source_ref": result.get("source_ref", ""),
                "explanation": result.get("explanation", ""),
                "alternatives": [],
                "needs_clarification": False,
                "message": f"Claude identified: {result.get('hebrew_term', '')}"
            }
        else:
            logger.info(f"  ✗ Claude could not find good match")
            
            return {
                "success": False,
                "needs_clarification": True,
                "message": "Could not confidently identify Hebrew term. Can you clarify?",
                "explanation": result.get("explanation", "")
            }
        
    except Exception as e:
        logger.error(f"  ✗ Claude verification failed: {e}", exc_info=True)
        
        return {
            "success": False,
            "needs_clarification": True,
            "message": f"Claude verification error: {str(e)}"
        }


# ==========================================
#  CONVENIENCE FUNCTIONS
# ==========================================

async def decipher_batch(queries: List[str]) -> List[Dict]:
    """
    Decipher multiple queries (useful for testing).
    """
    results = []
    for query in queries:
        result = await decipher(query)
        results.append(result)
    return results


# ==========================================
#  TESTING
# ==========================================

async def test_step_one():
    """Test Step 1 with various queries"""
    
    test_cases = [
        # Easy cases (should hit dictionary)
        "bari vishma",
        "chezkas haguf",
        
        # Yeshivish spellings
        "kesubos",
        "shabbos",
        
        # Complex phrases (will need transliteration)
        "shaviya anafshe chaticha deisura",
        
        # Ambiguous (may need clarification)
        "chezka",
    ]
    
    print("=" * 80)
    print("STEP 1 TEST SUITE")
    print("=" * 80)
    
    for query in test_cases:
        print(f"\n🔍 Testing: '{query}'")
        print("-" * 60)
        
        result = await decipher(query)
        
        if result["success"]:
            print(f"✓ SUCCESS via {result['method']}")
            print(f"  Hebrew: {result['hebrew_term']}")
            print(f"  Confidence: {result['confidence']}")
        else:
            print(f"✗ NEEDS CLARIFICATION")
            print(f"  Message: {result.get('message', '')}")
            if result.get('alternatives'):
                print(f"  Alternatives: {result['alternatives'][:3]}")


if __name__ == "__main__":
    # Run tests
    asyncio.run(test_step_one())