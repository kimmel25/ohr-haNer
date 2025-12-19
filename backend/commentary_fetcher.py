"""
Commentary Fetcher - SOLID Architecture
========================================

Discovers and fetches commentaries using Sefaria's Related API.

SOLID Principles Applied:
- Single Responsibility: Each class has one job
- Open/Closed: Extensible via strategies, not modification
- Liskov Substitution: Filter strategies are interchangeable
- Interface Segregation: Small, focused interfaces
- Dependency Inversion: Depends on abstractions (protocols)

Architecture:
    CommentaryFetcher (orchestrator)
    ├── AuthorRegistry (knows authors and their mappings)
    ├── RefNormalizer (handles ref format conversions)
    ├── CommentaryDiscoverer (uses get_related to find what exists)
    └── AuthorFilter (strategy for filtering results)
"""

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import (
    Dict, List, Optional, Set, Tuple, 
    Protocol, runtime_checkable, FrozenSet
)
from enum import Enum, auto

logger = logging.getLogger(__name__)


# =============================================================================
# SOURCE LEVELS (Shared with step_three_search.py)
# =============================================================================

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


# =============================================================================
# VALUE OBJECTS (Immutable Data)
# =============================================================================

@dataclass(frozen=True)
class AuthorIdentity:
    """
    Immutable identification of a Torah commentator.
    
    Maps between various representations:
    - User input: "Ran", "the Ran", "R' Nissim"
    - Sefaria prefix: "Ran on"
    - Display name: "הר"ן"
    """
    canonical_name: str          # "Ran"
    sefaria_prefix: str          # "Ran on"
    hebrew_name: str             # "הר״ן"
    level: str                   # SourceLevel constant
    aliases: FrozenSet[str]      # {"ran", "r' nissim", "rabbeinu nissim"}
    
    def matches(self, name: str) -> bool:
        """Check if a name matches this author."""
        name_lower = name.lower().strip()
        return (
            name_lower == self.canonical_name.lower() or
            name_lower in self.aliases
        )


@dataclass(frozen=True)
class DiscoveredCommentary:
    """A commentary discovered via the Related API."""
    ref: str                     # "Rashi on Pesachim 4b:3"
    he_ref: str                  # Hebrew ref
    author_name: str             # "Rashi"
    base_ref: str                # "Pesachim 4b:3" (what it comments on)
    level: str                   # SourceLevel
    text_preview: str = ""       # Preview snippet from related API
    category: str = ""           # Sefaria category


@dataclass
class FetchedCommentary:
    """A fully fetched commentary with text content."""
    ref: str
    he_ref: str
    author: str
    level: str
    level_hebrew: str
    hebrew_text: str
    english_text: str = ""
    base_ref: str = ""
    categories: List[str] = field(default_factory=list)


# =============================================================================
# PROTOCOLS (Dependency Inversion)
# =============================================================================

@runtime_checkable
class ISefariaClient(Protocol):
    """Interface for Sefaria API operations."""
    
    async def get_related(self, ref: str, with_text: bool = True) -> any:
        """Get related content (commentaries, links) for a ref."""
        ...
    
    async def get_text(self, ref: str) -> Optional[any]:
        """Fetch the text content for a ref."""
        ...


# =============================================================================
# AUTHOR REGISTRY (Single Responsibility: Author Knowledge)
# =============================================================================

