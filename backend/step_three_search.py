"""
Step 3: SEARCH - V7 Architecture (Local Corpus + Trickle Down)
==============================================================

This version uses the LOCAL Sefaria JSON export for:
- Phase A: LOCATE (find topic in SA/Tur/Rambam)
- Phase B: TRICKLE DOWN (extract citations from nosei keilim)
- Phase C: CROSS-REFERENCE (find main sugyos)
- Phase D: FETCH TARGET AUTHORS (use Sefaria API only here)

Key improvements:
- Minimal API calls (only for fetching actual source text)
- Uses local JSON for search and citation extraction
- Much faster and more reliable
"""

import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple

from config import get_settings
from models import ConfidenceLevel

# Import local corpus handler
try:
    from local_corpus import (
        get_local_corpus,
        discover_main_sugyos,
        LocalCorpus,
        GemaraCitation,
        LocalSearchHit,
        MASECHTA_MAP,
    )
    LOCAL_CORPUS_AVAILABLE = True
except ImportError:
    LOCAL_CORPUS_AVAILABLE = False
    logging.warning("local_corpus module not available - falling back to API-only mode")

if TYPE_CHECKING:
    from step_two_understand import QueryAnalysis, SearchMethod, Realm, QueryType

try:
    from step_two_understand import QueryAnalysis, SearchMethod, Realm, QueryType
except ImportError as e:
    logging.warning(f"Could not import from step_two_understand: {e}")

logger = logging.getLogger(__name__)
settings = get_settings()


# ==============================================================================
#  SOURCE LEVELS
# ==============================================================================

class SourceLevel(Enum):
    """Source levels - order represents typical trickle-up flow."""
    PASUK = "pasuk"
    TARGUM = "targum"
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

    @property
    def hebrew(self) -> str:
        return _LEVEL_HEBREW.get(self, self.value)


