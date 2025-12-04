"""
Step 1: DECIPHER - COST-OPTIMIZED VERSION
==========================================

Changes from original:
1. TEST_MODE environment variable - skip Claude calls during testing
2. Permanent caching for transliteration resolutions
3. Confidence threshold auto-accept (skip Claude for obvious matches)
4. Reduced variant generation (5 instead of 15)
5. Cost tracking and logging

Turn user's transliteration into Hebrew terms.

Three-Tool Cascade:
1. Word Dictionary (instant, learns at runtime) - FREE
2. Transliteration Map → Generate variants → Verify - FREE
3. Vector Search (BEREL) → Claude picks best - EXPENSIVE (use sparingly)

Only escalates to expensive tools if needed.
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Optional
import asyncio

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# ==========================================
#  COST CONTROL FLAGS
# ==========================================

# TEST MODE: Set to True to skip expensive Claude calls during testing
# Usage: export TEST_MODE=true && python test_step_one.py
TEST_MODE = os.environ.get("TEST_MODE", "false").lower() == "true"

# Confidence threshold for auto-accepting vector matches (skip Claude)
AUTO_ACCEPT_THRESHOLD = float(os.environ.get("AUTO_ACCEPT_THRESHOLD", "0.85"))

# Maximum variants to generate (lower = less searching = lower cost)
MAX_VARIANTS = int(os.environ.get("MAX_VARIANTS", "5"))

# Cost tracking
_cost_tracker = {
    "claude_calls": 0,
    "vector_searches": 0,
    "claude_calls_saved_by_cache": 0,
    "claude_calls_saved_by_test_mode": 0,
    "claude_calls_saved_by_threshold": 0,
}


from tools.word_dictionary import get_dictionary
from tools.transliteration_map import (
    generate_hebrew_variants,
    generate_smart_variants,
    transliteration_confidence,
    normalize_query
)

# Logging
from logging_config import get_logger
logger = get_logger(__name__)

# Log startup configuration
if TEST_MODE:
    logger.warning("⚠️  TEST_MODE ENABLED - Claude calls will be skipped (SAVES MONEY)")
logger.info(f"Configuration: AUTO_ACCEPT_THRESHOLD={AUTO_ACCEPT_THRESHOLD}, MAX_VARIANTS={MAX_VARIANTS}")


# ==========================================
#  COST TRACKING UTILITIES
# ==========================================

def get_cost_stats() -> Dict:
    """Get current cost statistics"""
    return {
        **_cost_tracker,
        "estimated_cost_usd": _cost_tracker["claude_calls"] * 0.03,  # ~$0.03 per call
        "estimated_savings_usd": (
            _cost_tracker["claude_calls_saved_by_cache"] * 0.03 +
            _cost_tracker["claude_calls_saved_by_test_mode"] * 0.03 +
            _cost_tracker["claude_calls_saved_by_threshold"] * 0.03
        )
    }


def reset_cost_stats():
    """Reset cost tracking (call at start of test runs)"""
    global _cost_tracker
    _cost_tracker = {
        "claude_calls": 0,
        "vector_searches": 0,
        "claude_calls_saved_by_cache": 0,
        "claude_calls_saved_by_test_mode": 0,
        "claude_calls_saved_by_threshold": 0,
    }


def log_cost_summary():
    """Log cost summary (call at end of test runs)"""
    stats = get_cost_stats()
    logger.info("="*80)
    logger.info("COST SUMMARY")
    logger.info("="*80)
    logger.info(f"Claude API calls made: {stats['claude_calls']}")
    logger.info(f"Vector searches performed: {stats['vector_searches']}")
    logger.info(f"Estimated cost: ${stats['estimated_cost_usd']:.2f}")
    logger.info(f"")
    logger.info(f"SAVINGS:")
    logger.info(f"  Saved by caching: {stats['claude_calls_saved_by_cache']} calls")
    logger.info(f"  Saved by TEST_MODE: {stats['claude_calls_saved_by_test_mode']} calls")
    logger.info(f"  Saved by threshold: {stats['claude_calls_saved_by_threshold']} calls")
    logger.info(f"  Total estimated savings: ${stats['estimated_savings_usd']:.2f}")
    logger.info("="*80)


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
    # TOOL 1: WORD DICTIONARY (INSTANT, FREE)
    # ========================================
    
    logger.info("\n[TOOL 1] Word Dictionary - Checking cache...")
    
    dictionary = get_dictionary()
    dict_result = dictionary.lookup(query_normalized)
    
    if dict_result and dict_result["confidence"] == "high":
        logger.info(f"✓ DICTIONARY HIT! {dict_result['hebrew']}")
        logger.info(f"  Confidence: {dict_result['confidence']}")
        logger.info(f"  Usage: {dict_result['usage_count']} times")
        logger.info(f"  💰 SAVED $0.03 (no Claude call needed)")
        
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
    # TOOL 2: TRANSLITERATION MAP (FREE)
    # ========================================
    
    logger.info("\n[TOOL 2] Transliteration Map - Generating Hebrew variants...")

    # Generate FEWER variants to reduce search cost
    # OLD: max_variants=15, NEW: max_variants=5 (configurable)
    variants = generate_smart_variants(query_normalized, max_variants=MAX_VARIANTS)
    logger.info(f"  Generated {len(variants)} SMART Hebrew variants (max={MAX_VARIANTS})")

    # Fallback: If smart generation produces too few, try full generation
    if len(variants) < 3:
        logger.info(f"  → Smart generation produced only {len(variants)} variants, trying full generation...")
        variants = generate_hebrew_variants(query_normalized, max_variants=MAX_VARIANTS * 2)
        logger.info(f"  Generated {len(variants)} variants using full algorithm")

    if len(variants) == 0:
        logger.warning("  ✗ Could not generate any Hebrew variants")
        return {
            "success": False,
            "needs_clarification": True,
            "message": "Could not transliterate. Can you type in Hebrew or clarify?"
        }

    # Log first few variants for debugging
    logger.info(f"  Sample variants: {variants[:5]}")
    
    translit_confidence_score = transliteration_confidence(query_normalized)
    logger.info(f"  Transliteration confidence: {translit_confidence_score}")
    
    if len(variants) == 1 and translit_confidence_score == "high":
        # Only one possible spelling and high confidence
        hebrew_term = variants[0]
        logger.info(f"✓ SINGLE HIGH-CONFIDENCE VARIANT: {hebrew_term}")
        logger.info(f"  💰 SAVED $0.03 (no Claude call needed)")
        
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
    # TOOL 3: VECTOR SEARCH + CLAUDE (EXPENSIVE!)
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
        num_to_search = len(variants)  # Search all variants (now limited to 5)
        logger.info(f"  Searching vector index for {num_to_search} variants...")

        search_results = []
        for i, variant in enumerate(variants, 1):
            logger.debug(f"    Searching variant {i}/{num_to_search}: '{variant}'")
            results = vector_engine.search(variant, top_k=3)
            _cost_tracker["vector_searches"] += 1
            
            if results:
                logger.debug(f"      → Found {len(results)} results (top score: {results[0]['score']:.3f})")
                search_results.extend(results)
            else:
                logger.debug(f"      → No results")

        if not search_results:
            logger.warning("  ✗ No matches found in vector search for any variant")
            logger.warning(f"  Tried these Hebrew variants: {variants[:5]}...")
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
            he_preview = result.get('he_text', '')[:50]
            logger.info(f"    {i}. {result.get('ref', '')} (score: {result.get('score', 0):.3f})")
            logger.debug(f"       Hebrew: {he_preview}...")
        
        # NEW: Auto-accept if top match has very high confidence (skip Claude!)
        top_score = unique_results[0]['score'] if unique_results else 0
        if top_score > AUTO_ACCEPT_THRESHOLD:
            logger.info(f"  ✅ HIGH CONFIDENCE VECTOR MATCH: {top_score:.3f} > {AUTO_ACCEPT_THRESHOLD}")
            logger.info(f"  💰 SAVED $0.03 (skipping Claude verification)")
            _cost_tracker["claude_calls_saved_by_threshold"] += 1
            
            hebrew_term = unique_results[0]['he_text'][:50]
            
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
                "source_ref": unique_results[0].get('ref', ''),
                "alternatives": [],
                "needs_clarification": False,
                "message": f"Vector search found: {hebrew_term}"
            }
        
        # Medium confidence → Ask Claude to verify (or skip in TEST_MODE)
        logger.info(f"  → Score {top_score:.3f} < {AUTO_ACCEPT_THRESHOLD}, sending to Claude...")
        
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
#  CLAUDE VERIFICATION (WITH CACHING!)
# ==========================================

async def claude_verify_candidates(
    query: str,
    candidates: List[Dict]
) -> Dict:
    """
    Have Claude review vector search candidates and pick the best match.
    
    NEW FEATURES:
    1. Permanent caching (transliterations never change)
    2. TEST_MODE support (skip Claude during testing)
    3. Cost tracking
    """
    logger.info("  [CLAUDE] Verifying candidates...")
    
    # NEW: Check cache FIRST (permanent cache)
    from cache_manager import claude_cache
    cache_key = f"step1_verify:{query}"
    cached = claude_cache.get(cache_key)
    
    if cached:
        logger.info("  💰 CACHE HIT: Using cached Claude verification")
        logger.info(f"  Cached result: {cached.get('hebrew_term', '')}")
        _cost_tracker["claude_calls_saved_by_cache"] += 1
        return cached
    
    # NEW: TEST_MODE - skip Claude, use top vector result
    if TEST_MODE:
        logger.warning("  ⚠️  TEST_MODE: Skipping Claude call, using top vector match")
        _cost_tracker["claude_calls_saved_by_test_mode"] += 1
        
        # Use top candidate
        if candidates:
            top_candidate = candidates[0]
            result = {
                "success": True,
                "hebrew_term": top_candidate.get('he_text', '')[:50],
                "confidence": "medium",  # Lower confidence since Claude didn't verify
                "method": "vector",
                "source_ref": top_candidate.get('ref', ''),
                "explanation": f"TEST_MODE: Auto-selected top vector match (score: {top_candidate.get('score', 0):.3f})",
                "alternatives": [],
                "needs_clarification": False,
                "message": f"[TEST_MODE] Vector match: {top_candidate.get('he_text', '')[:50]}"
            }
            
            # Cache it
            claude_cache.set(cache_key, result)
            return result
        else:
            return {
                "success": False,
                "needs_clarification": True,
                "message": "[TEST_MODE] No candidates available"
            }
    
    # Import Claude (only when actually needed)
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
        logger.info("  💸 Making Claude API call... (cost: ~$0.03)")
        _cost_tracker["claude_calls"] += 1
        
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=800,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}]
        )
        
        response_text = response.content[0].text
        logger.debug(f"  [CLAUDE] Response: {response_text[:200]}...")

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
            
            final_result = {
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
            
            # NEW: Cache the result PERMANENTLY
            claude_cache.set(cache_key, final_result)
            logger.info("  💾 Cached result for future queries")
            
            return final_result
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
    
    reset_cost_stats()  # Reset cost tracking
    
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
    print(f"TEST_MODE: {TEST_MODE}")
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
    
    # Print cost summary
    log_cost_summary()


if __name__ == "__main__":
    # Run tests
    asyncio.run(test_step_one())