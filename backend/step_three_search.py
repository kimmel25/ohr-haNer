"""
Step 3: SEARCH - Fetch and Organize Sources
============================================

This step takes the SearchStrategy from Step 2 and:
1. FETCH: Get the actual source texts from Sefaria
2. ORGANIZE: Arrange them in trickle-up order
3. FORMAT: Prepare the final output for the user
"""

import asyncio
import logging
from typing import Any, Dict, Iterable, List, Tuple

from models import (
    ConfidenceLevel,
    FetchStrategy,
    QueryType,
    RelatedSugya,
    RelatedSugyaResult,
    SearchResult,
    SearchStrategy,
    Source,
    SourceLevel,
)
from utils.levels import LEVEL_HEBREW_NAMES, get_level_order

logger = logging.getLogger("pipeline.step3")


# ==========================================
#  SOURCE FETCHING
# ==========================================

async def fetch_sources(strategy: SearchStrategy) -> List[Source]:
    """Phase 1: FETCH - Get source texts from Sefaria based on strategy."""
    logger.info("[FETCH] Getting sources for primary=%s", strategy.primary_source)

    sources: List[Source] = []

    if not strategy.primary_source:
        logger.warning("[FETCH] No primary source specified")
        return sources

    try:
        from tools.sefaria_client import get_sefaria_client

        client = get_sefaria_client()

        logger.info("[FETCH] Getting Gemara: %s", strategy.primary_source)
        gemara = await client.get_text(strategy.primary_source)

        if gemara:
            sources.append(
                Source(
                    ref=gemara.ref,
                    he_ref=gemara.he_ref,
                    level=SourceLevel.GEMARA,
                    level_hebrew=LEVEL_HEBREW_NAMES.get(
                        SourceLevel.GEMARA.value, "גמרא"
                    ),
                    level_order=get_level_order(SourceLevel.GEMARA),
                    hebrew_text=gemara.hebrew[:2000] if gemara.hebrew else "",
                    english_text=gemara.english[:2000] if gemara.english else "",
                    author="",
                    categories=gemara.categories,
                    is_primary=True,
                    relevance_note="Primary source",
                )
            )

        logger.info("[FETCH] Getting related content...")
        related = await client.get_related(strategy.primary_source)
        levels_to_fetch = _get_levels_for_depth(strategy.depth)

        for commentary in related.commentaries:
            level = _map_client_level(commentary.level)
            if level not in levels_to_fetch:
                continue

            comm_text = await client.get_text(commentary.ref)
            if not comm_text:
                continue

            sources.append(
                Source(
                    ref=comm_text.ref,
                    he_ref=comm_text.he_ref,
                    level=level,
                    level_hebrew=LEVEL_HEBREW_NAMES.get(
                        level.value, level.name.title()
                    ),
                    level_order=get_level_order(level),
                    hebrew_text=comm_text.hebrew[:1500] if comm_text.hebrew else "",
                    english_text=comm_text.english[:1500] if comm_text.english else "",
                    author=_extract_author(commentary.category, comm_text.categories),
                    categories=comm_text.categories,
                    is_primary=False,
                    relevance_note="",
                )
            )

        logger.info("[FETCH] Retrieved %s sources", len(sources))

    except Exception as exc:  # noqa: BLE001
        logger.error("[FETCH] Error: %s", exc, exc_info=True)

    return sources


def _get_levels_for_depth(depth: str) -> set:
    """Determine which source levels to include based on depth setting."""
    levels = {SourceLevel.GEMARA}

    if depth in ["standard", "expanded", "full"]:
        levels.update(
            {
                SourceLevel.RASHI,
                SourceLevel.TOSFOS,
                SourceLevel.MISHNA,
                SourceLevel.CHUMASH,
            }
        )

    if depth in ["expanded", "full"]:
        levels.update({SourceLevel.RISHONIM, SourceLevel.RAMBAM})

    if depth == "full":
        levels.update(
            {
                SourceLevel.TUR,
                SourceLevel.SHULCHAN_ARUCH,
                SourceLevel.NOSEI_KEILIM,
                SourceLevel.ACHARONIM,
            }
        )

    return levels


def _map_client_level(client_level: Any) -> SourceLevel:
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

        if hasattr(client_level, "name"):
            try:
                return SourceLevel[client_level.name.upper()]
            except (KeyError, AttributeError):
                pass
    except Exception:
        pass

    return SourceLevel.OTHER


