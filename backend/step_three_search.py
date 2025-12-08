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
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

# Import from Step 2
from step_two_understand import (
    SearchStrategy, 
    QueryType, 
    FetchStrategy,
    RelatedSugya
)


# ==========================================
#  DATA STRUCTURES
# ==========================================

class SourceLevel(Enum):
    """
    Levels in the trickle-up hierarchy.
    Numbers determine display order.
    """
    CHUMASH = 1       # פסוק
    MISHNA = 2        # משנה
    GEMARA = 3        # גמרא
    RASHI = 4         # רש"י
    TOSFOS = 5        # תוספות
    RISHONIM = 6      # ראשונים
    RAMBAM = 7        # רמב"ם (both rishon and posek)
    TUR = 8           # טור
    SHULCHAN_ARUCH = 9    # שולחן ערוך
    NOSEI_KEILIM = 10     # נושאי כלים
    ACHARONIM = 11        # אחרונים
    OTHER = 99


# Hebrew names for display
LEVEL_HEBREW_NAMES = {
    SourceLevel.CHUMASH: "חומש",
    SourceLevel.MISHNA: "משנה",
    SourceLevel.GEMARA: "גמרא",
    SourceLevel.RASHI: "רש\"י",
    SourceLevel.TOSFOS: "תוספות",
    SourceLevel.RISHONIM: "ראשונים",
    SourceLevel.RAMBAM: "רמב\"ם",
    SourceLevel.TUR: "טור",
    SourceLevel.SHULCHAN_ARUCH: "שולחן ערוך",
    SourceLevel.NOSEI_KEILIM: "נושאי כלים",
    SourceLevel.ACHARONIM: "אחרונים",
    SourceLevel.OTHER: "אחר"
}


@dataclass
class Source:
    """A single source text."""
    ref: str                    # Sefaria reference
    he_ref: str                 # Hebrew reference
    level: SourceLevel          # Where it fits in hierarchy
    hebrew_text: str            # The actual Hebrew text
    english_text: str           # English translation (if available)
    author: str                 # Author/commentator name
    categories: List[str]       # Sefaria categories
    
    # Display helpers
    level_hebrew: str = ""      # Hebrew name for the level
    is_primary: bool = False    # Is this the main source?
    relevance_note: str = ""    # Why this source is included
    
    def __post_init__(self):
        if not self.level_hebrew:
            self.level_hebrew = LEVEL_HEBREW_NAMES.get(self.level, "")
    
    def to_dict(self) -> Dict:
        return {
            "ref": self.ref,
            "he_ref": self.he_ref,
            "level": self.level.name,
            "level_order": self.level.value,
            "level_hebrew": self.level_hebrew,
            "hebrew_text": self.hebrew_text,
            "english_text": self.english_text,
            "author": self.author,
            "categories": self.categories,
            "is_primary": self.is_primary,
            "relevance_note": self.relevance_note
        }


@dataclass
class RelatedSugyaResult:
    """A related sugya with brief info (not full sources)."""
    ref: str
    he_ref: str
    connection: str         # How it relates to main sugya
    importance: str         # primary/secondary/tangential
    preview_text: str       # Brief snippet to show what it's about
    
    def to_dict(self) -> Dict:
        return {
            "ref": self.ref,
            "he_ref": self.he_ref,
            "connection": self.connection,
            "importance": self.importance,
            "preview_text": self.preview_text
        }


