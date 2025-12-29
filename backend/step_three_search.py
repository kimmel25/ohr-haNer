"""
Step 3: SEARCH - V17 Improved Trickle-Down Logic
=================================================

V17 FIXES (building on V16):
1. Filters out GENERIC ROOT WORDS when specific phrases exist
   - If topics = ["חזקת הגוף", "חזקת ממון", "חזקה"], removes "חזקה"
   - Prevents generic matches from polluting intersection logic
2. For comparison queries: Requires BOTH PRIMARY concepts to intersect
   - Not just "any 2 topics" but "the specific concepts being compared"
   - e.g., for "chezkas haguf vs chezkas mammon", only uses simanim
     that mention BOTH "חזקת הגוף" AND "חזקת ממון"

V16 FIXES:
1. Searches for SPECIFIC PHRASES (e.g., "חזקת הגוף") not just root words ("חזקה")
2. For comparison queries: Requires BOTH concepts to appear in source before extracting citations
3. Filters extracted citations by Claude's target_masechtos
4. Prioritizes sources that mention multiple query concepts
5. Uses Claude's picks as ground truth anchors

V17 FLOW:
1. Get Claude's info from Step 2 (locations, topics, synonyms, target_masechtos)
2. FILTER OUT generic root words from topics (V17 new)
3. For comparison queries: Search for sources mentioning BOTH PRIMARY topics
4. Extract citations ONLY from matching sources
5. Filter citations by target_masechtos
6. Priority 1: Claude's picks + search results in proximity
7. Validate remaining with trickle-up and word search
8. Claude reviews Priority 2 and 3
"""

import logging
import re
import json
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple

from anthropic import Anthropic
from config import get_settings

# =============================================================================
#  IMPORTS
# =============================================================================

try:
    from models import ConfidenceLevel
except ImportError:
    class ConfidenceLevel(Enum):
        HIGH = "high"
        MEDIUM = "medium"
        LOW = "low"

try:
    from local_corpus import (
        get_local_corpus,
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
    
    def extract_gemara_citations(text: str) -> List:
        """Fallback citation extractor."""
        return []

if TYPE_CHECKING:
    from step_two_understand import QueryAnalysis, SearchMethod, Realm, QueryType

try:
    from step_two_understand import QueryAnalysis, SearchMethod, Realm, QueryType
except ImportError as e:
    logging.warning(f"Could not import from step_two_understand: {e}")

logger = logging.getLogger(__name__)
settings = get_settings()


# =============================================================================
#  CONFIGURATION
# =============================================================================

PROXIMITY_RADIUS = 2
WORD_CONTEXT_WINDOW = 50
MIN_TERM_MATCH_RATIO = 0.5

# V16: Masechta name variations for filtering
MASECHTA_ALIASES = {
    'kesubos': ['ketubot', 'kesubos', 'כתובות'],
    'ketubot': ['ketubot', 'kesubos', 'כתובות'],
    'bava kamma': ['bava kamma', 'bava kama', 'בבא קמא'],
    'bava metzia': ['bava metzia', 'bava metziah', 'בבא מציעא'],
    'bava basra': ['bava batra', 'bava basra', 'בבא בתרא'],
    'bava batra': ['bava batra', 'bava basra', 'בבא בתרא'],
    'gittin': ['gittin', 'גיטין'],
    'kiddushin': ['kiddushin', 'kidushin', 'קידושין'],
    'sanhedrin': ['sanhedrin', 'סנהדרין'],
    'yevamot': ['yevamot', 'yevamos', 'יבמות'],
    'nedarim': ['nedarim', 'נדרים'],
    'shabbat': ['shabbat', 'shabbos', 'שבת'],
    'pesachim': ['pesachim', 'psachim', 'פסחים'],
    'chullin': ['chullin', 'chulin', 'חולין'],
}


# =============================================================================
#  SOURCE LEVELS
# =============================================================================

class SourceLevel(Enum):
    """Source levels in traditional trickle-up order."""
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
    SourceLevel.MISHNA: "משנה",
    SourceLevel.GEMARA_BAVLI: "גמרא בבלי",
    SourceLevel.RASHI: 'רש"י',
    SourceLevel.TOSFOS: "תוספות",
    SourceLevel.RISHONIM: "ראשונים",
    SourceLevel.RAMBAM: 'רמב"ם',
    SourceLevel.TUR: "טור",
    SourceLevel.SHULCHAN_ARUCH: "שולחן ערוך",
    SourceLevel.NOSEI_KEILIM: "נושאי כלים",
    SourceLevel.ACHARONIM: "אחרונים",
}


class Priority(Enum):
    """Source priority levels."""
    P1 = 1
    P2 = 2
    P3 = 3


# =============================================================================
#  DATA STRUCTURES
# =============================================================================

@dataclass
class Source:
    """A single source with text and metadata."""
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
    priority: Priority = Priority.P3
    source_origin: str = ""
    validation_method: str = ""

    @property
    def level_hebrew(self) -> str:
        return self.level.hebrew


@dataclass
class CandidateSource:
    """A candidate source before final validation."""
    ref: str
    hebrew_text: str = ""
    citation_count: int = 0
    source_origin: str = ""
    priority: Priority = Priority.P3
    validation_method: str = ""
    in_claude_proximity: bool = False
    validated_by_trickle_up: bool = False
    passed_word_search: bool = False
    claude_confidence: float = 0.0
    claude_reason: str = ""
    matched_terms: List[str] = field(default_factory=list)
    missing_terms: List[str] = field(default_factory=list)
    # V16: Track which topics this source matched
    topics_matched: List[str] = field(default_factory=list)


@dataclass 
class SearchResult:
    """Complete search result."""
    original_query: str
    search_topics: List[str]
    sources: List[Source] = field(default_factory=list)
    sources_by_level: Dict[str, List[Source]] = field(default_factory=dict)
    sources_by_priority: Dict[int, List[Source]] = field(default_factory=dict)
    
    claude_picks: List[str] = field(default_factory=list)
    priority_1_refs: List[str] = field(default_factory=list)
    priority_2_refs: List[str] = field(default_factory=list)
    priority_3_refs: List[str] = field(default_factory=list)
    rejected_refs: List[Tuple[str, str]] = field(default_factory=list)
    
    total_sources: int = 0
    levels_found: List[str] = field(default_factory=list)
    search_description: str = ""
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    needs_clarification: bool = False
    clarification_question: Optional[str] = None


