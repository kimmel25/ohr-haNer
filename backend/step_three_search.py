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

# Import the new commentary fetcher
try:
    from commentary_fetcher import (
        CommentaryFetcherFactory,
        CommentaryDiscoverer,
        AuthorRegistry,
        RefNormalizer,
        FetchedCommentary,
        fetch_commentaries_v2,
        to_source
    )
    COMMENTARY_FETCHER_AVAILABLE = True
except ImportError:
    COMMENTARY_FETCHER_AVAILABLE = False

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
        # Build search query.
        # NOTE: We do NOT prefix the masechta name into the text query, since that
        # can over-constrain (the segment won't contain the book title).
        search_query = inyan

        # Build ES path filters:
        # - category_filter: coarse corpus slice (e.g., ["Bavli"], ["Tanakh"])
        # - masechta_filter: narrow to a specific book by path fragment (e.g., "Pesachim")
        search_filters = []
        if category_filter:
            search_filters.extend(category_filter)
        if masechta_filter:
            search_filters.append(masechta_filter)

        logger.info(f"[SEARCH] Searching Sefaria for INYAN: '{search_query}' filters={search_filters}")
        
        results = await client.search(search_query, size=size, filters=search_filters)
        
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
    """
    sources = []
    base_refs = []
    found_refs: Set[str] = set()
    
    search_terms = analysis.search_topics_hebrew or analysis.search_topics
    if not search_terms:
        logger.warning("[FIND] No search topics provided!")
        return [], []

    terms = [t.strip() for t in search_terms if isinstance(t, str) and t.strip()]
    display_inyan = " / ".join(terms) if terms else " ".join(search_terms)
    
    logger.info(f"[FIND] Phase 1: Finding base sources for INYAN: '{display_inyan}'")
    logger.info(f"[FIND] Target masechtos: {analysis.target_masechtos}")
    logger.info(f"[FIND] Source categories enabled: bavli={analysis.source_categories.gemara_bavli}, mishna={analysis.source_categories.mishnayos}, psukim={analysis.source_categories.psukim}")

    # Search each topic separately; then merge.
    # Joining multiple topics into one ES query over-constrains and often returns 0 hits.
    async def gather_hits(category_filter: List[str], masechta_filter: str = None, per_term_size: int = 30) -> List[Dict]:
        combined = []
        for term in terms or [display_inyan]:
            combined.extend(await search_sefaria_for_inyan(
                term,
                masechta_filter=masechta_filter,
                category_filter=category_filter,
                size=per_term_size
            ))
        # Deduplicate by ref preserving order
        seen = set()
        out = []
        for h in combined:
            ref = getattr(h, "ref", None) or (h.get("ref") if isinstance(h, dict) else None)
            if ref and ref not in seen:
                seen.add(ref)
                out.append(h)
        return out

    inyan = display_inyan
    logger.info(f"[FIND] Phase 1: Finding base sources for INYAN: '{inyan}'")
    
    # === Search Psukim ===
    if analysis.source_categories.psukim:
        logger.info("[FIND] Searching psukim...")
        hits = await gather_hits(["Tanakh"])
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
        hits = await gather_hits(["Mishnah"])
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
        logger.info(f"[FIND] Searching in masechtos: {masechtos_to_search}")
        
        for masechta in masechtos_to_search:
            logger.info(f"[FIND]   Searching masechta: {masechta or 'all'}")
            hits = await gather_hits(["Bavli"], masechta_filter=masechta, per_term_size=30)
            logger.info(f"[FIND]   Got {len(hits)} hits for {masechta or 'all'}")
            
            for idx, hit in enumerate(hits[:10]):
                logger.debug(f"[FIND]     Hit {idx+1}: {hit.ref} (is_base={is_base_gemara_ref(hit.ref)})")
                
                if is_base_gemara_ref(hit.ref) and hit.ref not in found_refs:
                    found_refs.add(hit.ref)
                    
                    text = await get_text(hit.ref)
                    if text:
                        hebrew_preview = (getattr(text, 'hebrew', '') or '')[:100]
                        logger.info(f"[FIND]       ✓ Added base source: {hit.ref}")
                        logger.debug(f"[FIND]         Hebrew preview: {hebrew_preview}...")
                        
                        sources.append(Source(
                            ref=hit.ref,
                            he_ref=getattr(hit, 'he_ref', hit.ref),
                            level=SourceLevel.GEMARA_BAVLI,
                            level_hebrew=LEVEL_HEBREW[SourceLevel.GEMARA_BAVLI],
                            hebrew_text=getattr(text, 'hebrew', '') or '',
                            relevance_description=f"גמרא העוסקת ב{display_inyan}",
                            is_primary=True
                        ))
                        base_refs.append(hit.ref)
                    else:
                        logger.warning(f"[FIND]       ✗ Could not fetch text for: {hit.ref}")
    
    logger.info(f"[FIND] Phase 1 complete: {len(sources)} base sources, {len(base_refs)} gemara refs")
    logger.info(f"[FIND] Base refs: {base_refs}")
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
    
    Uses DISCOVERY-BASED approach:
    1. Ask Sefaria what commentaries exist (via /api/related/)
    2. Filter to target authors
    3. Fetch full text for matching commentaries
    
    This is more reliable than constructing refs blindly because:
    - Commentary numbering doesn't align with Gemara line numbers
    - Not all commentators comment on every passage
    - The related API tells us exactly what exists
    """
    sources = []
    found_refs: Set[str] = set()
    
    if not base_refs:
        logger.warning("[FETCH] No base refs to fetch commentaries on!")
        return []
    
    logger.info(f"[FETCH] Phase 2: Fetching commentaries on {len(base_refs)} base refs")
    logger.info(f"[FETCH] Base refs: {base_refs}")
    logger.info(f"[FETCH] Target authors from analysis: {analysis.target_authors}")
    
    # Build target author set (normalized)
    target_authors_lower = set()
    for author in analysis.target_authors:
        target_authors_lower.add(author.lower().strip())
        # Also add common variations
        if author.lower() == "tosfos":
            target_authors_lower.add("tosafot")
        elif author.lower() == "tosafot":
            target_authors_lower.add("tosfos")
    
    # Add from source_categories if specified
    if analysis.source_categories.rashi:
        target_authors_lower.add("rashi")
    if analysis.source_categories.tosfos:
        target_authors_lower.add("tosafot")
        target_authors_lower.add("tosfos")
    if analysis.source_categories.rishonim:
        target_authors_lower.update(["ran", "rashba", "ritva", "ramban", "rosh", "meiri"])
    
    logger.info(f"[FETCH] Target authors (normalized): {sorted(target_authors_lower)}")
    
    # Get Sefaria client
    try:
        from tools.sefaria_client import get_sefaria_client
        client = get_sefaria_client()
    except Exception as e:
        logger.error(f"[FETCH] Could not get Sefaria client: {e}")
        return []
    
    # Process each base ref - use DISCOVERY approach
    for base_idx, base_ref in enumerate(base_refs[:5], 1):
        logger.info(f"[FETCH] Processing base ref {base_idx}/{min(len(base_refs), 5)}: {base_ref}")
        
        # Get daf-level ref for broader discovery
        daf_ref = _to_daf_level(base_ref)
        logger.info(f"[FETCH]   Discovering commentaries on: {daf_ref}")
        
        try:
            # DISCOVERY: Ask Sefaria what commentaries exist
            related = await client.get_related(daf_ref, with_text=True)
            
            if not related or not related.commentaries:
                logger.warning(f"[FETCH]   No commentaries found for {daf_ref}")
                continue
            
            logger.info(f"[FETCH]   Found {len(related.commentaries)} total commentaries")
            
            # Filter and fetch each matching commentary
            for comm in related.commentaries:
                # Extract author from ref (e.g., "Rashi on Pesachim 4b:1" -> "Rashi")
                author_name = _extract_author_from_ref(comm.ref)
                if not author_name:
                    continue
                
                # Check if this author is in our target list
                author_lower = author_name.lower()
                if target_authors_lower and author_lower not in target_authors_lower:
                    continue
                
                # Skip if already fetched
                if comm.ref in found_refs:
                    continue
                found_refs.add(comm.ref)
                
                # Fetch full text
                logger.debug(f"[FETCH]     Fetching: {comm.ref}")
                text = await get_text(comm.ref)
                
                if text:
                    hebrew = getattr(text, 'hebrew', '') or ''
                    if hebrew:
                        # Determine level
                        level = _get_level_for_author(author_name)
                        
                        logger.info(f"[FETCH]     ✓ Got {author_name}: {comm.ref} ({len(hebrew)} chars)")
                        
                        sources.append(Source(
                            ref=comm.ref,
                            he_ref=getattr(text, 'he_ref', comm.ref),
                            level=level,
                            level_hebrew=LEVEL_HEBREW.get(level, author_name),
                            hebrew_text=hebrew,
                            author=author_name,
                            relevance_description=f"{author_name} על {daf_ref}"
                        ))
                    else:
                        logger.debug(f"[FETCH]     ✗ Empty text: {comm.ref}")
                else:
                    logger.debug(f"[FETCH]     ✗ Could not fetch: {comm.ref}")
                        
        except Exception as e:
            logger.error(f"[FETCH] Error processing {base_ref}: {e}")
            continue
    
    # =========================================================================
    # PHASE 2B: EXPLICIT FETCH FOR MISSING TARGET AUTHORS
    # =========================================================================
    # Check which specifically requested authors weren't found
    found_authors = set(s.author.lower() for s in sources)
    original_target_authors = [a.lower() for a in analysis.target_authors]
    
    missing_authors = []
    for target in original_target_authors:
        # Normalize variations
        target_normalized = target
        if target in ["tosfos", "tosafot"]:
            if "tosfos" not in found_authors and "tosafot" not in found_authors:
                missing_authors.append(target)
        elif target not in found_authors:
            missing_authors.append(target)
    
    if missing_authors:
        logger.warning(f"[FETCH] ⚠️  Missing requested authors: {missing_authors}")
        logger.info(f"[FETCH] Attempting explicit fetch for missing authors...")
        
        # Try explicit fetching for each missing author
        for missing_author in missing_authors:
            for base_ref in base_refs[:5]:  # Limit to first 5 base refs
                # Extract masechta and daf
                masechta, daf = _extract_masechta_and_daf(base_ref)
                if not masechta or not daf:
                    continue
                
                # Get refs to try for this author
                refs_to_try = _get_refs_to_try_for_author(missing_author, masechta, daf)
                
                for ref_to_try in refs_to_try:
                    if ref_to_try in found_refs:
                        continue
                    
                    logger.info(f"[FETCH]   Trying explicit: {ref_to_try}")
                    
                    try:
                        text = await get_text(ref_to_try)
                        if text:
                            hebrew = getattr(text, 'hebrew', '') or ''
                            if hebrew and len(hebrew.strip()) > 10:
                                found_refs.add(ref_to_try)
                                
                                level = _get_level_for_author(missing_author)
                                author_display = missing_author.title()
                                
                                logger.info(f"[FETCH]   ✓ FOUND {author_display}: {ref_to_try} ({len(hebrew)} chars)")
                                
                                sources.append(Source(
                                    ref=ref_to_try,
                                    he_ref=getattr(text, 'he_ref', ref_to_try),
                                    level=level,
                                    level_hebrew=LEVEL_HEBREW.get(level, author_display),
                                    hebrew_text=hebrew,
                                    author=author_display,
                                    relevance_description=f"{author_display} על {masechta} {daf}"
                                ))
                                # Found for this author, move to next author
                                break
                    except Exception as e:
                        logger.debug(f"[FETCH]   Error with {ref_to_try}: {e}")
                
                # If we found something for this author, don't check more base refs
                if any(s.author.lower() == missing_author for s in sources):
                    break
    
    # Sort by level (Rashi first, then Tosfos, etc.)
    level_order = {
        SourceLevel.RASHI: 1,
        SourceLevel.TOSFOS: 2,
        SourceLevel.RISHONIM: 3,
        SourceLevel.ACHARONIM: 4,
    }
    sources.sort(key=lambda s: level_order.get(s.level, 99))
    
    # Log final results
    logger.info(f"[FETCH] Phase 2 complete: {len(sources)} commentaries fetched")
    
    # Log by author for clarity
    by_author = {}
    for source in sources:
        author = source.author
        if author not in by_author:
            by_author[author] = 0
        by_author[author] += 1
    
    logger.info(f"[FETCH] Sources by author:")
    for author, count in sorted(by_author.items()):
        logger.info(f"[FETCH]   • {author}: {count}")
    
    # Check if any target authors are still missing
    final_found_authors = set(s.author.lower() for s in sources)
    still_missing = [a for a in original_target_authors 
                    if a not in final_found_authors 
                    and not (a in ["tosfos", "tosafot"] and ("tosfos" in final_found_authors or "tosafot" in final_found_authors))]
    
    if still_missing:
        logger.warning(f"[FETCH] ⚠️  Could not find: {still_missing}")
        logger.warning(f"[FETCH]    These authors may not have commentary on this sugya in Sefaria")
    
    return sources


