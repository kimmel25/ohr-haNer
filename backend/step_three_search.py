"""
Step 3: SEARCH - V9 Architecture (Claude-Validated Discovery)
=============================================================

V9 KEY CHANGE:
- After keyword search finds simanim/dapim, ASK CLAUDE if they're correct
- Claude validates: "For comparing chezkas mammon vs chezkas haguf, 
  is Bava Batra 40a the right sugya? Or should it be Kesubos 12b?"
- If Claude says wrong, use Claude's suggested sugyos instead

WHY THIS WORKS:
- Keyword search finds simanim with literal words but wrong CONCEPTS
- YD 190 contains "חזקת הגוף" but it's about Niddah, not kesubos disputes
- Claude knows the Torah and can redirect to actual relevant sugyos

PHASES:
A: LOCATE - Keyword search SA/Tur for topic
B: VALIDATE - Ask Claude if discovered locations are correct
C: TRICKLE DOWN - Extract citations OR use Claude's direct suggestions
D: FETCH - Get sources from Sefaria API
"""

import logging
import re
import json
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple

from anthropic import Anthropic

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
    logging.warning("local_corpus module not available")

if TYPE_CHECKING:
    from step_two_understand import QueryAnalysis

try:
    from step_two_understand import QueryAnalysis
except ImportError as e:
    logging.warning(f"Could not import from step_two_understand: {e}")

logger = logging.getLogger(__name__)
settings = get_settings()


# ==============================================================================
#  SOURCE LEVELS & DATA STRUCTURES (unchanged from V8)
# ==============================================================================

class SourceLevel(Enum):
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


_LEVEL_HEBREW = {
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


@dataclass
class Source:
    ref: str
    he_ref: str
    level: SourceLevel
    hebrew_text: str
    english_text: str = ""
    author: str = ""
    categories: List[str] = field(default_factory=list)
    relevance_description: str = ""
    is_primary: bool = False
    citation_count: int = 0

    @property
    def level_hebrew(self) -> str:
        return self.level.hebrew


@dataclass
class DiscoveryResult:
    topic: str
    topic_hebrew: str
    sa_simanim: Dict[str, List[int]] = field(default_factory=dict)
    tur_simanim: Dict[str, List[int]] = field(default_factory=dict)
    rambam_halachos: List[str] = field(default_factory=list)
    all_citations: List[Any] = field(default_factory=list)
    daf_counts: Dict[str, int] = field(default_factory=dict)
    main_sugyos: List[str] = field(default_factory=list)
    claude_validated: bool = False
    claude_suggested: bool = False


@dataclass
class SearchResult:
    original_query: str
    search_topics: List[str]
    sources: List[Source] = field(default_factory=list)
    sources_by_level: Dict[str, List[Source]] = field(default_factory=dict)
    discovery: Optional[DiscoveryResult] = None
    discovered_dapim: List[str] = field(default_factory=list)
    total_sources: int = 0
    levels_found: List[str] = field(default_factory=list)
    search_description: str = ""
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    needs_clarification: bool = False
    clarification_question: Optional[str] = None


# ==============================================================================
#  CLAUDE VALIDATION - THE V9 KEY FEATURE
# ==============================================================================

def _get_anthropic_client() -> Anthropic:
    """Get Anthropic client."""
    return Anthropic(api_key=settings.anthropic_api_key)


async def validate_and_suggest_sugyos(
    original_query: str,
    topics_hebrew: List[str],
    discovered_dapim: List[str],
    query_type: str,
    target_masechtos: List[str] = None
) -> Dict[str, Any]:
    """
    V9 CORE: Ask Claude to validate discovered sugyos OR suggest correct ones.
    
    Returns:
        {
            "valid": bool,  # Are discovered_dapim correct?
            "suggested_dapim": [...],  # If not valid, Claude's suggestions
            "reasoning": str,
            "confidence": str  # high/medium/low
        }
    """
    logger.info("")
    logger.info("=" * 50)
    logger.info("V9: CLAUDE VALIDATION OF DISCOVERED SUGYOS")
    logger.info("=" * 50)
    
    client = _get_anthropic_client()
    
    # Format discovered dapim for Claude
    dapim_list = ", ".join(discovered_dapim[:10]) if discovered_dapim else "None found"
    masechtos_hint = f"User mentioned: {', '.join(target_masechtos)}" if target_masechtos else ""
    
    prompt = f"""You are a Torah scholar validating search results.

ORIGINAL QUERY: "{original_query}"
HEBREW TOPICS: {topics_hebrew}
QUERY TYPE: {query_type}
{masechtos_hint}

Our keyword search found these as the main sugyos:
{dapim_list}

TASK: Are these the CORRECT main sugyos for this query?

Think carefully:
1. What is the user ACTUALLY asking about?
2. Do the discovered dapim discuss THAT topic, or something else with similar words?
3. What are the REAL main sugyos in Shas for this topic?

EXAMPLES OF WRONG RESULTS:
- Query "chezkas haguf vs chezkas mammon" → Found "Niddah 10a" (wrong! that's about a woman's status, not the conceptual comparison)
- The REAL sugyos for comparing these chazakos are in Kesubos (12b, 75b) and Kiddushin (66b)

Return ONLY valid JSON:
{{
    "valid": true/false,
    "reasoning": "brief explanation",
    "suggested_dapim": ["Masechta Daf", ...],  // If valid=false, provide correct sugyos
    "confidence": "high/medium/low"
}}

If the discovered dapim are correct, set valid=true and suggested_dapim=[].
If wrong, set valid=false and provide the ACTUAL main sugyos."""

    try:
        logger.info(f"Asking Claude to validate: {dapim_list}")
        
        response = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=1000,
            temperature=0,
            messages=[{"role": "user", "content": prompt}]
        )
        
        raw_text = response.content[0].text.strip()
        logger.info(f"Claude validation response: {raw_text[:500]}")
        
        # Parse JSON
        json_match = re.search(r'\{[\s\S]*\}', raw_text)
        if json_match:
            result = json.loads(json_match.group())
            
            logger.info(f"  Valid: {result.get('valid')}")
            logger.info(f"  Confidence: {result.get('confidence')}")
            logger.info(f"  Reasoning: {result.get('reasoning', '')[:100]}")
            
            if not result.get('valid') and result.get('suggested_dapim'):
                logger.info(f"  Claude suggests: {result.get('suggested_dapim')}")
            
            return result
        else:
            logger.warning("Could not parse Claude's response as JSON")
            return {"valid": True, "suggested_dapim": [], "confidence": "low"}
            
    except Exception as e:
        logger.error(f"Claude validation failed: {e}")
        return {"valid": True, "suggested_dapim": [], "confidence": "low"}


