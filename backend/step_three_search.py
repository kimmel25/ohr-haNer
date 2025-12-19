"""
Step 3: SEARCH - Fetch and Organize Sources
============================================

Takes QueryAnalysis from Step 2 and executes the search plan.

REALM-AWARE ARCHITECTURE:
- Each realm (Gemara, Chumash, Halacha, etc.) has its own search strategy
- Strategies share common infrastructure but handle realm-specific patterns
- Step 2's QueryAnalysis drives which strategy is used

KEY DISTINCTION:
1. FIND the sources on the INYAN (using search_topics)
2. FETCH the commentaries on those sources (using target_authors)
"""

import logging
import re
from abc import ABC, abstractmethod
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field

from models import ConfidenceLevel

if TYPE_CHECKING:
    from step_two_understand import QueryAnalysis, SearchMethod, Realm

try:
    from step_two_understand import QueryAnalysis, SearchMethod, Realm
except ImportError as e:
    logging.warning(f"Could not import from step_two_understand: {e}")

logger = logging.getLogger(__name__)


# ==============================================================================
#  HELPERS
# ==============================================================================

def _extract_hebrew_text(text_obj: Any) -> str:
    """Safely extract Hebrew text from a Sefaria text response."""
    if not text_obj:
        return ""
    hebrew = getattr(text_obj, 'hebrew', None)
    if hebrew:
        return hebrew if isinstance(hebrew, str) else str(hebrew)
    return ""


def _extract_he_ref(obj: Any, fallback: str) -> str:
    """Safely extract he_ref from an object with fallback."""
    return getattr(obj, 'he_ref', fallback) or fallback


def _get_ref_from_hit(hit: Any) -> Optional[str]:
    """Extract ref from a hit object (handles both object and dict)."""
    if hasattr(hit, 'ref'):
        return hit.ref
    if isinstance(hit, dict):
        return hit.get('ref')
    return None


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
        """Get Hebrew name for this level."""
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

# Ordered list for organizing results
TRICKLE_UP_ORDER: List[SourceLevel] = list(SourceLevel)

# Public alias for backward compatibility
LEVEL_HEBREW = _LEVEL_HEBREW


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

    @property
    def level_hebrew(self) -> str:
        """Get Hebrew name for source level."""
        return self.level.hebrew


@dataclass
class SearchResult:
    """Complete search result."""
    original_query: str
    search_topics: List[str]

    sources: List[Source] = field(default_factory=list)
    sources_by_level: Dict[str, List[Source]] = field(default_factory=dict)

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

def _get_sefaria_client():
    """Get Sefaria client instance (lazy import to avoid circular deps)."""
    from tools.sefaria_client import get_sefaria_client
    return get_sefaria_client()


async def search_sefaria(
    query: str,
    category_filter: Optional[List[str]] = None,
    book_filter: Optional[str] = None,
    size: int = 30
) -> List[Any]:
    """
    Search Sefaria for a topic/concept.

    Args:
        query: The topic/concept to search for
        category_filter: Optional list of categories to filter results
        book_filter: Optional specific book to filter results
        size: Maximum number of results to return

    Returns:
        List of search hits from Sefaria
    """
    search_filters = []
    if category_filter:
        search_filters.extend(category_filter)
    if book_filter:
        search_filters.append(book_filter)

    logger.debug(f"Searching Sefaria: query='{query}', filters={search_filters}, size={size}")

    try:
        client = _get_sefaria_client()
        results = await client.search(query, size=size, filters=search_filters)

        if results and results.hits:
            logger.debug(f"Found {len(results.hits)} hits for '{query}'")
            return results.hits

        logger.debug(f"No results found for '{query}'")
        return []

    except Exception as e:
        logger.error(f"Failed to search Sefaria for '{query}': {e}")
        return []


async def get_text(ref: str) -> Optional[Any]:
    """Fetch text content from Sefaria."""
    try:
        client = _get_sefaria_client()
        return await client.get_text(ref)
    except Exception as e:
        logger.error(f"Failed to fetch text '{ref}': {e}")
        return None


async def get_related(ref: str, with_text: bool = False) -> Optional[Any]:
    """Get related links/commentaries for a reference."""
    try:
        client = _get_sefaria_client()
        return await client.get_related(ref, with_text=with_text)
    except Exception as e:
        logger.error(f"Failed to get related for '{ref}': {e}")
        return None


# ==============================================================================
#  AUTHOR CONFIGURATION - Realm-aware
# ==============================================================================

@dataclass
class AuthorConfig:
    """Configuration for an author/meforesh."""
    name: str
    level: SourceLevel
    # Patterns by realm: {realm: [patterns]}
    # Pattern placeholders: {ref}, {book}, {chapter}, {verse}, {daf}, {siman}
    ref_patterns: Dict[str, List[str]] = field(default_factory=dict)
    aliases: List[str] = field(default_factory=list)