def _extract_author(category: str, categories: List[str]) -> str:
    """Extract author name from category info."""
    author_map = {
        "rashi": 'רש"י',
        "tosafot": "תוספות",
        "tosfos": "תוספות",
        "ramban": 'רמב"ן',
        "rashba": 'רשב"א',
        "ritva": 'ריטב"א',
        "ran": 'הר"ן',
        "rosh": 'הרא"ש',
        "rambam": 'רמב"ם',
        "maharsha": 'מהרש"א',
        "pnei yehoshua": "פני יהושע",
        "shita mekubetzet": "שיטה מקובצת",
    }

    category_lower = category.lower()
    for eng, heb in author_map.items():
        if eng in category_lower:
            return heb

    return category or (categories[0] if categories else "")


# ==========================================
#  SOURCE ORGANIZATION
# ==========================================

def organize_sources(sources: List[Source]) -> Tuple[List[Source], Dict[str, List[Source]]]:
    """
    Phase 2: ORGANIZE - Arrange sources in trickle-up order.

    Returns:
        (ordered_list, grouped_by_level)
    """
    logger.info("[ORGANIZE] Organizing %s sources", len(sources))

    sorted_sources = sorted(sources, key=lambda source: source.level_order)

    by_level: Dict[str, List[Source]] = {}
    for source in sorted_sources:
        level_key = (
            source.level.name.upper() if hasattr(source.level, "name") else str(source.level).upper()
        )
        by_level.setdefault(level_key, []).append(source)

    for level_name, level_sources in by_level.items():
        logger.info("  %s: %s sources", level_name, len(level_sources))

    return sorted_sources, by_level


async def fetch_related_previews(
    related_sugyos: Iterable[RelatedSugya],
) -> List[RelatedSugyaResult]:
    """
    Fetch brief previews for related sugyos.
    We don't fetch full sources - just enough to show what they're about.
    """
    results: List[RelatedSugyaResult] = []

    if not related_sugyos:
        return results

    try:
        from tools.sefaria_client import get_sefaria_client

        client = get_sefaria_client()

        for sugya in related_sugyos:
            if not sugya.ref:
                continue

            text = await client.get_text(sugya.ref)
            preview = ""
            if text and text.hebrew:
                preview = text.hebrew[:200]
                if len(text.hebrew) > 200:
                    preview += "..."

            results.append(
                RelatedSugyaResult(
                    ref=sugya.ref,
                    he_ref=sugya.he_ref or sugya.ref,
                    connection=sugya.connection,
                    importance=sugya.importance,
                    preview_text=preview,
                )
            )

    except Exception as exc:  # noqa: BLE001
        logger.warning("[RELATED] Error fetching previews: %s", exc)

    return results


# ==========================================
#  MAIN STEP 3 FUNCTION
# ==========================================

async def search(
    strategy: SearchStrategy,
    original_query: str,
    hebrew_term: str,
) -> SearchResult:
    """
    Main entry point for Step 3: SEARCH.

    Args:
        strategy: SearchStrategy from Step 2
        original_query: User's original input
        hebrew_term: Hebrew term from Step 1

    Returns:
        SearchResult with all sources organized for display.
    """
    logger.info("=" * 60)
    logger.info("STEP 3: SEARCH")
    logger.info("  Strategy: %s", strategy.fetch_strategy)
    logger.info("  Primary:  %s", strategy.primary_source)
    logger.info("  Depth:    %s", strategy.depth)

    # Phase 1: FETCH
    logger.info("[Phase 1: FETCH]")
    sources = await fetch_sources(strategy)

    # Phase 2: ORGANIZE
    logger.info("[Phase 2: ORGANIZE]")
    sorted_sources, sources_by_level = organize_sources(sources)

    # Phase 2b: RELATED SUGYOS
    logger.info("[Phase 2b: RELATED SUGYOS]")
    related_results = await fetch_related_previews(strategy.related_sugyos)
    logger.info("  %s related sugyos", len(related_results))

    # Phase 3: FORMAT
    logger.info("[Phase 3: FORMAT]")
    levels_included = [
        LEVEL_HEBREW_NAMES.get(level.lower(), level.title())
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
        clarification_prompt=strategy.clarification_prompt,
    )

    logger.info("  Total sources: %s", result.total_sources)
    logger.info("  Levels: %s", levels_included)
    logger.info("  Related: %s", len(related_results))
    logger.info("=" * 60)

    return result


# ==========================================
#  MOCK DATA FOR TESTING
# ==========================================