_LEVEL_HEBREW: Dict[SourceLevel, str] = {
    SourceLevel.PASUK: "פסוק",
    SourceLevel.TARGUM: "תרגום",
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


# ==============================================================================
#  SOURCE DATA STRUCTURES  
# ==============================================================================

@dataclass
class Source:
    """A single source with its text and metadata."""
    ref: str
    he_ref: str
    level: SourceLevel
    hebrew_text: str
    english_text: str = ""
    author: str = ""
    categories: List[str] = field(default_factory=list)
    relevance_description: str = ""
    is_primary: bool = False
    citation_count: int = 0  # How many times this was cited by nosei keilim

    @property
    def level_hebrew(self) -> str:
        return self.level.hebrew


@dataclass
class DiscoveryResult:
    """Result of the trickle-down discovery process."""
    topic: str
    topic_hebrew: str
    
    # Phase A results
    sa_simanim: Dict[str, List[int]] = field(default_factory=dict)  # {chelek: [simanim]}
    tur_simanim: Dict[str, List[int]] = field(default_factory=dict)
    rambam_halachos: List[str] = field(default_factory=list)
    
    # Phase B results
    all_citations: List[GemaraCitation] = field(default_factory=list)
    daf_counts: Dict[str, int] = field(default_factory=dict)  # {ref: count}
    
    # Phase C results
    main_sugyos: List[str] = field(default_factory=list)  # Top dapim by citation count


@dataclass
class SearchResult:
    """Complete search result."""
    original_query: str
    search_topics: List[str]
    
    sources: List[Source] = field(default_factory=list)
    sources_by_level: Dict[str, List[Source]] = field(default_factory=dict)
    
    # Discovery info
    discovery: Optional[DiscoveryResult] = None
    discovered_dapim: List[str] = field(default_factory=list)
    
    total_sources: int = 0
    levels_found: List[str] = field(default_factory=list)
    search_description: str = ""
    
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    needs_clarification: bool = False
    clarification_question: Optional[str] = None


# ==============================================================================
#  SEFARIA API HELPERS (for Phase D only)
# ==============================================================================

def _get_sefaria_client():
    """Get Sefaria client instance."""
    try:
        from tools.sefaria_client import get_sefaria_client
        return get_sefaria_client()
    except ImportError:
        from sefaria_client import get_sefaria_client
        return get_sefaria_client()


async def fetch_source_text(ref: str) -> Optional[Source]:
    """Fetch a single source from Sefaria API."""
    try:
        client = _get_sefaria_client()
        text_result = await client.get_text(ref)
        
        if not text_result:
            return None
        
        hebrew = getattr(text_result, 'hebrew', '') or ''
        if isinstance(hebrew, list):
            hebrew = ' '.join(str(h) for h in hebrew if h)
        
        english = getattr(text_result, 'english', '') or ''
        if isinstance(english, list):
            english = ' '.join(str(e) for e in english if e)
        
        he_ref = getattr(text_result, 'he_ref', ref) or ref
        categories = getattr(text_result, 'categories', []) or []
        
        # Determine level from ref/categories
        level = _determine_level_from_ref(ref, categories)
        
        return Source(
            ref=ref,
            he_ref=he_ref,
            level=level,
            hebrew_text=hebrew,
            english_text=english,
            categories=categories,
            is_primary=True
        )
    
    except Exception as e:
        logger.warning(f"Failed to fetch {ref}: {e}")
        return None


async def fetch_commentaries_on_daf(
    daf_ref: str, 
    target_authors: Set[str]
) -> List[Source]:
    """Fetch specific commentaries on a gemara daf."""
    sources = []
    
    try:
        client = _get_sefaria_client()
        related = await client.get_related(daf_ref)
        
        if not related or not related.commentaries:
            return sources
        
        for comm in related.commentaries:
            # Extract author from ref
            author = _extract_author_from_ref(comm.ref)
            
            # Check if this author is in our target list
            if not _author_matches(author, target_authors):
                continue
            
            # Fetch the text
            source = await fetch_source_text(comm.ref)
            if source:
                source.author = author
                source.relevance_description = f"{author} על {daf_ref}"
                sources.append(source)
    
    except Exception as e:
        logger.warning(f"Failed to fetch commentaries on {daf_ref}: {e}")
    
    return sources


def _determine_level_from_ref(ref: str, categories: List[str]) -> SourceLevel:
    """Determine source level from reference string and categories."""
    ref_lower = ref.lower()
    
    if "rashi" in ref_lower:
        return SourceLevel.RASHI
    elif "tosafot" in ref_lower or "tosfos" in ref_lower:
        return SourceLevel.TOSFOS
    elif any(c in categories for c in ["Talmud", "Bavli"]):
        return SourceLevel.GEMARA_BAVLI
    elif "yerushalmi" in ref_lower:
        return SourceLevel.GEMARA_YERUSHALMI
    elif "mishnah" in ref_lower or "mishna" in ref_lower:
        return SourceLevel.MISHNA
    elif "rambam" in ref_lower or "mishneh torah" in ref_lower:
        return SourceLevel.RAMBAM
    elif "shulchan" in ref_lower:
        return SourceLevel.SHULCHAN_ARUCH
    elif "tur" in ref_lower:
        return SourceLevel.TUR
    elif any(n in ref_lower for n in ["ran", "rashba", "ritva", "ramban", "meiri"]):
        return SourceLevel.RISHONIM
    elif any(n in ref_lower for n in ["magen avraham", "taz", "shach", "mishna berura"]):
        return SourceLevel.NOSEI_KEILIM
    
    return SourceLevel.RISHONIM


def _extract_author_from_ref(ref: str) -> str:
    """Extract author name from a reference string."""
    # "Rashi on Pesachim 4b:2" -> "Rashi"
    match = re.match(r'^(.+?)\s+on\s+', ref, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return ref.split()[0] if ref else ""


def _author_matches(author: str, target_authors: Set[str]) -> bool:
    """Check if an author matches any in the target set."""
    author_lower = author.lower()
    
    for target in target_authors:
        target_lower = target.lower()
        if target_lower in author_lower or author_lower in target_lower:
            return True
        
        # Handle variations
        if target_lower == "tosafos" and "tosafot" in author_lower:
            return True
        if target_lower == "tosafot" and "tosfos" in author_lower:
            return True
    
    return False


# ==============================================================================
#  TRICKLE DOWN SEARCH (V7)
# ==============================================================================

async def trickle_down_search_v7(
    analysis: "QueryAnalysis",
    corpus_root: Path = None
) -> SearchResult:
    """
    V7 Trickle-Down Search using local corpus.
    
    PHASE A: LOCATE - Find topic in SA/Tur/Rambam
    PHASE B: TRICKLE DOWN - Extract citations from nosei keilim  
    PHASE C: CROSS-REFERENCE - Identify main sugyos
    PHASE D: FETCH TARGET AUTHORS - Get requested sources from Sefaria
    """
    logger.info("=" * 60)
    logger.info("STEP 3: SEARCH - V7 Trickle-Down (Local Corpus)")
    logger.info("=" * 60)
    
    # Get topic from analysis
    topic = analysis.search_topics[0] if analysis.search_topics else ""
    topic_hebrew = analysis.search_topics_hebrew[0] if analysis.search_topics_hebrew else topic
    
    logger.info(f"Topic: {topic_hebrew} ({topic})")
    logger.info(f"Target authors: {analysis.target_authors}")
    
    # Initialize result
    result = SearchResult(
        original_query=analysis.original_query,
        search_topics=analysis.search_topics_hebrew,
    )
    
    # Check if local corpus is available
    if not LOCAL_CORPUS_AVAILABLE:
        logger.warning("Local corpus not available - falling back to API search")
        return await _fallback_api_search(analysis)
    
    # Get local corpus instance
    corpus = get_local_corpus(corpus_root)
    
    # =========================================================================
    # PHASE A + B + C: Discover main sugyos via local corpus
    # =========================================================================
    logger.info("")
    logger.info("PHASE A/B/C: Discovering main sugyos via local corpus")
    logger.info("-" * 50)
    
    # Determine default masechta if user mentioned one
    default_masechta = None
    if analysis.target_masechtos:
        # Convert English masechta to Hebrew
        masechta_en = analysis.target_masechtos[0]
        for he, en in MASECHTA_MAP.items():
            if en.lower() == masechta_en.lower():
                default_masechta = he
                break
    
    # Run discovery
    daf_counts, all_citations = discover_main_sugyos(
        corpus, 
        topic_hebrew,
        default_masechta=default_masechta
    )
    
    if not daf_counts:
        logger.warning("No citations found in local corpus")
        # Could fall back to API search here
        return await _fallback_api_search(analysis)
    
    # Get main sugyos (top dapim by citation count)
    main_sugyos = list(daf_counts.keys())[:10]  # Top 10
    
    logger.info(f"Discovered {len(main_sugyos)} main sugyos:")
    for i, sugya in enumerate(main_sugyos[:5], 1):
        logger.info(f"  {i}. {sugya} ({daf_counts[sugya]} citations)")
    
    result.discovered_dapim = main_sugyos
    
    # Create discovery result
    discovery = DiscoveryResult(
        topic=topic,
        topic_hebrew=topic_hebrew,
        all_citations=all_citations,
        daf_counts=daf_counts,
        main_sugyos=main_sugyos,
    )
    result.discovery = discovery
    
    # =========================================================================
    # PHASE D: Fetch target authors on discovered sugyos
    # =========================================================================
    logger.info("")
    logger.info("PHASE D: Fetching target authors on main sugyos")
    logger.info("-" * 50)
    
    sources: List[Source] = []
    
    # Build target authors set
    target_authors = set(analysis.target_authors) if analysis.target_authors else set()
    
    # Add defaults based on query type
    if analysis.source_categories.rashi:
        target_authors.add("rashi")
    if analysis.source_categories.tosfos:
        target_authors.update(["tosafot", "tosfos"])
    if analysis.source_categories.rishonim:
        target_authors.update(["ran", "rashba", "ritva", "ramban", "meiri", "rosh"])
    
    # If no specific authors requested, use defaults
    if not target_authors:
        target_authors = {"rashi", "tosafot", "ran", "rashba", "ritva"}
    
    logger.info(f"Target authors: {target_authors}")
    
    # Fetch sources for top sugyos
    for daf_ref in main_sugyos[:5]:  # Limit to top 5 sugyos
        logger.info(f"  Fetching sources for: {daf_ref}")
        
        # Fetch the gemara text itself
        gemara_source = await fetch_source_text(daf_ref)
        if gemara_source:
            gemara_source.citation_count = daf_counts.get(daf_ref, 0)
            gemara_source.relevance_description = f"Main sugya ({daf_counts.get(daf_ref, 0)} citations)"
            sources.append(gemara_source)
        
        # Fetch commentaries
        commentaries = await fetch_commentaries_on_daf(daf_ref, target_authors)
        for comm in commentaries:
            comm.citation_count = daf_counts.get(daf_ref, 0)
            sources.append(comm)
        
        logger.info(f"    Found {len(commentaries)} commentaries")
    
    # =========================================================================
    # Organize results
    # =========================================================================
    
    # Sort by citation count (primary sugyos first)
    sources.sort(key=lambda s: (-s.citation_count, s.level.value))
    
    # Group by level
    sources_by_level: Dict[str, List[Source]] = {}
    for source in sources:
        level_key = source.level_hebrew
        if level_key not in sources_by_level:
            sources_by_level[level_key] = []
        sources_by_level[level_key].append(source)
    
    result.sources = sources
    result.sources_by_level = sources_by_level
    result.total_sources = len(sources)
    result.levels_found = list(sources_by_level.keys())
    result.confidence = ConfidenceLevel.HIGH if len(sources) > 5 else ConfidenceLevel.MEDIUM
    
    result.search_description = (
        f"Found {len(sources)} sources across {len(main_sugyos)} main sugyos. "
        f"Top sugya: {main_sugyos[0] if main_sugyos else 'N/A'} "
        f"({daf_counts.get(main_sugyos[0], 0) if main_sugyos else 0} citations from nosei keilim)"
    )
    
    # Write output files
    try:
        from source_output import SourceOutputWriter
        writer = SourceOutputWriter()
        output_files = writer.write_results(result, analysis.original_query, formats=["txt", "html"])
        logger.debug(f"Generated output files: {list(output_files.keys())}")
    except Exception as e:
        logger.warning(f"Could not write output files: {e}")
    
    logger.info("")
    logger.info("=" * 60)
    logger.info(f"STEP 3 COMPLETE: {len(sources)} sources found")
    logger.info("=" * 60)
    
    return result


async def _fallback_api_search(analysis: "QueryAnalysis") -> SearchResult:
    """Fallback to API-only search when local corpus unavailable."""
    logger.info("Using fallback API search")
    
    # Simple search implementation
    sources = []
    
    topic_hebrew = analysis.search_topics_hebrew[0] if analysis.search_topics_hebrew else ""
    
    try:
        client = _get_sefaria_client()
        results = await client.search(topic_hebrew, size=30)
        
        if results and results.hits:
            for hit in results.hits[:10]:
                ref = getattr(hit, 'ref', None)
                if ref:
                    source = await fetch_source_text(ref)
                    if source:
                        sources.append(source)
    except Exception as e:
        logger.error(f"Fallback search failed: {e}")
    
    return SearchResult(
        original_query=analysis.original_query,
        search_topics=analysis.search_topics_hebrew,
        sources=sources,
        total_sources=len(sources),
        confidence=ConfidenceLevel.LOW,
        search_description="Fallback API search (local corpus unavailable)"
    )


# ==============================================================================
#  MAIN SEARCH FUNCTION
# ==============================================================================

async def search(analysis: "QueryAnalysis") -> SearchResult:
    """
    Main entry point for Step 3: SEARCH.
    
    Routes to appropriate search strategy based on analysis.
    """
    logger.info("=" * 60)
    logger.info("STEP 3: SEARCH")
    logger.info(f"  Query: {analysis.original_query}")
    logger.info(f"  Realm: {analysis.realm}")
    logger.info(f"  Topics: {analysis.search_topics_hebrew}")
    logger.info(f"  Method: {analysis.search_method}")
    if analysis.target_masechtos:
        logger.info(f"  Masechtos: {analysis.target_masechtos}")
    if analysis.target_authors:
        logger.info(f"  Authors: {analysis.target_authors}")
    logger.info("=" * 60)
    
    # Determine query type
    query_type = getattr(analysis.query_type, 'value', str(analysis.query_type))
    search_method = getattr(analysis.search_method, 'value', str(analysis.search_method))
    
    # For comparison/shittah/machlokes queries, use trickle-down
    if query_type in ('comparison', 'machlokes', 'shittah', 'sugya'):
        logger.info(f"Query type '{query_type}' -> using V7 Trickle-Down")
        return await trickle_down_search_v7(analysis)
    
    # For other queries, check search method
    if search_method == "trickle_down":
        return await trickle_down_search_v7(analysis)
    
    # Default to trickle-down for now
    return await trickle_down_search_v7(analysis)


# ==============================================================================
#  EXPORTS
# ==============================================================================

__all__ = [
    'search',
    'trickle_down_search_v7',
    'Source',
    'SourceLevel',
    'SearchResult',
    'DiscoveryResult',
]