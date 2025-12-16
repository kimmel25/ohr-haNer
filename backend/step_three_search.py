"""
Step 3: SEARCH - Fetch and Organize Sources
============================================

This step takes the SearchStrategy from Step 2 and:
1. FETCH: Get the actual source texts from Sefaria
2. ORGANIZE: Arrange them in trickle-up order
3. FORMAT: Prepare the final output for the user

ARCHITECTURE: Extensible Handler Pattern
----------------------------------------
Each fetch_strategy has its own handler function. To add a new strategy:
1. Write an async handler: async def _fetch_<strategy_name>(strategy) -> List[Source]
2. Register it in FETCH_HANDLERS dict
3. Done!

TRICKLE-UP ORDER (from Architecture.md):
1. פסוק (Chumash) - if applicable
2. משנה
3. גמרא
4. רש"י / תוספות
5. ראשונים (רמב"ם, רשב"א, ריטב"א, ר"ן, etc.)
6. טור / שולחן ערוך
7. נושאי כלים (ש"ך, ט"ז)
8. אחרונים (קצות, פני יהושע)
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Callable, Any

logger = logging.getLogger(__name__)

# Import centralized Pydantic models from models.py
from models import (
    SourceLevel,
    Source,
    RelatedSugya,
    RelatedSugyaResult,
    SearchResult,
    SearchStrategy,
    QueryType,
    FetchStrategy,
    ConfidenceLevel
)


# ==========================================
#  CONSTANTS & CONFIGURATION
# ==========================================

# Hebrew names for display (using string enum values as keys)
LEVEL_HEBREW_NAMES = {
    "chumash": "חומש",
    "mishna": "משנה",
    "gemara": "גמרא",
    "rashi": 'רש"י',
    "tosfos": "תוספות",
    "rishonim": "ראשונים",
    "rambam": 'רמב"ם',
    "tur": "טור",
    "shulchan_aruch": "שולחן ערוך",
    "nosei_keilim": "נושאי כלים",
    "acharonim": "אחרונים",
    "other": "אחר"
}

# Depth configurations - which levels to include at each depth
DEPTH_LEVELS = {
    "basic": {SourceLevel.GEMARA},
    "standard": {
        SourceLevel.GEMARA,
        SourceLevel.RASHI,
        SourceLevel.TOSFOS,
        SourceLevel.MISHNA,
        SourceLevel.CHUMASH
    },
    "expanded": {
        SourceLevel.GEMARA,
        SourceLevel.RASHI,
        SourceLevel.TOSFOS,
        SourceLevel.MISHNA,
        SourceLevel.CHUMASH,
        SourceLevel.RISHONIM,
        SourceLevel.RAMBAM
    },
    "full": {
        SourceLevel.GEMARA,
        SourceLevel.RASHI,
        SourceLevel.TOSFOS,
        SourceLevel.MISHNA,
        SourceLevel.CHUMASH,
        SourceLevel.RISHONIM,
        SourceLevel.RAMBAM,
        SourceLevel.TUR,
        SourceLevel.SHULCHAN_ARUCH,
        SourceLevel.NOSEI_KEILIM,
        SourceLevel.ACHARONIM
    }
}


# ==========================================
#  HELPER FUNCTIONS
# ==========================================

def get_level_order(level: SourceLevel) -> int:
    """
    Get the numeric order for a SourceLevel.
    This preserves the trickle-up hierarchy for sorting.
    """
    order_map = {
        SourceLevel.CHUMASH: 1,
        SourceLevel.MISHNA: 2,
        SourceLevel.GEMARA: 3,
        SourceLevel.RASHI: 4,
        SourceLevel.TOSFOS: 5,
        SourceLevel.RISHONIM: 6,
        SourceLevel.RAMBAM: 7,
        SourceLevel.TUR: 8,
        SourceLevel.SHULCHAN_ARUCH: 9,
        SourceLevel.NOSEI_KEILIM: 10,
        SourceLevel.ACHARONIM: 11,
        SourceLevel.OTHER: 99
    }
    return order_map.get(level, 99)


def get_levels_for_depth(depth: str) -> set:
    """Determine which source levels to include based on depth setting."""
    return DEPTH_LEVELS.get(depth, DEPTH_LEVELS["standard"])


def map_client_level(client_level) -> SourceLevel:
    """Map Sefaria client's SourceLevel to our SourceLevel."""
    try:
        if isinstance(client_level, SourceLevel):
            return client_level
        
        if isinstance(client_level, str):
            try:
                return SourceLevel(client_level.lower())
            except ValueError:
                try:
                    return SourceLevel[client_level.upper()]
                except KeyError:
                    pass
        
        if hasattr(client_level, 'name'):
            try:
                return SourceLevel[client_level.name.upper()]
            except (KeyError, AttributeError):
                pass
                
    except Exception:
        pass
    
    return SourceLevel.OTHER