# =============================================================================
#  CLIENTS
# =============================================================================

_sefaria_client = None
_anthropic_client = None


def _get_sefaria_client():
    global _sefaria_client
    if _sefaria_client is None:
        try:
            from tools.sefaria_client import SefariaClient
            _sefaria_client = SefariaClient()
        except ImportError:
            logger.warning("SefariaClient not available")
    return _sefaria_client


def _get_anthropic_client():
    global _anthropic_client
    if _anthropic_client is None:
        try:
            _anthropic_client = Anthropic(api_key=settings.anthropic_api_key)
        except Exception as e:
            logger.warning(f"Could not create Anthropic client: {e}")
    return _anthropic_client


# =============================================================================
#  HELPER FUNCTIONS
# =============================================================================

def parse_gemara_ref(ref: str) -> Optional[Tuple[str, int, str]]:
    """Parse a gemara ref into (masechta, daf_number, amud)."""
    match = re.match(r'^([A-Za-z\s]+)\s+(\d+)([ab])$', ref.strip())
    if match:
        return (match.group(1).strip(), int(match.group(2)), match.group(3))
    return None


def refs_in_proximity(ref1: str, ref2: str, radius: int = PROXIMITY_RADIUS) -> bool:
    """Check if two gemara refs are within radius dafim of each other."""
    parsed1 = parse_gemara_ref(ref1)
    parsed2 = parse_gemara_ref(ref2)
    
    if not parsed1 or not parsed2:
        return False
    
    masechta1, daf1, amud1 = parsed1
    masechta2, daf2, amud2 = parsed2
    
    if masechta1.lower() != masechta2.lower():
        return False
    
    pos1 = daf1 * 2 + (0 if amud1 == 'a' else 1)
    pos2 = daf2 * 2 + (0 if amud2 == 'a' else 1)
    
    return abs(pos1 - pos2) <= radius * 2


def normalize_hebrew(text: str) -> str:
    """Normalize Hebrew text for matching."""
    if not text:
        return ""
    text = re.sub(r'[\u0591-\u05C7]', '', text)
    sofit_map = {'ם': 'מ', 'ן': 'נ', 'ך': 'כ', 'ף': 'פ', 'ץ': 'צ'}
    for sofit, regular in sofit_map.items():
        text = text.replace(sofit, regular)
    return text.lower()


def extract_daf_refs_from_text(text: str) -> List[str]:
    """Extract gemara daf references from free text."""
    refs = []
    masechtos = [
        'Kesubos', 'Ketubot', 'Bava Kamma', 'Bava Metzia', 'Bava Basra', 'Bava Batra',
        'Gittin', 'Kiddushin', 'Sanhedrin', 'Shabbat', 'Shabbos', 'Eruvin',
        'Pesachim', 'Yoma', 'Sukkah', 'Beitzah', 'Rosh Hashanah', 'Taanis',
        'Megillah', 'Moed Katan', 'Chagigah', 'Yevamot', 'Nedarim', 'Nazir',
        'Sotah', 'Makkot', 'Shevuot', 'Avodah Zarah', 'Horayot', 'Zevachim',
        'Menachot', 'Chullin', 'Bechorot', 'Arachin', 'Temurah', 'Keritot',
        'Meilah', 'Niddah'
    ]
    
    for masechta in masechtos:
        pattern = rf'\b{masechta}\s+(\d+)\s*([ab])\b'
        for match in re.finditer(pattern, text, re.IGNORECASE):
            refs.append(f"{masechta} {match.group(1)}{match.group(2).lower()}")
    
    return refs


# =============================================================================
#  V16: IMPROVED MATCHING FUNCTIONS
# =============================================================================

def _filter_generic_roots(topics: List[str]) -> List[str]:
    """
    V17: Filter out generic root words when specific phrases containing them exist.
    
    Example:
        Input:  ["חזקת הגוף", "חזקת ממון", "חזקה"]
        Output: ["חזקת הגוף", "חזקת ממון"]
        
    Why: For comparison queries, we want simanim that mention BOTH specific concepts,
    not just any siman that mentions the generic root. If we keep "חזקה", then
    a siman matching "חזקה" + "חזקת הגוף" counts as 2 topics, but that's wrong -
    it's really just discussing חזקת הגוף.
    
    The rule: If topic A is a substring of topic B (or vice versa), keep only the longer one.
    """
    if not topics or len(topics) <= 1:
        return topics
    
    # Normalize for comparison
    def norm(s):
        return normalize_hebrew(s.strip())
    
    filtered = []
    for topic in topics:
        topic_norm = norm(topic)
        
        # Check if this topic is a substring of any other topic
        is_substring_of_another = False
        for other in topics:
            if other == topic:
                continue
            other_norm = norm(other)
            # If this topic is contained within another (longer) topic, skip it
            if topic_norm in other_norm and len(topic_norm) < len(other_norm):
                is_substring_of_another = True
                break
        
        if not is_substring_of_another:
            filtered.append(topic)
    
    return filtered


def matches_target_masechtos(ref: str, target_masechtos: List[str]) -> bool:
    """
    Check if a gemara ref matches one of the target masechtos.
    Uses aliases to handle spelling variations.
    """
    if not target_masechtos:
        return True  # No filter
    
    parsed = parse_gemara_ref(ref)
    if not parsed:
        return False
    
    masechta = parsed[0].lower()
    
    for target in target_masechtos:
        target_lower = target.lower()
        # Direct match
        if target_lower in masechta or masechta in target_lower:
            return True
        # Check aliases
        if target_lower in MASECHTA_ALIASES:
            for alias in MASECHTA_ALIASES[target_lower]:
                if alias.lower() in masechta or masechta in alias.lower():
                    return True
    
    return False


def text_contains_phrase(text: str, phrase: str) -> bool:
    """
    Check if text contains the phrase (or close variant).
    More lenient than exact match - allows for nikud and sofit variations.
    """
    if not text or not phrase:
        return False
    
    norm_text = normalize_hebrew(text)
    norm_phrase = normalize_hebrew(phrase)
    
    # Direct substring match
    if norm_phrase in norm_text:
        return True
    
    # Split phrase into words and check if all appear
    phrase_words = norm_phrase.split()
    if len(phrase_words) > 1:
        return all(word in norm_text for word in phrase_words if len(word) > 2)
    
    return False