# ==============================================================================
#  SEFARIA API HELPERS
# ==============================================================================

def _get_sefaria_client():
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
        level = _determine_level_from_ref(ref, categories)
        
        return Source(
            ref=ref, he_ref=he_ref, level=level,
            hebrew_text=hebrew, english_text=english,
            categories=categories, is_primary=True
        )
    except Exception as e:
        logger.warning(f"Failed to fetch {ref}: {e}")
        return None


async def fetch_commentaries_on_daf(daf_ref: str, target_authors: Set[str]) -> List[Source]:
    """Fetch specific commentaries on a gemara daf."""
    sources = []
    try:
        client = _get_sefaria_client()
        related = await client.get_related(daf_ref)
        
        if not related or not related.commentaries:
            return sources
        
        for comm in related.commentaries:
            author = _extract_author_from_ref(comm.ref)
            if not _author_matches(author, target_authors):
                continue
            source = await fetch_source_text(comm.ref)
            if source:
                source.author = author
                sources.append(source)
    except Exception as e:
        logger.warning(f"Failed to fetch commentaries for {daf_ref}: {e}")
    
    return sources


def _determine_level_from_ref(ref: str, categories: List[str]) -> SourceLevel:
    if "Rashi" in ref:
        return SourceLevel.RASHI
    if "Tosafot" in ref or "Tosfos" in ref:
        return SourceLevel.TOSFOS
    if categories:
        cat_str = " ".join(categories).lower()
        if "talmud" in cat_str and "bavli" in cat_str:
            return SourceLevel.GEMARA_BAVLI
        if "mishnah" in cat_str:
            return SourceLevel.MISHNA
    return SourceLevel.RISHONIM


def _extract_author_from_ref(ref: str) -> str:
    match = re.match(r'^(.+?)\s+on\s+', ref, re.IGNORECASE)
    return match.group(1).strip() if match else ref.split()[0] if ref else ""


def _author_matches(author: str, target_authors: Set[str]) -> bool:
    author_lower = author.lower()
    for target in target_authors:
        target_lower = target.lower()
        if target_lower in author_lower or author_lower in target_lower:
            return True
        if target_lower == "tosafos" and "tosafot" in author_lower:
            return True
    return False


# ==============================================================================
#  MAIN SEARCH FUNCTION - V9
# ==============================================================================

