"""
Sefaria Term Validator - COMPLETE FIX
======================================

Validates Hebrew term variants against Sefaria's actual corpus.
Uses Sefaria's FREE search API to check if a term exists and how common it is.

FIXES:
1. Changed from GET to POST (Sefaria requires POST for search-wrapper)
2. Fixed reference extraction (uses _id field, not _source.ref)
"""

import httpx
import asyncio
from typing import List, Dict, Optional
from urllib.parse import quote
import logging

logger = logging.getLogger(__name__)


class SefariaValidator:
    """
    Validates Hebrew terms against Sefaria's corpus.
    
    Uses the Sefaria search API to:
    1. Check if a term exists
    2. Get hit count (frequency)
    3. Get sample sources where it appears
    """
    
    BASE_URL = "https://www.sefaria.org/api/search-wrapper"
    
    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout
        self._cache: Dict[str, Dict] = {}  # Simple in-memory cache
    
    async def validate_term(self, hebrew_term: str) -> Dict:
        """
        Check if a Hebrew term exists in Sefaria.
        
        Returns:
            {
                "found": True/False,
                "hits": 123,  # Number of occurrences
                "sample_refs": ["Berachos 10a", ...],  # Sample sources
                "term": "מיגו"
            }
        """
        # Check cache
        if hebrew_term in self._cache:
            logger.debug(f"  Cache hit: {hebrew_term}")
            return self._cache[hebrew_term]
        
        logger.debug(f"  Validating: {hebrew_term}")
        
        try:
            async with httpx.AsyncClient(verify=False, timeout=self.timeout) as client:
                # FIXED: Use POST instead of GET
                # FIXED: Send as JSON body instead of query params
                payload = {
                    "query": hebrew_term,
                    "type": "text",
                    "size": 5,
                }
                
                # Use POST with JSON payload
                response = await client.post(self.BASE_URL, json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Check for error field (in case API still has issues)
                    if "error" in data:
                        logger.warning(f"  Sefaria API error: {data['error']}")
                        return {"found": False, "hits": 0, "sample_refs": [], "term": hebrew_term}
                    
                    # Extract results
                    hits = data.get("hits", {}).get("total", 0)
                    
                    # Handle both old and new Elasticsearch response formats
                    if isinstance(hits, dict):
                        hits = hits.get("value", 0)
                    
                    results = data.get("hits", {}).get("hits", [])
                    
                    # FIXED: Extract sample references from _id field, not _source.ref
                    sample_refs = []
                    for hit in results[:5]:
                        # The reference is in the _id field
                        ref = hit.get("_id", "")
                        if ref:
                            # Clean up the reference (remove version info in parentheses)
                            # "Ketubot 16a:13 (William Davidson Edition [he])" -> "Ketubot 16a:13"
                            clean_ref = ref.split(" (")[0] if " (" in ref else ref
                            sample_refs.append(clean_ref)
                    
                    result = {
                        "found": hits > 0,
                        "hits": hits,
                        "sample_refs": sample_refs,
                        "term": hebrew_term
                    }
                    
                    # Cache it
                    self._cache[hebrew_term] = result
                    
                    logger.debug(f"    → {hebrew_term}: {hits} hits")
                    if sample_refs:
                        logger.debug(f"       Sample: {sample_refs[0]}")
                    
                    return result
                else:
                    logger.warning(f"  Sefaria API error: HTTP {response.status_code}")
                    return {"found": False, "hits": 0, "sample_refs": [], "term": hebrew_term}
                    
        except Exception as e:
            logger.error(f"  Sefaria validation error: {e}")
            return {"found": False, "hits": 0, "sample_refs": [], "term": hebrew_term, "error": str(e)}
    
    async def validate_variants(self, variants: List[str]) -> List[Dict]:
        """
        Validate multiple Hebrew variants concurrently.
        
        Returns list sorted by hit count (most common first).
        """
        if not variants:
            return []
        
        logger.info(f"  Validating {len(variants)} variants against Sefaria...")
        
        # Run all validations concurrently
        tasks = [self.validate_term(v) for v in variants]
        results = await asyncio.gather(*tasks)
        
        # Filter to found terms and sort by hits
        found_results = [r for r in results if r.get("found")]
        found_results.sort(key=lambda x: x.get("hits", 0), reverse=True)
        
        logger.info(f"  Found {len(found_results)}/{len(variants)} valid terms")
        
        if found_results:
            top = found_results[0]
            logger.info(f"  Best match: '{top['term']}' ({top['hits']} hits)")
        
        return found_results
    
    async def find_best_variant(self, variants: List[str]) -> Optional[Dict]:
        """
        Find the best (most common) valid variant.
        
        Returns the variant with the highest hit count, or None if none found.
        """
        results = await self.validate_variants(variants)
        return results[0] if results else None


# Global instance
_validator: Optional[SefariaValidator] = None


def get_validator() -> SefariaValidator:
    """Get global validator instance"""
    global _validator
    if _validator is None:
        _validator = SefariaValidator()
    return _validator


# ==========================================
#  TESTING
# ==========================================

async def test_validator():
    """Test the Sefaria validator with common terms"""
    validator = get_validator()
    
    print("\n" + "="*80)
    print("SEFARIA VALIDATOR TEST - COMPLETE FIX")
    print("="*80)
    
    # Test cases: transliteration → expected Hebrew variants
    test_cases = [
        # (query, variants_to_test)
        ("migu", ["מיגו", "מגו"]),
        ("umdena", ["אומדנא", "אומדנה", "אמדנה"]),
        ("kal vchomer", ["קל וחומר", "קל וחמר"]),
        ("kesubos", ["כתובות"]),
    ]
    
    for query, variants in test_cases:
        print(f"\n🔍 Query: '{query}'")
        print(f"   Variants: {variants}")
        
        best = await validator.find_best_variant(variants)
        
        if best:
            print(f"   ✅ Best match: '{best['term']}' ({best['hits']} hits)")
            if best.get('sample_refs'):
                print(f"      Sample: {best['sample_refs'][0]}")
            else:
                print(f"      ⚠️  No sample refs returned")
        else:
            print(f"   ❌ No valid terms found")
    
    print("\n" + "="*80)
    print("Test complete!")
    print("="*80)


if __name__ == "__main__":
    # Set up logging for tests
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    asyncio.run(test_validator())