def count_topic_matches(text: str, topics: List[str]) -> Tuple[int, List[str]]:
    """
    Count how many topics appear in the text.
    Returns (count, list_of_matched_topics).
    """
    matched = []
    for topic in topics:
        if text_contains_phrase(text, topic):
            matched.append(topic)
    return len(matched), matched


# =============================================================================
#  STEP 1: EXTRACT CLAUDE'S INFO FROM STEP 2
# =============================================================================

def extract_claude_info(analysis: "QueryAnalysis") -> Dict[str, Any]:
    """
    Extract all relevant info from Step 2's QueryAnalysis.
    V16: Also extract query_type for intersection logic.
    """
    logger.info("=" * 70)
    logger.info("[PHASE 1] EXTRACTING CLAUDE'S INFO FROM STEP 2")
    logger.info("=" * 70)
    
    info = {
        "claude_picks": [],
        "search_topics_hebrew": [],
        "synonyms": [],
        "search_method": "trickle_down",
        "target_masechtos": [],
        "target_authors": [],
        "inyan_description": "",
        "query_type": "topic",  # V16: Added for intersection logic
    }
    
    # Extract Hebrew topics
    if analysis.search_topics_hebrew:
        info["search_topics_hebrew"] = list(analysis.search_topics_hebrew)
        logger.info(f"  Topics (Hebrew): {info['search_topics_hebrew']}")
    
    # V16: Extract query type
    query_type = getattr(analysis, 'query_type', None)
    if query_type:
        info["query_type"] = str(query_type.value) if hasattr(query_type, 'value') else str(query_type)
    logger.info(f"  Query type: {info['query_type']}")
    
    # Extract synonyms and inyan
    reasoning = getattr(analysis, 'reasoning', '') or ''
    inyan = getattr(analysis, 'inyan_description', '') or ''
    info["inyan_description"] = inyan
    
    # Extract daf references
    picks = set()
    
    if analysis.target_dapim:
        for daf in analysis.target_dapim:
            if parse_gemara_ref(daf):
                picks.add(daf)
                logger.info(f"  [target_dapim] {daf}")
    
    for ref in extract_daf_refs_from_text(reasoning):
        picks.add(ref)
        logger.info(f"  [reasoning] {ref}")
    
    for ref in extract_daf_refs_from_text(inyan):
        picks.add(ref)
        logger.info(f"  [inyan] {ref}")
    
    info["claude_picks"] = list(picks)
    
    # Search method
    search_method = getattr(analysis, 'search_method', None)
    if search_method:
        info["search_method"] = str(search_method.value) if hasattr(search_method, 'value') else str(search_method)
    logger.info(f"  Search method: {info['search_method']}")
    
    # Target masechtos - V16: Important for filtering
    if analysis.target_masechtos:
        info["target_masechtos"] = list(analysis.target_masechtos)
        logger.info(f"  Target masechtos: {info['target_masechtos']}")
    
    # Target authors
    if analysis.target_authors:
        info["target_authors"] = list(analysis.target_authors)
        logger.info(f"  Target authors: {info['target_authors']}")
    
    logger.info(f"\n  Total Claude picks: {len(info['claude_picks'])}")
    if info['claude_picks']:
        logger.info(f"  Picks: {info['claude_picks']}")
    
    return info


# =============================================================================
#  STEP 2: V16 IMPROVED TRICKLE-DOWN SEARCH
# =============================================================================