def extract_author(category: str, categories: List[str]) -> str:
    """Extract author name from category info."""
    author_map = {
        "rashi": 'רש"י',
        "tosafot": "תוספות",
        "tosafos": "תוספות",
        "ramban": 'רמב"ן',
        "rashba": 'רשב"א',
        "ritva": 'ריטב"א',
        "ran": 'ר"ן',
        "rosh": 'רא"ש',
        "rambam": 'רמב"ם',
        "maharsha": 'מהרש"א',
        "pnei yehoshua": "פני יהושע",
        "shita mekubetzet": "שיטה מקובצת",
    }
    
    category_lower = category.lower()
    for eng, heb in author_map.items():
        if eng in category_lower:
            return heb
    
    for cat in categories:
        cat_lower = cat.lower()
        for eng, heb in author_map.items():
            if eng in cat_lower:
                return heb
    
    return ""


def detect_source_level(ref: str, categories: List[str]) -> SourceLevel:
    """
    Detect the SourceLevel from a Sefaria reference and its categories.
    Used when fetching direct refs that don't come with level metadata.
    """
    ref_lower = ref.lower()
    cats_lower = [c.lower() for c in categories]
    cats_joined = " ".join(cats_lower)
    
    # Check ref patterns first
    if "rashi on" in ref_lower or "rashi" in cats_joined:
        return SourceLevel.RASHI
    if "tosafot on" in ref_lower or "tosafos on" in ref_lower or "tosafot" in cats_joined:
        return SourceLevel.TOSFOS
    if "ran on" in ref_lower:
        return SourceLevel.RISHONIM
    if "rashba on" in ref_lower or "ritva on" in ref_lower:
        return SourceLevel.RISHONIM
    if "rambam" in ref_lower or "mishneh torah" in ref_lower:
        return SourceLevel.RAMBAM
    if "shulchan arukh" in ref_lower or "shulchan aruch" in ref_lower:
        return SourceLevel.SHULCHAN_ARUCH
    if "tur" in ref_lower and "commentary" not in cats_joined:
        return SourceLevel.TUR
    
    # Check categories
    if "talmud" in cats_joined and "commentary" not in cats_joined:
        return SourceLevel.GEMARA
    if "mishnah" in cats_joined and "commentary" not in cats_joined:
        return SourceLevel.MISHNA
    if "tanakh" in cats_joined or "torah" in cats_joined:
        return SourceLevel.CHUMASH
    
    return SourceLevel.OTHER


# ==========================================
#  CORE FETCHING UTILITIES
# ==========================================

