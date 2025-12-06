"""
Sefaria Term Validator - DIAGNOSTIC VERSION
===========================================

This version includes detailed logging of API responses to diagnose
why we're getting 0 hits for valid terms.
"""

import httpx
import asyncio
import json
from typing import List, Dict, Optional
from urllib.parse import quote
import logging

logger = logging.getLogger(__name__)


class SefariaValidator:
    """
    Validates Hebrew terms against Sefaria's corpus.
    
    DIAGNOSTIC VERSION - Logs full API responses
    """
    
    BASE_URL = "https://www.sefaria.org/api/search-wrapper"
    
    def __init__(self, timeout: float = 10.0, verbose: bool = False):
        self.timeout = timeout
        self.verbose = verbose
        self._cache: Dict[str, Dict] = {}
    
    async def validate_term(self, hebrew_term: str) -> Dict:
        """
        Check if a Hebrew term exists in Sefaria.
        
        Returns:
            {
                "found": True/False,
                "hits": 123,
                "sample_refs": [...],
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
                params = {
                    "query": hebrew_term,
                    "type": "text",
                    "size": 5,
                }
                
                response = await client.post(self.BASE_URL, json=params)  # ✅                
                # LOG THE RAW RESPONSE
                if self.verbose or logger.level <= logging.DEBUG:
                    logger.debug(f"\n  === RAW API RESPONSE FOR '{hebrew_term}' ===")
                    logger.debug(f"  Status Code: {response.status_code}")
                    logger.debug(f"  URL: {response.url}")
                    
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            # Log the keys
                            logger.debug(f"  JSON Keys: {list(data.keys())}")
                            
                            # Log the full response (or truncated if too long)
                            json_str = json.dumps(data, ensure_ascii=False, indent=2)
                            if len(json_str) > 1000:
                                json_str = json_str[:1000] + "\n... (truncated, see full response below)"
                            logger.debug(f"  JSON Response:\n{json_str}")
                            
                        except json.JSONDecodeError:
                            logger.error(f"  Failed to parse JSON response")
                            logger.error(f"  Raw text: {response.text[:500]}")
                    else:
                        logger.error(f"  HTTP Error: {response.status_code}")
                        logger.error(f"  Response: {response.text[:500]}")
                    
                    logger.debug(f"  === END RAW RESPONSE ===\n")
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Try to extract hits - with detailed logging
                    logger.debug(f"  Parsing hits for '{hebrew_term}'...")
                    
                    # Check if 'hits' field exists
                    if "hits" not in data:
                        logger.warning(f"  ⚠️  No 'hits' field in response for '{hebrew_term}'")
                        logger.warning(f"  Available fields: {list(data.keys())}")
                        return {"found": False, "hits": 0, "sample_refs": [], "term": hebrew_term}
                    
                    hits_field = data.get("hits", {})
                    logger.debug(f"  'hits' field type: {type(hits_field)}")
                    
                    # Extract total hits
                    if isinstance(hits_field, dict):
                        # Check for 'total' field
                        if "total" not in hits_field:
                            logger.warning(f"  ⚠️  No 'total' field in hits for '{hebrew_term}'")
                            logger.warning(f"  hits fields: {list(hits_field.keys())}")
                        
                        total_field = hits_field.get("total", 0)
                        logger.debug(f"  'total' field type: {type(total_field)}")
                        logger.debug(f"  'total' field value: {total_field}")
                        
                        # Handle both response formats
                        if isinstance(total_field, dict):
                            hits = total_field.get("value", 0)
                            logger.debug(f"  Extracted from dict: {hits} hits")
                        else:
                            hits = total_field if isinstance(total_field, int) else 0
                            logger.debug(f"  Direct value: {hits} hits")
                    else:
                        logger.warning(f"  ⚠️  'hits' is not a dict: {hits_field}")
                        hits = 0
                    
                    # Extract sample results
                    sample_refs = []
                    results = hits_field.get("hits", []) if isinstance(hits_field, dict) else []
                    
                    logger.debug(f"  Found {len(results)} result objects")
                    
                    for hit in results[:5]:
                        if isinstance(hit, dict):
                            # Try multiple possible locations for the reference
                            ref = (
                                hit.get("_source", {}).get("ref") or
                                hit.get("ref") or
                                hit.get("_id")
                            )
                            if ref:
                                sample_refs.append(ref)
                                logger.debug(f"  Sample ref: {ref}")
                    
                    result = {
                        "found": hits > 0,
                        "hits": hits,
                        "sample_refs": sample_refs,
                        "term": hebrew_term
                    }
                    
                    # Cache it
                    self._cache[hebrew_term] = result
                    
                    logger.debug(f"  FINAL RESULT → {hebrew_term}: {hits} hits")
                    return result
                else:
                    logger.warning(f"  Sefaria API error: HTTP {response.status_code}")
                    return {"found": False, "hits": 0, "sample_refs": [], "term": hebrew_term}
                    
        except Exception as e:
            logger.error(f"  Sefaria validation error for '{hebrew_term}': {e}", exc_info=True)
            return {"found": False, "hits": 0, "sample_refs": [], "term": hebrew_term, "error": str(e)}
    
    async def validate_variants(self, variants: List[str]) -> List[Dict]:
        """Validate multiple Hebrew variants concurrently"""
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
        """Find the best (most common) valid variant"""
        results = await self.validate_variants(variants)
        return results[0] if results else None


# Global instance
_validator: Optional[SefariaValidator] = None


def get_validator(verbose: bool = False) -> SefariaValidator:
    """Get global validator instance"""
    global _validator
    if _validator is None:
        _validator = SefariaValidator(verbose=verbose)
    return _validator


# ==========================================
#  TESTING
# ==========================================

async def test_validator():
    """Test the validator with known terms"""
    
    print("\n" + "="*80)
    print("SEFARIA VALIDATOR TEST - DIAGNOSTIC VERSION")
    print("="*80)
    
    # Create validator with verbose logging
    validator = SefariaValidator(verbose=True)
    
    # Test with terms that DEFINITELY exist
    test_cases = [
        ("migu", ["מיגו", "מגו"]),
        ("kal vchomer", ["קל וחומר"]),
        ("kesubos", ["כתובות"]),
    ]
    
    for query, variants in test_cases:
        print(f"\n{'='*80}")
        print(f"Query: '{query}'")
        print(f"Variants: {variants}")
        print(f"{'='*80}")
        
        best = await validator.find_best_variant(variants)
        
        if best:
            print(f"\n✅ FOUND: '{best['term']}' ({best['hits']} hits)")
            if best.get('sample_refs'):
                print(f"   Sample sources: {best['sample_refs'][:2]}")
        else:
            print(f"\n❌ NOT FOUND")
            print(f"   This suggests an API problem!")
    
    print("\n" + "="*80)
    print("DIAGNOSTIC TEST COMPLETE")
    print("="*80)


if __name__ == "__main__":
    # Set up detailed logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    asyncio.run(test_validator())