async def run_search(
    info: Dict[str, Any],
    corpus: Optional["LocalCorpus"] = None
) -> Tuple[List[CandidateSource], Dict[str, int]]:
    """
    V17 Improved trickle-down search.
    
    KEY CHANGES from V16:
    1. Filter out generic root words when specific phrases exist
       (e.g., remove "חזקה" when we have "חזקת הגוף" and "חזקת ממון")
    2. For comparison queries: Require the SPECIFIC concepts to intersect
    3. Filter citations by target_masechtos
    4. Search for full phrases, not just root words
    """
    logger.info("\n" + "=" * 70)
    logger.info("[PHASE 2] V17 IMPROVED TRICKLE-DOWN SEARCH")
    logger.info("=" * 70)
    
    candidates: List[CandidateSource] = []
    daf_counts: Dict[str, int] = defaultdict(int)
    seen_refs: Set[str] = set()
    
    topics = info["search_topics_hebrew"]
    target_masechtos = info.get("target_masechtos", [])
    query_type = info.get("query_type", "topic")
    
    # V17: Filter out generic root words when specific phrases exist
    # If we have ["חזקת הגוף", "חזקת ממון", "חזקה"], remove "חזקה" because it's just noise
    original_topics = list(topics)
    filtered_topics = _filter_generic_roots(topics)
    
    if len(filtered_topics) < len(original_topics):
        logger.info(f"  V17: Filtered generic roots: {original_topics} -> {filtered_topics}")
    
    topics = filtered_topics if filtered_topics else original_topics
    
    # V17: For comparison queries, identify the PRIMARY concepts to intersect
    is_comparison = query_type in ("comparison", "machlokes")
    
    # For comparison, we want simanim that mention BOTH primary concepts
    # Take the first 2 specific topics as the primary comparison targets
    primary_topics = topics[:2] if is_comparison and len(topics) >= 2 else topics
    min_topics_required = 2 if is_comparison and len(primary_topics) >= 2 else 1
    
    logger.info(f"  Original topics: {original_topics}")
    logger.info(f"  Filtered topics: {topics}")
    logger.info(f"  Primary topics for intersection: {primary_topics}")
    logger.info(f"  Target masechtos: {target_masechtos}")
    logger.info(f"  Query type: {query_type}")
    logger.info(f"  Is comparison: {is_comparison}")
    logger.info(f"  Min topics required for intersection: {min_topics_required}")
    
    if not topics:
        logger.warning("  No search topics provided")
        return candidates, dict(daf_counts)
    
    # TRICKLE-DOWN: Search acharonim, extract citations
    if info["search_method"] in ("trickle_down", "hybrid"):
        logger.info("\n  [TRICKLE-DOWN V16] Searching with phrase matching...")
        
        if corpus:
            # V16: Search for EACH specific topic phrase
            # For comparisons, we'll track which simanim mention multiple topics
            siman_topic_hits: Dict[str, Set[str]] = defaultdict(set)  # siman -> set of topics
            siman_texts: Dict[str, str] = {}  # siman -> text content
            siman_citations: Dict[str, List] = {}  # siman -> list of citations
            
            for topic in topics:
                logger.info(f"\n    Searching for FULL PHRASE: '{topic}'")
                
                try:
                    for chelek in ["cm", "eh", "yd", "oc"]:
                        try:
                            hits = corpus.search_shulchan_aruch(topic, chelek)
                            if hits:
                                logger.info(f"      SA {chelek.upper()}: {len(hits)} simanim for '{topic}'")
                                for hit in hits[:20]:
                                    siman_key = f"SA_{chelek}_{getattr(hit, 'siman', str(hit))}"
                                    siman_topic_hits[siman_key].add(topic)
                                    
                                    # Store text and citations
                                    if siman_key not in siman_texts:
                                        text = getattr(hit, 'text', '') or getattr(hit, 'content', '') or ''
                                        siman_texts[siman_key] = text
                                        
                                        # Try to get citations
                                        citations = []
                                        if hasattr(corpus, 'extract_citations_from_siman'):
                                            try:
                                                siman = getattr(hit, 'siman', None)
                                                if siman:
                                                    citations = corpus.extract_citations_from_siman(chelek, siman)
                                            except:
                                                pass
                                        if not citations and text:
                                            citations = extract_gemara_citations(text)
                                        siman_citations[siman_key] = citations or []
                                        
                        except TypeError:
                            pass
                        except Exception as e:
                            logger.debug(f"      Error: {e}")
                    
                    # Also search Tur
                    for chelek in ["cm", "eh", "yd", "oc"]:
                        try:
                            hits = corpus.search_tur(topic, chelek)
                            if hits:
                                logger.info(f"      Tur {chelek.upper()}: {len(hits)} simanim for '{topic}'")
                                for hit in hits[:15]:
                                    siman_key = f"Tur_{chelek}_{getattr(hit, 'siman', str(hit))}"
                                    siman_topic_hits[siman_key].add(topic)
                                    
                                    if siman_key not in siman_texts:
                                        text = getattr(hit, 'text', '') or getattr(hit, 'content', '') or ''
                                        siman_texts[siman_key] = text
                                        
                                        citations = []
                                        if hasattr(corpus, 'extract_citations_from_tur_siman'):
                                            try:
                                                siman = getattr(hit, 'siman', None)
                                                if siman:
                                                    citations = corpus.extract_citations_from_tur_siman(chelek, siman)
                                            except:
                                                pass
                                        if not citations and text:
                                            citations = extract_gemara_citations(text)
                                        siman_citations[siman_key] = citations or []
                                        
                        except TypeError:
                            pass
                        except Exception as e:
                            logger.debug(f"      Tur error: {e}")
                            
                except Exception as e:
                    logger.warning(f"      Error searching for '{topic}': {e}")
            
            # V17: Now filter simanim by how many PRIMARY topics they match
            # For comparison queries, we need simanim that discuss BOTH primary concepts
            logger.info(f"\n  [V17 INTERSECTION LOGIC]")
            logger.info(f"    Total simanim found: {len(siman_topic_hits)}")
            logger.info(f"    Primary topics for intersection: {primary_topics}")
            
            # V17: For comparisons, check if siman matches the PRIMARY topics specifically
            # Not just "any 2 topics" but "the 2 concepts being compared"
            if is_comparison and len(primary_topics) >= 2:
                # A siman qualifies if it matches BOTH primary topics
                simanim_with_both_primary = {}
                for siman_key, matched_topics in siman_topic_hits.items():
                    # Check how many of the PRIMARY topics this siman matches
                    primary_matched = [t for t in primary_topics if t in matched_topics]
                    if len(primary_matched) >= min_topics_required:
                        simanim_with_both_primary[siman_key] = matched_topics
                
                logger.info(f"    Simanim matching BOTH primary topics: {len(simanim_with_both_primary)}")
                
                if simanim_with_both_primary:
                    logger.info(f"    Using STRICT INTERSECTION - only simanim with BOTH primary concepts")
                    simanim_to_use = simanim_with_both_primary
                else:
                    # Fallback: try simanim with at least one primary topic
                    simanim_with_any_primary = {
                        k: v for k, v in siman_topic_hits.items()
                        if any(t in v for t in primary_topics)
                    }
                    logger.info(f"    FALLBACK - simanim with at least one primary topic: {len(simanim_with_any_primary)}")
                    simanim_to_use = simanim_with_any_primary if simanim_with_any_primary else siman_topic_hits
            else:
                # Non-comparison: original logic
                simanim_with_multiple = {k: v for k, v in siman_topic_hits.items() if len(v) >= min_topics_required}
                logger.info(f"    Simanim with >= {min_topics_required} topics: {len(simanim_with_multiple)}")
                
                if simanim_with_multiple:
                    logger.info(f"    Using INTERSECTION - only simanim with multiple topics")
                    simanim_to_use = simanim_with_multiple
                else:
                    logger.info(f"    FALLBACK - using ALL simanim (no intersection found)")
                    simanim_to_use = siman_topic_hits
            
            # Extract citations from selected simanim
            for siman_key, matched_topics in simanim_to_use.items():
                citations = siman_citations.get(siman_key, [])
                
                # V16: Give bonus to citations from multi-topic simanim
                bonus = len(matched_topics)
                
                for cite in citations:
                    if hasattr(cite, 'masechta'):
                        ref = f"{cite.masechta} {cite.daf}"
                    elif isinstance(cite, str):
                        ref = cite
                    else:
                        continue
                    
                    # V16: FILTER by target_masechtos
                    if target_masechtos and not matches_target_masechtos(ref, target_masechtos):
                        logger.debug(f"      Filtered out {ref} - not in target masechtos")
                        continue
                    
                    # Add with bonus weighting
                    daf_counts[ref] += bonus
                    
                    if ref not in seen_refs:
                        seen_refs.add(ref)
                        candidates.append(CandidateSource(
                            ref=ref,
                            citation_count=bonus,
                            source_origin=f"trickle_down_{siman_key.split('_')[0].lower()}",
                            topics_matched=list(matched_topics)
                        ))
                        
                        if len(matched_topics) >= min_topics_required:
                            logger.info(f"      ✓ {ref} (from {siman_key}, matched: {matched_topics})")
            
            logger.info(f"\n    Citations extracted: {len(candidates)}")
            
            # V16: Show top candidates with their topic matches
            sorted_by_count = sorted(candidates, key=lambda c: c.citation_count, reverse=True)[:10]
            if sorted_by_count:
                logger.info(f"    Top candidates:")
                for c in sorted_by_count[:5]:
                    logger.info(f"      {c.ref}: count={c.citation_count}, topics={c.topics_matched}")
    
    # TRICKLE-UP: Search gemara directly
    if info["search_method"] in ("trickle_up", "hybrid"):
        logger.info("\n  [TRICKLE-UP] Searching gemara directly...")
        
        client = _get_sefaria_client()
        if client:
            for topic in topics[:2]:
                try:
                    results = await client.search(topic, filters=["Talmud"])
                    if results and hasattr(results, 'hits'):
                        for hit in results.hits[:20]:
                            ref = hit.ref
                            
                            # V16: Filter by target masechtos
                            if target_masechtos and not matches_target_masechtos(ref, target_masechtos):
                                continue
                                
                            if ref and ref not in seen_refs:
                                seen_refs.add(ref)
                                candidates.append(CandidateSource(
                                    ref=ref,
                                    source_origin="trickle_up_search"
                                ))
                except Exception as e:
                    logger.warning(f"      Trickle-up search error: {e}")
    
    # Update citation counts
    for c in candidates:
        if c.citation_count == 0:
            c.citation_count = daf_counts.get(c.ref, 0)
    
    logger.info(f"\n  Total candidates found: {len(candidates)}")
    logger.info(f"  Unique dafim with citations: {len(daf_counts)}")
    
    # Log top cited dafim
    sorted_dafim = sorted(daf_counts.items(), key=lambda x: -x[1])[:10]
    if sorted_dafim:
        logger.info(f"  Top cited: {sorted_dafim}")
    
    return candidates, dict(daf_counts)