async def fetch_single_source(ref: str, is_primary: bool = False, related_term: str = None) -> Optional[Source]:
    """
    Fetch a single source from Sefaria by reference.
    This is the atomic building block used by all handlers.
    
    Args:
        ref: Sefaria reference string (e.g., "Ran on Pesachim 4b")
        is_primary: Whether this is a primary source
        related_term: Optional Hebrew term this source relates to (for multi-term queries)
    
    Returns:
        Source object or None if fetch failed
    """
    if not ref:
        return None
        
    try:
        from tools.sefaria_client import get_sefaria_client
        client = get_sefaria_client()
        
        logger.debug(f"[FETCH-SINGLE] Getting: {ref}")
        text = await client.get_text(ref)
        
        if not text:
            logger.warning(f"[FETCH-SINGLE] No text returned for: {ref}")
            return None
        
        # Detect level from ref and categories
        level = detect_source_level(ref, text.categories or [])
        
        source = Source(
            ref=text.ref,
            he_ref=text.he_ref or text.ref,
            level=level,
            level_hebrew=LEVEL_HEBREW_NAMES.get(level.value, "אחר"),
            level_order=get_level_order(level),
            hebrew_text=text.hebrew[:2000] if text.hebrew else "",
            english_text=text.english[:2000] if text.english else "",
            author=extract_author(ref, text.categories or []),
            categories=text.categories or [],
            is_primary=is_primary,
            relevance_note="Primary source" if is_primary else "",
            related_term=related_term
        )
        
        logger.debug(f"[FETCH-SINGLE] ✓ Got {ref} ({level.value})")
        return source
        
    except Exception as e:
        logger.error(f"[FETCH-SINGLE] Error fetching {ref}: {e}")
        return None


async def fetch_with_commentaries(ref: str, depth: str = "standard") -> List[Source]:
    """
    Fetch a primary source and its commentaries.
    Used for trickle-up style fetching.
    
    Args:
        ref: Primary Sefaria reference (usually Gemara)
        depth: How deep to go in the commentary hierarchy
    
    Returns:
        List of Source objects (primary + commentaries)
    """
    sources: List[Source] = []
    
    if not ref:
        return sources
    
    try:
        from tools.sefaria_client import get_sefaria_client
        client = get_sefaria_client()
        
        # Get primary text
        logger.info(f"[FETCH-WITH-COMM] Getting primary: {ref}")
        primary = await fetch_single_source(ref, is_primary=True)
        if primary:
            sources.append(primary)
        
        # Get related content (commentaries)
        logger.info(f"[FETCH-WITH-COMM] Getting commentaries...")
        related = await client.get_related(ref)
        
        if not related or not related.commentaries:
            logger.info(f"[FETCH-WITH-COMM] No commentaries found")
            return sources
        
        # Filter by depth
        levels_to_fetch = get_levels_for_depth(depth)
        
        for commentary in related.commentaries:
            level = map_client_level(commentary.level)
            
            if level not in levels_to_fetch:
                continue
            
            comm_source = await fetch_single_source(commentary.ref)
            if comm_source:
                # Override the level detection with the one from related API
                comm_source.level = level
                comm_source.level_hebrew = LEVEL_HEBREW_NAMES.get(level.value, "")
                comm_source.level_order = get_level_order(level)
                sources.append(comm_source)
        
        logger.info(f"[FETCH-WITH-COMM] Retrieved {len(sources)} sources")
        
    except Exception as e:
        logger.error(f"[FETCH-WITH-COMM] Error: {e}", exc_info=True)
    
    return sources


# ==========================================
#  FETCH STRATEGY HANDLERS
# ==========================================

async def _fetch_trickle_up(strategy: SearchStrategy) -> List[Source]:
    """
    Handler for TRICKLE_UP strategy.
    
    Fetches a primary Gemara source and its commentaries in hierarchical order.
    This is the classic "open the Gemara and see what's there" approach.
    
    Uses: strategy.primary_source, strategy.depth
    """
    logger.info("[HANDLER:TRICKLE_UP] Starting trickle-up fetch")
    
    primary_ref = strategy.primary_source
    if not primary_ref:
        # Fallback: try primary_sources list
        if strategy.primary_sources:
            primary_ref = strategy.primary_sources[0]
            logger.info(f"[HANDLER:TRICKLE_UP] Using first of primary_sources: {primary_ref}")
    
    if not primary_ref:
        logger.warning("[HANDLER:TRICKLE_UP] No primary source to fetch")
        return []
    
    sources = await fetch_with_commentaries(primary_ref, strategy.depth)
    logger.info(f"[HANDLER:TRICKLE_UP] Complete: {len(sources)} sources")
    return sources


