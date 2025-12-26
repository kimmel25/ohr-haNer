"""
Step 3: SEARCH - V11 Architecture
==================================

V11 VISION (from Doyv):
- Determine trickle up vs down based on query type
- Cast a WIDE net - don't filter early, sweep up with confirmation later
- CONFIRMATION LOOPS: Verify results by going the opposite direction
- No rigidity - let Claude's understanding guide us

TRICKLE DOWN (for complex/multi-topic/sugya queries):
1. Search BROADLY in SA, Tur, Rambam, Achronim for the inyan
2. Extract ALL gemara citations from nosei keilim
3. Rank by citation count
4. Claude validates
5. TRICKLE UP from found gemaras: get Rashi, Tosfos, Rishonim
6. CONFIRMATION: Check if rishonim trace back UP to achronim/SA/Tur/Rambam
7. Keep sources that confirm, flag ones that don't

TRICKLE UP (for simple/single-word/halacha/chumash queries):
1. Find earliest source (pasuk → mishna → gemara → psak)
2. Follow chain upward through rishonim → achronim
3. CONFIRMATION: Trickle down from highest source to verify
4. Keep sources that form complete chains
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

try:
    from models import ConfidenceLevel
except ImportError:
    class ConfidenceLevel(Enum):
        HIGH = "high"
        MEDIUM = "medium"
        LOW = "low"

# Import local corpus handler
try:
    from local_corpus import (
        get_local_corpus,
        discover_main_sugyos,
        LocalCorpus,
        GemaraCitation,
        LocalSearchHit,
        MASECHTA_MAP,
        extract_gemara_citations,
    )
    LOCAL_CORPUS_AVAILABLE = True
except ImportError:
    LOCAL_CORPUS_AVAILABLE = False
    logging.warning("local_corpus module not available")

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
#  DATA STRUCTURES
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
    citation_count: int = 0
    confirmed: bool = False  # V11: Did this source pass confirmation?
    confirmation_path: List[str] = field(default_factory=list)  # V11: How was it confirmed?

    @property
    def level_hebrew(self) -> str:
        return self.level.hebrew


@dataclass
class ConfirmationResult:
    """V11: Result of confirmation loop."""
    sugya: str
    confirmed: bool
    path_up: List[str] = field(default_factory=list)  # rishonim found
    path_down: List[str] = field(default_factory=list)  # achronim that cite it
    confidence: float = 0.0
    reason: str = ""


@dataclass
class DiscoveryResult:
    """Result of the discovery process."""
    topic: str
    topic_hebrew: str
    
    sa_simanim: Dict[str, List[int]] = field(default_factory=dict)
    tur_simanim: Dict[str, List[int]] = field(default_factory=dict)
    rambam_halachos: List[str] = field(default_factory=list)
    
    all_citations: List[GemaraCitation] = field(default_factory=list)
    daf_counts: Dict[str, int] = field(default_factory=dict)
    
    main_sugyos: List[str] = field(default_factory=list)
    confirmed_sugyos: List[str] = field(default_factory=list)  # V11
    search_method_used: str = ""


@dataclass
class SearchResult:
    """Complete search result."""
    original_query: str
    search_topics: List[str]
    
    sources: List[Source] = field(default_factory=list)
    sources_by_level: Dict[str, List[Source]] = field(default_factory=dict)
    
    discovery: Optional[DiscoveryResult] = None
    discovered_dapim: List[str] = field(default_factory=list)
    confirmed_dapim: List[str] = field(default_factory=list)  # V11
    
    total_sources: int = 0
    levels_found: List[str] = field(default_factory=list)
    search_description: str = ""
    
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    needs_clarification: bool = False
    clarification_question: Optional[str] = None


# ==============================================================================
#  SEFARIA CLIENT (cached singleton)
# ==============================================================================

_sefaria_client = None

def _get_sefaria_client():
    global _sefaria_client
    if _sefaria_client is None:
        try:
            from tools.sefaria_client import SefariaClient
            _sefaria_client = SefariaClient()
        except ImportError:
            logger.warning("SefariaClient not available")
            return None
    return _sefaria_client


# ==============================================================================
#  V11: DETERMINE SEARCH DIRECTION
# ==============================================================================

def determine_search_direction(analysis: "QueryAnalysis") -> str:
    """
    V11: Determine whether to start with trickle-down or trickle-up.
    
    TRICKLE DOWN for:
    - Multiple topics (comparison queries)
    - Complex conceptual questions
    - Sugya explorations
    - Machlokes/shittah queries
    
    TRICKLE UP for:
    - Simple single-word queries
    - Halacha psak requests
    - Chumash/pasuk questions
    - Known specific locations
    """
    query_type = getattr(analysis.query_type, 'value', str(analysis.query_type))
    realm = getattr(analysis.realm, 'value', str(analysis.realm))
    method = getattr(analysis.search_method, 'value', str(analysis.search_method))
    
    # Check if Claude already decided
    if method == "trickle_up":
        return "trickle_up"
    if method == "trickle_down":
        return "trickle_down"
    if method == "direct":
        return "direct"
    
    # Use query characteristics to decide
    topics = analysis.search_topics_hebrew or []
    
    # Multiple distinct topics → trickle down
    if len(topics) >= 2:
        logger.info(f"[V11] Multiple topics ({len(topics)}) → trickle_down")
        return "trickle_down"
    
    # Complex query types → trickle down
    complex_types = ["comparison", "machlokes", "shittah", "sugya"]
    if query_type in complex_types:
        logger.info(f"[V11] Complex query type ({query_type}) → trickle_down")
        return "trickle_down"
    
    # Simple realms → trickle up
    simple_realms = ["chumash", "mishna", "halacha"]
    if realm in simple_realms:
        logger.info(f"[V11] Simple realm ({realm}) → trickle_up")
        return "trickle_up"
    
    # Single simple topic → trickle up
    if len(topics) == 1 and len(topics[0].split()) <= 2:
        logger.info(f"[V11] Single simple topic → trickle_up")
        return "trickle_up"
    
    # Default to trickle down for gemara realm
    logger.info(f"[V11] Default for gemara → trickle_down")
    return "trickle_down"


# ==============================================================================
#  V11: BROAD SEARCH - Cast a Wide Net
# ==============================================================================

def broad_search_all_sources(
    corpus: "LocalCorpus",
    topics_hebrew: List[str]
) -> Tuple[Dict[str, int], List[GemaraCitation], Dict[str, List[str]]]:
    """
    V11: Search BROADLY across ALL sources. Don't filter early.
    
    Returns:
        - daf_counts: {daf_ref: citation_count}
        - all_citations: List of all citations found
        - source_locations: {source_type: [locations found]}
    """
    logger.info("=" * 60)
    logger.info("[V11 BROAD SEARCH] Casting wide net across all sources")
    logger.info(f"  Topics: {topics_hebrew}")
    logger.info("=" * 60)
    
    all_citations: List[GemaraCitation] = []
    daf_counts: Dict[str, int] = defaultdict(int)
    source_locations: Dict[str, List[str]] = {
        "sa": [],
        "tur": [],
        "rambam": [],
    }
    
    # Search for EACH topic separately (don't combine with AND logic)
    for topic in topics_hebrew:
        logger.info(f"\n[V11] Searching for topic: '{topic}'")
        
        # =================================================================
        # SHULCHAN ARUCH - Search ALL cheleks
        # =================================================================
        for chelek in ["oc", "yd", "eh", "cm"]:
            try:
                hits = corpus.search_shulchan_aruch(topic, chelek)
                if hits:
                    logger.info(f"  SA {chelek.upper()}: {len(hits)} simanim")
                    for hit in hits:
                        siman = hit.siman
                        source_locations["sa"].append(f"{chelek.upper()} {siman}")
                        
                        # Extract citations from nosei keilim
                        citations = corpus.extract_citations_from_siman(chelek, siman)
                        for cite in citations:
                            daf_ref = f"{cite.masechta} {cite.daf}"
                            daf_counts[daf_ref] += 1
                        all_citations.extend(citations)
            except Exception as e:
                logger.debug(f"  SA {chelek.upper()} error: {e}")
        
        # =================================================================
        # TUR - Search ALL cheleks
        # =================================================================
        for chelek in ["oc", "yd", "eh", "cm"]:
            try:
                hits = corpus.search_tur(topic, chelek)
                if hits:
                    logger.info(f"  Tur {chelek.upper()}: {len(hits)} simanim")
                    for hit in hits:
                        siman = hit.siman
                        source_locations["tur"].append(f"{chelek.upper()} {siman}")
                        
                        # Extract citations from Tur nosei keilim
                        citations = corpus.extract_citations_from_tur_siman(chelek, siman)
                        for cite in citations:
                            daf_ref = f"{cite.masechta} {cite.daf}"
                            daf_counts[daf_ref] += 1
                        all_citations.extend(citations)
            except Exception as e:
                logger.debug(f"  Tur {chelek.upper()} error: {e}")
        
        # =================================================================
        # RAMBAM - Search all sefarim
        # =================================================================
        try:
            rambam_hits = corpus.search_rambam(topic)
            if rambam_hits:
                logger.info(f"  Rambam: {len(rambam_hits)} halachos")
                for hit in rambam_hits:
                    source_locations["rambam"].append(hit.ref)
                    
                    # Extract perek number for nosei keilim lookup
                    # Format is typically "Hilchot X, Perek Y"
                    try:
                        sefer = hit.sefer if hasattr(hit, 'sefer') else ""
                        perek = hit.seif if hasattr(hit, 'seif') else 1
                        if sefer and perek:
                            citations = corpus.extract_citations_from_rambam(sefer, perek)
                            for cite in citations:
                                daf_ref = f"{cite.masechta} {cite.daf}"
                                daf_counts[daf_ref] += 1
                            all_citations.extend(citations)
                    except Exception as e:
                        logger.debug(f"  Rambam citation extraction error: {e}")
        except Exception as e:
            logger.debug(f"  Rambam error: {e}")
    
    # Sort by citation count
    sorted_counts = dict(sorted(daf_counts.items(), key=lambda x: -x[1]))
    
    logger.info("\n" + "=" * 60)
    logger.info(f"[V11 BROAD SEARCH] Complete")
    logger.info(f"  Total citations: {len(all_citations)}")
    logger.info(f"  Unique dapim: {len(sorted_counts)}")
    logger.info(f"  SA locations: {len(source_locations['sa'])}")
    logger.info(f"  Tur locations: {len(source_locations['tur'])}")
    logger.info(f"  Rambam locations: {len(source_locations['rambam'])}")
    
    if sorted_counts:
        logger.info("\n  Top 10 dapim by citation count:")
        for i, (ref, count) in enumerate(list(sorted_counts.items())[:10], 1):
            logger.info(f"    {i}. {ref}: {count} citations")
    
    return sorted_counts, all_citations, source_locations


# ==============================================================================
#  V11: CLAUDE VALIDATION WITH INYAN UNDERSTANDING
# ==============================================================================

def validate_sugyos_with_claude_v11(
    candidate_sugyos: List[str],
    daf_counts: Dict[str, int],
    analysis: "QueryAnalysis",
    source_locations: Dict[str, List[str]],
    max_candidates: int = 20
) -> List[str]:
    """
    V11: Have Claude review candidates with FULL context about the inyan.
    
    Claude gets:
    - The original query and what the user wants
    - Which SA/Tur/Rambam simanim mentioned the topic
    - The candidate sugyos
    
    Claude returns which sugyos are actually relevant.
    """
    if not candidate_sugyos:
        return []
    
    candidates_to_check = candidate_sugyos[:max_candidates]
    logger.info(f"[V11 CLAUDE] Reviewing {len(candidates_to_check)} candidates")
    
    # Build rich context for Claude
    query_context = f"""