# =============================================================================
#  STEP 3: CLASSIFY BY PROXIMITY TO CLAUDE'S PICKS
# =============================================================================

def classify_by_proximity(
    candidates: List[CandidateSource],
    claude_picks: List[str]
) -> Tuple[List[CandidateSource], List[CandidateSource]]:
    """
    Classify candidates based on proximity to Claude's picks.
    Claude's picks themselves are ALWAYS Priority 1.
    """
    logger.info("\n" + "=" * 70)
    logger.info("[PHASE 3] CLASSIFYING BY PROXIMITY TO CLAUDE'S PICKS")
    logger.info(f"  Claude's picks: {claude_picks}")
    logger.info("=" * 70)
    
    priority_1: List[CandidateSource] = []
    list_x: List[CandidateSource] = []
    seen_refs: Set[str] = set()
    
    # Claude's picks are ALWAYS Priority 1
    for pick in claude_picks:
        if pick not in seen_refs:
            seen_refs.add(pick)
            priority_1.append(CandidateSource(
                ref=pick,
                source_origin="claude_pick",
                priority=Priority.P1,
                validation_method="claude_pick",
                in_claude_proximity=True,
            ))
            logger.info(f"  ✓ PRIORITY 1: {pick} (Claude's pick)")
    
    # Check search candidates for proximity
    for candidate in candidates:
        if candidate.ref in seen_refs:
            continue
            
        in_proximity = False
        for pick in claude_picks:
            if refs_in_proximity(candidate.ref, pick, PROXIMITY_RADIUS):
                in_proximity = True
                break
        
        if in_proximity:
            seen_refs.add(candidate.ref)
            candidate.in_claude_proximity = True
            candidate.priority = Priority.P1
            candidate.validation_method = "proximity"
            priority_1.append(candidate)
            logger.info(f"  ✓ PRIORITY 1: {candidate.ref} (near Claude's pick)")
        else:
            list_x.append(candidate)
    
    logger.info(f"\n  Priority 1 (Claude's picks + proximity): {len(priority_1)}")
    logger.info(f"  List[X] (needs validation): {len(list_x)}")
    
    return priority_1, list_x


# =============================================================================
#  STEP 4: VALIDATE LIST[X] WITH TRICKLE-UP
# =============================================================================

async def validate_with_trickle_up(
    list_x: List[CandidateSource],
    topics_hebrew: List[str],
    corpus: Optional["LocalCorpus"] = None
) -> Tuple[List[CandidateSource], List[CandidateSource]]:
    """
    Validate List[X] candidates using trickle-up search.
    """
    logger.info("\n" + "=" * 70)
    logger.info("[PHASE 4] VALIDATING LIST[X] WITH TRICKLE-UP")
    logger.info("=" * 70)
    
    if not list_x:
        return [], []
    
    trickle_up_refs: Set[str] = set()
    
    client = _get_sefaria_client()
    if client:
        for topic in topics_hebrew[:2]:
            logger.info(f"  Trickle-up search for: '{topic}'")
            try:
                results = await client.search(topic, filters=["Talmud"])
                if results and hasattr(results, 'hits'):
                    for hit in results.hits[:30]:
                        ref = hit.ref
                        if ref:
                            parsed = parse_gemara_ref(ref)
                            if parsed:
                                trickle_up_refs.add(f"{parsed[0]} {parsed[1]}{parsed[2]}")
                    logger.info(f"    Found {len(results.hits)} hits")
            except Exception as e:
                logger.warning(f"    Search error: {e}")
    
    logger.info(f"  Trickle-up found {len(trickle_up_refs)} unique dafim")
    
    priority_2: List[CandidateSource] = []
    priority_3: List[CandidateSource] = []
    
    for candidate in list_x:
        validated = False
        for tu_ref in trickle_up_refs:
            if refs_in_proximity(candidate.ref, tu_ref, radius=1):
                validated = True
                break
        
        if validated:
            candidate.validated_by_trickle_up = True
            candidate.priority = Priority.P2
            candidate.validation_method = "trickle_up"
            priority_2.append(candidate)
            logger.info(f"  ✓ PRIORITY 2: {candidate.ref} (validated by trickle-up)")
        else:
            candidate.priority = Priority.P3
            priority_3.append(candidate)
            logger.debug(f"  → PRIORITY 3: {candidate.ref} (not in trickle-up)")
    
    logger.info(f"\n  Priority 2 (validated): {len(priority_2)}")
    logger.info(f"  Priority 3 (unvalidated): {len(priority_3)}")
    
    return priority_2, priority_3


