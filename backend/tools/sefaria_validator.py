"""
Sefaria Term Validator V3 - Connection Pooling + Batch Validation
===================================================================

IMPROVEMENTS FROM V2:
1. CONNECTION POOLING: Single httpx.AsyncClient shared across all requests
   - Eliminates ~100-200ms TCP+TLS overhead per request
   - Uses HTTP/2 keep-alive connections

2. BATCH VALIDATION: Parallel validation of multiple variants
   - validate_batch() runs multiple terms concurrently
   - Significant speedup for phrase validation

3. AUTHOR-AWARE VALIDATION: find_best_validated_with_authors()
   - Integrates with Master KB to prioritize author names
   - Prevents generic Hebrew words from beating proper nouns

Architecture:
- Singleton AsyncClient with connection pooling
- Cache still per-validator (could be moved to module level)
- Graceful cleanup via close() or context manager
"""

import httpx
import asyncio
from typing import List, Dict, Optional, Set
import logging
import atexit

logger = logging.getLogger(__name__)


# ==========================================
#  CONNECTION POOL MANAGEMENT
# ==========================================

class SefariaValidator:
    """
    Validates Hebrew terms against Sefaria's corpus.
    
    V3 FEATURES:
    - Connection pooling (shared httpx.AsyncClient)
    - Batch validation (parallel requests)
    - Author-aware scoring
    """
    
    BASE_URL = "https://www.sefaria.org/api/search-wrapper"
    
    # Class-level shared client for connection pooling
    _shared_client: Optional[httpx.AsyncClient] = None
    _client_lock = asyncio.Lock() if hasattr(asyncio, 'Lock') else None
    
    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout
        self._cache: Dict[str, Dict] = {}
        self._author_names: Optional[Set[str]] = None  # Lazy-loaded from Master KB
    
    async def _get_client(self) -> httpx.AsyncClient:
        """
        Get or create the shared HTTP client with connection pooling.
        
        Uses a singleton pattern to reuse TCP connections across requests.
        HTTP/2 multiplexing allows multiple concurrent requests over one connection.
        """
        if SefariaValidator._shared_client is None or SefariaValidator._shared_client.is_closed:
            # Create client with connection pooling settings
            SefariaValidator._shared_client = httpx.AsyncClient(
                verify=False,  # Sefaria uses valid certs, but some envs have issues
                timeout=httpx.Timeout(self.timeout, connect=5.0),
                http2=False,  # Disabled HTTP/2 (requires h2 package)
                limits=httpx.Limits(
                    max_connections=20,
                    max_keepalive_connections=10,
                    keepalive_expiry=30.0
                )
            )
            logger.debug("[VALIDATOR] Created shared HTTP client with connection pooling")
        
        return SefariaValidator._shared_client
    
    async def close(self):
        """Close the shared HTTP client (call on shutdown)."""
        if SefariaValidator._shared_client and not SefariaValidator._shared_client.is_closed:
            await SefariaValidator._shared_client.aclose()
            SefariaValidator._shared_client = None
            logger.debug("[VALIDATOR] Closed shared HTTP client")
    
    def _load_author_names(self) -> Set[str]:
        """
        Lazy-load author names from Master KB for author-aware validation.
        
        Returns a set of normalized Hebrew author names/variations.
        """
        if self._author_names is not None:
            return self._author_names
        
        try:
            from .torah_authors_master import AUTHOR_LOOKUP_INDEX
        except ImportError:
            try:
                from tools.torah_authors_master import AUTHOR_LOOKUP_INDEX
            except ImportError:
                logger.warning("[VALIDATOR] Could not import Master KB - author detection disabled")
                self._author_names = set()
                return self._author_names

        self._author_names = {self._normalize_for_author_check(k) for k in AUTHOR_LOOKUP_INDEX.keys()}
        logger.debug(f"[VALIDATOR] Loaded {len(self._author_names)} author names from Master KB")
        
        return self._author_names
    
    def _normalize_for_author_check(self, hebrew_term: str) -> str:
        """Normalize Hebrew for author matching (remove quotes, punctuation)."""
        import re
        # Remove quotes, geresh, gershayim
        normalized = re.sub(r'["\'\u05F3\u05F4״׳]', '', hebrew_term)
        # Remove spaces
        normalized = normalized.replace(' ', '')
        return normalized
    
    def is_author_name(self, hebrew_term: str) -> bool:
        """Check if a Hebrew term is a known author name."""
        author_names = self._load_author_names()
        normalized = self._normalize_for_author_check(hebrew_term)
        return normalized in author_names

    # ------------------------------------------
    #  AUTHOR DISAMBIGUATION (prevents 'Rashi' -> 'Rosh' type landmines)
    # ------------------------------------------

    @staticmethod
    def _latin_norm(s: Optional[str]) -> str:
        """Normalize Latin input for matching (letters only, lowercase)."""
        import re
        if not s:
            return ""
        return re.sub(r"[^a-z]", "", s.lower())

    @staticmethod
    def _levenshtein(a: str, b: str) -> int:
        """Small Levenshtein distance implementation (no dependencies)."""
        if a == b:
            return 0
        if not a:
            return len(b)
        if not b:
            return len(a)
        # DP with two rows
        prev = list(range(len(b) + 1))
        for i, ca in enumerate(a, 1):
            cur = [i]
            for j, cb in enumerate(b, 1):
                ins = cur[j-1] + 1
                dele = prev[j] + 1
                sub = prev[j-1] + (0 if ca == cb else 1)
                cur.append(min(ins, dele, sub))
            prev = cur
        return prev[-1]

    def _candidate_tokens(self, cand: Dict[str, str]) -> Set[str]:
        """Generate plausible latin tokens for an author candidate."""
        import re
        tokens = set()
        cid = self._latin_norm(cand.get("id", ""))
        if cid:
            tokens.add(cid)
        pen = self._latin_norm(cand.get("primary_name_en", ""))
        if pen:
            tokens.add(pen)
            # also add first word if it's multi-word
            parts = re.split(r"\s+", cand.get("primary_name_en", "").strip())
            if parts:
                first = self._latin_norm(parts[0])
                if first:
                    tokens.add(first)
        return tokens

    def _author_candidate_matches_original(self, original_word: Optional[str], cand: Dict[str, str]) -> bool:
        """
        Decide if an author-candidate is plausibly what the user typed.

        Example landmine: original='rashi' but a Hebrew variant hits 'ראש' (Rosh).
        We should NOT treat that as an author-match for 'rashi'.
        """
        o = self._latin_norm(original_word)
        if not o:
            return True  # no constraint
        tokens = self._candidate_tokens(cand)
        if not tokens:
            return True

        for t in tokens:
            if not t:
                continue
            if o == t or o in t or t in o:
                return True
            # allow small typos for longer names
            if len(o) >= 5 and len(t) >= 5 and self._levenshtein(o, t) <= 1:
                return True
        return False

    # ==========================================
    #  SINGLE TERM VALIDATION
    # ==========================================
    
    async def validate_term(self, hebrew_term: str) -> Dict:
        """
        Check if a Hebrew term exists in Sefaria.
        
        Returns:
            {
                "found": True/False,
                "hits": 123,
                "sample_refs": ["Berachos 10a", ...],
                "term": "מיגו",
                "is_author": True/False
            }
        """
        # Check cache first
        if hebrew_term in self._cache:
            logger.debug(f"  Cache hit: {hebrew_term}")
            return self._cache[hebrew_term]
        
        logger.debug(f"  Validating: {hebrew_term}")
        
        try:
            client = await self._get_client()
            
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
                
                # Check if this is an author name
                is_author = self.is_author_name(hebrew_term)

                # If it looks like an author, capture which author(s) we think it is.
                author_candidates = []
                if is_author:
                    try:
                        from .torah_authors_master import get_author_matches
                    except Exception:
                        try:
                            from tools.torah_authors_master import get_author_matches
                        except Exception:
                            get_author_matches = None

                    if get_author_matches:
                        try:
                            matches = get_author_matches(hebrew_term)
                            for a in matches:
                                author_candidates.append({
                                    "id": a.get("id", ""),
                                    "primary_name_en": a.get("primary_name_en", ""),
                                    "primary_name_he": a.get("primary_name_he", ""),
                                })
                        except Exception:
                            author_candidates = []
                
                result = {
                    "found": hits > 0,
                    "hits": hits,
                    "sample_refs": sample_refs,
                    "term": hebrew_term,
                    "is_author": is_author,
                    "author_candidates": author_candidates
                }
                
                self._cache[hebrew_term] = result
                
                logger.debug(f"    → {hebrew_term}: {hits} hits" + (" [AUTHOR]" if is_author else ""))
                
                return result
            else:
                logger.warning(f"  Sefaria API error: HTTP {response.status_code}")
                return {"found": False, "hits": 0, "sample_refs": [], "term": hebrew_term}
                
        except Exception as e:
            logger.error(f"  Sefaria validation error: {e}")
            return {"found": False, "hits": 0, "sample_refs": [], "term": hebrew_term, "error": str(e)}
    
    # ==========================================
    #  BATCH VALIDATION (PARALLEL)
    # ==========================================
    
    async def validate_batch(self, terms: List[str], max_concurrent: int = 5) -> Dict[str, Dict]:
        """
        Validate multiple terms in parallel.
        
        This is much faster than sequential validation when checking
        many variants (e.g., 10 phrase variants).
        
        Args:
            terms: List of Hebrew terms to validate
            max_concurrent: Max parallel requests (to avoid rate limiting)
        
        Returns:
            Dict mapping term -> validation result
        """
        if not terms:
            return {}
        
        logger.debug(f"[BATCH] Validating {len(terms)} terms in parallel (max {max_concurrent} concurrent)")
        
        # Use semaphore to limit concurrency
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def validate_with_semaphore(term: str) -> tuple:
            async with semaphore:
                result = await self.validate_term(term)
                return (term, result)
        
        # Run all validations concurrently
        tasks = [validate_with_semaphore(term) for term in terms]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Build result dict
        result_dict = {}
        for item in results:
            if isinstance(item, Exception):
                logger.warning(f"[BATCH] Validation error: {item}")
                continue
            term, result = item
            result_dict[term] = result
        
        valid_count = sum(1 for r in result_dict.values() if r.get('found'))
        logger.debug(f"[BATCH] Complete: {valid_count}/{len(terms)} valid")
        
        return result_dict
    
    # ==========================================
    #  AUTHOR-AWARE WEIGHTED VALIDATION
    # ==========================================
    
    async def find_best_validated_with_authors(
        self,
        variants: List[str],
        original_word: str = None,
        parallel: bool = True
    ) -> Optional[Dict]:
        """
        Find the BEST variant using author-aware weighted scoring.
        
        SCORING LOGIC:
        1. AUTHOR NAMES GET ABSOLUTE PRIORITY
           - Any valid author match is returned immediately
           - Among multiple authors, pick highest hits
        2. If no authors found, use hit-count weighting:
           - 1000+ hits: score = hits * 20
           - 100-999 hits: score = hits * 10
           - 10-99 hits: score = hits * 5
           - 1-9 hits: score = hits * 1
        
        This two-phase approach ensures "רש"י" (133 hits) ALWAYS beats
        "ראשי" (10000 hits) because authors are checked first.
        
        Args:
            variants: List of Hebrew variants to check
            original_word: Original transliteration (for logging)
            parallel: If True, validate all variants in parallel (faster)
        
        Returns:
            Best validation result dict or None
        """
        if not variants:
            return None
        
        logger.debug(f"[WEIGHTED-VALIDATION] Checking {len(variants)} variants for '{original_word}'")
        
        # Validate all variants (parallel or sequential)
        if parallel and len(variants) > 2:
            results = await self.validate_batch(variants)
        else:
            results = {}
            for v in variants:
                results[v] = await self.validate_term(v)
        
        # PHASE 1: Check for author matches FIRST (absolute priority)
        author_results = []
        non_author_results = []
        
        for variant, result in results.items():
            hits = result.get('hits', 0)
            if hits == 0:
                continue
            
            is_author = result.get('is_author', False)
            if is_author:
                author_results.append((variant, result, hits))
                logger.debug(f"[WEIGHTED-VALIDATION]   {variant}: {hits} hits [AUTHOR MATCH]")
            else:
                non_author_results.append((variant, result, hits))
        
        # If we found any authors, return the best one (highest hits among authors)
        
        if author_results:
                    # If original_word is provided, only treat an "author match" as valid
                    # when it plausibly matches what the user typed (prevents Rashi->Rosh landmines).
                    filtered_authors = []
                    for variant, result, hits in author_results:
                        cands = result.get("author_candidates") or []
                        if not cands:
                            # If we can't identify the author, keep it (back-compat)
                            filtered_authors.append((variant, result, hits))
                            continue

                        if any(self._author_candidate_matches_original(original_word, c) for c in cands):
                            filtered_authors.append((variant, result, hits))
                        else:
                            # Demote to non-author pool
                            non_author_results.append((variant, result, hits))

                    if filtered_authors:
                        filtered_authors.sort(key=lambda x: x[2], reverse=True)
                        best_variant, best_result, best_hits = filtered_authors[0]
                        logger.info(f"[WEIGHTED-VALIDATION] ✓ AUTHOR PRIORITY: '{best_variant}' ({best_hits} hits)")
                        return best_result

        # PHASE 2: No authors found, use standard hit-count weighting
        best_score = 0
        best_result = None
        best_variant = None
        
        for variant, result, hits in non_author_results:
            # Standard hit-count weighting
            if hits >= 1000:
                score = hits * 20
                confidence = "very_high"
            elif hits >= 100:
                score = hits * 10
                confidence = "high"
            elif hits >= 10:
                score = hits * 5
                confidence = "medium"
            else:
                score = hits * 1
                confidence = "low"
            
            logger.debug(f"[WEIGHTED-VALIDATION]   {variant}: {hits} hits, score={score}, confidence={confidence}")
            
            if score > best_score:
                best_score = score
                best_result = result
                best_variant = variant
        
        if best_result:
            logger.info(f"[WEIGHTED-VALIDATION] ✓ Best match: '{best_variant}' ({best_result['hits']} hits, score={best_score})")
        else:
            logger.warning(f"[WEIGHTED-VALIDATION] ✗ No valid variants found")
        
        return best_result
    
    # ==========================================
    #  LEGACY METHODS (for backward compatibility)
    # ==========================================
    
    async def find_first_valid(
        self, 
        variants: List[str], 
        min_hits: int = 1
    ) -> Optional[Dict]:
        """
        Find the FIRST variant that exists in Sefaria.
        
        Kept for backward compatibility. For author-aware validation,
        use find_best_validated_with_authors() instead.
        """
        if not variants:
            return None
        
        logger.info(f"  Checking {len(variants)} variants in preference order...")
        
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
        """DEPRECATED: Use find_best_validated_with_authors() instead."""
        logger.warning("  find_best_variant() is deprecated. Use find_best_validated_with_authors()")
        return await self.find_best_validated_with_authors(variants)
    
    async def validate_variants(self, variants: List[str]) -> List[Dict]:
        """Validate multiple variants and return all results."""
        results = await self.validate_batch(variants)
        return [r for r in results.values() if r.get("found")]
    
    def clear_cache(self):
        """Clear the validation cache."""
        self._cache.clear()
        logger.info("  Cache cleared")