class AuthorRegistry:
    """
    Registry of Torah commentators and their Sefaria mappings.
    
    Single Responsibility: Knows about authors and how to identify them.
    Open/Closed: Add new authors without modifying existing code.
    """
    
    # Class-level registry
    _authors: Dict[str, AuthorIdentity] = {}
    _initialized: bool = False
    
    @classmethod
    def _ensure_initialized(cls):
        """Lazy initialization of author data."""
        if cls._initialized:
            return
        
        # Define all known authors
        authors = [
            AuthorIdentity(
                canonical_name="Rashi",
                sefaria_prefix="Rashi on",
                hebrew_name='רש"י',
                level=SourceLevel.RASHI,
                aliases=frozenset({"rashi", "r' shlomo yitzchaki", "רש״י", "רש\"י"})
            ),
            AuthorIdentity(
                canonical_name="Tosafot",
                sefaria_prefix="Tosafot on",
                hebrew_name="תוספות",
                level=SourceLevel.TOSFOS,
                aliases=frozenset({"tosafot", "tosfos", "tosafos", "tosfot", "תוספות", "בעלי התוספות"})
            ),
            AuthorIdentity(
                canonical_name="Ran",
                sefaria_prefix="Ran on",
                hebrew_name='ר"ן',
                level=SourceLevel.RISHONIM,
                aliases=frozenset({"ran", "r' nissim", "rabbeinu nissim", "הר״ן", "ר\"ן", "רבינו נסים"})
            ),
            AuthorIdentity(
                canonical_name="Rashba",
                sefaria_prefix="Rashba on",
                hebrew_name='רשב"א',
                level=SourceLevel.RISHONIM,
                aliases=frozenset({"rashba", "r' shlomo ben aderes", "רשב״א", "רשב\"א"})
            ),
            AuthorIdentity(
                canonical_name="Ritva",
                sefaria_prefix="Ritva on",
                hebrew_name='ריטב"א',
                level=SourceLevel.RISHONIM,
                aliases=frozenset({"ritva", "r' yom tov", "ריטב״א", "ריטב\"א"})
            ),
            AuthorIdentity(
                canonical_name="Ramban",
                sefaria_prefix="Ramban on",
                hebrew_name='רמב"ן',
                level=SourceLevel.RISHONIM,
                aliases=frozenset({"ramban", "nachmanides", "r' moshe ben nachman", "רמב״ן", "רמב\"ן"})
            ),
            AuthorIdentity(
                canonical_name="Rosh",
                sefaria_prefix="Rosh on",
                hebrew_name='רא"ש',
                level=SourceLevel.RISHONIM,
                aliases=frozenset({"rosh", "r' asher", "rabbeinu asher", "רא״ש", "רא\"ש"})
            ),
            AuthorIdentity(
                canonical_name="Meiri",
                sefaria_prefix="Meiri on",
                hebrew_name="מאירי",
                level=SourceLevel.RISHONIM,
                aliases=frozenset({"meiri", "beis habechira", "בית הבחירה", "מאירי"})
            ),
            AuthorIdentity(
                canonical_name="Nimukei Yosef",
                sefaria_prefix="Nimukei Yosef on",
                hebrew_name="נימוקי יוסף",
                level=SourceLevel.RISHONIM,
                aliases=frozenset({"nimukei yosef", "נימוקי יוסף"})
            ),
            AuthorIdentity(
                canonical_name="Mordechai",
                sefaria_prefix="Mordechai on",
                hebrew_name="מרדכי",
                level=SourceLevel.RISHONIM,
                aliases=frozenset({"mordechai", "מרדכי", "the mordechai"})
            ),
            AuthorIdentity(
                canonical_name="Maharsha",
                sefaria_prefix="Chidushei Halachot on",  # Sefaria's actual prefix
                hebrew_name='מהרש"א',
                level=SourceLevel.ACHARONIM,
                aliases=frozenset({"maharsha", "מהרש״א", "מהרש\"א", "chidushei halachot"})
            ),
            AuthorIdentity(
                canonical_name="Pnei Yehoshua",
                sefaria_prefix="Pnei Yehoshua on",
                hebrew_name="פני יהושע",
                level=SourceLevel.ACHARONIM,
                aliases=frozenset({"pnei yehoshua", "penei yehoshua", "פני יהושע"})
            ),
        ]
        
        # Register each author
        for author in authors:
            cls._register(author)
        
        cls._initialized = True
    
    @classmethod
    def _register(cls, author: AuthorIdentity):
        """Register an author with all their aliases."""
        # Register by canonical name
        cls._authors[author.canonical_name.lower()] = author
        # Register by all aliases
        for alias in author.aliases:
            cls._authors[alias.lower()] = author
    
    @classmethod
    def find(cls, name: str) -> Optional[AuthorIdentity]:
        """Find an author by any of their names/aliases."""
        cls._ensure_initialized()
        return cls._authors.get(name.lower().strip())
    
    @classmethod
    def find_by_sefaria_prefix(cls, prefix: str) -> Optional[AuthorIdentity]:
        """Find author by their Sefaria prefix (e.g., 'Rashi on')."""
        cls._ensure_initialized()
        prefix_lower = prefix.lower().strip()
        for author in set(cls._authors.values()):
            if author.sefaria_prefix.lower() == prefix_lower:
                return author
        return None
    
    @classmethod
    def extract_from_ref(cls, ref: str) -> Optional[AuthorIdentity]:
        """
        Extract author from a commentary reference.
        
        "Rashi on Pesachim 4b" -> AuthorIdentity for Rashi
        "Tosafot on Ketubot 9a:1" -> AuthorIdentity for Tosafot
        """
        cls._ensure_initialized()
        
        # Pattern: "[Author] on [Text]"
        match = re.match(r'^(.+?)\s+on\s+', ref, re.IGNORECASE)
        if match:
            author_part = match.group(1).strip()
            return cls.find(author_part)
        
        # Try Hebrew pattern: "[Author] על [Text]" (less common in Sefaria refs)
        match = re.match(r'^(.+?)\s+על\s+', ref)
        if match:
            author_part = match.group(1).strip()
            return cls.find(author_part)
        
        return None
    
    @classmethod
    def get_level_for_author(cls, author_name: str) -> str:
        """Get the SourceLevel for an author name."""
        author = cls.find(author_name)
        return author.level if author else SourceLevel.RISHONIM
    
    @classmethod
    def all_authors(cls) -> List[AuthorIdentity]:
        """Get all unique registered authors."""
        cls._ensure_initialized()
        return list(set(cls._authors.values()))