# =============================================================================
#  STEP 5: WORD SEARCH ON PRIORITY 3
# =============================================================================

async def word_search_validation(
    priority_3: List[CandidateSource],
    topics_hebrew: List[str],
    synonyms: List[str]
) -> Tuple[List[CandidateSource], List[CandidateSource]]:
    """
    Do word search on Priority 3 candidates.
    """
    logger.info("\n" + "=" * 70)
    logger.info("[PHASE 5] WORD SEARCH ON PRIORITY 3")
    logger.info(f"  Candidates: {len(priority_3)}")
    logger.info("=" * 70)
    
    if not priority_3:
        return [], []
    
    all_terms = list(set(topics_hebrew + synonyms))
    
    promoted: List[CandidateSource] = []
    remaining: List[CandidateSource] = []
    
    client = _get_sefaria_client()
    if not client:
        return [], priority_3
    
    for candidate in priority_3[:20]:
        try:
            result = await client.get_text(candidate.ref)
            if not result or not hasattr(result, 'hebrew') or not result.hebrew:
                remaining.append(candidate)
                continue
            
            hebrew_text = result.hebrew
            if isinstance(hebrew_text, list):
                hebrew_text = " ".join(str(x) for x in hebrew_text if x)
            
            candidate.hebrew_text = hebrew_text
            normalized_text = normalize_hebrew(hebrew_text)
            
            matched = []
            missing = []
            
            for term in all_terms:
                normalized_term = normalize_hebrew(term)
                if normalized_term and len(normalized_term) > 2:
                    if normalized_term in normalized_text:
                        matched.append(term)
                    else:
                        missing.append(term)
            
            candidate.matched_terms = matched
            candidate.missing_terms = missing
            
            total_terms = len([t for t in all_terms if len(normalize_hebrew(t)) > 2])
            match_ratio = len(matched) / total_terms if total_terms > 0 else 0
            
            logger.debug(f"  {candidate.ref}: matched {len(matched)}/{total_terms} ({match_ratio:.1%})")
            
            if match_ratio >= MIN_TERM_MATCH_RATIO:
                candidate.passed_word_search = True
                candidate.priority = Priority.P2
                candidate.validation_method = "word_search"
                promoted.append(candidate)
                logger.info(f"  ↑ PROMOTED to P2: {candidate.ref} ({match_ratio:.1%} terms matched)")
            else:
                remaining.append(candidate)
                
        except Exception as e:
            logger.debug(f"  Error fetching {candidate.ref}: {e}")
            remaining.append(candidate)
    
    remaining.extend(priority_3[20:])
    
    logger.info(f"\n  Promoted to P2: {len(promoted)}")
    logger.info(f"  Remaining P3: {len(remaining)}")
    
    return promoted, remaining


# =============================================================================
#  STEP 6: CLAUDE REVIEW OF PRIORITY 2 AND 3
# =============================================================================

CLAUDE_REVIEW_PROMPT = """You are reviewing Torah sources for relevance to a user's query.

ORIGINAL QUERY: {query}
TOPIC DESCRIPTION: {inyan}
SEARCH TERMS: {terms}

Below are candidate sources in two groups:

## PRIORITY 2 (Already partially validated - be generous, don't throw these out unless clearly irrelevant)
{priority_2_text}

## PRIORITY 3 (Unvalidated - be more strict, only keep if clearly relevant)
{priority_3_text}

For each source, evaluate if it genuinely discusses the topic the user asked about.

IMPORTANT:
- For Priority 2: Keep unless CLEARLY irrelevant. Give benefit of the doubt.
- For Priority 3: Only keep if you're confident it's relevant. Reject if unsure.

Return a JSON object:
{{
  "keep": [
    {{"ref": "...", "reason": "brief reason to keep"}},
    ...
  ],
  "reject": [
    {{"ref": "...", "reason": "brief reason to reject"}},
    ...
  ]
}}

Return ONLY the JSON, no other text."""


async def claude_review(
    priority_2: List[CandidateSource],
    priority_3: List[CandidateSource],
    query: str,
    inyan: str,
    topics: List[str]
) -> Tuple[List[CandidateSource], List[Tuple[str, str]]]:
    """
    Have Claude review Priority 2 and Priority 3 sources.
    """
    logger.info("\n" + "=" * 70)
    logger.info("[PHASE 6] CLAUDE REVIEW OF PRIORITY 2 AND 3")
    logger.info(f"  Priority 2: {len(priority_2)}")
    logger.info(f"  Priority 3: {len(priority_3)}")
    logger.info("=" * 70)
    
    if not priority_2 and not priority_3:
        return [], []
    
    client = _get_anthropic_client()
    if not client:
        logger.warning("  No Anthropic client - keeping all P2, rejecting all P3")
        rejected = [(c.ref, "No Claude review available") for c in priority_3]
        return priority_2, rejected
    
    def format_sources(sources: List[CandidateSource]) -> str:
        if not sources:
            return "(none)"
        
        text = ""
        for c in sources[:10]:
            snippet = c.hebrew_text[:300] + "..." if len(c.hebrew_text) > 300 else c.hebrew_text
            text += f"\n[{c.ref}]\n"
            text += f"Matched terms: {c.matched_terms}\n"
            text += f"Text: {snippet}\n"
            text += "-" * 30 + "\n"
        return text
    
    prompt = CLAUDE_REVIEW_PROMPT.format(
        query=query,
        inyan=inyan,
        terms=", ".join(topics),
        priority_2_text=format_sources(priority_2),
        priority_3_text=format_sources(priority_3)
    )
    
    try:
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        response_text = response.content[0].text.strip()
        
        if response_text.startswith("```"):
            response_text = re.sub(r'^```json?\n?', '', response_text)
            response_text = re.sub(r'\n?```$', '', response_text)
        
        result = json.loads(response_text)
        
        keep_refs = {item["ref"] for item in result.get("keep", [])}
        reject_list = [(item["ref"], item["reason"]) for item in result.get("reject", [])]
        
        all_candidates = {c.ref: c for c in priority_2 + priority_3}
        kept = []
        
        for ref in keep_refs:
            if ref in all_candidates:
                candidate = all_candidates[ref]
                candidate.claude_confidence = 1.0
                kept.append(candidate)
                logger.info(f"  ✓ KEEP: {ref}")
        
        for ref, reason in reject_list:
            logger.info(f"  ✗ REJECT: {ref} - {reason}")
        
        for c in priority_2:
            if c.ref not in keep_refs and c.ref not in {r[0] for r in reject_list}:
                kept.append(c)
                logger.info(f"  ✓ KEEP (P2 default): {c.ref}")
        
        logger.info(f"\n  Total kept: {len(kept)}")
        logger.info(f"  Total rejected: {len(reject_list)}")
        
        return kept, reject_list
        
    except json.JSONDecodeError as e:
        logger.error(f"  JSON parse error: {e}")
        rejected = [(c.ref, "JSON parse error") for c in priority_3]
        return priority_2, rejected
        
    except Exception as e:
        logger.error(f"  Claude review error: {e}")
        rejected = [(c.ref, str(e)) for c in priority_3]
        return priority_2, rejected