ORIGINAL QUERY: {analysis.original_query}
QUERY TYPE: {getattr(analysis.query_type, 'value', str(analysis.query_type))}
REALM: {getattr(analysis.realm, 'value', str(analysis.realm))}

HEBREW TOPICS (what the user is looking for):
{chr(10).join(f'  - {t}' for t in analysis.search_topics_hebrew)}

ENGLISH TOPICS:
{chr(10).join(f'  - {t}' for t in analysis.search_topics)}

WHERE WE FOUND THE TOPIC MENTIONED:
- Shulchan Aruch: {', '.join(source_locations.get('sa', [])[:10]) or 'None found'}
- Tur: {', '.join(source_locations.get('tur', [])[:10]) or 'None found'}
- Rambam: {', '.join(source_locations.get('rambam', [])[:5]) or 'None found'}

CLAUDE'S REASONING FROM STEP 2:
{analysis.reasoning}
"""
    
    candidates_info = "\n".join([
        f"  {i+1}. {sugya} ({daf_counts.get(sugya, 0)} citations from nosei keilim)"
        for i, sugya in enumerate(candidates_to_check)
    ])
    
    prompt = f"""You are a Torah research assistant validating gemara search results.

{query_context}

CANDIDATE SUGYOS (found by extracting gemara citations from nosei keilim):
{candidates_info}