def _extract_masechta_and_daf(ref: str) -> tuple:
    """
    Extract masechta and daf from a Gemara reference.
    
    "Pesachim 4b:5" -> ("Pesachim", "4b")
    "Pesachim 4b" -> ("Pesachim", "4b")
    """
    # Pattern: [Masechta] [Daf][a/b][:line]
    match = re.match(r'^([A-Za-z\s]+?)\s*(\d+[ab])(?::\d+)?$', ref.strip())
    if match:
        return match.group(1).strip(), match.group(2)
    return None, None


def _get_refs_to_try_for_author(author_name: str, masechta: str, daf: str) -> List[str]:
    """
    Get list of refs to try for an author on a specific daf.
    
    Handles special cases like the Ran (primary work is on Rif).
    """
    author_lower = author_name.lower()
    refs = []
    
    # Special handling for Ran - try multiple formats
    if author_lower == "ran":
        refs = [
            f"Ran on {masechta} {daf}",           # Primary (on Rif, but indexed by Gemara daf)
            f"Chiddushei HaRan on {masechta} {daf}",  # Novellae
        ]
    
    # Rashba
    elif author_lower == "rashba":
        refs = [
            f"Rashba on {masechta} {daf}",
            f"Chiddushei HaRashba on {masechta} {daf}",
        ]
    
    # Ritva
    elif author_lower == "ritva":
        refs = [
            f"Ritva on {masechta} {daf}",
            f"Chiddushei HaRitva on {masechta} {daf}",
        ]
    
    # Ramban
    elif author_lower == "ramban":
        refs = [
            f"Ramban on {masechta} {daf}",
            f"Chiddushei HaRamban on {masechta} {daf}",
        ]
    
    # Default
    else:
        refs = [f"{author_name.title()} on {masechta} {daf}"]
    
    return refs