# =============================================================================
#  STEP 7: FETCH FINAL SOURCES
# =============================================================================

async def fetch_final_sources(
    priority_1: List[CandidateSource],
    kept_sources: List[CandidateSource],
    target_authors: List[str]
) -> List[Source]:
    """
    Fetch full text and commentaries for all kept sources.
    """
    logger.info("\n" + "=" * 70)
    logger.info("[PHASE 7] FETCHING FINAL SOURCES")
    logger.info(f"  Priority 1: {len(priority_1)}")
    logger.info(f"  Kept (P2/P3): {len(kept_sources)}")
    logger.info(f"  Target authors: {target_authors}")
    logger.info("=" * 70)
    
    all_candidates = priority_1 + kept_sources
    seen_refs = set()
    sources: List[Source] = []
    
    client = _get_sefaria_client()
    if not client:
        return sources
    
    for candidate in all_candidates:
        if candidate.ref in seen_refs:
            continue
        seen_refs.add(candidate.ref)
        
        try:
            # Fetch gemara if we don't have text
            if not candidate.hebrew_text:
                result = await client.get_text(candidate.ref)
                if result and hasattr(result, 'hebrew') and result.hebrew:
                    hebrew_text = result.hebrew
                    if isinstance(hebrew_text, list):
                        hebrew_text = " ".join(str(x) for x in hebrew_text if x)
                    candidate.hebrew_text = hebrew_text
            
            # Create main source
            sources.append(Source(
                ref=candidate.ref,
                he_ref=candidate.ref,
                level=SourceLevel.GEMARA_BAVLI,
                hebrew_text=candidate.hebrew_text,
                is_primary=True,
                priority=candidate.priority,
                source_origin=candidate.source_origin,
                validation_method=candidate.validation_method,
                citation_count=candidate.citation_count
            ))
            
            # Fetch commentaries
            for author in ['rashi', 'tosafot']:
                if not target_authors or author in [a.lower() for a in target_authors]:
                    try:
                        comm_ref = f"{author.title()} on {candidate.ref}"
                        comm_result = await client.get_text(comm_ref)
                        
                        if comm_result and hasattr(comm_result, 'hebrew') and comm_result.hebrew:
                            comm_text = comm_result.hebrew
                            if isinstance(comm_text, list):
                                comm_text = " ".join(str(x) for x in comm_text if x)
                            
                            sources.append(Source(
                                ref=comm_ref,
                                he_ref=comm_ref,
                                level=SourceLevel.RASHI if author == 'rashi' else SourceLevel.TOSFOS,
                                hebrew_text=comm_text,
                                author=author.title(),
                                priority=candidate.priority
                            ))
                    except:
                        pass
                        
        except Exception as e:
            logger.warning(f"  Error fetching {candidate.ref}: {e}")
    
    logger.info(f"  Total sources fetched: {len(sources)}")
    return sources


# =============================================================================
#  MAIN SEARCH FUNCTION (V17)
# =============================================================================

