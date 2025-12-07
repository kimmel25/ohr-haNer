"""
Sefaria Term Validator V2 - "First Valid Wins"
==============================================

ARCHITECTURAL CHANGE:
Instead of picking the variant with the MOST Sefaria hits,
we now return the FIRST variant that has ANY hits.

Why? Because the transliteration map generates variants in
PREFERENCE ORDER (כתיב מלא first). The "simpler" spelling
often has more hits in classical texts, but we want the
"fuller" modern spelling that users expect.

Example:
- Variants: [מיגו, מגו]  (in preference order)
- Sefaria hits: מיגו=300, מגו=500
- Old logic: Returns מגו (most hits)
- New logic: Returns מיגו (first valid)
"""

import httpx
import asyncio
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class SefariaValidator:
    """
    Validates Hebrew terms against Sefaria's corpus.
    
    KEY CHANGE: find_first_valid() returns first variant with ANY hits,
    rather than the variant with MOST hits.
    """
    
    BASE_URL = "https://www.sefaria.org/api/search-wrapper"
    
    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout
        self._cache: Dict[str, Dict] = {}
    
    async def validate_term(self, hebrew_term: str) -> Dict:
        """
        Check if a Hebrew term exists in Sefaria.
        
        Returns:
            {
                "found": True/False,
                "hits": 123,
                "sample_refs": ["Berachos 10a", ...],
                "term": "מיגו"
            }
        """
        # Check cache first
        if hebrew_term in self._cache:
            logger.debug(f"  Cache hit: {hebrew_term}")
            return self._cache[hebrew_term]
        
        logger.debug(f"  Validating: {hebrew_term}")
        
        try:
            async with httpx.AsyncClient(verify=False, timeout=self.timeout) as client:
                payload = {
                    "query": hebrew_term,
                    "type": "text",
                    "size": 5,
                }
                
                response = await client.post(self.BASE_URL, json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if "error" in data:
                        logger.warning(f"  Sefaria API error: {data['error']}")
                        return {"found": False, "hits": 0, "sample_refs": [], "term": hebrew_term}
                    
                    # Extract hit count
                    hits = data.get("hits", {}).get("total", 0)
                    if isinstance(hits, dict):
                        hits = hits.get("value", 0)
                    
                    # Extract sample references
                    results = data.get("hits", {}).get("hits", [])
                    sample_refs = []
                    for hit in results[:5]:
                        ref = hit.get("_id", "")
                        if ref:
                            clean_ref = ref.split(" (")[0] if " (" in ref else ref
                            sample_refs.append(clean_ref)
                    
                    result = {
                        "found": hits > 0,
                        "hits": hits,
                        "sample_refs": sample_refs,
                        "term": hebrew_term
                    }
                    
                    self._cache[hebrew_term] = result
                    
                    logger.debug(f"    → {hebrew_term}: {hits} hits")
                    
                    return result
                else:
                    logger.warning(f"  Sefaria API error: HTTP {response.status_code}")
                    return {"found": False, "hits": 0, "sample_refs": [], "term": hebrew_term}
                    
        except Exception as e:
            logger.error(f"  Sefaria validation error: {e}")
            return {"found": False, "hits": 0, "sample_refs": [], "term": hebrew_term, "error": str(e)}
    
    async def find_first_valid(
        self, 
        variants: List[str], 
        min_hits: int = 1
    ) -> Optional[Dict]:
        """
        Find the FIRST variant that exists in Sefaria.
        
        This is the KEY ARCHITECTURAL CHANGE.
        
        Instead of checking ALL variants and picking highest hits,
        we check variants IN ORDER and return the FIRST one that
        has >= min_hits.
        
        Args:
            variants: Hebrew variants in PREFERENCE ORDER (best first)
            min_hits: Minimum hits to consider valid (default 1)
        
        Returns:
            First valid variant's result dict, or None if none found
        
        Why this matters:
            variants = ["מיגו", "מגו"]
            
            Old logic (find_best_variant):
                - Check both concurrently
                - מיגו has 300 hits, מגו has 500 hits
                - Return מגו (wrong! user expects מיגו)
            
            New logic (find_first_valid):
                - Check מיגו first
                - מיגו has 300 hits (>= 1)
                - Return מיגו immediately (correct!)
        """
        if not variants:
            return None
        
        logger.info(f"  Checking {len(variants)} variants in preference order...")
        
        # Check variants ONE AT A TIME in order
        for i, variant in enumerate(variants):
            result = await self.validate_term(variant)
            
            if result.get("found") and result.get("hits", 0) >= min_hits:
                logger.info(f"  ✓ Found valid term at position {i+1}: '{variant}' ({result['hits']} hits)")
                return result
            else:
                logger.debug(f"    Position {i+1}: '{variant}' - not found or insufficient hits")
        
        logger.info(f"  ✗ No valid variants found")
        return None
    
    async def find_best_variant(self, variants: List[str]) -> Optional[Dict]:
        """
        DEPRECATED: Use find_first_valid() instead.
        
        This method is kept for backward compatibility but now
        just calls find_first_valid().
        
        The old behavior of "pick highest hits" is intentionally
        removed because it produced wrong results for כתיב מלא.
        """
        logger.warning("  find_best_variant() is deprecated. Use find_first_valid()")
        return await self.find_first_valid(variants)
    
    async def validate_variants(self, variants: List[str]) -> List[Dict]:
        """
        Validate multiple variants and return all results.
        
        Note: For most use cases, find_first_valid() is preferred
        because it stops early once a valid term is found.
        
        This method checks ALL variants (for diagnostic purposes).
        """
        if not variants:
            return []
        
        logger.info(f"  Validating {len(variants)} variants against Sefaria...")
        
        # Run all validations concurrently
        tasks = [self.validate_term(v) for v in variants]
        results = await asyncio.gather(*tasks)
        
        # Filter to found terms
        found_results = [r for r in results if r.get("found")]
        
        logger.info(f"  Found {len(found_results)}/{len(variants)} valid terms")
        
        return found_results
    
    def clear_cache(self):
        """Clear the validation cache."""
        self._cache.clear()
        logger.info("  Cache cleared")


# Global instance
_validator: Optional[SefariaValidator] = None


def get_validator() -> SefariaValidator:
    """Get global validator instance."""
    global _validator
    if _validator is None:
        _validator = SefariaValidator()
    return _validator


# ==========================================
#  TESTING
# ==========================================

async def test_first_valid_logic():
    """Test that find_first_valid() returns first match, not best match."""
    
    print("\n" + "=" * 70)
    print("SEFARIA VALIDATOR V2 - 'FIRST VALID WINS' TEST")
    print("=" * 70)
    
    validator = get_validator()
    
    # Test case: migu
    # מיגו should be returned even if מגו has more hits
    print("\n--- Test: migu variants ---")
    variants = ["מיגו", "מגו"]
    print(f"Variants in order: {variants}")
    
    result = await validator.find_first_valid(variants)
    
    if result:
        print(f"✓ Returned: '{result['term']}' ({result['hits']} hits)")
        if result['term'] == "מיגו":
            print("  CORRECT: First variant was returned!")
        else:
            print("  WRONG: Should have returned מיגו")
    else:
        print("✗ No valid variant found")
    
    # Test case: shaveh
    print("\n--- Test: shaveh variants ---")
    variants = ["שווה", "שוה"]
    print(f"Variants in order: {variants}")
    
    result = await validator.find_first_valid(variants)
    
    if result:
        print(f"✓ Returned: '{result['term']}' ({result['hits']} hits)")
    else:
        print("✗ No valid variant found")
    
    # Test case: checking both hits for comparison
    print("\n--- Diagnostic: Compare hit counts ---")
    
    test_pairs = [
        ("מיגו", "מגו"),
        ("שווה", "שוה"),
        ("מעניינו", "מענינו"),
    ]
    
    for full, simple in test_pairs:
        full_result = await validator.validate_term(full)
        simple_result = await validator.validate_term(simple)
        
        print(f"\n  {full}: {full_result.get('hits', 0)} hits")
        print(f"  {simple}: {simple_result.get('hits', 0)} hits")
        
        if full_result.get('hits', 0) < simple_result.get('hits', 0):
            print(f"  → Old logic would pick '{simple}' (wrong)")
            print(f"  → New logic picks '{full}' (correct)")
    
    print("\n" + "=" * 70)
    print("Test complete!")
    print("=" * 70)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    asyncio.run(test_first_valid_logic())