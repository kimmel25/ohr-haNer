"""
Step 3: SEARCH - Fetch and Organize Sources
============================================

Takes QueryAnalysis from Step 2 and executes the search plan.

KEY DISTINCTION (from Architecture):
1. FIND the sources on the INYAN (using search_topics)
2. FETCH the commentaries on those sources (using target_authors)

This is NOT keyword searching with author names!

TRICKLE UP (from Architecture):
- Find psukim on this inyan
- Find mishnayos quoting those psukim or discussing the inyan
- Find gemara discussing the inyan (Bavli first)
- THEN fetch: Rashi → Tosfos → other Rishonim → Tur → SA → etc.

TRICKLE DOWN:
- Start from acharonim/poskim mentioning the inyan
- Trace their citations back to rishonim → gemara → mishna → pasuk
"""

import logging
import asyncio
import re
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field

from models import ConfidenceLevel

# Import Step 2's output type
try:
    from step_two_understand import (
        QueryAnalysis, 
        SearchMethod, 
        QueryType,
        Breadth,
        SourceCategories
    )
except ImportError:
    pass

logger = logging.getLogger(__name__)


# ==============================================================================
#  SOURCE LEVELS (Trickle-Up Order)
# ==============================================================================

class SourceLevel:
    """Source levels in trickle-up order."""
    PASUK = "pasuk"
    MISHNA = "mishna"
    TOSEFTA = "tosefta"
    GEMARA_BAVLI = "gemara_bavli"
    GEMARA_YERUSHALMI = "gemara_yerushalmi"
    MIDRASH = "midrash"
    RASHI = "rashi"
    TOSFOS = "tosfos"
    RISHONIM = "rishonim"
    RAMBAM = "rambam"
    TUR = "tur"
    SHULCHAN_ARUCH = "shulchan_aruch"
    NOSEI_KEILIM = "nosei_keilim"
    ACHARONIM = "acharonim"
    OTHER = "other"


TRICKLE_UP_ORDER = [
    SourceLevel.PASUK,
    SourceLevel.MISHNA,
    SourceLevel.TOSEFTA,
    SourceLevel.GEMARA_BAVLI,
    SourceLevel.GEMARA_YERUSHALMI,
    SourceLevel.MIDRASH,
    SourceLevel.RASHI,
    SourceLevel.TOSFOS,
    SourceLevel.RISHONIM,
    SourceLevel.RAMBAM,
    SourceLevel.TUR,
    SourceLevel.SHULCHAN_ARUCH,
    SourceLevel.NOSEI_KEILIM,
    SourceLevel.ACHARONIM,
]

LEVEL_HEBREW = {
    SourceLevel.PASUK: "פסוק",
    SourceLevel.MISHNA: "משנה",
    SourceLevel.TOSEFTA: "תוספתא",
    SourceLevel.GEMARA_BAVLI: "גמרא בבלי",
    SourceLevel.GEMARA_YERUSHALMI: "ירושלמי",
    SourceLevel.MIDRASH: "מדרש",
    SourceLevel.RASHI: 'רש"י',
    SourceLevel.TOSFOS: "תוספות",
    SourceLevel.RISHONIM: "ראשונים",
    SourceLevel.RAMBAM: 'רמב"ם',
    SourceLevel.TUR: "טור",
    SourceLevel.SHULCHAN_ARUCH: "שולחן ערוך",
    SourceLevel.NOSEI_KEILIM: "נושאי כלים",
    SourceLevel.ACHARONIM: "אחרונים",
}

# Map author names to Sefaria prefixes
AUTHOR_TO_SEFARIA_PREFIX = {
    "Rashi": "Rashi on",
    "Tosfos": "Tosafot on",
    "Tosafot": "Tosafot on",
    "Ran": "Ran on",
    "Rashba": "Rashba on",
    "Ritva": "Ritva on",
    "Ramban": "Ramban on",
    "Rosh": "Rosh on",
    "Meiri": "Meiri on",
    "Maharsha": "Chidushei Agadot on",  # or Chidushei Halachot
}


# ==============================================================================
#  SOURCE DATA STRUCTURES
# ==============================================================================

@dataclass
class Source:
    """A single source."""
    ref: str
    he_ref: str
    level: str
    level_hebrew: str
    hebrew_text: str
    english_text: str = ""
    author: str = ""
    categories: List[str] = field(default_factory=list)
    relevance_description: str = ""
    is_primary: bool = False