async def search(analysis: "QueryAnalysis") -> SearchResult:
    """
    V17 Search with Improved Trickle-Down Logic.
    
    KEY IMPROVEMENTS:
    1. Filters generic root words when specific phrases exist
    2. For comparison queries: Uses STRICT intersection on PRIMARY concepts
    3. Filters citations by Claude's target_masechtos
    4. Prioritizes sources mentioning multiple query concepts
    """
    logger.info("\n" + "=" * 70)
    logger.info("STEP 3: SEARCH [V16 - Improved Trickle-Down]")
    logger.info("=" * 70)
    logger.info(f"  Query: {analysis.original_query}")
    logger.info(f"  Topics: {analysis.search_topics_hebrew}")
    
    result = SearchResult(
        original_query=analysis.original_query,
        search_topics=analysis.search_topics_hebrew or [],
    )
    
    # =========================================================================
    # PHASE 1: Extract Claude's info
    # =========================================================================
    info = extract_claude_info(analysis)
    result.claude_picks = info["claude_picks"]
    
    # =========================================================================
    # PHASE 2: Run V16 improved search
    # =========================================================================
    corpus = None
    if LOCAL_CORPUS_AVAILABLE:
        try:
            corpus = LocalCorpus()
        except:
            pass
    
    candidates, daf_counts = await run_search(info, corpus)
    
    # =========================================================================
    # PHASE 3: Classify by proximity
    # =========================================================================
    priority_1, list_x = classify_by_proximity(candidates, info["claude_picks"])
    
    # =========================================================================
    # PHASE 4: Validate with trickle-up
    # =========================================================================
    priority_2, priority_3 = await validate_with_trickle_up(
        list_x, info["search_topics_hebrew"], corpus
    )
    
    # =========================================================================
    # PHASE 5: Word search on P3
    # =========================================================================
    promoted, remaining_p3 = await word_search_validation(
        priority_3, info["search_topics_hebrew"], info.get("synonyms", [])
    )
    priority_2.extend(promoted)
    priority_3 = remaining_p3
    
    # =========================================================================
    # PHASE 6: Claude review
    # =========================================================================
    kept, rejected = await claude_review(
        priority_2, priority_3,
        analysis.original_query,
        info["inyan_description"],
        info["search_topics_hebrew"]
    )
    
    result.rejected_refs = rejected
    
    # =========================================================================
    # PHASE 7: Fetch sources
    # =========================================================================
    sources = await fetch_final_sources(
        priority_1, kept, info["target_authors"]
    )
    
    # =========================================================================
    # Organize results
    # =========================================================================
    result.sources = sources
    result.total_sources = len(sources)
    
    # Group by level
    by_level: Dict[str, List[Source]] = defaultdict(list)
    for s in sources:
        by_level[s.level.hebrew].append(s)
    result.sources_by_level = dict(by_level)
    result.levels_found = list(by_level.keys())
    
    # Group by priority
    by_priority: Dict[int, List[Source]] = defaultdict(list)
    for s in sources:
        by_priority[s.priority.value].append(s)
    result.sources_by_priority = dict(by_priority)
    
    # Summary refs
    result.priority_1_refs = [c.ref for c in priority_1]
    result.priority_2_refs = [c.ref for c in kept if c.priority == Priority.P2]
    result.priority_3_refs = [c.ref for c in kept if c.priority == Priority.P3]
    
    result.search_description = (
        f"V17 Search: {len(priority_1)} Priority 1 (proximity), "
        f"{len(result.priority_2_refs)} Priority 2 (validated), "
        f"{len(result.priority_3_refs)} Priority 3 (Claude approved). "
        f"Rejected: {len(rejected)}. Total: {len(sources)} sources."
    )
    
    result.confidence = (
        ConfidenceLevel.HIGH if len(priority_1) >= 2 
        else ConfidenceLevel.MEDIUM if sources 
        else ConfidenceLevel.LOW
    )
    
    # Write output
    try:
        from source_output import SourceOutputWriter
        writer = SourceOutputWriter()
        writer.write_results(result, analysis.original_query, formats=["txt", "html"])
    except Exception as e:
        logger.warning(f"Could not write output: {e}")
    
    # =========================================================================
    # COMPREHENSIVE SUMMARY
    # =========================================================================
    logger.info("\n" + "=" * 80)
    logger.info("                         PIPELINE SUMMARY (V17)")
    logger.info("=" * 80)
    
    logger.info("\n[QUERY]")
    logger.info(f"  Original: {analysis.original_query}")
    logger.info(f"  Topics (Hebrew): {analysis.search_topics_hebrew}")
    logger.info(f"  Search method: {analysis.search_method}")
    logger.info(f"  Query type: {info.get('query_type', 'unknown')}")
    
    logger.info("\n[CLAUDE'S ANALYSIS]")
    logger.info(f"  Claude's picks: {result.claude_picks}")
    logger.info(f"  Target masechtos: {info.get('target_masechtos', [])}")
    logger.info(f"  Target authors: {info.get('target_authors', [])}")
    
    logger.info("\n[V17 TRICKLE-DOWN IMPROVEMENTS]")
    logger.info(f"  Filtered generic root words from topics")
    logger.info(f"  Searched for full phrases (not just root words)")
    is_comparison = info.get('query_type', '') in ('comparison', 'machlokes')
    if is_comparison:
        logger.info(f"  Used STRICT INTERSECTION for comparison query (V17)")
        logger.info(f"  Required BOTH primary concepts to match")
    if info.get('target_masechtos'):
        logger.info(f"  Filtered citations by target masechtos: {info['target_masechtos']}")
    
    logger.info("\n[PRIORITY CLASSIFICATION]")
    logger.info(f"  Priority 1 (Claude's picks + proximity): {len(result.priority_1_refs)}")
    for ref in result.priority_1_refs[:5]:
        logger.info(f"    ✓ {ref}")
    if len(result.priority_1_refs) > 5:
        logger.info(f"    ... and {len(result.priority_1_refs) - 5} more")
    
    logger.info(f"  Priority 2 (validated): {len(result.priority_2_refs)}")
    for ref in result.priority_2_refs[:5]:
        logger.info(f"    ✓ {ref}")
    
    logger.info(f"  Priority 3 (kept after review): {len(result.priority_3_refs)}")
    for ref in result.priority_3_refs[:3]:
        logger.info(f"    ? {ref}")
        
    logger.info(f"  Rejected: {len(rejected)}")
    for ref, reason in rejected[:3]:
        logger.info(f"    ✗ {ref}: {reason}")
    
    logger.info("\n[FINAL OUTPUT]")
    logger.info(f"  Total sources fetched: {len(sources)}")
    logger.info(f"  Sources with text: {sum(1 for s in sources if s.hebrew_text)}")
    logger.info(f"  Levels found: {result.levels_found}")
    
    # Check for overlap between trickle-down and Claude's picks
    p2_and_p3 = set(result.priority_2_refs + result.priority_3_refs)
    claude_adjacent = set()
    for cp in result.claude_picks:
        for other in p2_and_p3:
            if refs_in_proximity(cp, other, PROXIMITY_RADIUS):
                claude_adjacent.add(other)
    
    logger.info("\n[VALIDATION]")
    logger.info(f"  Trickle-down sources near Claude's picks: {len(claude_adjacent)}")
    if claude_adjacent:
        for ref in list(claude_adjacent)[:5]:
            logger.info(f"    ~ {ref}")
    else:
        logger.info("    (No overlap - consider checking search terms)")
    
    logger.info("\n" + "=" * 80)
    logger.info("                       END PIPELINE SUMMARY")
    logger.info("=" * 80 + "\n")
    
    return result


# Backwards compatibility
trickle_down_search_v17 = search
trickle_down_search_v16 = search
trickle_down_search_v15 = search
trickle_down_search_v14 = search
trickle_down_search_v13 = search


__all__ = [
    'search',
    'trickle_down_search_v17',
    'trickle_down_search_v16',
    'extract_claude_info',
    'run_search',
    'classify_by_proximity',
    'validate_with_trickle_up',
    'word_search_validation',
    'claude_review',
    'fetch_final_sources',
    'Source',
    'SourceLevel',
    'SearchResult',
    'CandidateSource',
    'Priority',
    'matches_target_masechtos',
    'text_contains_phrase',
    'count_topic_matches',
    '_filter_generic_roots',
]