@dataclass 
class SearchResult:
    """
    Complete output from Step 3.
    This is what the frontend receives.
    """
    # The query info
    original_query: str
    hebrew_term: str
    
    # What we found
    primary_source: Optional[str]       # Main Gemara reference
    primary_source_he: Optional[str]
    
    # Sources organized by level (trickle-up)
    sources: List[Source]               # All sources in display order
    sources_by_level: Dict[str, List[Source]]  # Grouped by level
    
    # Related sugyos (per user preference - show if important)
    related_sugyos: List[RelatedSugyaResult]
    
    # Metadata
    total_sources: int
    levels_included: List[str]
    
    # Claude's reasoning
    interpretation: str                 # What we think user wanted
    confidence: str                     # high/medium/low
    
    # If we're uncertain
    needs_clarification: bool
    clarification_prompt: Optional[str]
    
    def to_dict(self) -> Dict:
        return {
            "original_query": self.original_query,
            "hebrew_term": self.hebrew_term,
            "primary_source": self.primary_source,
            "primary_source_he": self.primary_source_he,
            "sources": [s.to_dict() for s in self.sources],
            "sources_by_level": {
                level: [s.to_dict() for s in sources]
                for level, sources in self.sources_by_level.items()
            },
            "related_sugyos": [s.to_dict() for s in self.related_sugyos],
            "total_sources": self.total_sources,
            "levels_included": self.levels_included,
            "interpretation": self.interpretation,
            "confidence": self.confidence,
            "needs_clarification": self.needs_clarification,
            "clarification_prompt": self.clarification_prompt
        }


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
        from tools.sefaria_client import get_sefaria_client, SourceLevel as ClientSourceLevel
        client = get_sefaria_client()
        
        # Get the primary Gemara text
        logger.info(f"[FETCH] Getting Gemara: {strategy.primary_source}")
        gemara = await client.get_text(strategy.primary_source)
        
        if gemara:
            sources.append(Source(
                ref=gemara.ref,
                he_ref=gemara.he_ref,
                level=SourceLevel.GEMARA,
                hebrew_text=gemara.hebrew[:2000] if gemara.hebrew else "",  # Limit length
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
    # The client uses similar enum values, but we need to map them
    try:
        return SourceLevel[client_level.name]
    except (KeyError, AttributeError):
        return SourceLevel.OTHER


def _extract_author(category: str, categories: List[str]) -> str:
    """Extract author name from category info."""
    
    # Common author patterns
    author_map = {
        "rashi": "רש\"י",
        "tosafot": "תוספות",
        "tosafos": "תוספות",
        "ramban": "רמב\"ן",
        "rashba": "רשב\"א",
        "ritva": "ריטב\"א",
        "ran": "ר\"ן",
        "rosh": "רא\"ש",
        "rambam": "רמב\"ם",
        "maharsha": "מהרש\"א",
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
    
    # Sort by level (trickle-up order: Chumash → Mishna → Gemara → ...)
    sorted_sources = sorted(sources, key=lambda s: s.level.value)
    
    # Group by level
    by_level: Dict[str, List[Source]] = {}
    for source in sorted_sources:
        level_name = source.level.name
        if level_name not in by_level:
            by_level[level_name] = []
        by_level[level_name].append(source)
    
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
        LEVEL_HEBREW_NAMES.get(SourceLevel[level], level)
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
        needs_clarification=(strategy.confidence == "low"),
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
            hebrew_text="ת\"ר הנושא את האשה ולא מצא לה בתולים היא אומרת משארסתני נאנסתי והוא אומר לא כי אלא עד שלא ארסתיך והיה מקחי מקח טעות...",
            english_text="The Sages taught: One who marries a woman and did not find her a virgin...",
            author="",
            categories=["Talmud", "Bavli", "Seder Nashim", "Ketubot"],
            is_primary=True,
            relevance_note="Primary sugya discussing חזקת הגוף"
        ),
        Source(
            ref="Rashi on Ketubot 9a:1",
            he_ref="רש״י על כתובות ט׳ א:א",
            level=SourceLevel.RASHI,
            hebrew_text="משארסתני נאנסתי - ולא נבעלתי ברצון ולא פקע קדושין...",
            english_text="",
            author="רש\"י",
            categories=["Commentary", "Talmud", "Rashi"],
            is_primary=False,
            relevance_note=""
        ),
        Source(
            ref="Tosafot on Ketubot 9a:1:1",
            he_ref="תוספות על כתובות ט׳ א:א:א",
            level=SourceLevel.TOSFOS,
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
        levels_included=["גמרא", "רש\"י", "תוספות"],
        interpretation="The user is looking for the sugya of חזקת הגוף, which is primarily discussed in Kesubos 9a regarding a case where a woman claims she was violated after erusin.",
        confidence="high",
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
        confidence="high"
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