# =============================================================================
# REF NORMALIZER (Single Responsibility: Ref Format Handling)
# =============================================================================

class RefNormalizer:
    """
    Normalizes Sefaria references for consistent handling.
    
    Handles conversions between:
    - Line-level refs: "Pesachim 4b:5"
    - Daf-level refs: "Pesachim 4b"
    - Commentary refs: "Rashi on Pesachim 4b:3"
    """
    
    # Pattern for daf refs with optional line number
    DAF_PATTERN = re.compile(
        r'^(?P<masechta>[A-Za-z\s]+)\s*(?P<daf>\d+[ab])(?::(?P<line>\d+))?$',
        re.IGNORECASE
    )
    
    # Pattern for commentary refs
    COMMENTARY_PATTERN = re.compile(
        r'^(?P<author>.+?)\s+on\s+(?P<base>.+)$',
        re.IGNORECASE
    )
    
    @classmethod
    def to_daf_level(cls, ref: str) -> str:
        """
        Convert a line-level ref to daf-level.
        
        "Pesachim 4b:5" -> "Pesachim 4b"
        "Pesachim 4b" -> "Pesachim 4b" (unchanged)
        """
        match = cls.DAF_PATTERN.match(ref.strip())
        if match:
            masechta = match.group('masechta').strip()
            daf = match.group('daf')
            return f"{masechta} {daf}"
        return ref
    
    @classmethod
    def extract_base_from_commentary(cls, commentary_ref: str) -> Optional[str]:
        """
        Extract the base text ref from a commentary ref.
        
        "Rashi on Pesachim 4b:1" -> "Pesachim 4b:1"
        "Ran on Ketubot 9a" -> "Ketubot 9a"
        """
        match = cls.COMMENTARY_PATTERN.match(commentary_ref.strip())
        if match:
            return match.group('base').strip()
        return None
    
    @classmethod
    def extract_author_from_commentary(cls, commentary_ref: str) -> Optional[str]:
        """
        Extract the author name from a commentary ref.
        
        "Rashi on Pesachim 4b:1" -> "Rashi"
        "Tosafot on Ketubot 9a" -> "Tosafot"
        """
        match = cls.COMMENTARY_PATTERN.match(commentary_ref.strip())
        if match:
            return match.group('author').strip()
        return None
    
    @classmethod
    def get_masechta(cls, ref: str) -> Optional[str]:
        """
        Extract masechta name from a ref.
        
        "Pesachim 4b:5" -> "Pesachim"
        "Rashi on Ketubot 9a" -> "Ketubot"
        """
        # First check if it's a commentary ref
        base = cls.extract_base_from_commentary(ref)
        if base:
            ref = base
        
        match = cls.DAF_PATTERN.match(ref.strip())
        if match:
            return match.group('masechta').strip()
        return None
    
    @classmethod
    def normalize_for_display(cls, ref: str) -> str:
        """Normalize ref for consistent display."""
        return ref.strip()


# =============================================================================
# AUTHOR FILTER STRATEGIES (Open/Closed Principle)
# =============================================================================

class AuthorFilterStrategy(ABC):
    """
    Abstract strategy for filtering commentaries by author.
    
    Liskov Substitution: Any filter can replace another.
    """
    
    @abstractmethod
    def should_include(self, commentary: DiscoveredCommentary) -> bool:
        """Determine if a commentary should be included."""
        pass
    
    @abstractmethod
    def describe(self) -> str:
        """Human-readable description of this filter."""
        pass