@dataclass
class SearchResult:
    """Complete search result."""
    original_query: str
    search_topics: List[str]
    
    sources: List[Source] = field(default_factory=list)
    sources_by_level: Dict[str, List[Source]] = field(default_factory=dict)
    
    # Base sources found (the gemara/mishna refs)
    base_refs_found: List[str] = field(default_factory=list)
    
    total_sources: int = 0
    levels_found: List[str] = field(default_factory=list)
    search_description: str = ""
    
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    needs_clarification: bool = False
    clarification_question: Optional[str] = None


# ==============================================================================
#  SEFARIA API HELPERS
# ==============================================================================

async def search_sefaria_for_inyan(
    inyan: str, 
    masechta_filter: str = None,
    category_filter: List[str] = None,
    size: int = 30
) -> List[Dict]:
    """
    Search Sefaria for an INYAN (topic/concept).
    
    This searches for the actual concept, NOT for author names.
    """
    try:
        from tools.sefaria_client import get_sefaria_client
        client = get_sefaria_client()
        
        # Build search query - just the inyan
        search_query = inyan
        
        # If masechta specified, add it to narrow results
        if masechta_filter:
            search_query = f"{masechta_filter} {inyan}"
        
        logger.info(f"[SEARCH] Searching Sefaria for INYAN: '{search_query}'")
        
        results = await client.search(search_query, size=size, filters=category_filter)
        
        if results and results.hits:
            logger.info(f"[SEARCH] Found {len(results.hits)} hits")
            return results.hits
        return []
        
    except Exception as e:
        logger.error(f"[SEARCH] Error searching for '{inyan}': {e}")
        return []


async def get_text(ref: str) -> Optional[Dict]:
    """Fetch text content from Sefaria."""
    try:
        from tools.sefaria_client import get_sefaria_client
        client = get_sefaria_client()
        return await client.get_text(ref)
    except Exception as e:
        logger.error(f"[SEARCH] Error fetching '{ref}': {e}")
        return None


async def get_links(ref: str) -> List[Dict]:
    """Get links/citations for a reference."""
    try:
        from tools.sefaria_client import get_sefaria_client
        client = get_sefaria_client()
        return await client.get_related(ref)
    except Exception as e:
        logger.error(f"[SEARCH] Error getting links for '{ref}': {e}")
        return []


def is_base_gemara_ref(ref: str) -> bool:
    """Check if this is a base Gemara ref (not a commentary)."""
    ref_lower = ref.lower()
    # Base gemara refs don't have "on" in them
    if " on " in ref_lower:
        return False
    # Should have daf pattern
    if re.search(r'\d+[ab]', ref):
        return True
    return False