# ==========================================
#  GLOBAL INSTANCE
# ==========================================

_validator: Optional[SefariaValidator] = None


def get_validator() -> SefariaValidator:
    """Get global validator instance."""
    global _validator
    if _validator is None:
        _validator = SefariaValidator()
    return _validator


async def cleanup_validator():
    """Cleanup function to close connections on shutdown."""
    global _validator
    if _validator:
        await _validator.close()
        _validator = None


# ==========================================
#  TESTING
# ==========================================

async def test_author_aware_validation():
    """Test that author names beat generic words."""
    
    print("\n" + "=" * 70)
    print("SEFARIA VALIDATOR V3 - AUTHOR-AWARE VALIDATION TEST")
    print("=" * 70)
    
    validator = get_validator()
    
    # Test case: rashi variants
    # רש"י should beat ראשי even though ראשי has more hits
    print("\n--- Test: rashi variants (author vs generic) ---")
    variants = ['רש"י', 'רשי', 'ראשי', 'ראש']
    print(f"Variants: {variants}")
    
    result = await validator.find_best_validated_with_authors(variants, "rashi")
    
    if result:
        print(f"\n✓ Selected: '{result['term']}' ({result['hits']} hits)")
        if result.get('is_author'):
            print("  CORRECT: Author name was prioritized!")
        else:
            print("  CHECK: Result may be wrong if an author variant was available")
    else:
        print("✗ No valid variant found")
    
    # Test case: ran variants
    print("\n--- Test: ran variants ---")
    variants = ['רן', 'ראן']
    print(f"Variants: {variants}")
    
    result = await validator.find_best_validated_with_authors(variants, "ran")
    
    if result:
        print(f"✓ Selected: '{result['term']}' ({result['hits']} hits)")
        print(f"  Is author: {result.get('is_author', False)}")
    
    # Test parallel validation
    print("\n--- Test: Batch validation performance ---")
    import time
    
    batch_terms = ['מיגו', 'חזקה', 'ביטול', 'שיטה', 'רש"י', 'תוספות', 'רן', 'רמב"ם']
    
    start = time.time()
    results = await validator.validate_batch(batch_terms)
    elapsed = time.time() - start
    
    print(f"Validated {len(batch_terms)} terms in {elapsed:.2f}s ({elapsed/len(batch_terms)*1000:.0f}ms per term)")
    
    for term, result in results.items():
        author_tag = " [AUTHOR]" if result.get('is_author') else ""
        print(f"  {term}: {result.get('hits', 0)} hits{author_tag}")
    
    # Cleanup
    await validator.close()
    
    print("\n" + "=" * 70)
    print("Test complete!")
    print("=" * 70)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    asyncio.run(test_author_aware_validation())