def create_mock_result(hebrew_term: str, original_query: str) -> SearchResult:
    """
    Create mock result for testing when Sefaria is unavailable.
    Uses realistic data structure.
    """
    mock_sources = [
        Source(
            ref="Ketubot 9a",
            he_ref="כתובות ט ע\"א",
            level=SourceLevel.GEMARA,
            level_hebrew=LEVEL_HEBREW_NAMES.get(SourceLevel.GEMARA.value, "גמרא"),
            level_order=get_level_order(SourceLevel.GEMARA),
            hebrew_text="הסוגיה הראשית העוסקת בדיני כתובה והשלכות המקרה.",
            english_text="Primary sugya discussing ketubah obligations.",
            author="",
            categories=["Talmud", "Bavli", "Ketubot"],
            is_primary=True,
            relevance_note="Primary sugya",
        ),
        Source(
            ref="Rashi on Ketubot 9a:1",
            he_ref='רש"י כתובות ט ע"א:1',
            level=SourceLevel.RASHI,
            level_hebrew=LEVEL_HEBREW_NAMES.get(SourceLevel.RASHI.value, 'רש"י'),
            level_order=get_level_order(SourceLevel.RASHI),
            hebrew_text="ביאור רש\"י על דברי הגמרא.",
            english_text="Rashi commentary on the sugya.",
            author='רש"י',
            categories=["Commentary", "Talmud", "Rashi"],
            is_primary=False,
            relevance_note="",
        ),
        Source(
            ref="Tosafot on Ketubot 9a:1:1",
            he_ref="תוספות כתובות ט ע\"א:1:1",
            level=SourceLevel.TOSFOS,
            level_hebrew=LEVEL_HEBREW_NAMES.get(SourceLevel.TOSFOS.value, "תוספות"),
            level_order=get_level_order(SourceLevel.TOSFOS),
            hebrew_text="קושיה ותירוץ בסגנון בעלי התוספות.",
            english_text="Tosafot analysis on the sugya.",
            author="תוספות",
            categories=["Commentary", "Talmud", "Tosafot"],
            is_primary=False,
            relevance_note="",
        ),
    ]

    mock_related = [
        RelatedSugyaResult(
            ref="Niddah 2a",
            he_ref="נידה ב ע\"א",
            connection="Parallel discussion relevant to the topic.",
            importance="secondary",
            preview_text="קטע קצר מתוך הסוגיה המקבילה.",
        ),
    ]

    sorted_sources, by_level = organize_sources(mock_sources)

    return SearchResult(
        original_query=original_query,
        hebrew_term=hebrew_term,
        primary_source="Ketubot 9a",
        primary_source_he="כתובות ט ע\"א",
        sources=sorted_sources,
        sources_by_level=by_level,
        related_sugyos=mock_related,
        total_sources=len(sorted_sources),
        levels_included=[
            LEVEL_HEBREW_NAMES.get(SourceLevel.GEMARA.value, "גמרא"),
            LEVEL_HEBREW_NAMES.get(SourceLevel.RASHI.value, 'רש"י'),
            LEVEL_HEBREW_NAMES.get(SourceLevel.TOSFOS.value, "תוספות"),
        ],
        interpretation=(
            "The user is looking for the sugya, starting from the primary Gemara "
            "and moving through classic commentaries."
        ),
        confidence=ConfidenceLevel.HIGH,
        needs_clarification=False,
        clarification_prompt=None,
    )


# ==========================================
#  TESTING
# ==========================================

async def test_search() -> None:
    """Test Step 3 with a mock strategy."""
    print("=" * 70)
    print("STEP 3 TEST: SEARCH")
    print("=" * 70)

    strategy = SearchStrategy(
        query_type=QueryType.SUGYA_CONCEPT,
        primary_source="Ketubot 9a",
        primary_source_he="כתובות ט ע\"א",
        reasoning="Primary sugya for the requested topic.",
        related_sugyos=[
            RelatedSugya(
                ref="Niddah 2a",
                he_ref="נידה ב ע\"א",
                connection="Also discusses this concept",
                importance="secondary",
            )
        ],
        fetch_strategy=FetchStrategy.TRICKLE_UP,
        depth="standard",
        confidence=ConfidenceLevel.HIGH,
    )

    result = await search(strategy, "chezkas haguf", "חזקת הגוף")

    print("\nResult Summary:")
    print(f"  Primary: {result.primary_source}")
    print(f"  Total sources: {result.total_sources}")
    print(f"  Levels: {result.levels_included}")
    print(f"  Confidence: {result.confidence}")

    print("\nSources by level:")
    for level, sources in result.sources_by_level.items():
        print(f"  {level}:")
        for source in sources:
            author = source.author if hasattr(source, "author") else source.get("author", "")
            print(f"    - {source.ref} ({author or 'N/A'})")

    if result.related_sugyos:
        print("\nRelated sugyos:")
        for related in result.related_sugyos:
            print(f"  - {related.ref}: {related.connection}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
    )

    asyncio.run(test_search())