def extract_base_ref(ref: str) -> Optional[str]:
    """
    Extract the base Gemara ref from a commentary ref.
    
    "Rashi on Pesachim 4b:1" → "Pesachim 4b"
    "Ran on Pesachim 4b:2:3" → "Pesachim 4b"
    """
    # Pattern: [Something] on [Masechta] [Daf]
    match = re.search(r'on\s+([A-Za-z\s]+\d+[ab])', ref, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


def construct_commentary_ref(base_ref: str, author: str) -> Optional[str]:
    """
    Construct a commentary reference.
    
    base_ref: "Pesachim 4b"
    author: "Ran"
    returns: "Ran on Pesachim 4b"
    """
    prefix = AUTHOR_TO_SEFARIA_PREFIX.get(author)
    if prefix:
        return f"{prefix} {base_ref}"
    # Try direct construction
    return f"{author} on {base_ref}"


# ==============================================================================
#  PHASE 1: FIND BASE SOURCES (The INYAN)
# ==============================================================================

async def find_base_sources(
    analysis: QueryAnalysis
) -> Tuple[List[Source], List[str]]:
    """
    PHASE 1: Find the base sources where the INYAN is discussed.
    
    Uses search_topics (NOT author names) to find:
    - Psukim
    - Mishnayos  
    - Gemara
    
    Returns: (list of Source objects, list of base refs for commentary fetching)
    """
    sources = []
    base_refs = []  # Gemara refs to fetch commentaries on
    found_refs: Set[str] = set()
    
    # Get the search terms - the INYAN
    search_terms = analysis.search_topics_hebrew or analysis.search_topics
    if not search_terms:
        logger.warning("[FIND] No search topics provided!")
        return [], []
    
    inyan = " ".join(search_terms)
    logger.info(f"[FIND] Phase 1: Finding base sources for INYAN: '{inyan}'")
    
    # === Search Psukim ===
    if analysis.source_categories.psukim:
        logger.info("[FIND] Searching psukim...")
        hits = await search_sefaria_for_inyan(inyan, category_filter=["Tanakh"])
        for hit in hits[:5]:
            if hit.ref not in found_refs:
                found_refs.add(hit.ref)
                text = await get_text(hit.ref)
                if text:
                    sources.append(Source(
                        ref=hit.ref,
                        he_ref=getattr(hit, 'he_ref', hit.ref),
                        level=SourceLevel.PASUK,
                        level_hebrew=LEVEL_HEBREW[SourceLevel.PASUK],
                        hebrew_text=getattr(text, 'hebrew', '') or '',
                        relevance_description=f"פסוק העוסק ב{inyan}"
                    ))
    
    # === Search Mishnayos ===
    if analysis.source_categories.mishnayos:
        logger.info("[FIND] Searching mishnayos...")
        hits = await search_sefaria_for_inyan(inyan, category_filter=["Mishnah"])
        for hit in hits[:5]:
            if hit.ref not in found_refs:
                found_refs.add(hit.ref)
                text = await get_text(hit.ref)
                if text:
                    sources.append(Source(
                        ref=hit.ref,
                        he_ref=getattr(hit, 'he_ref', hit.ref),
                        level=SourceLevel.MISHNA,
                        level_hebrew=LEVEL_HEBREW[SourceLevel.MISHNA],
                        hebrew_text=getattr(text, 'hebrew', '') or '',
                        relevance_description=f"משנה העוסקת ב{inyan}"
                    ))
    
    # === Search Gemara Bavli (PRIMARY) ===
    if analysis.source_categories.gemara_bavli:
        logger.info("[FIND] Searching Gemara Bavli...")
        
        # If we have target masechtos, search within them
        masechtos_to_search = analysis.target_masechtos or [None]
        
        for masechta in masechtos_to_search:
            hits = await search_sefaria_for_inyan(
                inyan, 
                masechta_filter=masechta,
                category_filter=["Bavli"]
            )
            
            for hit in hits[:10]:
                # Only include base gemara refs (not commentaries)
                if is_base_gemara_ref(hit.ref) and hit.ref not in found_refs:
                    found_refs.add(hit.ref)
                    
                    text = await get_text(hit.ref)
                    if text:
                        sources.append(Source(
                            ref=hit.ref,
                            he_ref=getattr(hit, 'he_ref', hit.ref),
                            level=SourceLevel.GEMARA_BAVLI,
                            level_hebrew=LEVEL_HEBREW[SourceLevel.GEMARA_BAVLI],
                            hebrew_text=getattr(text, 'hebrew', '') or '',
                            relevance_description=f"גמרא העוסקת ב{inyan}",
                            is_primary=True
                        ))
                        
                        # Add to base_refs for commentary fetching
                        base_refs.append(hit.ref)
    
    logger.info(f"[FIND] Phase 1 complete: {len(sources)} base sources, {len(base_refs)} gemara refs")
    return sources, base_refs


# ==============================================================================
#  PHASE 2: FETCH COMMENTARIES ON BASE SOURCES
# ==============================================================================

async def fetch_commentaries(
    base_refs: List[str],
    analysis: QueryAnalysis
) -> List[Source]:
    """
    PHASE 2: Fetch commentaries on the base sources found.
    
    Uses target_authors to determine WHICH commentaries to fetch.
    Constructs refs like "Rashi on Pesachim 4b" and fetches them.
    """
    sources = []
    found_refs: Set[str] = set()
    
    if not base_refs:
        logger.warning("[FETCH] No base refs to fetch commentaries on!")
        return []
    
    logger.info(f"[FETCH] Phase 2: Fetching commentaries on {len(base_refs)} base refs")
    logger.info(f"[FETCH] Target authors: {analysis.target_authors}")
    
    # Determine which authors to fetch
    authors_to_fetch = []
    
    # Always fetch Rashi if requested
    if analysis.source_categories.rashi:
        authors_to_fetch.append(("Rashi", SourceLevel.RASHI))
    
    # Always fetch Tosfos if requested
    if analysis.source_categories.tosfos:
        authors_to_fetch.append(("Tosafot", SourceLevel.TOSFOS))
    
    # Add specifically requested authors (from target_authors)
    for author in analysis.target_authors:
        author_normalized = author.strip()
        if author_normalized.lower() not in ["rashi", "tosfos", "tosafot"]:
            authors_to_fetch.append((author_normalized, SourceLevel.RISHONIM))
    
    # Add other rishonim if requested
    if analysis.source_categories.rishonim:
        additional_rishonim = ["Ran", "Rashba", "Ritva", "Ramban"]
        for rishon in additional_rishonim:
            if rishon not in [a[0] for a in authors_to_fetch]:
                authors_to_fetch.append((rishon, SourceLevel.RISHONIM))
    
    logger.info(f"[FETCH] Will fetch: {[a[0] for a in authors_to_fetch]}")
    
    # For each base ref, fetch the commentaries
    for base_ref in base_refs[:5]:  # Limit to avoid too many API calls
        for author, level in authors_to_fetch:
            commentary_ref = construct_commentary_ref(base_ref, author)
            
            if commentary_ref and commentary_ref not in found_refs:
                found_refs.add(commentary_ref)
                
                text = await get_text(commentary_ref)
                if text:
                    hebrew = getattr(text, 'hebrew', '') or ''
                    if hebrew:  # Only add if we got actual text
                        sources.append(Source(
                            ref=commentary_ref,
                            he_ref=getattr(text, 'he_ref', commentary_ref),
                            level=level,
                            level_hebrew=LEVEL_HEBREW.get(level, author),
                            hebrew_text=hebrew,
                            author=author,
                            relevance_description=f"{author} על {base_ref}"
                        ))
                        logger.debug(f"[FETCH] Got: {commentary_ref}")
    
    logger.info(f"[FETCH] Phase 2 complete: {len(sources)} commentaries fetched")
    return sources


# ==============================================================================
#  TRICKLE UP SEARCH
# ==============================================================================

async def trickle_up_search(analysis: QueryAnalysis) -> List[Source]:
    """
    TRICKLE UP: Find base sources, then layer commentaries on top.
    
    Phase 1: Find psukim → mishnayos → gemara on the INYAN
    Phase 2: Fetch Rashi → Tosfos → Rishonim on those sources
    """
    logger.info("[TRICKLE UP] Starting trickle-up search")
    
    # Phase 1: Find base sources
    base_sources, base_refs = await find_base_sources(analysis)
    
    # Phase 2: Fetch commentaries on base sources
    commentary_sources = await fetch_commentaries(base_refs, analysis)
    
    # Combine
    all_sources = base_sources + commentary_sources
    
    logger.info(f"[TRICKLE UP] Complete: {len(all_sources)} total sources")
    return all_sources


# ==============================================================================
#  TRICKLE DOWN SEARCH
# ==============================================================================

async def trickle_down_search(analysis: QueryAnalysis) -> List[Source]:
    """
    TRICKLE DOWN: Start from later sources, trace citations back.
    
    1. Search acharonim/poskim for the inyan
    2. Get what they cite
    3. Fetch those earlier sources
    """
    logger.info("[TRICKLE DOWN] Starting trickle-down search")
    
    sources = []
    found_refs: Set[str] = set()
    cited_refs: Set[str] = set()
    
    search_terms = analysis.search_topics_hebrew or analysis.search_topics
    inyan = " ".join(search_terms) if search_terms else ""
    
    if not inyan:
        logger.warning("[TRICKLE DOWN] No search topics!")
        return []
    
    # Search in halachic literature
    logger.info(f"[TRICKLE DOWN] Searching later sources for: '{inyan}'")
    hits = await search_sefaria_for_inyan(inyan, category_filter=["Halakhah"])
    
    for hit in hits[:15]:
        if hit.ref not in found_refs:
            found_refs.add(hit.ref)
            
            text = await get_text(hit.ref)
            if text:
                # Determine level
                ref_lower = hit.ref.lower()
                if "shulchan" in ref_lower:
                    level = SourceLevel.SHULCHAN_ARUCH
                elif "tur" in ref_lower:
                    level = SourceLevel.TUR
                elif "rambam" in ref_lower or "mishneh torah" in ref_lower:
                    level = SourceLevel.RAMBAM
                else:
                    level = SourceLevel.ACHARONIM
                
                sources.append(Source(
                    ref=hit.ref,
                    he_ref=getattr(hit, 'he_ref', hit.ref),
                    level=level,
                    level_hebrew=LEVEL_HEBREW.get(level, ""),
                    hebrew_text=getattr(text, 'hebrew', '') or '',
                    relevance_description=f"מקור מאוחר על {inyan}"
                ))
                
                # Get what this source cites
                links = await get_links(hit.ref)
                if links and hasattr(links, 'links'):
                    for link in getattr(links, 'links', [])[:5]:
                        if hasattr(link, 'ref'):
                            cited_refs.add(link.ref)
    
    # Fetch cited sources (tracing back)
    logger.info(f"[TRICKLE DOWN] Tracing back {len(cited_refs)} citations...")
    for ref in list(cited_refs)[:20]:
        if ref not in found_refs:
            found_refs.add(ref)
            text = await get_text(ref)
            if text:
                # Determine level from ref
                ref_lower = ref.lower()
                if " on " not in ref_lower and re.search(r'\d+[ab]', ref):
                    level = SourceLevel.GEMARA_BAVLI
                    is_primary = True
                elif "rashi on" in ref_lower:
                    level = SourceLevel.RASHI
                    is_primary = False
                elif "tosafot on" in ref_lower:
                    level = SourceLevel.TOSFOS
                    is_primary = False
                else:
                    level = SourceLevel.RISHONIM
                    is_primary = False
                
                sources.append(Source(
                    ref=ref,
                    he_ref=getattr(text, 'he_ref', ref),
                    level=level,
                    level_hebrew=LEVEL_HEBREW.get(level, ""),
                    hebrew_text=getattr(text, 'hebrew', '') or '',
                    relevance_description=f"מקור המצוטט על {inyan}",
                    is_primary=is_primary
                ))
    
    logger.info(f"[TRICKLE DOWN] Complete: {len(sources)} sources")
    return sources


# ==============================================================================
#  HYBRID SEARCH
# ==============================================================================

async def hybrid_search(analysis: QueryAnalysis) -> List[Source]:
    """Run both methods and combine, marking common sources as primary."""
    logger.info("[HYBRID] Running both search methods...")
    
    up_sources = await trickle_up_search(analysis)
    down_sources = await trickle_down_search(analysis)
    
    # Find common refs
    up_refs = {s.ref for s in up_sources}
    down_refs = {s.ref for s in down_sources}
    common = up_refs & down_refs
    
    # Combine, avoiding duplicates
    all_sources = []
    seen = set()
    
    for source in up_sources + down_sources:
        if source.ref not in seen:
            seen.add(source.ref)
            if source.ref in common:
                source.is_primary = True
                source.relevance_description += " (נמצא בשתי שיטות החיפוש)"
            all_sources.append(source)
    
    logger.info(f"[HYBRID] Complete: {len(all_sources)} sources, {len(common)} common")
    return all_sources


# ==============================================================================
#  ORGANIZE SOURCES
# ==============================================================================

def organize_sources(sources: List[Source]) -> Tuple[List[Source], Dict[str, List[Source]]]:
    """Organize sources in trickle-up order."""
    level_order = {level: i for i, level in enumerate(TRICKLE_UP_ORDER)}
    
    sorted_sources = sorted(
        sources,
        key=lambda s: (level_order.get(s.level, 99), not s.is_primary)
    )
    
    by_level = {}
    for source in sorted_sources:
        level_name = source.level_hebrew or source.level
        if level_name not in by_level:
            by_level[level_name] = []
        by_level[level_name].append(source)
    
    return sorted_sources, by_level


def generate_description(analysis: QueryAnalysis, sources: List[Source], base_refs: List[str]) -> str:
    """Generate search description for the user."""
    parts = []
    
    inyan = " ".join(analysis.search_topics_hebrew or analysis.search_topics or [])
    parts.append(f"חיפוש עבור: {inyan}")
    
    if analysis.target_masechtos:
        parts.append(f"במסכתות: {', '.join(analysis.target_masechtos)}")
    
    if base_refs:
        parts.append(f"נמצאו סוגיות ב: {', '.join(base_refs[:3])}")
    
    if analysis.target_authors:
        parts.append(f"הובאו פירושי: {', '.join(analysis.target_authors)}")
    
    parts.append(f"סה\"כ {len(sources)} מקורות")
    
    return "\n".join(parts)


# ==============================================================================
#  MAIN ENTRY POINT
# ==============================================================================

async def search(
    analysis: QueryAnalysis,
    original_query: str = None,
    hebrew_term: str = None,
) -> SearchResult:
    """
    Step 3: SEARCH - Execute the search plan from Step 2.
    
    Uses:
    - analysis.search_topics_hebrew → WHAT to search (the INYAN)
    - analysis.target_masechtos → WHERE to look
    - analysis.target_authors → WHOSE commentary to fetch
    - analysis.search_method → HOW to search
    """
    logger.info("=" * 70)
    logger.info("[STEP 3: SEARCH] Executing search plan")
    logger.info("=" * 70)
    logger.info(f"  INYAN to search: {analysis.search_topics_hebrew}")
    logger.info(f"  WHERE: {analysis.target_masechtos}")
    logger.info(f"  WHOSE commentary: {analysis.target_authors}")
    logger.info(f"  Method: {analysis.search_method.value}")
    
    # Execute search based on method
    if analysis.search_method == SearchMethod.TRICKLE_UP:
        sources = await trickle_up_search(analysis)
    elif analysis.search_method == SearchMethod.TRICKLE_DOWN:
        sources = await trickle_down_search(analysis)
    elif analysis.search_method == SearchMethod.HYBRID:
        sources = await hybrid_search(analysis)
    else:  # DIRECT
        sources = await trickle_up_search(analysis)
    
    # Organize
    sorted_sources, by_level = organize_sources(sources)
    
    # Get base refs for description
    base_refs = [s.ref for s in sources if s.level == SourceLevel.GEMARA_BAVLI]
    
    # Generate description
    description = generate_description(analysis, sorted_sources, base_refs)
    
    result = SearchResult(
        original_query=analysis.original_query,
        search_topics=analysis.search_topics_hebrew or analysis.search_topics,
        sources=sorted_sources,
        sources_by_level=by_level,
        base_refs_found=base_refs,
        total_sources=len(sorted_sources),
        levels_found=list(by_level.keys()),
        search_description=description,
        confidence=analysis.confidence,
        needs_clarification=analysis.needs_clarification,
        clarification_question=analysis.clarification_question,
    )
    
    logger.info("=" * 70)
    logger.info(f"[STEP 3: SEARCH] Complete")
    logger.info(f"  Base refs found: {base_refs[:3]}")
    logger.info(f"  Total sources: {result.total_sources}")
    logger.info(f"  Levels: {result.levels_found}")
    logger.info("=" * 70)
    
    return result


# Alias
run_step_three = search


# ==============================================================================
#  TESTING
# ==============================================================================

async def test_step_three():
    """Test Step 3."""
    from step_two_understand import (
        QueryAnalysis, SearchMethod, QueryType, Breadth, Realm, SourceCategories
    )
    
    print("=" * 70)
    print("STEP 3 TEST: SEARCH")
    print("=" * 70)
    
    # Simulate what Step 2 would produce
    analysis = QueryAnalysis(
        original_query="what is the rans shittah in bittul chometz",
        hebrew_terms_from_step1=["רן", "שיטה", "ביטול חמץ", "תוספות", "רש\"י"],
        query_type=QueryType.SHITTAH,
        realm=Realm.GEMARA,
        breadth=Breadth.STANDARD,
        search_method=SearchMethod.TRICKLE_UP,
        search_topics=["bittul chometz"],
        search_topics_hebrew=["ביטול חמץ"],  # This is what gets searched!
        target_masechtos=["Pesachim"],
        target_authors=["Ran", "Rashi", "Tosfos"],  # This determines commentaries!
        source_categories=SourceCategories(
            gemara_bavli=True,
            rashi=True,
            tosfos=True,
            rishonim=True,
        ),
        confidence=ConfidenceLevel.HIGH,
    )
    
    print(f"\nSearch plan:")
    print(f"  INYAN: {analysis.search_topics_hebrew}")
    print(f"  WHERE: {analysis.target_masechtos}")
    print(f"  WHOSE: {analysis.target_authors}")
    
    result = await search(analysis)
    
    print(f"\nResults:")
    print(f"  Base refs found: {result.base_refs_found}")
    print(f"  Total sources: {result.total_sources}")
    print(f"  Levels: {result.levels_found}")
    
    print(f"\n{result.search_description}")
    
    if result.sources:
        print(f"\nSources:")
        for source in result.sources[:10]:
            print(f"  • {source.ref} ({source.level_hebrew})")
            print(f"    {source.relevance_description}")


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)-8s | %(message)s')
    asyncio.run(test_step_three())