YOUR TASK:
Determine which gemaras are ACTUALLY relevant to what the user wants.

IMPORTANT CONSIDERATIONS:
1. Many words have multiple meanings in different contexts
   - "חזקה" can mean: chezkas haguf, chezkas mammon, chazakah (3-year possession), chezkas kashrus
   - Make sure the sugya discusses the SPECIFIC concept the user asked about
   
2. Think about WHICH masechtos would logically discuss this topic
   - Monetary presumptions → Kesubos, Bava Kamma, Bava Basra
   - Shabbos laws → Shabbat, Eruvin
   - Marriage laws → Kesubos, Kiddushin, Gittin
   
3. Consider the citation count - higher counts suggest more relevance

4. Be INCLUSIVE rather than exclusive - if a sugya MIGHT be relevant, keep it
   - We will do a confirmation step later
   - Better to include a marginal source than miss a good one

Return a JSON object:
{{
    "relevant_sugyos": ["Sugya 1", "Sugya 2", ...],
    "definitely_irrelevant": [
        {{"sugya": "Sugya Name", "reason": "Brief explanation"}}
    ],
    "reasoning": "Your overall assessment of which sugyos are most important"
}}

Return ONLY valid JSON, no markdown.
"""
    
    try:
        client = Anthropic()
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2000,
            temperature=0,
            messages=[{"role": "user", "content": prompt}]
        )
        
        response_text = response.content[0].text.strip()
        logger.debug(f"[V11 CLAUDE] Raw response: {response_text[:500]}...")
        
        # Clean markdown if present
        if response_text.startswith("```"):
            response_text = re.sub(r'^```(?:json)?\s*', '', response_text)
            response_text = re.sub(r'\s*```$', '', response_text)
        
        result = json.loads(response_text)
        
        relevant = result.get("relevant_sugyos", [])
        irrelevant = result.get("definitely_irrelevant", [])
        reasoning = result.get("reasoning", "")
        
        logger.info(f"[V11 CLAUDE] Kept {len(relevant)}, removed {len(irrelevant)}")
        logger.info(f"[V11 CLAUDE] Reasoning: {reasoning[:200]}...")
        
        # Match against our candidates
        validated = []
        for sugya in candidates_to_check:
            sugya_lower = sugya.lower()
            for r in relevant:
                if r.lower() in sugya_lower or sugya_lower in r.lower():
                    validated.append(sugya)
                    break
        
        if not validated and candidates_to_check:
            # If Claude rejected everything, keep top 5 by citation count
            # This is a safety net - don't return empty
            logger.warning("[V11 CLAUDE] All rejected - keeping top 5 as fallback")
            validated = candidates_to_check[:5]
        
        return validated
        
    except Exception as e:
        logger.error(f"[V11 CLAUDE] Error: {e}")
        return candidates_to_check[:10]


# ==============================================================================
#  V11: TRICKLE UP FROM GEMARAS - Get Rishonim
# ==============================================================================

async def trickle_up_from_gemaras(
    main_sugyos: List[str],
    target_authors: Set[str]
) -> Dict[str, List[Source]]:
    """
    V11: For each gemara, fetch the rishonim/commentaries.
    
    Returns: {daf_ref: [list of sources]}
    """
    logger.info("\n[V11 TRICKLE UP] Getting rishonim for discovered gemaras")
    
    result: Dict[str, List[Source]] = {}
    client = _get_sefaria_client()
    
    if not client:
        logger.warning("No Sefaria client available")
        return result
    
    for daf_ref in main_sugyos[:10]:  # Limit to top 10
        logger.info(f"  Fetching commentaries for: {daf_ref}")
        
        sources = []
        
        # Fetch gemara text first
        try:
            gemara_source = await fetch_source_text(daf_ref)
            if gemara_source:
                sources.append(gemara_source)
        except Exception as e:
            logger.debug(f"    Gemara fetch error: {e}")
        
        # Fetch commentaries
        try:
            commentaries = await fetch_commentaries_on_daf(daf_ref, target_authors)
            sources.extend(commentaries)
            logger.info(f"    Found {len(commentaries)} commentaries")
        except Exception as e:
            logger.debug(f"    Commentary fetch error: {e}")
        
        result[daf_ref] = sources
    
    return result


# ==============================================================================
#  V11: CONFIRMATION LOOP - Verify with Opposite Direction
# ==============================================================================

async def confirm_sugyos_with_trickle_down(
    sugyos: List[str],
    rishonim_by_daf: Dict[str, List[Source]],
    source_locations: Dict[str, List[str]],
    analysis: "QueryAnalysis"
) -> List[ConfirmationResult]:
    """
    V11 CONFIRMATION: Check if rishonim on these gemaras trace back to achronim.
    
    Logic:
    - We found gemaras by trickle-down (extracting citations from nosei keilim)
    - Now we trickle-up: get rishonim on those gemaras
    - CONFIRM: Do any of those rishonim cite concepts that appear in SA/Tur?
    
    This ensures we didn't just find keyword matches but actual relevant sugyos.
    """
    logger.info("\n[V11 CONFIRMATION] Verifying sugyos trace back to achronim")
    
    results: List[ConfirmationResult] = []
    topics_hebrew = analysis.search_topics_hebrew or []
    
    for sugya in sugyos:
        sources = rishonim_by_daf.get(sugya, [])
        
        # Check if topic appears in rishonim text
        topic_found_in_rishonim = False
        rishonim_mentioning_topic = []
        
        for source in sources:
            text = source.hebrew_text or ""
            for topic in topics_hebrew:
                # Check if any of the topic words appear
                topic_words = topic.split()
                if any(word in text for word in topic_words if len(word) > 2):
                    topic_found_in_rishonim = True
                    rishonim_mentioning_topic.append(source.ref)
                    break
        
        # Build confirmation result
        conf = ConfirmationResult(
            sugya=sugya,
            confirmed=topic_found_in_rishonim,
            path_up=rishonim_mentioning_topic[:5],
            path_down=source_locations.get("sa", [])[:3],
            confidence=0.8 if topic_found_in_rishonim else 0.3,
            reason="Topic found in rishonim" if topic_found_in_rishonim else "Topic not found in rishonim text"
        )
        
        results.append(conf)
        
        if topic_found_in_rishonim:
            logger.info(f"  ✓ {sugya} CONFIRMED - topic in {len(rishonim_mentioning_topic)} rishonim")
        else:
            logger.info(f"  ? {sugya} UNCONFIRMED - topic not in rishonim text")
    
    return results


# ==============================================================================
#  HELPER FUNCTIONS (from original)
# ==============================================================================

async def fetch_source_text(ref: str) -> Optional[Source]:
    """Fetch a source text from Sefaria."""
    client = _get_sefaria_client()
    if not client:
        return None
    
    try:
        result = await client.get_text(ref)
        if not result:
            return None
        
        # Determine source level
        level = SourceLevel.GEMARA_BAVLI
        ref_lower = ref.lower()
        if "rashi" in ref_lower:
            level = SourceLevel.RASHI
        elif "tosafot" in ref_lower or "tosfos" in ref_lower:
            level = SourceLevel.TOSFOS
        elif any(r in ref_lower for r in ["ran", "rashba", "ritva", "ramban", "meiri"]):
            level = SourceLevel.RISHONIM
        
        # Get text
        he_text = ""
        if hasattr(result, 'he') and result.he:
            if isinstance(result.he, list):
                he_text = " ".join(str(x) for x in result.he if x)
            else:
                he_text = str(result.he)
        
        # Skip English for likely copyrighted content
        en_text = ""
        categories = getattr(result, 'categories', []) or []
        if not should_skip_english(categories, ref):
            if hasattr(result, 'text') and result.text:
                if isinstance(result.text, list):
                    en_text = " ".join(str(x) for x in result.text if x)
                else:
                    en_text = str(result.text)
        
        he_ref = getattr(result, 'heRef', ref) or ref
        
        return Source(
            ref=ref,
            he_ref=he_ref,
            level=level,
            hebrew_text=he_text,
            english_text=en_text,
            categories=categories,
        )
        
    except Exception as e:
        logger.debug(f"Error fetching {ref}: {e}")
        return None


async def fetch_commentaries_on_daf(daf_ref: str, target_authors: Set[str]) -> List[Source]:
    """Fetch commentaries on a specific daf."""
    client = _get_sefaria_client()
    if not client:
        return []
    
    sources = []
    
    # Build list of refs to fetch
    commentary_refs = []
    
    # Standard gemara commentaries
    if "rashi" in target_authors or not target_authors:
        commentary_refs.append(f"Rashi on {daf_ref}")
    if "tosafot" in target_authors or "tosfos" in target_authors or not target_authors:
        commentary_refs.append(f"Tosafot on {daf_ref}")
    
    # Rishonim
    rishonim = ["Ran", "Rashba", "Ritva", "Ramban", "Meiri", "Rashbam", "Rabbeinu Gershom"]
    for rishon in rishonim:
        if rishon.lower() in target_authors or not target_authors:
            commentary_refs.append(f"{rishon} on {daf_ref}")
    
    # Try to fetch each
    for ref in commentary_refs:
        try:
            source = await fetch_source_text(ref)
            if source and source.hebrew_text and len(source.hebrew_text) > 50:
                sources.append(source)
        except Exception as e:
            logger.debug(f"Could not fetch {ref}: {e}")
    
    return sources


def should_skip_english(categories: List[str], ref: str) -> bool:
    """Determine if English text should be skipped due to copyright."""
    cats_lower = [c.lower() for c in categories]
    skip_cats = {"talmud", "bavli", "yerushalmi"}
    
    if any(cat in cats_lower for cat in skip_cats):
        return True
    
    # Skip if it looks like a daf reference
    ref_lower = ref.lower()
    if re.search(r'\s\d+[ab](?:$|:|\s)', ref_lower):
        return True
    
    return False


# ==============================================================================
#  V11: MAIN TRICKLE DOWN SEARCH
# ==============================================================================

async def trickle_down_search_v11(analysis: "QueryAnalysis") -> SearchResult:
    """
    V11 Trickle-Down Search with Confirmation Loop.
    
    Flow:
    1. BROAD SEARCH: Search SA, Tur, Rambam for ALL topics
    2. EXTRACT: Get gemara citations from nosei keilim
    3. RANK: Sort by citation count
    4. VALIDATE: Claude reviews candidates
    5. TRICKLE UP: Get rishonim on validated gemaras
    6. CONFIRM: Check if rishonim trace back to achronim
    7. ORGANIZE: Return confirmed sources
    """
    logger.info("=" * 70)
    logger.info("[V11] STEP 3: SEARCH - Trickle-Down with Confirmation")
    logger.info("=" * 70)
    
    topics_hebrew = analysis.search_topics_hebrew or []
    topic = analysis.search_topics[0] if analysis.search_topics else ""
    
    result = SearchResult(
        original_query=analysis.original_query,
        search_topics=analysis.search_topics_hebrew,
    )
    
    if not LOCAL_CORPUS_AVAILABLE:
        logger.warning("Local corpus not available")
        return result
    
    try:
        corpus = LocalCorpus()
    except Exception as e:
        logger.error(f"Could not initialize local corpus: {e}")
        return result
    
    # =========================================================================
    # PHASE 1: BROAD SEARCH - Cast a Wide Net
    # =========================================================================
    logger.info("\n" + "=" * 60)
    logger.info("PHASE 1: BROAD SEARCH")
    logger.info("=" * 60)
    
    daf_counts, all_citations, source_locations = broad_search_all_sources(
        corpus, topics_hebrew
    )
    
    if not daf_counts:
        logger.warning("No citations found in broad search")
        # TODO: Try trickle-up as fallback
        return result
    
    # =========================================================================
    # PHASE 2: CLAUDE VALIDATION
    # =========================================================================
    logger.info("\n" + "=" * 60)
    logger.info("PHASE 2: CLAUDE VALIDATION")
    logger.info("=" * 60)
    
    candidate_sugyos = list(daf_counts.keys())[:25]  # Top 25 by citation count
    
    validated_sugyos = validate_sugyos_with_claude_v11(
        candidate_sugyos,
        daf_counts,
        analysis,
        source_locations
    )
    
    logger.info(f"Validated sugyos: {len(validated_sugyos)}")
    for sugya in validated_sugyos[:5]:
        logger.info(f"  - {sugya}")
    
    # =========================================================================
    # PHASE 3: TRICKLE UP - Get Rishonim
    # =========================================================================
    logger.info("\n" + "=" * 60)
    logger.info("PHASE 3: TRICKLE UP - Fetching Rishonim")
    logger.info("=" * 60)
    
    target_authors = set(a.lower() for a in (analysis.target_authors or []))
    if analysis.source_categories:
        if analysis.source_categories.rashi:
            target_authors.add("rashi")
        if analysis.source_categories.tosfos:
            target_authors.add("tosafot")
        if analysis.source_categories.rishonim:
            target_authors.update(["ran", "rashba", "ritva", "ramban", "meiri"])
    
    if not target_authors:
        target_authors = {"rashi", "tosafot", "ran", "rashba"}
    
    rishonim_by_daf = await trickle_up_from_gemaras(validated_sugyos, target_authors)
    
    # =========================================================================
    # PHASE 4: CONFIRMATION - Verify Sources
    # =========================================================================
    logger.info("\n" + "=" * 60)
    logger.info("PHASE 4: CONFIRMATION - Verifying Sources")
    logger.info("=" * 60)
    
    confirmations = await confirm_sugyos_with_trickle_down(
        validated_sugyos,
        rishonim_by_daf,
        source_locations,
        analysis
    )
    
    confirmed_sugyos = [c.sugya for c in confirmations if c.confirmed]
    unconfirmed_sugyos = [c.sugya for c in confirmations if not c.confirmed]
    
    logger.info(f"\nConfirmed: {len(confirmed_sugyos)}")
    logger.info(f"Unconfirmed: {len(unconfirmed_sugyos)}")
    
    # Keep confirmed + unconfirmed (but mark them)
    # Unconfirmed might still be valid - just couldn't verify
    final_sugyos = confirmed_sugyos + unconfirmed_sugyos[:3]
    
    # =========================================================================
    # PHASE 5: ORGANIZE RESULTS
    # =========================================================================
    logger.info("\n" + "=" * 60)
    logger.info("PHASE 5: ORGANIZING RESULTS")
    logger.info("=" * 60)
    
    all_sources: List[Source] = []
    
    for sugya in final_sugyos[:10]:
        sources = rishonim_by_daf.get(sugya, [])
        is_confirmed = sugya in confirmed_sugyos
        
        for source in sources:
            source.confirmed = is_confirmed
            source.citation_count = daf_counts.get(sugya, 0)
            all_sources.append(source)
    
    # Sort: confirmed first, then by citation count
    all_sources.sort(key=lambda s: (-int(s.confirmed), -s.citation_count))
    
    # Group by level
    sources_by_level: Dict[str, List[Source]] = {}
    for source in all_sources:
        level_key = source.level_hebrew
        if level_key not in sources_by_level:
            sources_by_level[level_key] = []
        sources_by_level[level_key].append(source)
    
    # Build result
    result.sources = all_sources
    result.sources_by_level = sources_by_level
    result.total_sources = len(all_sources)
    result.levels_found = list(sources_by_level.keys())
    result.discovered_dapim = validated_sugyos
    result.confirmed_dapim = confirmed_sugyos
    
    result.confidence = (
        ConfidenceLevel.HIGH if len(confirmed_sugyos) >= 3
        else ConfidenceLevel.MEDIUM if len(confirmed_sugyos) >= 1
        else ConfidenceLevel.LOW
    )
    
    result.search_description = (
        f"Found {len(all_sources)} sources. "
        f"Confirmed sugyos: {', '.join(confirmed_sugyos[:3]) if confirmed_sugyos else 'None'}. "
        f"Method: trickle_down with confirmation."
    )
    
    # Build discovery result
    result.discovery = DiscoveryResult(
        topic=topic,
        topic_hebrew=", ".join(topics_hebrew),
        all_citations=all_citations,
        daf_counts=daf_counts,
        main_sugyos=validated_sugyos,
        confirmed_sugyos=confirmed_sugyos,
        search_method_used="trickle_down_v11",
    )
    
    # Write output files
    try:
        from source_output import SourceOutputWriter
        writer = SourceOutputWriter()
        writer.write_results(result, analysis.original_query, formats=["txt", "html"])
    except Exception as e:
        logger.warning(f"Could not write output files: {e}")
    
    logger.info("\n" + "=" * 70)
    logger.info(f"[V11] STEP 3 COMPLETE: {len(all_sources)} sources found")
    logger.info(f"  Confirmed sugyos: {confirmed_sugyos}")
    logger.info("=" * 70)
    
    return result


# ==============================================================================
#  V11: TRICKLE UP SEARCH (for simple queries)
# ==============================================================================

async def trickle_up_search_v11(analysis: "QueryAnalysis") -> SearchResult:
    """
    V11 Trickle-Up Search with Confirmation Loop.
    
    For simple queries (single topic, halacha, chumash):
    1. Find earliest source (pasuk/mishna/gemara)
    2. Build up through rishonim → achronim
    3. CONFIRM: Trickle down to verify chain is complete
    """
    logger.info("=" * 70)
    logger.info("[V11] STEP 3: SEARCH - Trickle-Up with Confirmation")
    logger.info("=" * 70)
    
    topics_hebrew = analysis.search_topics_hebrew or []
    topic = topics_hebrew[0] if topics_hebrew else ""
    
    result = SearchResult(
        original_query=analysis.original_query,
        search_topics=topics_hebrew,
    )
    
    client = _get_sefaria_client()
    if not client:
        logger.warning("Sefaria client not available")
        return result
    
    # =========================================================================
    # PHASE 1: FIND EARLIEST SOURCE
    # =========================================================================
    logger.info("\n[V11 TRICKLE-UP] Phase 1: Finding earliest source")
    
    found_sources: List[Source] = []
    base_refs: List[str] = []
    
    # Try Mishna first
    try:
        search_result = await client.search(topic, size=20, filters=["Mishnah"])
        if search_result and search_result.hits:
            for hit in search_result.hits[:5]:
                ref = getattr(hit, 'ref', '')
                if ref:
                    base_refs.append(ref)
                    source = await fetch_source_text(ref)
                    if source:
                        source.level = SourceLevel.MISHNA
                        found_sources.append(source)
            logger.info(f"  Found {len(base_refs)} Mishna refs")
    except Exception as e:
        logger.debug(f"  Mishna search error: {e}")
    
    # Try Gemara
    if not base_refs:
        try:
            search_result = await client.search(topic, size=30)
            if search_result and search_result.hits:
                for hit in search_result.hits[:10]:
                    ref = getattr(hit, 'ref', '')
                    if ref and re.search(r'\s\d+[ab]', ref):  # Looks like a daf
                        base_refs.append(ref)
                        source = await fetch_source_text(ref)
                        if source:
                            found_sources.append(source)
                logger.info(f"  Found {len(base_refs)} Gemara refs")
        except Exception as e:
            logger.debug(f"  Gemara search error: {e}")
    
    if not base_refs:
        logger.warning("No base sources found - switching to trickle-down")
        return await trickle_down_search_v11(analysis)
    
    # =========================================================================
    # PHASE 2: BUILD UP - Get commentaries
    # =========================================================================
    logger.info("\n[V11 TRICKLE-UP] Phase 2: Building up through commentaries")
    
    target_authors = set(a.lower() for a in (analysis.target_authors or []))
    if not target_authors:
        target_authors = {"rashi", "tosafot", "ran", "rashba"}
    
    for ref in base_refs[:5]:
        commentaries = await fetch_commentaries_on_daf(ref, target_authors)
        found_sources.extend(commentaries)
    
    # =========================================================================
    # PHASE 3: CONFIRM - Check if traces back to achronim
    # =========================================================================
    logger.info("\n[V11 TRICKLE-UP] Phase 3: Confirmation")
    
    # Try to find these refs cited in SA/Tur
    confirmed_refs = []
    
    if LOCAL_CORPUS_AVAILABLE:
        try:
            corpus = LocalCorpus()
            
            for ref in base_refs[:3]:
                # Extract daf info
                match = re.search(r'(\w+)\s+(\d+[ab])', ref)
                if match:
                    masechta = match.group(1)
                    daf = match.group(2)
                    
                    # Search for this daf in nosei keilim
                    for chelek in ["oc", "yd", "eh", "cm"]:
                        try:
                            hits = corpus.search_shulchan_aruch(masechta, chelek)
                            if hits:
                                confirmed_refs.append(ref)
                                logger.info(f"  ✓ {ref} confirmed - found in SA {chelek.upper()}")
                                break
                        except:
                            pass
        except Exception as e:
            logger.debug(f"Confirmation error: {e}")
    
    # =========================================================================
    # PHASE 4: ORGANIZE RESULTS
    # =========================================================================
    # Sort by level
    found_sources.sort(key=lambda s: list(SourceLevel).index(s.level) if s.level in list(SourceLevel) else 99)
    
    # Mark confirmed
    for source in found_sources:
        if any(ref in source.ref for ref in confirmed_refs):
            source.confirmed = True
    
    # Group by level
    sources_by_level: Dict[str, List[Source]] = {}
    for source in found_sources:
        level_key = source.level_hebrew
        if level_key not in sources_by_level:
            sources_by_level[level_key] = []
        sources_by_level[level_key].append(source)
    
    result.sources = found_sources
    result.sources_by_level = sources_by_level
    result.total_sources = len(found_sources)
    result.levels_found = list(sources_by_level.keys())
    result.discovered_dapim = base_refs
    result.confirmed_dapim = confirmed_refs
    
    result.confidence = (
        ConfidenceLevel.HIGH if confirmed_refs
        else ConfidenceLevel.MEDIUM if found_sources
        else ConfidenceLevel.LOW
    )
    
    logger.info(f"\n[V11] TRICKLE-UP COMPLETE: {len(found_sources)} sources")
    
    return result


# ==============================================================================
#  MAIN SEARCH FUNCTION
# ==============================================================================

async def search(analysis: "QueryAnalysis") -> SearchResult:
    """V11 Main entry point for Step 3: SEARCH."""
    logger.info("=" * 70)
    logger.info("STEP 3: SEARCH [V11]")
    logger.info(f"  Query: {analysis.original_query}")
    logger.info(f"  Realm: {analysis.realm}")
    logger.info(f"  Topics: {analysis.search_topics_hebrew}")
    logger.info(f"  Method from Step 2: {analysis.search_method}")
    logger.info("=" * 70)
    
    # Determine direction
    direction = determine_search_direction(analysis)
    logger.info(f"  Search direction: {direction}")
    
    if direction == "trickle_up":
        return await trickle_up_search_v11(analysis)
    elif direction == "direct":
        # For direct refs, just fetch
        return await trickle_up_search_v11(analysis)
    else:
        return await trickle_down_search_v11(analysis)


# Aliases for backwards compatibility
trickle_down_search_v10 = trickle_down_search_v11
trickle_down_search_v9 = trickle_down_search_v11
trickle_down_search_v8 = trickle_down_search_v11


__all__ = [
    'search',
    'trickle_down_search_v11',
    'trickle_up_search_v11',
    'determine_search_direction',
    'Source',
    'SourceLevel',
    'SearchResult',
    'DiscoveryResult',
    'ConfirmationResult',
]