# Comprehensive author registry
AUTHOR_REGISTRY: Dict[str, AuthorConfig] = {
    # === RASHI ===
    "rashi": AuthorConfig(
        name="Rashi",
        level=SourceLevel.RASHI,
        ref_patterns={
            "chumash": ["Rashi on {ref}"],
            "gemara": ["Rashi on {ref}"],
            "nach": ["Rashi on {ref}"],
        },
        aliases=["rashi", 'רש"י', "reb shlomo yitzchaki"],
    ),
    # === TOSFOS ===
    "tosafot": AuthorConfig(
        name="Tosafot",
        level=SourceLevel.TOSFOS,
        ref_patterns={
            "gemara": ["Tosafot on {ref}"],
        },
        aliases=["tosafot", "tosfos", "תוספות"],
    ),
    # === CHUMASH MEFORSHIM ===
    "ramban_chumash": AuthorConfig(
        name="Ramban",
        level=SourceLevel.RISHONIM,
        ref_patterns={
            "chumash": ["Ramban on {ref}"],
        },
        aliases=["ramban", 'רמב"ן'],
    ),
    "ibn_ezra": AuthorConfig(
        name="Ibn Ezra",
        level=SourceLevel.RISHONIM,
        ref_patterns={
            "chumash": ["Ibn Ezra on {ref}"],
        },
        aliases=["ibn ezra", "אבן עזרא"],
    ),
    "sforno": AuthorConfig(
        name="Sforno",
        level=SourceLevel.RISHONIM,
        ref_patterns={
            "chumash": ["Sforno on {ref}"],
        },
        aliases=["sforno", "ספורנו"],
    ),
    "ohr_hachaim": AuthorConfig(
        name="Or HaChaim",
        level=SourceLevel.ACHARONIM,
        ref_patterns={
            "chumash": ["Or HaChaim on {ref}"],
        },
        aliases=["ohr hachaim", "or hachaim", "אור החיים"],
    ),
    # === GEMARA RISHONIM ===
    "ran": AuthorConfig(
        name="Ran",
        level=SourceLevel.RISHONIM,
        ref_patterns={
            # Ran al HaRif - note: uses Rif pagination, not Gemara
            "gemara": ["Ran on {ref}"],
        },
        aliases=["ran", 'ר"ן', "רן"],
    ),
    "rashba": AuthorConfig(
        name="Rashba",
        level=SourceLevel.RISHONIM,
        ref_patterns={
            "gemara": ["Rashba on {ref}", "Chiddushei HaRashba on {ref}"],
        },
        aliases=["rashba", 'רשב"א'],
    ),
    "ritva": AuthorConfig(
        name="Ritva",
        level=SourceLevel.RISHONIM,
        ref_patterns={
            "gemara": ["Ritva on {ref}", "Chiddushei HaRitva on {ref}"],
        },
        aliases=["ritva", 'ריטב"א'],
    ),
    "ramban_gemara": AuthorConfig(
        name="Ramban",
        level=SourceLevel.RISHONIM,
        ref_patterns={
            "gemara": ["Ramban on {ref}", "Chiddushei HaRamban on {ref}"],
        },
        aliases=["ramban", 'רמב"ן'],
    ),
    "rosh": AuthorConfig(
        name="Rosh",
        level=SourceLevel.RISHONIM,
        ref_patterns={
            "gemara": ["Rosh on {ref}"],
        },
        aliases=["rosh", 'רא"ש'],
    ),
    "meiri": AuthorConfig(
        name="Meiri",
        level=SourceLevel.RISHONIM,
        ref_patterns={
            "gemara": ["Meiri on {ref}"],
        },
        aliases=["meiri", "מאירי"],
    ),
    # === HALACHA ===
    "rambam": AuthorConfig(
        name="Rambam",
        level=SourceLevel.RAMBAM,
        ref_patterns={
            "halacha": ["Mishneh Torah, {ref}"],
        },
        aliases=["rambam", 'רמב"ם', "maimonides"],
    ),
    "mechaber": AuthorConfig(
        name="Shulchan Aruch",
        level=SourceLevel.SHULCHAN_ARUCH,
        ref_patterns={
            "halacha": ["Shulchan Arukh, {ref}"],
        },
        aliases=["mechaber", "shulchan aruch", "מחבר"],
    ),
    "rema": AuthorConfig(
        name="Rema",
        level=SourceLevel.SHULCHAN_ARUCH,
        ref_patterns={
            "halacha": ["Shulchan Arukh, {ref}"],  # Rema is in the SA text
        },
        aliases=["rema", 'רמ"א', "rama"],
    ),
    # === NOSEI KEILIM ===
    "mishnah_berurah": AuthorConfig(
        name="Mishnah Berurah",
        level=SourceLevel.NOSEI_KEILIM,
        ref_patterns={
            "halacha": ["Mishnah Berurah {ref}"],
        },
        aliases=["mishnah berurah", "mishna berura", "משנה ברורה"],
    ),
    "magen_avraham": AuthorConfig(
        name="Magen Avraham",
        level=SourceLevel.NOSEI_KEILIM,
        ref_patterns={
            "halacha": ["Magen Avraham on Shulchan Arukh, Orach Chaim {siman}"],
        },
        aliases=["magen avraham", "מגן אברהם"],
    ),
    # === ACHARONIM ===
    "maharsha": AuthorConfig(
        name="Maharsha",
        level=SourceLevel.ACHARONIM,
        ref_patterns={
            "gemara": ["Chidushei Agadot on {ref}", "Chidushei Halachot on {ref}"],
        },
        aliases=["maharsha", 'מהרש"א'],
    ),
}


def get_author_config(author_name: str, realm: str = "gemara") -> Optional[AuthorConfig]:
    """Get author config by name, considering realm for disambiguation."""
    author_lower = author_name.lower().strip()

    # Direct lookup
    if author_lower in AUTHOR_REGISTRY:
        return AUTHOR_REGISTRY[author_lower]

    # Check aliases
    for key, config in AUTHOR_REGISTRY.items():
        if author_lower in [a.lower() for a in config.aliases]:
            # For authors with realm-specific entries (like Ramban)
            if realm == "chumash" and "chumash" in key:
                return config
            elif realm == "gemara" and "gemara" in key:
                return config
            elif realm not in key:  # Generic match
                return config

    return None


def get_level_for_author(author_name: str) -> SourceLevel:
    """Get the SourceLevel for an author name."""
    config = get_author_config(author_name)
    return config.level if config else SourceLevel.RISHONIM


# ==============================================================================
#  ABSTRACT SEARCH STRATEGY (Strategy Pattern)
# ==============================================================================