class TargetAuthorsFilter(AuthorFilterStrategy):
    """Filter to include only specific target authors."""
    
    def __init__(self, target_authors: List[str]):
        self._targets: Set[str] = set()
        for author in target_authors:
            # Add the author name itself
            self._targets.add(author.lower().strip())
            # Also add canonical name if we can find it
            identity = AuthorRegistry.find(author)
            if identity:
                self._targets.add(identity.canonical_name.lower())
                self._targets.update(identity.aliases)
    
    def should_include(self, commentary: DiscoveredCommentary) -> bool:
        author_lower = commentary.author_name.lower().strip()
        return author_lower in self._targets
    
    def describe(self) -> str:
        return f"Target authors: {sorted(self._targets)}"


class AllAuthorsFilter(AuthorFilterStrategy):
    """Include all commentaries (no filtering)."""
    
    def should_include(self, commentary: DiscoveredCommentary) -> bool:
        return True
    
    def describe(self) -> str:
        return "All authors"


class LevelFilter(AuthorFilterStrategy):
    """Filter by source level (Rishonim, Acharonim, etc.)."""
    
    def __init__(self, allowed_levels: List[str]):
        self._allowed = set(allowed_levels)
    
    def should_include(self, commentary: DiscoveredCommentary) -> bool:
        return commentary.level in self._allowed
    
    def describe(self) -> str:
        return f"Levels: {sorted(self._allowed)}"


class CompositeFilter(AuthorFilterStrategy):
    """Combine multiple filters with AND logic."""
    
    def __init__(self, filters: List[AuthorFilterStrategy]):
        self._filters = filters
    
    def should_include(self, commentary: DiscoveredCommentary) -> bool:
        return all(f.should_include(commentary) for f in self._filters)
    
    def describe(self) -> str:
        return " AND ".join(f.describe() for f in self._filters)


# =============================================================================
# COMMENTARY DISCOVERER (Single Responsibility: Discovery)
# =============================================================================

class CommentaryDiscoverer:
    """
    Discovers available commentaries using Sefaria's Related API.
    
    Instead of guessing at refs, asks Sefaria what actually exists.
    """
    
    def __init__(self, client: ISefariaClient):
        self._client = client
        self._cache: Dict[str, List[DiscoveredCommentary]] = {}
    
    async def discover(self, base_ref: str) -> List[DiscoveredCommentary]:
        """
        Discover all commentaries that exist for a given base ref.
        
        Uses Sefaria's /api/related/ endpoint which returns all
        linked commentaries for a given passage.
        """
        # Check cache first
        cache_key = base_ref.lower().strip()
        if cache_key in self._cache:
            logger.debug(f"[DISCOVER] Cache hit for {base_ref}")
            return self._cache[cache_key]
        
        logger.info(f"[DISCOVER] Finding commentaries for: {base_ref}")
        
        commentaries = []
        
        try:
            related = await self._client.get_related(base_ref, with_text=True)
            
            if not related:
                logger.warning(f"[DISCOVER] No related content for {base_ref}")
                return []
            
            # Process each commentary from the related response
            for comm in getattr(related, 'commentaries', []):
                # Extract author from the ref
                author_name = RefNormalizer.extract_author_from_commentary(comm.ref)
                if not author_name:
                    # Try to get from category
                    author_name = getattr(comm, 'category', '') or 'Unknown'
                
                # Determine level
                author_identity = AuthorRegistry.find(author_name)
                level = author_identity.level if author_identity else SourceLevel.RISHONIM
                
                discovered = DiscoveredCommentary(
                    ref=comm.ref,
                    he_ref=getattr(comm, 'he_ref', comm.ref),
                    author_name=author_name,
                    base_ref=base_ref,
                    level=level,
                    text_preview=getattr(comm, 'text_snippet', '')[:200] if hasattr(comm, 'text_snippet') else '',
                    category=getattr(comm, 'category', '')
                )
                commentaries.append(discovered)
                logger.debug(f"[DISCOVER]   Found: {comm.ref} ({author_name})")
            
            logger.info(f"[DISCOVER] Found {len(commentaries)} commentaries for {base_ref}")
            
            # Cache the results
            self._cache[cache_key] = commentaries
            
        except Exception as e:
            logger.error(f"[DISCOVER] Error discovering commentaries for {base_ref}: {e}")
        
        return commentaries
    
    async def discover_for_daf(self, line_ref: str) -> List[DiscoveredCommentary]:
        """
        Discover commentaries for the entire daf, not just a specific line.
        
        This is more reliable because commentaries might not align perfectly
        with Gemara line numbers.
        
        "Pesachim 4b:5" -> discovers all commentaries on "Pesachim 4b"
        """
        daf_ref = RefNormalizer.to_daf_level(line_ref)
        return await self.discover(daf_ref)
    
    def clear_cache(self):
        """Clear the discovery cache."""
        self._cache.clear()