async def _fetch_direct(strategy: SearchStrategy) -> List[Source]:
    """
    Handler for DIRECT strategy.
    
    Fetches specific references directly without expanding to commentaries.
    Used for comparison queries, specific lookups, or when Step 2 knows
    exactly what sources are needed.
    
    Uses: strategy.primary_sources (list), falls back to strategy.primary_source
    """
    logger.info("[HANDLER:DIRECT] Starting direct fetch")
    
    # Gather all refs to fetch
    refs_to_fetch = []
    
    # Primary sources list takes precedence (for comparisons)
    if strategy.primary_sources:
        refs_to_fetch.extend(strategy.primary_sources)
        logger.info(f"[HANDLER:DIRECT] Using primary_sources: {strategy.primary_sources}")
    
    # Fallback to single primary_source
    if not refs_to_fetch and strategy.primary_source:
        refs_to_fetch.append(strategy.primary_source)
        logger.info(f"[HANDLER:DIRECT] Using primary_source: {strategy.primary_source}")
    
    if not refs_to_fetch:
        logger.warning("[HANDLER:DIRECT] No refs to fetch")
        return []
    
    # Fetch all refs
    sources = []
    for i, ref in enumerate(refs_to_fetch):
        is_primary = (i == 0)  # First one is primary
        source = await fetch_single_source(ref, is_primary=is_primary)
        if source:
            sources.append(source)
        else:
            logger.warning(f"[HANDLER:DIRECT] Could not fetch: {ref}")
    
    logger.info(f"[HANDLER:DIRECT] Complete: {len(sources)}/{len(refs_to_fetch)} sources")
    return sources


async def _fetch_multi_term(strategy: SearchStrategy) -> List[Source]:
    """
    Handler for MULTI_TERM strategy.
    
    Fetches sources for multiple Hebrew terms, keeping track of which
    source relates to which term. Used for complex queries with multiple
    concepts.
    
    Uses: strategy.primary_sources, strategy.comparison_terms
    """
    logger.info("[HANDLER:MULTI_TERM] Starting multi-term fetch")
    
    # For now, same as direct but with term tracking
    # Future: could expand each term to its own trickle-up
    sources = []
    
    refs = strategy.primary_sources or []
    terms = strategy.comparison_terms or []
    
    # Pair refs with terms if available
    for i, ref in enumerate(refs):
        term = terms[i] if i < len(terms) else None
        source = await fetch_single_source(ref, is_primary=(i == 0), related_term=term)
        if source:
            sources.append(source)
    
    logger.info(f"[HANDLER:MULTI_TERM] Complete: {len(sources)} sources")
    return sources


async def _fetch_survey(strategy: SearchStrategy) -> List[Source]:
    """
    Handler for SURVEY strategy.
    
    Broad overview across multiple masechtos or sources.
    Gets a sampling of sources to show the breadth of a topic.
    
    TODO: Implement when needed
    """
    logger.info("[HANDLER:SURVEY] Survey fetch - using direct as fallback")
    # For now, fallback to direct
    return await _fetch_direct(strategy)