async def trickle_down_search_v9(
    analysis: "QueryAnalysis",
    corpus_root: Path = None
) -> SearchResult:
    """
    V9 Trickle-Down Search with Claude Validation.
    
    FLOW:
    1. Keyword search local corpus → discovered dapim
    2. ASK CLAUDE: "Are these correct for this query?"
    3. If Claude says NO → use Claude's suggested dapim instead
    4. Fetch sources from Sefaria
    """
    logger.info("=" * 60)
    logger.info("STEP 3: SEARCH - V9 (Claude-Validated Discovery)")
    logger.info("=" * 60)
    
    # Extract topics
    topics_hebrew = analysis.search_topics_hebrew if analysis.search_topics_hebrew else []
    topics_english = analysis.search_topics if analysis.search_topics else []
    topic = topics_english[0] if topics_english else ""
    topic_hebrew = topics_hebrew[0] if topics_hebrew else topic
    
    # Filter verbose topics (same as V8.1)
    core_topics = [t for t in topics_hebrew if len(t.split()) <= 3]
    if not core_topics:
        core_topics = topics_hebrew[:2] if len(topics_hebrew) >= 2 else topics_hebrew
    
    logger.info(f"Topics: {core_topics}")
    logger.info(f"Query type: {analysis.query_type}")
    logger.info(f"Target authors: {analysis.target_authors}")
    
    # Initialize result
    result = SearchResult(
        original_query=analysis.original_query,
        search_topics=core_topics,
    )
    
    # =========================================================================
    # PHASE A: Keyword search local corpus
    # =========================================================================
    discovered_dapim = []
    daf_counts = {}
    all_citations = []
    
    if LOCAL_CORPUS_AVAILABLE:
        corpus = get_local_corpus(corpus_root)
        
        logger.info("")
        logger.info("PHASE A: Keyword search in local corpus")
        logger.info("-" * 50)
        
        # Combined search
        if len(core_topics) >= 2:
            combined_query = " ".join(core_topics[:2])
        else:
            combined_query = core_topics[0] if core_topics else topic_hebrew
        
        logger.info(f"Searching: '{combined_query}'")
        daf_counts, all_citations = discover_main_sugyos(corpus, combined_query)
        
        # If combined fails, try intersection (same as V8.1)
        if not daf_counts and len(core_topics) >= 2:
            logger.info("Combined search failed, trying intersection...")
            
            topic_results = {}
            for single_topic in core_topics[:2]:
                single_counts, _ = discover_main_sugyos(corpus, single_topic)
                if single_counts:
                    topic_results[single_topic] = single_counts
            
            if len(topic_results) >= 2:
                topics_list = list(topic_results.keys())
                dapim_1 = set(topic_results[topics_list[0]].keys())
                dapim_2 = set(topic_results[topics_list[1]].keys())
                intersection = dapim_1 & dapim_2
                
                logger.info(f"Intersection: {len(intersection)} dapim")
                
                if intersection:
                    merged = {}
                    for daf in intersection:
                        merged[daf] = sum(topic_results[t].get(daf, 0) for t in topic_results)
                    daf_counts = dict(sorted(merged.items(), key=lambda x: -x[1]))
        
        discovered_dapim = list(daf_counts.keys())[:10] if daf_counts else []
        logger.info(f"Keyword search found: {discovered_dapim[:5]}")
    
    # =========================================================================
    # PHASE B: CLAUDE VALIDATION (V9 KEY FEATURE)
    # =========================================================================
    query_type_str = getattr(analysis.query_type, 'value', str(analysis.query_type))
    
    # Always validate for comparison/conceptual queries, or if results seem off
    should_validate = (
        query_type_str in ('comparison', 'conceptual', 'machlokes', 'shittah') or
        len(core_topics) >= 2  # Multi-topic query
    )
    
    main_sugyos = discovered_dapim
    claude_validated = False
    claude_suggested = False
    
    if should_validate and discovered_dapim:
        validation = await validate_and_suggest_sugyos(
            original_query=analysis.original_query,
            topics_hebrew=core_topics,
            discovered_dapim=discovered_dapim,
            query_type=query_type_str,
            target_masechtos=analysis.target_masechtos
        )
        
        claude_validated = True
        
        if not validation.get('valid', True) and validation.get('suggested_dapim'):
            # Claude says our results are wrong - use Claude's suggestions
            logger.info("")
            logger.info("=" * 50)
            logger.info("V9: Using Claude's suggested sugyos instead!")
            logger.info("=" * 50)
            
            main_sugyos = validation['suggested_dapim']
            claude_suggested = True
            
            # Build new daf_counts from Claude's suggestions
            daf_counts = {daf: 10 for daf in main_sugyos}  # Equal weight
            
            logger.info(f"New main sugyos: {main_sugyos}")
        else:
            logger.info("Claude validated: discovered sugyos are correct")
    
    elif not discovered_dapim:
        # No keyword results - ask Claude directly
        logger.info("")
        logger.info("No keyword results - asking Claude for sugyos directly")
        
        validation = await validate_and_suggest_sugyos(
            original_query=analysis.original_query,
            topics_hebrew=core_topics,
            discovered_dapim=[],
            query_type=query_type_str,
            target_masechtos=analysis.target_masechtos
        )
        
        if validation.get('suggested_dapim'):
            main_sugyos = validation['suggested_dapim']
            daf_counts = {daf: 10 for daf in main_sugyos}
            claude_suggested = True
            logger.info(f"Claude suggested: {main_sugyos}")
    
    if not main_sugyos:
        logger.warning("No sugyos found")
        return await _fallback_api_search(analysis)
    
    result.discovered_dapim = main_sugyos
    
    # Create discovery result
    discovery = DiscoveryResult(
        topic=topic,
        topic_hebrew=core_topics[0] if core_topics else topic_hebrew,
        daf_counts=daf_counts,
        main_sugyos=main_sugyos,
        all_citations=all_citations,
        claude_validated=claude_validated,
        claude_suggested=claude_suggested,
    )
    result.discovery = discovery
    
    # =========================================================================
    # PHASE C: Fetch sources from Sefaria
    # =========================================================================
    logger.info("")
    logger.info("PHASE C: Fetching sources from Sefaria")
    logger.info("-" * 50)
    
    sources: List[Source] = []
    
    # Build target authors
    target_authors = set(analysis.target_authors) if analysis.target_authors else set()
    if analysis.source_categories.rashi:
        target_authors.add("rashi")
    if analysis.source_categories.tosfos:
        target_authors.update(["tosafot", "tosfos"])
    if analysis.source_categories.rishonim:
        target_authors.update(["ran", "rashba", "ritva", "ramban", "meiri", "rosh"])
    if not target_authors:
        target_authors = {"rashi", "tosafot", "ran", "rashba", "ritva"}
    
    logger.info(f"Target authors: {target_authors}")
    
    # Fetch for each main sugya
    for daf_ref in main_sugyos[:5]:
        logger.info(f"  Fetching: {daf_ref}")
        
        gemara = await fetch_source_text(daf_ref)
        if gemara:
            gemara.citation_count = daf_counts.get(daf_ref, 0)
            gemara.relevance_description = "Main sugya" + (" (Claude suggested)" if claude_suggested else "")
            sources.append(gemara)
        
        commentaries = await fetch_commentaries_on_daf(daf_ref, target_authors)
        for comm in commentaries:
            comm.citation_count = daf_counts.get(daf_ref, 0)
            sources.append(comm)
        
        logger.info(f"    Found {len(commentaries)} commentaries")
    
    # Organize results
    sources.sort(key=lambda s: (-s.citation_count, s.level.value))
    
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
    result.confidence = ConfidenceLevel.HIGH if claude_validated else ConfidenceLevel.MEDIUM
    
    method_desc = "Claude-suggested" if claude_suggested else "keyword-discovered"
    result.search_description = (
        f"Found {len(sources)} sources across {len(main_sugyos)} main sugyos ({method_desc}). "
        f"Top sugya: {main_sugyos[0] if main_sugyos else 'N/A'}"
    )
    
    # Write output
    try:
        from source_output import SourceOutputWriter
        writer = SourceOutputWriter()
        writer.write_results(result, analysis.original_query, formats=["txt", "html"])
    except Exception as e:
        logger.warning(f"Could not write output: {e}")
    
    logger.info("")
    logger.info("=" * 60)
    logger.info(f"STEP 3 COMPLETE: {len(sources)} sources")
    if claude_suggested:
        logger.info("  (Used Claude-suggested sugyos)")
    logger.info("=" * 60)
    
    return result


