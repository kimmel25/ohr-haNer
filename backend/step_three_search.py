"""
Step 3: SEARCH - Fetch and Organize Sources
============================================

This step takes the SearchStrategy from Step 2 and:
1. FETCH: Get the actual source texts from Sefaria
2. ORGANIZE: Arrange them in trickle-up order
3. FORMAT: Prepare the final output for the user

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
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Import from Step 2
from step_two_understand import (
    SearchStrategy, 
    QueryType, 
    FetchStrategy,
    RelatedSugya
)

# Import centralized Pydantic models from models.py
from models import (
    SourceLevel,
    Source,
    RelatedSugyaResult,
    SearchResult,
    ConfidenceLevel
)


# ==========================================
#  HEBREW NAMES AND HELPERS
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


# ==========================================
#  SOURCE FETCHING
# ==========================================

async def fetch_sources(strategy: SearchStrategy) -> List[Source]:
    """
    Phase 1: FETCH - Get source texts from Sefaria based on strategy.
    """
    logger.info(f"[FETCH] Getting sources for: {strategy.primary_source}")
    
    sources: List[Source] = []
    
    if not strategy.primary_source:
        logger.warning("[FETCH] No primary source specified")
        return sources
    
    try:
        from tools.sefaria_client import get_sefaria_client
        client = get_sefaria_client()
        
        # Get the primary Gemara text
        logger.info(f"[FETCH] Getting Gemara: {strategy.primary_source}")
        gemara = await client.get_text(strategy.primary_source)
        
        if gemara:
            sources.append(Source(
                ref=gemara.ref,
                he_ref=gemara.he_ref,
                level=SourceLevel.GEMARA,
                level_hebrew=LEVEL_HEBREW_NAMES.get(SourceLevel.GEMARA.value, ""),
                level_order=get_level_order(SourceLevel.GEMARA),
                hebrew_text=gemara.hebrew[:2000] if gemara.hebrew else "",
                english_text=gemara.english[:2000] if gemara.english else "",
                author="",
                categories=gemara.categories,
                is_primary=True,
                relevance_note="Primary source"
            ))
        
        # Get related content (commentaries)
        logger.info(f"[FETCH] Getting related content...")
        related = await client.get_related(strategy.primary_source)
        
        # Determine which levels to include based on strategy.depth
        levels_to_fetch = _get_levels_for_depth(strategy.depth)
        
        # Fetch each relevant commentary
        for commentary in related.commentaries:
            level = _map_client_level(commentary.level)
            
            if level not in levels_to_fetch:
                continue
            
            # Get full text for this commentary
            comm_text = await client.get_text(commentary.ref)
            
            if comm_text:
                sources.append(Source(
                    ref=comm_text.ref,
                    he_ref=comm_text.he_ref,
                    level=level,
                    level_hebrew=LEVEL_HEBREW_NAMES.get(level.value, ""),
                    level_order=get_level_order(level),
                    hebrew_text=comm_text.hebrew[:1500] if comm_text.hebrew else "",
                    english_text=comm_text.english[:1500] if comm_text.english else "",
                    author=_extract_author(commentary.category, comm_text.categories),
                    categories=comm_text.categories,
                    is_primary=False,
                    relevance_note=""
                ))
        
        logger.info(f"[FETCH] Retrieved {len(sources)} sources")
        
    except Exception as e:
        logger.error(f"[FETCH] Error: {e}", exc_info=True)
    
    return sources


def _get_levels_for_depth(depth: str) -> set:
    """Determine which source levels to include based on depth setting."""
    # Always include Gemara
    levels = {SourceLevel.GEMARA}
    
    if depth in ["standard", "expanded", "full"]:
        # Standard: Gemara + Rashi + Tosfos + Mishna/Chumash
        levels.update({
            SourceLevel.RASHI,
            SourceLevel.TOSFOS,
            SourceLevel.MISHNA,
            SourceLevel.CHUMASH
        })
    
    if depth in ["expanded", "full"]:
        # Expanded: Add Rishonim and Rambam
        levels.update({
            SourceLevel.RISHONIM,
            SourceLevel.RAMBAM
        })
    
    if depth == "full":
        # Full: Everything
        levels.update({
            SourceLevel.TUR,
            SourceLevel.SHULCHAN_ARUCH,
            SourceLevel.NOSEI_KEILIM,
            SourceLevel.ACHARONIM
        })
    
    return levels


def _map_client_level(client_level) -> SourceLevel:
    """Map Sefaria client's SourceLevel to our SourceLevel."""
    # Handle various input types
    try:
        # If it's already our SourceLevel enum, return it
        if isinstance(client_level, SourceLevel):
            return client_level
        
        # If it's a string, try to match it
        if isinstance(client_level, str):
            # Try lowercase match first
            try:
                return SourceLevel(client_level.lower())
            except ValueError:
                # Try as enum name (uppercase)
                try:
                    return SourceLevel[client_level.upper()]
                except KeyError:
                    pass
        
        # If it has a name attribute (another enum type)
        if hasattr(client_level, 'name'):
            try:
                return SourceLevel[client_level.name.upper()]
            except (KeyError, AttributeError):
                pass
                
    except Exception:
        pass
    
    return SourceLevel.OTHER