async def _fetch_default(strategy: SearchStrategy) -> List[Source]:
    """
    Default/fallback handler when strategy is unknown.
    
    Tries to do something sensible:
    1. If primary_sources exists, use direct fetch
    2. If primary_source exists, use trickle-up
    3. Otherwise, return empty
    """
    logger.info("[HANDLER:DEFAULT] Using fallback logic")
    
    if strategy.primary_sources:
        logger.info("[HANDLER:DEFAULT] Found primary_sources, using direct")
        return await _fetch_direct(strategy)
    
    if strategy.primary_source:
        logger.info("[HANDLER:DEFAULT] Found primary_source, using trickle-up")
        return await _fetch_trickle_up(strategy)
    
    logger.warning("[HANDLER:DEFAULT] No sources to fetch")
    return []


# ==========================================
#  HANDLER REGISTRY
# ==========================================

# Map fetch_strategy values to handler functions
# To add a new strategy: add one line here + implement the handler above
FETCH_HANDLERS: Dict[str, Callable] = {
    "trickle_up": _fetch_trickle_up,
    "trickle_down": _fetch_trickle_up,  # Alias for now
    "direct": _fetch_direct,
    "multi_term": _fetch_multi_term,
    "survey": _fetch_survey,
    # Future handlers:
    # "author_focus": _fetch_author_focus,
    # "halacha_trace": _fetch_halacha_trace,
    # "sugya_archaeology": _fetch_sugya_archaeology,
}


async def fetch_sources(strategy: SearchStrategy) -> List[Source]:
    """
    Main fetch router - dispatches to appropriate handler based on strategy.
    
    This is the single entry point for all fetching. It:
    1. Determines which handler to use
    2. Logs the routing decision
    3. Calls the handler
    4. Returns the results
    """
    # Get strategy value (handle both enum and string)
    fetch_strategy = strategy.fetch_strategy
    if hasattr(fetch_strategy, 'value'):
        fetch_strategy = fetch_strategy.value
    
    logger.info(f"[FETCH-ROUTER] Strategy: {fetch_strategy}")
    
    # Get handler
    handler = FETCH_HANDLERS.get(fetch_strategy, _fetch_default)
    handler_name = handler.__name__
    
    logger.info(f"[FETCH-ROUTER] Routing to: {handler_name}")
    
    # Execute handler
    try:
        sources = await handler(strategy)
        logger.info(f"[FETCH-ROUTER] Handler returned {len(sources)} sources")
        return sources
    except Exception as e:
        logger.error(f"[FETCH-ROUTER] Handler {handler_name} failed: {e}", exc_info=True)
        return []


# ==========================================
#  ORGANIZATION (Phase 2)
# ==========================================

def organize_sources(sources: List[Source]) -> Tuple[List[Source], Dict[str, List[Source]]]:
    """
    Phase 2: ORGANIZE - Sort and group sources.
    
    Returns:
        Tuple of (sorted_flat_list, grouped_by_level_dict)
    """
    logger.info(f"[ORGANIZE] Organizing {len(sources)} sources")
    
    if not sources:
        return [], {}
    
    # Sort by level order
    sorted_sources = sorted(sources, key=lambda s: s.level_order)
    
    # Group by level
    by_level: Dict[str, List[Source]] = {}
    for source in sorted_sources:
        level_key = source.level.value if hasattr(source.level, 'value') else str(source.level)
        if level_key not in by_level:
            by_level[level_key] = []
        by_level[level_key].append(source)
    
    # Log organization
    for level, level_sources in by_level.items():
        logger.debug(f"[ORGANIZE] {level}: {len(level_sources)} sources")
    
    return sorted_sources, by_level


# ==========================================
#  RELATED SUGYOS (Phase 2b)
# ==========================================