class RealmSearchStrategy(ABC):
    """
    Abstract base for realm-specific search strategies.

    Each realm (Gemara, Chumash, Halacha, etc.) implements its own strategy
    for finding base sources and fetching commentaries.
    """

    @property
    @abstractmethod
    def realm_name(self) -> str:
        """Human-readable realm name."""
        pass

    @property
    @abstractmethod
    def sefaria_categories(self) -> List[str]:
        """Sefaria category filters for this realm."""
        pass

    @abstractmethod
    async def find_base_sources(
        self,
        analysis: "QueryAnalysis"
    ) -> Tuple[List[Source], List[str]]:
        """
        Find base sources where the INYAN is discussed.

        Returns:
            Tuple of (sources found, base refs for commentary fetching)
        """
        pass

    @abstractmethod
    async def fetch_commentaries(
        self,
        base_refs: List[str],
        analysis: "QueryAnalysis"
    ) -> List[Source]:
        """
        Fetch commentaries on the base sources.

        Args:
            base_refs: References to fetch commentaries on
            analysis: Query analysis with target authors

        Returns:
            List of commentary sources
        """
        pass

    def get_ref_pattern_for_author(
        self,
        author_name: str,
        base_ref: str
    ) -> List[str]:
        """
        Get Sefaria reference patterns for an author on a base ref.

        Can be overridden by subclasses for realm-specific patterns.
        """
        config = get_author_config(author_name, self.realm_name)
        if config and self.realm_name in config.ref_patterns:
            return [p.format(ref=base_ref) for p in config.ref_patterns[self.realm_name]]
        # Default pattern
        return [f"{author_name.title()} on {base_ref}"]

    async def _gather_and_dedupe_hits(
        self,
        search_terms: List[str],
        category_filter: Optional[List[str]] = None,
        book_filter: Optional[str] = None,
        size: int = 30
    ) -> List[Any]:
        """Gather and deduplicate search hits across all search terms."""
        combined = []
        for term in search_terms:
            combined.extend(await search_sefaria(
                term,
                category_filter=category_filter or self.sefaria_categories,
                book_filter=book_filter,
                size=size
            ))

        # Deduplicate by ref
        seen: Set[str] = set()
        out = []
        for hit in combined:
            ref = _get_ref_from_hit(hit)
            if ref and ref not in seen:
                seen.add(ref)
                out.append(hit)
        return out

    async def _fetch_and_create_source(
        self,
        ref: str,
        level: SourceLevel,
        relevance_desc: str,
        author: str = "",
        is_primary: bool = False
    ) -> Optional[Source]:
        """Fetch text and create Source if valid."""
        text = await get_text(ref)
        hebrew = _extract_hebrew_text(text)
        if not hebrew:
            return None

        return Source(
            ref=ref,
            he_ref=_extract_he_ref(text, ref),
            level=level,
            hebrew_text=hebrew,
            author=author,
            relevance_description=relevance_desc,
            is_primary=is_primary
        )


# ==============================================================================
#  GEMARA SEARCH STRATEGY
# ==============================================================================