# =============================================================================
# COMMENTARY FETCHER (Orchestrator)
# =============================================================================

class CommentaryFetcher:
    """
    Fetches commentaries on base sources using discovery-based approach.
    
    This is the main orchestrator that:
    1. Discovers what commentaries exist (via Related API)
    2. Filters to target authors
    3. Fetches full text for each
    4. Returns organized results
    
    Dependency Inversion: Depends on ISefariaClient protocol, not concrete class.
    """
    
    def __init__(
        self,
        client: ISefariaClient,
        discoverer: Optional[CommentaryDiscoverer] = None
    ):
        self._client = client
        self._discoverer = discoverer or CommentaryDiscoverer(client)
    
    async def fetch(
        self,
        base_refs: List[str],
        target_authors: Optional[List[str]] = None,
        include_all_on_daf: bool = True,
        max_per_author: int = 5,
        max_total: int = 50
    ) -> List[FetchedCommentary]:
        """
        Fetch commentaries for the given base refs.
        
        Args:
            base_refs: List of base text refs (e.g., ["Pesachim 4b:5", "Pesachim 10a:1"])
            target_authors: If provided, only fetch these authors. If None, fetch all.
            include_all_on_daf: If True, discover commentaries for entire daf, not just line
            max_per_author: Maximum commentaries to fetch per author
            max_total: Maximum total commentaries to fetch
        
        Returns:
            List of FetchedCommentary objects with full text
        """
        if not base_refs:
            logger.warning("[FETCH] No base refs provided")
            return []
        
        # Build the filter strategy
        if target_authors:
            filter_strategy = TargetAuthorsFilter(target_authors)
            logger.info(f"[FETCH] Filtering to authors: {target_authors}")
        else:
            filter_strategy = AllAuthorsFilter()
            logger.info("[FETCH] Fetching all available commentaries")
        
        # Track what we've fetched to avoid duplicates
        fetched_refs: Set[str] = set()
        results: List[FetchedCommentary] = []
        author_counts: Dict[str, int] = {}
        
        # Process each base ref
        for base_idx, base_ref in enumerate(base_refs, 1):
            if len(results) >= max_total:
                logger.info(f"[FETCH] Reached max total ({max_total}), stopping")
                break
            
            logger.info(f"[FETCH] Processing base ref {base_idx}/{len(base_refs)}: {base_ref}")
            
            # Discover available commentaries
            if include_all_on_daf:
                discovered = await self._discoverer.discover_for_daf(base_ref)
            else:
                discovered = await self._discoverer.discover(base_ref)
            
            # Filter and fetch
            for comm in discovered:
                # Check filter
                if not filter_strategy.should_include(comm):
                    continue
                
                # Check if already fetched
                if comm.ref in fetched_refs:
                    continue
                
                # Check per-author limit
                author_key = comm.author_name.lower()
                if author_counts.get(author_key, 0) >= max_per_author:
                    logger.debug(f"[FETCH] Skipping {comm.ref} - reached max for {comm.author_name}")
                    continue
                
                # Check total limit
                if len(results) >= max_total:
                    break
                
                # Fetch the full text
                fetched = await self._fetch_single(comm)
                if fetched:
                    results.append(fetched)
                    fetched_refs.add(comm.ref)
                    author_counts[author_key] = author_counts.get(author_key, 0) + 1
        
        # Sort by level (Rashi first, then Tosfos, then Rishonim, etc.)
        results.sort(key=lambda x: self._level_sort_key(x.level))
        
        logger.info(f"[FETCH] Complete: {len(results)} commentaries fetched")
        for result in results:
            logger.info(f"[FETCH]   • {result.ref} ({result.level_hebrew})")
        
        return results
    
    async def _fetch_single(self, discovered: DiscoveredCommentary) -> Optional[FetchedCommentary]:
        """Fetch full text for a single discovered commentary."""
        logger.debug(f"[FETCH] Fetching text: {discovered.ref}")
        
        try:
            text = await self._client.get_text(discovered.ref)
            
            if not text:
                logger.debug(f"[FETCH]   ✗ Not found: {discovered.ref}")
                return None
            
            hebrew = getattr(text, 'hebrew', '') or ''
            english = getattr(text, 'english', '') or ''
            
            if not hebrew and not english:
                logger.debug(f"[FETCH]   ✗ Empty text: {discovered.ref}")
                return None
            
            # Get level info
            level = discovered.level
            level_hebrew = LEVEL_HEBREW.get(level, discovered.author_name)
            
            logger.info(f"[FETCH]   ✓ Got {discovered.author_name}: {discovered.ref} ({len(hebrew)} chars)")
            
            return FetchedCommentary(
                ref=discovered.ref,
                he_ref=getattr(text, 'he_ref', discovered.ref),
                author=discovered.author_name,
                level=level,
                level_hebrew=level_hebrew,
                hebrew_text=hebrew,
                english_text=english,
                base_ref=discovered.base_ref,
                categories=getattr(text, 'categories', [])
            )
            
        except Exception as e:
            logger.error(f"[FETCH] Error fetching {discovered.ref}: {e}")
            return None
    
    def _level_sort_key(self, level: str) -> int:
        """Get sort order for a level."""
        order = {
            SourceLevel.RASHI: 1,
            SourceLevel.TOSFOS: 2,
            SourceLevel.RISHONIM: 3,
            SourceLevel.RAMBAM: 4,
            SourceLevel.ACHARONIM: 5,
            SourceLevel.OTHER: 99
        }
        return order.get(level, 50)