async def fetch_related_previews(related_sugyos: List[RelatedSugya]) -> List[RelatedSugyaResult]:
    """
    Fetch preview text for related sugyos.
    """
    results = []
    
    if not related_sugyos:
        return results
    
    try:
        from tools.sefaria_client import get_sefaria_client
        client = get_sefaria_client()
        
        for sugya in related_sugyos:
            # Handle both object and dict
            ref = sugya.ref if hasattr(sugya, 'ref') else sugya.get('ref')
            if not ref:
                continue
            
            he_ref = sugya.he_ref if hasattr(sugya, 'he_ref') else sugya.get('he_ref', ref)
            connection = sugya.connection if hasattr(sugya, 'connection') else sugya.get('connection', '')
            importance = sugya.importance if hasattr(sugya, 'importance') else sugya.get('importance', 'secondary')
            
            # Get just a snippet
            text = await client.get_text(ref)
            preview = ""
            if text and text.hebrew:
                preview = text.hebrew[:200] + "..." if len(text.hebrew) > 200 else text.hebrew
            
            results.append(RelatedSugyaResult(
                ref=ref,
                he_ref=he_ref,
                connection=connection,
                importance=importance,
                preview_text=preview
            ))
    
    except Exception as e:
        logger.warning(f"[RELATED] Error fetching previews: {e}")
    
    return results


# ==========================================
#  MAIN ENTRY POINT
# ==========================================

async def search(
    strategy: SearchStrategy,
    original_query: str,
    hebrew_term: str
) -> SearchResult:
    """
    Main entry point for Step 3: SEARCH
    
    Takes the strategy from Step 2 and returns organized sources.
    
    Args:
        strategy: SearchStrategy from Step 2
        original_query: User's original input
        hebrew_term: Hebrew term from Step 1
    
    Returns:
        SearchResult with all sources organized for display
    """
    logger.info("=" * 80)
    logger.info("STEP 3: SEARCH")
    logger.info("=" * 80)
    logger.info(f"  Strategy: {strategy.fetch_strategy}")
    logger.info(f"  Primary: {strategy.primary_source}")
    logger.info(f"  Primaries: {strategy.primary_sources}")
    logger.info(f"  Depth: {strategy.depth}")
    
    # Phase 1: FETCH (routed by strategy)
    logger.info("\n[Phase 1: FETCH]")
    sources = await fetch_sources(strategy)
    
    # Phase 2: ORGANIZE
    logger.info("\n[Phase 2: ORGANIZE]")
    sorted_sources, sources_by_level = organize_sources(sources)
    
    # Phase 2b: RELATED SUGYOS
    logger.info("\n[Phase 2b: RELATED SUGYOS]")
    related_results = await fetch_related_previews(strategy.related_sugyos)
    logger.info(f"  {len(related_results)} related sugyos")
    
    # Phase 3: FORMAT
    logger.info("\n[Phase 3: FORMAT]")
    
    levels_included = [
        LEVEL_HEBREW_NAMES.get(level.lower(), level)
        for level in sources_by_level.keys()
    ]
    
    # Determine primary source for result
    # Use primary_source if set, otherwise first of primary_sources
    result_primary = strategy.primary_source
    if not result_primary and strategy.primary_sources:
        result_primary = strategy.primary_sources[0]
    
    result_primary_he = strategy.primary_source_he
    if not result_primary_he and strategy.primary_sources_he:
        result_primary_he = strategy.primary_sources_he[0]
    
    # Handle confidence comparison (may be string or enum)
    confidence = strategy.confidence
    conf_value = confidence.value if hasattr(confidence, 'value') else confidence
    needs_clarification = (conf_value == "low" or conf_value == ConfidenceLevel.LOW)
    
    result = SearchResult(
        original_query=original_query,
        hebrew_term=hebrew_term,
        primary_source=result_primary,
        primary_source_he=result_primary_he,
        sources=sorted_sources,
        sources_by_level=sources_by_level,
        related_sugyos=related_results,
        total_sources=len(sorted_sources),
        levels_included=levels_included,
        interpretation=strategy.reasoning,
        confidence=confidence,
        needs_clarification=needs_clarification,
        clarification_prompt=strategy.clarification_prompt
    )
    
    logger.info(f"  Total sources: {result.total_sources}")
    logger.info(f"  Levels: {levels_included}")
    logger.info(f"  Related: {len(related_results)}")
    logger.info("=" * 80)
    
    return result