class GemaraSearchStrategy(RealmSearchStrategy):
    """Search strategy for Gemara/Talmud queries."""

    @property
    def realm_name(self) -> str:
        return "gemara"

    @property
    def sefaria_categories(self) -> List[str]:
        return ["Bavli"]

    def _is_base_gemara_ref(self, ref: str) -> bool:
        """Check if this is a base Gemara ref (not a commentary)."""
        return " on " not in ref.lower() and bool(re.search(r'\d+[ab]', ref))

    def _to_daf_level(self, ref: str) -> str:
        """Convert line-level ref to daf-level: 'Pesachim 4b:5' -> 'Pesachim 4b'."""
        match = re.match(r'^([A-Za-z\s]+\d+[ab])(?::\d+)?$', ref.strip(), re.IGNORECASE)
        return match.group(1).strip() if match else ref

    def _extract_masechta_and_daf(self, ref: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract masechta and daf: 'Pesachim 4b:5' -> ('Pesachim', '4b')."""
        match = re.match(r'^([A-Za-z\s]+?)\s*(\d+[ab])(?::\d+)?$', ref.strip())
        if match:
            return match.group(1).strip(), match.group(2)
        return None, None

    async def find_base_sources(
        self,
        analysis: "QueryAnalysis"
    ) -> Tuple[List[Source], List[str]]:
        """Find Gemara sugyos discussing the inyan."""
        sources: List[Source] = []
        base_refs: List[str] = []
        found_refs: Set[str] = set()

        search_terms = analysis.search_topics_hebrew or analysis.search_topics
        if not search_terms:
            logger.warning("No search topics for Gemara search")
            return [], []

        display_inyan = " / ".join(search_terms)
        logger.info(f"[Gemara] Finding base sources for '{display_inyan}'")

        # Search psukim if requested
        if analysis.source_categories.psukim:
            hits = await self._gather_and_dedupe_hits(search_terms, ["Tanakh"])
            for hit in hits[:5]:
                ref = _get_ref_from_hit(hit)
                if ref and ref not in found_refs:
                    source = await self._fetch_and_create_source(
                        ref, SourceLevel.PASUK, f"פסוק העוסק ב{display_inyan}"
                    )
                    if source:
                        found_refs.add(ref)
                        sources.append(source)

        # Search mishnayos if requested
        if analysis.source_categories.mishnayos:
            hits = await self._gather_and_dedupe_hits(search_terms, ["Mishnah"])
            for hit in hits[:5]:
                ref = _get_ref_from_hit(hit)
                if ref and ref not in found_refs:
                    source = await self._fetch_and_create_source(
                        ref, SourceLevel.MISHNA, f"משנה העוסקת ב{display_inyan}"
                    )
                    if source:
                        found_refs.add(ref)
                        sources.append(source)

        # Search Gemara Bavli (PRIMARY)
        if analysis.source_categories.gemara_bavli:
            masechtos = analysis.target_masechtos or [None]

            for masechta in masechtos:
                hits = await self._gather_and_dedupe_hits(
                    search_terms,
                    self.sefaria_categories,
                    book_filter=masechta,
                    size=30
                )

                for hit in hits[:10]:
                    ref = _get_ref_from_hit(hit)
                    if ref and self._is_base_gemara_ref(ref) and ref not in found_refs:
                        source = await self._fetch_and_create_source(
                            ref, SourceLevel.GEMARA_BAVLI,
                            f"גמרא העוסקת ב{display_inyan}",
                            is_primary=True
                        )
                        if source:
                            found_refs.add(ref)
                            sources.append(source)
                            base_refs.append(ref)
                            logger.debug(f"  Added base gemara: {ref}")

            if base_refs:
                logger.info(f"  Found {len(base_refs)} gemara sugyos")

        logger.info(f"[Gemara] Phase 1 complete: {len(sources)} sources, {len(base_refs)} base refs")
        return sources, base_refs

    async def fetch_commentaries(
        self,
        base_refs: List[str],
        analysis: "QueryAnalysis"
    ) -> List[Source]:
        """Fetch Gemara meforshim (Rashi, Tosfos, Rishonim, etc.)."""
        if not base_refs:
            return []

        logger.info(f"[Gemara] Fetching commentaries on {len(base_refs)} refs")

        sources: List[Source] = []
        found_refs: Set[str] = set()

        # Build target author set
        target_authors = self._build_target_authors(analysis)
        if target_authors:
            logger.debug(f"  Target authors: {sorted(target_authors)}")

        # Discovery-based fetch via related API
        for base_ref in base_refs[:5]:
            daf_ref = self._to_daf_level(base_ref)

            try:
                related = await get_related(daf_ref, with_text=True)
                if not related or not getattr(related, 'commentaries', None):
                    continue

                for comm in related.commentaries:
                    author = self._extract_author_from_ref(comm.ref)
                    if not author:
                        continue

                    # Filter by target authors
                    if target_authors and author.lower() not in target_authors:
                        continue

                    if comm.ref in found_refs:
                        continue

                    source = await self._fetch_and_create_source(
                        comm.ref,
                        get_level_for_author(author),
                        f"{author} על {daf_ref}",
                        author=author
                    )
                    if source:
                        found_refs.add(comm.ref)
                        sources.append(source)
                        logger.debug(f"    Added {author}: {comm.ref}")

            except Exception as e:
                logger.error(f"Error fetching commentaries for {base_ref}: {e}")

        # Explicit fetch for missing authors
        found_authors = {s.author.lower() for s in sources if s.author}
        missing = [a for a in analysis.target_authors if a.lower() not in found_authors]

        if missing:
            logger.info(f"  Missing authors: {missing}, attempting explicit fetch")
            for author in missing:
                for base_ref in base_refs[:5]:
                    patterns = self.get_ref_pattern_for_author(author, self._to_daf_level(base_ref))
                    for ref_try in patterns:
                        if ref_try in found_refs:
                            continue
                        source = await self._fetch_and_create_source(
                            ref_try,
                            get_level_for_author(author),
                            f"{author} על {base_ref}",
                            author=author
                        )
                        if source:
                            found_refs.add(ref_try)
                            sources.append(source)
                            break
                    if any(s.author.lower() == author.lower() for s in sources):
                        break

        # Sort by level
        level_priority = {
            SourceLevel.RASHI: 1,
            SourceLevel.TOSFOS: 2,
            SourceLevel.RISHONIM: 3,
            SourceLevel.ACHARONIM: 4,
        }
        sources.sort(key=lambda s: level_priority.get(s.level, 99))

        logger.info(f"[Gemara] Phase 2 complete: {len(sources)} commentaries")
        return sources

    def _build_target_authors(self, analysis: "QueryAnalysis") -> Set[str]:
        """Build normalized set of target authors."""
        authors: Set[str] = set()

        for a in analysis.target_authors:
            authors.add(a.lower())
            if a.lower() == "tosfos":
                authors.add("tosafot")
            elif a.lower() == "tosafot":
                authors.add("tosfos")

        if analysis.source_categories.rashi:
            authors.add("rashi")
        if analysis.source_categories.tosfos:
            authors.update(["tosafot", "tosfos"])
        if analysis.source_categories.rishonim:
            authors.update(["ran", "rashba", "ritva", "ramban", "rosh", "meiri"])

        return authors

    def _extract_author_from_ref(self, ref: str) -> Optional[str]:
        """Extract author name: 'Rashi on Pesachim 4b:1' -> 'Rashi'."""
        match = re.match(r'^(.+?)\s+on\s+', ref, re.IGNORECASE)
        return match.group(1).strip() if match else None


# ==============================================================================
#  CHUMASH SEARCH STRATEGY
# ==============================================================================

class ChumashSearchStrategy(RealmSearchStrategy):
    """Search strategy for Chumash/Torah queries."""

    @property
    def realm_name(self) -> str:
        return "chumash"

    @property
    def sefaria_categories(self) -> List[str]:
        return ["Tanakh", "Torah"]

    # Standard Chumash meforshim in display order
    MEFORSHIM_ORDER = ["Rashi", "Ramban", "Ibn Ezra", "Sforno", "Or HaChaim", "Kli Yakar"]

    async def find_base_sources(
        self,
        analysis: "QueryAnalysis"
    ) -> Tuple[List[Source], List[str]]:
        """Find pesukim discussing the topic."""
        sources: List[Source] = []
        base_refs: List[str] = []
        found_refs: Set[str] = set()

        search_terms = analysis.search_topics_hebrew or analysis.search_topics
        if not search_terms:
            logger.warning("No search topics for Chumash search")
            return [], []

        display_inyan = " / ".join(search_terms)
        logger.info(f"[Chumash] Finding pesukim for '{display_inyan}'")

        # If specific refs provided, use them directly
        if analysis.target_refs:
            for ref in analysis.target_refs:
                if ref not in found_refs:
                    source = await self._fetch_and_create_source(
                        ref, SourceLevel.PASUK, f"פסוק: {ref}", is_primary=True
                    )
                    if source:
                        found_refs.add(ref)
                        sources.append(source)
                        base_refs.append(ref)

        # Search by topic
        hits = await self._gather_and_dedupe_hits(search_terms, self.sefaria_categories)

        for hit in hits[:10]:
            ref = _get_ref_from_hit(hit)
            if ref and ref not in found_refs and " on " not in ref.lower():
                source = await self._fetch_and_create_source(
                    ref, SourceLevel.PASUK, f"פסוק העוסק ב{display_inyan}", is_primary=True
                )
                if source:
                    found_refs.add(ref)
                    sources.append(source)
                    base_refs.append(ref)
                    logger.debug(f"  Added pasuk: {ref}")

        logger.info(f"[Chumash] Found {len(base_refs)} pesukim")
        return sources, base_refs

    async def fetch_commentaries(
        self,
        base_refs: List[str],
        analysis: "QueryAnalysis"
    ) -> List[Source]:
        """Fetch Chumash meforshim (Rashi, Ramban, Ibn Ezra, etc.)."""
        if not base_refs:
            return []

        logger.info(f"[Chumash] Fetching meforshim on {len(base_refs)} pesukim")

        sources: List[Source] = []
        found_refs: Set[str] = set()

        # Determine which meforshim to fetch
        target_authors = set(a.lower() for a in analysis.target_authors) if analysis.target_authors else None
        meforshim_to_fetch = (
            [a for a in self.MEFORSHIM_ORDER if a.lower() in target_authors]
            if target_authors
            else self.MEFORSHIM_ORDER[:4]  # Default: top 4
        )

        for base_ref in base_refs[:5]:
            # Use related API for discovery
            try:
                related = await get_related(base_ref, with_text=True)
                if related and getattr(related, 'commentaries', None):
                    for comm in related.commentaries:
                        author = self._extract_author_from_ref(comm.ref)
                        if not author:
                            continue

                        # Filter by target
                        if target_authors and author.lower() not in target_authors:
                            continue

                        if comm.ref in found_refs:
                            continue

                        source = await self._fetch_and_create_source(
                            comm.ref,
                            get_level_for_author(author),
                            f"{author} על {base_ref}",
                            author=author
                        )
                        if source:
                            found_refs.add(comm.ref)
                            sources.append(source)
            except Exception as e:
                logger.debug(f"Related API failed for {base_ref}: {e}")

            # Explicit fetch for standard meforshim
            for meforesh in meforshim_to_fetch:
                patterns = self.get_ref_pattern_for_author(meforesh, base_ref)
                for pattern in patterns:
                    if pattern in found_refs:
                        continue
                    source = await self._fetch_and_create_source(
                        pattern,
                        get_level_for_author(meforesh),
                        f"{meforesh} על {base_ref}",
                        author=meforesh
                    )
                    if source:
                        found_refs.add(pattern)
                        sources.append(source)
                        break

        logger.info(f"[Chumash] Fetched {len(sources)} commentaries")
        return sources

    def _extract_author_from_ref(self, ref: str) -> Optional[str]:
        """Extract author: 'Rashi on Genesis 1:1' -> 'Rashi'."""
        match = re.match(r'^(.+?)\s+on\s+', ref, re.IGNORECASE)
        return match.group(1).strip() if match else None


# ==============================================================================
#  HALACHA SEARCH STRATEGY
# ==============================================================================

class HalachaSearchStrategy(RealmSearchStrategy):
    """Search strategy for Halacha queries (Shulchan Aruch, Rambam, etc.)."""

    @property
    def realm_name(self) -> str:
        return "halacha"

    @property
    def sefaria_categories(self) -> List[str]:
        return ["Halakhah"]

    async def find_base_sources(
        self,
        analysis: "QueryAnalysis"
    ) -> Tuple[List[Source], List[str]]:
        """Find halacha sources (Shulchan Aruch, Rambam, etc.)."""
        sources: List[Source] = []
        base_refs: List[str] = []
        found_refs: Set[str] = set()

        search_terms = analysis.search_topics_hebrew or analysis.search_topics
        if not search_terms:
            logger.warning("No search topics for Halacha search")
            return [], []

        display_inyan = " / ".join(search_terms)
        logger.info(f"[Halacha] Finding sources for '{display_inyan}'")

        # Search halachic literature
        hits = await self._gather_and_dedupe_hits(search_terms, self.sefaria_categories)

        for hit in hits[:15]:
            ref = _get_ref_from_hit(hit)
            if not ref or ref in found_refs:
                continue

            # Determine level from ref
            ref_lower = ref.lower()
            if "shulchan" in ref_lower:
                level = SourceLevel.SHULCHAN_ARUCH
            elif "tur" in ref_lower:
                level = SourceLevel.TUR
            elif "rambam" in ref_lower or "mishneh torah" in ref_lower:
                level = SourceLevel.RAMBAM
            else:
                level = SourceLevel.ACHARONIM

            source = await self._fetch_and_create_source(
                ref, level, f"הלכה על {display_inyan}", is_primary=True
            )
            if source:
                found_refs.add(ref)
                sources.append(source)
                base_refs.append(ref)

        logger.info(f"[Halacha] Found {len(base_refs)} halacha sources")
        return sources, base_refs

    async def fetch_commentaries(
        self,
        base_refs: List[str],
        analysis: "QueryAnalysis"
    ) -> List[Source]:
        """Fetch nosei keilim and trace back to Gemara sources."""
        if not base_refs:
            return []

        logger.info(f"[Halacha] Fetching nosei keilim and tracing sources")

        sources: List[Source] = []
        found_refs: Set[str] = set()
        cited_refs: Set[str] = set()

        # Get related/linked sources
        for ref in base_refs[:10]:
            try:
                related = await get_related(ref, with_text=True)
                if related:
                    # Get commentaries (nosei keilim)
                    if getattr(related, 'commentaries', None):
                        for comm in related.commentaries[:5]:
                            if comm.ref not in found_refs:
                                author = self._extract_author_from_ref(comm.ref)
                                source = await self._fetch_and_create_source(
                                    comm.ref,
                                    SourceLevel.NOSEI_KEILIM,
                                    f"נושא כלים על {ref}",
                                    author=author or ""
                                )
                                if source:
                                    found_refs.add(comm.ref)
                                    sources.append(source)

                    # Collect citations for tracing back
                    if getattr(related, 'links', None):
                        for link in related.links[:10]:
                            if hasattr(link, 'ref'):
                                cited_refs.add(link.ref)
            except Exception as e:
                logger.debug(f"Error getting related for {ref}: {e}")

        # Trace back to Gemara sources
        for ref in list(cited_refs)[:15]:
            if ref in found_refs:
                continue

            ref_lower = ref.lower()
            # Check if it's a Gemara ref
            if " on " not in ref_lower and re.search(r'\d+[ab]', ref):
                source = await self._fetch_and_create_source(
                    ref, SourceLevel.GEMARA_BAVLI, "מקור בגמרא", is_primary=True
                )
                if source:
                    found_refs.add(ref)
                    sources.append(source)

        logger.info(f"[Halacha] Fetched {len(sources)} related sources")
        return sources

    def _extract_author_from_ref(self, ref: str) -> Optional[str]:
        """Extract author from halacha commentary ref."""
        # Common patterns for nosei keilim
        patterns = [
            r'^(Mishnah Berurah)',
            r'^(Magen Avraham)',
            r'^(Taz)',
            r'^(Shach)',
            r'^(Beur Halacha)',
        ]
        for pattern in patterns:
            match = re.match(pattern, ref, re.IGNORECASE)
            if match:
                return match.group(1)
        return None


# ==============================================================================
#  GENERIC/FALLBACK STRATEGY
# ==============================================================================

class GenericSearchStrategy(RealmSearchStrategy):
    """Fallback strategy for unknown or general queries."""

    @property
    def realm_name(self) -> str:
        return "general"

    @property
    def sefaria_categories(self) -> List[str]:
        return []  # No filter = search everything

    async def find_base_sources(
        self,
        analysis: "QueryAnalysis"
    ) -> Tuple[List[Source], List[str]]:
        """Search across all categories."""
        sources: List[Source] = []
        base_refs: List[str] = []
        found_refs: Set[str] = set()

        search_terms = analysis.search_topics_hebrew or analysis.search_topics
        if not search_terms:
            return [], []

        display_inyan = " / ".join(search_terms)
        logger.info(f"[Generic] Searching for '{display_inyan}'")

        # If specific refs provided, fetch them
        if analysis.target_refs:
            for ref in analysis.target_refs:
                source = await self._fetch_and_create_source(
                    ref, SourceLevel.RISHONIM, f"מקור: {ref}", is_primary=True
                )
                if source:
                    found_refs.add(ref)
                    sources.append(source)
                    base_refs.append(ref)

        # General search
        hits = await self._gather_and_dedupe_hits(search_terms, None, size=20)

        for hit in hits[:15]:
            ref = _get_ref_from_hit(hit)
            if ref and ref not in found_refs:
                level = self._guess_level_from_ref(ref)
                source = await self._fetch_and_create_source(
                    ref, level, f"מקור על {display_inyan}"
                )
                if source:
                    found_refs.add(ref)
                    sources.append(source)
                    base_refs.append(ref)

        return sources, base_refs

    async def fetch_commentaries(
        self,
        base_refs: List[str],
        analysis: "QueryAnalysis"
    ) -> List[Source]:
        """Try to fetch commentaries using related API."""
        sources: List[Source] = []
        found_refs: Set[str] = set()

        for ref in base_refs[:5]:
            try:
                related = await get_related(ref, with_text=True)
                if related and getattr(related, 'commentaries', None):
                    for comm in related.commentaries[:5]:
                        if comm.ref not in found_refs:
                            source = await self._fetch_and_create_source(
                                comm.ref,
                                SourceLevel.RISHONIM,
                                f"פירוש על {ref}"
                            )
                            if source:
                                found_refs.add(comm.ref)
                                sources.append(source)
            except Exception:
                pass

        return sources

    def _guess_level_from_ref(self, ref: str) -> SourceLevel:
        """Guess source level from reference string."""
        ref_lower = ref.lower()
        if any(book in ref_lower for book in ["genesis", "exodus", "leviticus", "numbers", "deuteronomy", "bereishit", "shemot"]):
            return SourceLevel.PASUK
        if "mishnah" in ref_lower or "mishna" in ref_lower:
            return SourceLevel.MISHNA
        if re.search(r'\d+[ab]', ref) and " on " not in ref_lower:
            return SourceLevel.GEMARA_BAVLI
        if "rashi" in ref_lower:
            return SourceLevel.RASHI
        if "shulchan" in ref_lower:
            return SourceLevel.SHULCHAN_ARUCH
        return SourceLevel.RISHONIM


# ==============================================================================
#  STRATEGY FACTORY
# ==============================================================================

def get_search_strategy(realm: "Realm") -> RealmSearchStrategy:
    """
    Factory function to get the appropriate search strategy for a realm.

    Follows Open/Closed principle - add new strategies without modifying existing code.
    """
    from step_two_understand import Realm

    strategies: Dict[Realm, RealmSearchStrategy] = {
        Realm.GEMARA: GemaraSearchStrategy(),
        Realm.YERUSHALMI: GemaraSearchStrategy(),  # Similar enough
        Realm.CHUMASH: ChumashSearchStrategy(),
        Realm.MISHNAH: GemaraSearchStrategy(),  # Uses similar patterns
        Realm.HALACHA: HalachaSearchStrategy(),
        Realm.TANNAIC: GemaraSearchStrategy(),
        Realm.GENERAL: GenericSearchStrategy(),
        Realm.UNKNOWN: GenericSearchStrategy(),
    }

    strategy = strategies.get(realm, GenericSearchStrategy())
    logger.debug(f"Selected {strategy.__class__.__name__} for realm {realm}")
    return strategy


# ==============================================================================
#  TRICKLE UP/DOWN/HYBRID SEARCH
# ==============================================================================

async def trickle_up_search(analysis: "QueryAnalysis") -> List[Source]:
    """
    TRICKLE UP: Find base sources, then layer commentaries on top.

    Strategy selection is based on realm from Step 2.
    """
    logger.info("=" * 50)
    logger.info("Starting TRICKLE-UP search")
    logger.info("=" * 50)

    strategy = get_search_strategy(analysis.realm)

    base_sources, base_refs = await strategy.find_base_sources(analysis)
    commentary_sources = await strategy.fetch_commentaries(base_refs, analysis)

    all_sources = base_sources + commentary_sources
    logger.info(f"Trickle-up complete: {len(all_sources)} total sources")
    return all_sources


async def trickle_down_search(analysis: "QueryAnalysis") -> List[Source]:
    """
    TRICKLE DOWN: Start from later sources, trace citations back.

    Always uses HalachaSearchStrategy as starting point, then traces back.
    """
    logger.info("=" * 50)
    logger.info("Starting TRICKLE-DOWN search")
    logger.info("=" * 50)

    # Start with halacha sources
    halacha_strategy = HalachaSearchStrategy()

    sources: List[Source] = []
    found_refs: Set[str] = set()

    # Find halacha sources
    halacha_sources, halacha_refs = await halacha_strategy.find_base_sources(analysis)
    sources.extend(halacha_sources)
    found_refs.update(s.ref for s in halacha_sources)

    # Fetch nosei keilim and trace back
    traced_sources = await halacha_strategy.fetch_commentaries(halacha_refs, analysis)
    for s in traced_sources:
        if s.ref not in found_refs:
            found_refs.add(s.ref)
            sources.append(s)

    logger.info(f"Trickle-down complete: {len(sources)} sources")
    return sources


async def hybrid_search(analysis: "QueryAnalysis") -> List[Source]:
    """
    Run both trickle-up and trickle-down, combine and mark overlaps.
    """
    logger.info("=" * 50)
    logger.info("Starting HYBRID search")
    logger.info("=" * 50)

    up_sources = await trickle_up_search(analysis)
    down_sources = await trickle_down_search(analysis)

    up_refs = {s.ref for s in up_sources}
    down_refs = {s.ref for s in down_sources}
    common = up_refs & down_refs

    # Combine and deduplicate
    all_sources: List[Source] = []
    seen: Set[str] = set()

    for source in up_sources + down_sources:
        if source.ref in seen:
            continue
        seen.add(source.ref)

        if source.ref in common:
            source.is_primary = True
            source.relevance_description += " (נמצא בשתי שיטות החיפוש)"

        all_sources.append(source)

    logger.info(f"Hybrid complete: {len(all_sources)} sources ({len(common)} overlap)")
    return all_sources


async def direct_search(analysis: "QueryAnalysis") -> List[Source]:
    """
    DIRECT: Go straight to specific refs provided in analysis.
    """
    logger.info("=" * 50)
    logger.info("Starting DIRECT search")
    logger.info("=" * 50)

    sources: List[Source] = []

    # Use target_refs if provided
    refs_to_fetch = analysis.target_refs or []

    # Also construct refs from target_sefarim + other location info
    if analysis.target_sefarim:
        for sefer in analysis.target_sefarim:
            if analysis.target_simanim:
                for siman in analysis.target_simanim:
                    refs_to_fetch.append(f"{sefer} {siman}")
            elif analysis.target_perakim:
                for perek in analysis.target_perakim:
                    refs_to_fetch.append(f"{sefer} {perek}")

    strategy = get_search_strategy(analysis.realm)

    for ref in refs_to_fetch:
        source = await strategy._fetch_and_create_source(
            ref, SourceLevel.RISHONIM, f"מקור: {ref}", is_primary=True
        )
        if source:
            sources.append(source)

    # Also fetch commentaries if authors specified
    if sources and analysis.target_authors:
        base_refs = [s.ref for s in sources]
        commentaries = await strategy.fetch_commentaries(base_refs, analysis)
        sources.extend(commentaries)

    logger.info(f"Direct search complete: {len(sources)} sources")
    return sources


# ==============================================================================
#  ORGANIZE & DESCRIBE
# ==============================================================================

def organize_sources(sources: List[Source]) -> Tuple[List[Source], Dict[str, List[Source]]]:
    """Organize sources in trickle-up order."""
    level_order = {level: i for i, level in enumerate(TRICKLE_UP_ORDER)}

    sorted_sources = sorted(
        sources,
        key=lambda s: (level_order.get(s.level, 99), not s.is_primary)
    )

    by_level: Dict[str, List[Source]] = {}
    for source in sorted_sources:
        level_name = source.level_hebrew
        if level_name not in by_level:
            by_level[level_name] = []
        by_level[level_name].append(source)

    return sorted_sources, by_level


def generate_description(analysis: "QueryAnalysis", sources: List[Source], base_refs: List[str]) -> str:
    """Generate human-readable search description."""
    parts = []

    inyan = " ".join(analysis.search_topics_hebrew or analysis.search_topics or [])
    parts.append(f"חיפוש עבור: {inyan}")
    parts.append(f"תחום: {analysis.realm.value}")

    if analysis.target_masechtos:
        parts.append(f"במסכתות: {', '.join(analysis.target_masechtos)}")
    if analysis.target_sefarim:
        parts.append(f"בספרים: {', '.join(analysis.target_sefarim)}")
    if base_refs:
        parts.append(f"נמצאו מקורות ב: {', '.join(base_refs[:3])}")
    if analysis.target_authors:
        parts.append(f"הובאו פירושי: {', '.join(analysis.target_authors)}")

    parts.append(f'סה"כ {len(sources)} מקורות')

    return "\n".join(parts)


# ==============================================================================
#  MAIN ENTRY POINT
# ==============================================================================

async def search(analysis: "QueryAnalysis", **kwargs) -> SearchResult:
    """
    Step 3: SEARCH - Execute the search plan from Step 2.

    Dispatches to appropriate search method based on analysis.search_method,
    using realm-aware strategies.
    """
    logger.info("=" * 60)
    logger.info("STEP 3: SEARCH - Executing search plan")
    logger.info(f"  Query: {analysis.original_query}")
    logger.info(f"  Realm: {analysis.realm.value}")
    logger.info(f"  Topics: {analysis.search_topics_hebrew}")
    logger.info(f"  Method: {analysis.search_method.value}")
    if analysis.target_masechtos:
        logger.info(f"  Masechtos: {analysis.target_masechtos}")
    if analysis.target_sefarim:
        logger.info(f"  Sefarim: {analysis.target_sefarim}")
    if analysis.target_authors:
        logger.info(f"  Authors: {analysis.target_authors}")
    logger.info("=" * 60)

    # Dispatch based on search method
    from step_two_understand import SearchMethod

    if analysis.search_method == SearchMethod.TRICKLE_UP:
        sources = await trickle_up_search(analysis)
    elif analysis.search_method == SearchMethod.TRICKLE_DOWN:
        sources = await trickle_down_search(analysis)
    elif analysis.search_method == SearchMethod.HYBRID:
        sources = await hybrid_search(analysis)
    elif analysis.search_method == SearchMethod.DIRECT:
        sources = await direct_search(analysis)
    else:
        logger.warning(f"Unknown method '{analysis.search_method}', using trickle-up")
        sources = await trickle_up_search(analysis)

    # Organize results
    sorted_sources, by_level = organize_sources(sources)

    # Get base refs for description (realm-aware)
    base_refs = [s.ref for s in sources if s.is_primary][:5]
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

    # Generate output files if available
    try:
        from source_output import write_source_output
        output_files = write_source_output(
            result,
            query=analysis.original_query,
            output_dir="output",
            formats=["txt", "html"]
        )
        if output_files:
            logger.debug(f"Generated output files: {list(output_files.keys())}")
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"Could not generate output files: {e}")

    logger.info("=" * 60)
    logger.info(f"STEP 3 COMPLETE: {result.total_sources} sources across {len(by_level)} levels")
    logger.info("=" * 60)

    return result


# Alias for backward compatibility
run_step_three = search


# ==============================================================================
#  TESTING
# ==============================================================================

async def _test_step_three():
    """Test Step 3 with various realms."""
    from step_two_understand import (
        QueryAnalysis, SearchMethod, QueryType, Breadth, Realm, SourceCategories
    )

    print("=" * 60)
    print("STEP 3 TEST: SEARCH")
    print("=" * 60)

    # Test 1: Gemara query
    print("\n--- Test 1: Gemara Query ---")
    analysis = QueryAnalysis(
        original_query="what is the ran's shittah in bittul chometz",
        hebrew_terms_from_step1=["רן", "ביטול חמץ"],
        query_type=QueryType.SHITTAH,
        realm=Realm.GEMARA,
        breadth=Breadth.STANDARD,
        search_method=SearchMethod.TRICKLE_UP,
        search_topics=["bittul chometz"],
        search_topics_hebrew=["ביטול חמץ"],
        target_masechtos=["Pesachim"],
        target_authors=["Ran", "Rashi"],
        source_categories=SourceCategories(gemara_bavli=True, rashi=True),
        confidence=ConfidenceLevel.HIGH,
    )

    result = await search(analysis)
    print(f"  Total sources: {result.total_sources}")
    print(f"  Levels: {result.levels_found}")

    # Test 2: Chumash query
    print("\n--- Test 2: Chumash Query ---")
    analysis2 = QueryAnalysis(
        original_query="explain rashi on bereishis 1:1",
        hebrew_terms_from_step1=["רש\"י", "בראשית"],
        query_type=QueryType.PASUK,
        realm=Realm.CHUMASH,
        breadth=Breadth.NARROW,
        search_method=SearchMethod.DIRECT,
        search_topics=["creation", "bereishis"],
        search_topics_hebrew=["בריאה", "בראשית"],
        target_refs=["Genesis 1:1"],
        target_authors=["Rashi", "Ramban"],
        source_categories=SourceCategories(psukim=True, rashi=True),
        confidence=ConfidenceLevel.HIGH,
    )

    result2 = await search(analysis2)
    print(f"  Total sources: {result2.total_sources}")
    print(f"  Levels: {result2.levels_found}")


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
    )
    asyncio.run(_test_step_three())