# =============================================================================
# FACTORY (Creates configured instances)
# =============================================================================

class CommentaryFetcherFactory:
    """
    Factory for creating CommentaryFetcher instances.
    
    Encapsulates the construction complexity.
    """
    
    @staticmethod
    def create(client: ISefariaClient) -> CommentaryFetcher:
        """Create a fully configured CommentaryFetcher."""
        discoverer = CommentaryDiscoverer(client)
        return CommentaryFetcher(client, discoverer)
    
    @staticmethod
    def create_with_custom_discoverer(
        client: ISefariaClient,
        discoverer: CommentaryDiscoverer
    ) -> CommentaryFetcher:
        """Create with a custom discoverer (for testing)."""
        return CommentaryFetcher(client, discoverer)


# =============================================================================
# INTEGRATION HELPER (Bridge to step_three_search.py)
# =============================================================================

async def fetch_commentaries_v2(
    base_refs: List[str],
    target_authors: List[str],
    client: ISefariaClient,
    source_categories = None  # Optional SourceCategories from analysis
) -> List[FetchedCommentary]:
    """
    Drop-in replacement for the old fetch_commentaries function.
    
    Uses the new discovery-based approach internally.
    
    Args:
        base_refs: Base Gemara/Mishna refs to find commentaries on
        target_authors: Authors to fetch (from QueryAnalysis.target_authors)
        client: Sefaria client instance
        source_categories: Optional SourceCategories for additional author selection
    
    Returns:
        List of FetchedCommentary objects
    """
    # Build complete author list
    all_authors = list(target_authors) if target_authors else []
    
    # Add from source_categories if provided
    if source_categories:
        if getattr(source_categories, 'rashi', False) and 'Rashi' not in all_authors:
            all_authors.append('Rashi')
        if getattr(source_categories, 'tosfos', False) and 'Tosafot' not in all_authors:
            all_authors.append('Tosafot')
        if getattr(source_categories, 'rishonim', False):
            # Add common rishonim if not already present
            for rishon in ['Ran', 'Rashba', 'Ritva', 'Ramban']:
                if rishon not in all_authors:
                    all_authors.append(rishon)
    
    # Create fetcher and run
    fetcher = CommentaryFetcherFactory.create(client)
    
    return await fetcher.fetch(
        base_refs=base_refs,
        target_authors=all_authors if all_authors else None,
        include_all_on_daf=True,
        max_per_author=5,
        max_total=50
    )


# =============================================================================
# CONVERSION HELPER (To Source dataclass)
# =============================================================================

def to_source(fetched: FetchedCommentary) -> dict:
    """
    Convert FetchedCommentary to the Source dict format used by step_three_search.
    
    This bridges the new architecture to the existing code.
    """
    return {
        'ref': fetched.ref,
        'he_ref': fetched.he_ref,
        'level': fetched.level,
        'level_hebrew': fetched.level_hebrew,
        'hebrew_text': fetched.hebrew_text,
        'english_text': fetched.english_text,
        'author': fetched.author,
        'categories': fetched.categories,
        'relevance_description': f"{fetched.author} על {fetched.base_ref}",
        'is_primary': False
    }