def _to_daf_level(ref: str) -> str:
    """
    Convert a line-level ref to daf-level for broader commentary discovery.
    
    "Pesachim 4b:5" -> "Pesachim 4b"
    "Pesachim 4b" -> "Pesachim 4b" (unchanged)
    """
    # Pattern: [Masechta] [Daf][a/b][:Line]
    match = re.match(r'^([A-Za-z\s]+\d+[ab])(?::\d+)?$', ref.strip(), re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return ref


def _extract_author_from_ref(ref: str) -> Optional[str]:
    """
    Extract author name from a commentary reference.
    
    "Rashi on Pesachim 4b:1" -> "Rashi"
    "Tosafot on Ketubot 9a" -> "Tosafot"
    """
    match = re.match(r'^(.+?)\s+on\s+', ref, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


def _get_level_for_author(author_name: str) -> str:
    """Get the SourceLevel for an author name."""
    author_lower = author_name.lower()
    
    if author_lower == "rashi":
        return SourceLevel.RASHI
    elif author_lower in ["tosafot", "tosfos"]:
        return SourceLevel.TOSFOS
    elif author_lower in ["ran", "rashba", "ritva", "ramban", "rosh", "meiri", "nimukei yosef"]:
        return SourceLevel.RISHONIM
    elif author_lower in ["maharsha", "pnei yehoshua", "maharam"]:
        return SourceLevel.ACHARONIM
    else:
        return SourceLevel.RISHONIM  # Default


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
    
    # Search each topic separately, then merge
    hits = []
    terms = analysis.search_topics_hebrew or analysis.search_topics or [inyan]
    for term in terms:
        hits.extend(await search_sefaria_for_inyan(term, category_filter=["Halakhah"]))
    # Deduplicate by ref
    seen = set()
    deduped = []
    for h in hits:
        ref = getattr(h, "ref", None) or (h.get("ref") if isinstance(h, dict) else None)
        if ref and ref not in seen:
            seen.add(ref)
            deduped.append(h)
    hits = deduped
    
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
    """
    logger.info("=" * 70)
    logger.info("[STEP 3: SEARCH] Executing search plan")
    logger.info("=" * 70)
    logger.info(f"  Original query: {analysis.original_query}")
    logger.info(f"  INYAN to search: {analysis.search_topics_hebrew}")
    logger.info(f"  English topics: {analysis.search_topics}")
    logger.info(f"  WHERE (masechtos): {analysis.target_masechtos}")
    logger.info(f"  WHOSE commentary (authors): {analysis.target_authors}")
    logger.info(f"  Method: {analysis.search_method.value}")
    logger.info(f"  Source categories:")
    logger.info(f"    - Gemara Bavli: {analysis.source_categories.gemara_bavli}")
    logger.info(f"    - Rashi: {analysis.source_categories.rashi}")
    logger.info(f"    - Tosfos: {analysis.source_categories.tosfos}")
    logger.info(f"    - Rishonim: {analysis.source_categories.rishonim}")
    
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
    
    logger.info("=" * 70)
    logger.info(f"[STEP 3: SEARCH] Sources organized by level:")
    for level_name, level_sources in by_level.items():
        logger.info(f"  {level_name}: {len(level_sources)} sources")
        for idx, source in enumerate(level_sources[:3], 1):
            logger.info(f"    {idx}. {source.ref}")
            if idx == 3 and len(level_sources) > 3:
                logger.info(f"    ... and {len(level_sources) - 3} more")
    
    # Get base refs for description
    base_refs = [s.ref for s in sources if s.level == SourceLevel.GEMARA_BAVLI]
    
    logger.info(f"[STEP 3: SEARCH] Base Gemara refs found: {base_refs}")
    
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
    
    # =========================================================================
    # GENERATE SOURCE OUTPUT FILE
    # =========================================================================
    try:
        from source_output import write_source_output
        from datetime import datetime
        
        output_files = write_source_output(
            result,
            query=analysis.original_query,
            output_dir="output",
            formats=["txt", "html"]  # txt for quick review, html for nice reading
        )
        
        if output_files:
            logger.info(f"[OUTPUT] Source files generated:")
            for fmt, path in output_files.items():
                logger.info(f"[OUTPUT]   {fmt}: {path}")
    except ImportError:
        logger.debug("[OUTPUT] source_output module not available, skipping output generation")
    except Exception as e:
        logger.warning(f"[OUTPUT] Could not generate source output: {e}")
    
    logger.info("=" * 70)
    logger.info(f"[STEP 3: SEARCH] Complete")
    logger.info(f"  Base refs found: {base_refs}")
    logger.info(f"  Total sources: {result.total_sources}")
    logger.info(f"  Levels with sources: {result.levels_found}")
    logger.info(f"  Search description: {description}")
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