# ==========================================
#  MOCK DATA FOR TESTING
# ==========================================

def create_mock_result(hebrew_term: str, original_query: str) -> SearchResult:
    """
    Create mock result for testing when Sefaria is unavailable.
    """
    mock_sources = [
        Source(
            ref="Ketubot 9a",
            he_ref="כתובות ט׳ א",
            level=SourceLevel.GEMARA,
            level_hebrew=LEVEL_HEBREW_NAMES.get(SourceLevel.GEMARA.value, ""),
            level_order=get_level_order(SourceLevel.GEMARA),
            hebrew_text='ת"ר הנושא את האשה ולא מצא לה בתולים...',
            english_text="The Sages taught: One who marries a woman...",
            author="",
            categories=["Talmud", "Bavli", "Seder Nashim", "Ketubot"],
            is_primary=True,
            relevance_note="Primary sugya"
        ),
        Source(
            ref="Rashi on Ketubot 9a:1",
            he_ref='רש"י על כתובות ט׳ א:א',
            level=SourceLevel.RASHI,
            level_hebrew=LEVEL_HEBREW_NAMES.get(SourceLevel.RASHI.value, ""),
            level_order=get_level_order(SourceLevel.RASHI),
            hebrew_text="משארסתני נאנסתי - ולא נבעלתי ברצון...",
            english_text="",
            author='רש"י',
            categories=["Commentary", "Talmud", "Rashi"],
            is_primary=False,
            relevance_note=""
        ),
    ]
    
    sorted_sources, by_level = organize_sources(mock_sources)
    
    return SearchResult(
        original_query=original_query,
        hebrew_term=hebrew_term,
        primary_source="Ketubot 9a",
        primary_source_he="כתובות ט׳ א",
        sources=sorted_sources,
        sources_by_level=by_level,
        related_sugyos=[],
        total_sources=len(sorted_sources),
        levels_included=["גמרא", 'רש"י'],
        interpretation="Mock result for testing",
        confidence=ConfidenceLevel.HIGH,
        needs_clarification=False,
        clarification_prompt=None
    )


# ==========================================
#  TESTING
# ==========================================

async def test_search():
    """Test Step 3 with various strategies."""
    
    print("=" * 70)
    print("STEP 3 TEST: SEARCH (Handler Registry Pattern)")
    print("=" * 70)
    
    # Test 1: Trickle-up (original behavior)
    print("\n--- Test 1: Trickle-Up ---")
    strategy1 = SearchStrategy(
        query_type=QueryType.SUGYA_CONCEPT,
        primary_source="Ketubot 9a",
        primary_source_he="כתובות ט׳ א",
        reasoning="Testing trickle-up",
        fetch_strategy=FetchStrategy.TRICKLE_UP,
        depth="standard",
        confidence=ConfidenceLevel.HIGH
    )
    result1 = await search(strategy1, "chezkas haguf", "חזקת הגוף")
    print(f"  Sources: {result1.total_sources}")
    
    # Test 2: Direct with multiple sources (comparison)
    print("\n--- Test 2: Direct (Comparison) ---")
    strategy2 = SearchStrategy(
        query_type=QueryType.COMPARISON,
        primary_source=None,  # Intentionally None
        primary_sources=["Ran on Pesachim 4b", "Tosafot on Pesachim 4b", "Rashi on Pesachim 4b"],
        reasoning="Comparing three commentators",
        fetch_strategy=FetchStrategy.DIRECT,
        depth="standard",
        confidence=ConfidenceLevel.MEDIUM
    )
    result2 = await search(strategy2, "bittul chometz comparison", "ביטול חמץ")
    print(f"  Sources: {result2.total_sources}")
    
    print("\n" + "=" * 70)
    print("Tests complete!")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    asyncio.run(test_search())