# Backwards compatibility
trickle_down_search_v8 = trickle_down_search_v9
trickle_down_search_v7 = trickle_down_search_v9


async def _fallback_api_search(analysis: "QueryAnalysis") -> SearchResult:
    """Fallback when nothing works."""
    logger.info("Using fallback API search")
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
        logger.error(f"Fallback failed: {e}")
    
    return SearchResult(
        original_query=analysis.original_query,
        search_topics=analysis.search_topics_hebrew,
        sources=sources,
        total_sources=len(sources),
        confidence=ConfidenceLevel.LOW,
        search_description="Fallback API search"
    )


async def search(analysis: "QueryAnalysis") -> SearchResult:
    """Main entry point for Step 3."""
    logger.info("=" * 60)
    logger.info("STEP 3: SEARCH")
    logger.info(f"  Query: {analysis.original_query}")
    logger.info(f"  Topics: {analysis.search_topics_hebrew}")
    logger.info(f"  Method: {analysis.search_method}")
    logger.info("=" * 60)
    
    return await trickle_down_search_v9(analysis)


__all__ = [
    'search',
    'trickle_down_search_v9',
    'trickle_down_search_v8',
    'trickle_down_search_v7',
    'Source',
    'SourceLevel',
    'SearchResult',
    'DiscoveryResult',
]