def _extract_author(category: str, categories: List[str]) -> str:
    """Extract author name from category info."""
    
    # Common author patterns (using yeshivish spelling with sav)
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
    
    return category


# ==========================================
#  SOURCE ORGANIZATION
# ==========================================

def organize_sources(sources: List[Source]) -> Tuple[List[Source], Dict[str, List[Source]]]:
    """
    Phase 2: ORGANIZE - Arrange sources in trickle-up order.
    
    Returns:
        (ordered_list, grouped_by_level)
    """
    logger.info(f"[ORGANIZE] Organizing {len(sources)} sources")
    
    # Sort by level_order (numeric ordering)
    sorted_sources = sorted(sources, key=lambda s: s.level_order)
    
    # Group by level
    by_level: Dict[str, List[Source]] = {}
    for source in sorted_sources:
        # Use uppercase level name as key (e.g., "GEMARA")
        # Handle both enum and string types
        if hasattr(source.level, 'name'):
            level_key = source.level.name.upper()
        else:
            level_key = str(source.level).upper()
        if level_key not in by_level:
            by_level[level_key] = []
        by_level[level_key].append(source)
    
    # Log what we have
    for level_name, level_sources in by_level.items():
        logger.info(f"  {level_name}: {len(level_sources)} sources")
    
    return sorted_sources, by_level


async def fetch_related_previews(
    related_sugyos: List[RelatedSugya]
) -> List[RelatedSugyaResult]:
    """
    Fetch brief previews for related sugyos.
    We don't fetch full sources - just enough to show what they're about.
    """
    results = []
    
    if not related_sugyos:
        return results
    
    try:
        from tools.sefaria_client import get_sefaria_client
        client = get_sefaria_client()
        
        for sugya in related_sugyos:
            if not sugya.ref:
                continue
            
            # Get just a snippet
            text = await client.get_text(sugya.ref)
            preview = ""
            if text and text.hebrew:
                preview = text.hebrew[:200] + "..." if len(text.hebrew) > 200 else text.hebrew
            
            results.append(RelatedSugyaResult(
                ref=sugya.ref,
                he_ref=sugya.he_ref or sugya.ref,
                connection=sugya.connection,
                importance=sugya.importance,
                preview_text=preview
            ))
    
    except Exception as e:
        logger.warning(f"[RELATED] Error fetching previews: {e}")
    
    return results


# ==========================================
#  MAIN STEP 3 FUNCTION
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
    logger.info(f"  Strategy: {strategy.fetch_strategy.value}")
    logger.info(f"  Primary: {strategy.primary_source}")
    logger.info(f"  Depth: {strategy.depth}")
    
    # Phase 1: FETCH
    logger.info("\n[Phase 1: FETCH]")
    sources = await fetch_sources(strategy)
    
    # Phase 2: ORGANIZE
    logger.info("\n[Phase 2: ORGANIZE]")
    sorted_sources, sources_by_level = organize_sources(sources)
    
    # Fetch related sugya previews
    logger.info("\n[Phase 2b: RELATED SUGYOS]")
    related_results = await fetch_related_previews(strategy.related_sugyos)
    logger.info(f"  {len(related_results)} related sugyos")
    
    # Phase 3: FORMAT (build final result)
    logger.info("\n[Phase 3: FORMAT]")
    
    levels_included = [
        LEVEL_HEBREW_NAMES.get(level.lower(), level)
        for level in sources_by_level.keys()
    ]
    
    result = SearchResult(
        original_query=original_query,
        hebrew_term=hebrew_term,
        primary_source=strategy.primary_source,
        primary_source_he=strategy.primary_source_he,
        sources=sorted_sources,
        sources_by_level=sources_by_level,
        related_sugyos=related_results,
        total_sources=len(sorted_sources),
        levels_included=levels_included,
        interpretation=strategy.reasoning,
        confidence=strategy.confidence,
        needs_clarification=(strategy.confidence == ConfidenceLevel.LOW),
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
    Uses realistic data structure.
    """
    
    # Mock sources for "חזקת הגוף"
    mock_sources = [
        Source(
            ref="Ketubot 9a",
            he_ref="כתובות ט׳ א",
            level=SourceLevel.GEMARA,
            level_hebrew=LEVEL_HEBREW_NAMES.get(SourceLevel.GEMARA.value, ""),
            level_order=get_level_order(SourceLevel.GEMARA),
            hebrew_text='ת"ר הנושא את האשה ולא מצא לה בתולים היא אומרת משארסתני נאנסתי והוא אומר לא כי אלא עד שלא ארסתיך והיה מקחי מקח טעות...',
            english_text="The Sages taught: One who marries a woman and did not find her a virgin...",
            author="",
            categories=["Talmud", "Bavli", "Seder Nashim", "Ketubot"],
            is_primary=True,
            relevance_note="Primary sugya discussing חזקת הגוף"
        ),
        Source(
            ref="Rashi on Ketubot 9a:1",
            he_ref='רש"י על כתובות ט׳ א:א',
            level=SourceLevel.RASHI,
            level_hebrew=LEVEL_HEBREW_NAMES.get(SourceLevel.RASHI.value, ""),
            level_order=get_level_order(SourceLevel.RASHI),
            hebrew_text="משארסתני נאנסתי - ולא נבעלתי ברצון ולא פקע קדושין...",
            english_text="",
            author='רש"י',
            categories=["Commentary", "Talmud", "Rashi"],
            is_primary=False,
            relevance_note=""
        ),
        Source(
            ref="Tosafot on Ketubot 9a:1:1",
            he_ref="תוספות על כתובות ט׳ א:א:א",
            level=SourceLevel.TOSFOS,
            level_hebrew=LEVEL_HEBREW_NAMES.get(SourceLevel.TOSFOS.value, ""),
            level_order=get_level_order(SourceLevel.TOSFOS),
            hebrew_text="העמד אשה על חזקתה - וא\"ת והא חזקה דגופא עדיפא מחזקת ממון...",
            english_text="",
            author="תוספות",
            categories=["Commentary", "Talmud", "Tosafot"],
            is_primary=False,
            relevance_note=""
        ),
    ]
    
    mock_related = [
        RelatedSugyaResult(
            ref="Niddah 2a",
            he_ref="נדה ב׳ א",
            connection="Also discusses העמדת אשה על חזקתה",
            importance="secondary",
            preview_text="שמאי אומר כל הנשים דיין שעתן..."
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
        related_sugyos=mock_related,
        total_sources=len(sorted_sources),
        levels_included=["גמרא", 'רש"י', "תוספות"],
        interpretation="The user is looking for the sugya of חזקת הגוף, which is primarily discussed in Kesubos 9a regarding a case where a woman claims she was violated after erusin.",
        confidence=ConfidenceLevel.HIGH,
        needs_clarification=False,
        clarification_prompt=None
    )


# ==========================================
#  TESTING
# ==========================================

async def test_search():
    """Test Step 3."""
    
    print("=" * 70)
    print("STEP 3 TEST: SEARCH")
    print("=" * 70)
    
    # Create a mock strategy (as if from Step 2)
    from step_two_understand import SearchStrategy, QueryType, FetchStrategy, RelatedSugya
    
    strategy = SearchStrategy(
        query_type=QueryType.SUGYA_CONCEPT,
        primary_source="Ketubot 9a",
        primary_source_he="כתובות ט׳ א",
        reasoning="חזקת הגוף is primarily discussed in Kesubos 9a",
        related_sugyos=[
            RelatedSugya(
                ref="Niddah 2a",
                he_ref="נדה ב׳ א",
                connection="Also discusses חזקת הגוף",
                importance="secondary"
            )
        ],
        fetch_strategy=FetchStrategy.TRICKLE_UP,
        depth="standard",
        confidence=ConfidenceLevel.HIGH
    )
    
    result = await search(strategy, "chezkas haguf", "חזקת הגוף")
    
    print(f"\nResult Summary:")
    print(f"  Primary: {result.primary_source}")
    print(f"  Total sources: {result.total_sources}")
    print(f"  Levels: {result.levels_included}")
    print(f"  Confidence: {result.confidence}")
    
    print(f"\nSources by level:")
    for level, sources in result.sources_by_level.items():
        print(f"  {level}:")
        for s in sources:
            print(f"    - {s.ref} ({s.author or 'N/A'})")
    
    if result.related_sugyos:
        print(f"\nRelated sugyos:")
        for r in result.related_sugyos:
            print(f"  - {r.ref}: {r.connection}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    asyncio.run(test_search())