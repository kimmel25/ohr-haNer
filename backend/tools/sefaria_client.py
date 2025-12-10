"""
Sefaria API Client
==================

Comprehensive wrapper for Sefaria's API endpoints.
This is the data layer for Steps 2 and 3.

Endpoints used:
- Search API: Find where terms appear in the corpus
- Texts API: Fetch actual text content
- Related API: Get linked commentaries and related texts
- Index API: Get metadata about texts

Key Design Decisions:
- All methods are async for performance
- Results are cached to reduce API calls
- We handle Sefaria's Hebrew/English ref formats
"""

import httpx
import asyncio
import json
import re
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
from pathlib import Path
import hashlib
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Import centralized SourceLevel definition from models.py
from models import SourceLevel


# ==========================================
#  LEVEL ORDERING HELPER
# ==========================================

def get_level_order(level: SourceLevel) -> int:
    """
    Get the numeric order for a SourceLevel.
    This preserves the trickle-up hierarchy for sorting.
    """
    order_map = {
        SourceLevel.CHUMASH: 1,
        SourceLevel.MISHNA: 2,
        SourceLevel.GEMARA: 3,
        SourceLevel.RASHI: 4,
        SourceLevel.TOSFOS: 5,
        SourceLevel.RISHONIM: 6,
        SourceLevel.RAMBAM: 7,
        SourceLevel.TUR: 8,
        SourceLevel.SHULCHAN_ARUCH: 9,
        SourceLevel.NOSEI_KEILIM: 10,
        SourceLevel.ACHARONIM: 11,
        SourceLevel.OTHER: 99
    }
    return order_map.get(level, 99)


# ==========================================
#  DATA STRUCTURES
# ==========================================

@dataclass
class SearchHit:
    """A single search result from Sefaria."""
    ref: str                    # e.g., "Kesubos 9a:1"
    he_ref: str                 # e.g., "כתובות ט׳ א:א"
    text_snippet: str           # Hebrew text snippet
    english_snippet: str        # English text snippet (if available)
    score: float                # Search relevance score
    category: str               # e.g., "Talmud"
    path: List[str]             # e.g., ["Talmud", "Bavli", "Seder Nashim", "Kesubos"]


@dataclass
class SearchResults:
    """Aggregated search results with metadata."""
    query: str
    total_hits: int
    hits: List[SearchHit]
    hits_by_category: Dict[str, int]      # Count per category
    hits_by_masechta: Dict[str, int]      # Count per masechta (for Talmud)
    top_refs: List[str]                    # Most relevant refs


@dataclass
class TextContent:
    """Content of a specific text reference."""
    ref: str
    he_ref: str
    hebrew: str                 # Hebrew text (can be list for segmented texts)
    english: str                # English translation (if available)
    categories: List[str]
    level: SourceLevel
    section_names: List[str]    # e.g., ["Daf", "Line"]
    is_complex: bool            # Whether this is a complex/nested text


@dataclass
class RelatedText:
    """A text related to another (commentary, link, etc.)."""
    ref: str
    he_ref: str
    text_snippet: str
    relationship: str           # e.g., "commentary", "reference", "related"
    source_ref: str             # What it's related to
    level: SourceLevel
    category: str


@dataclass
class RelatedContent:
    """All content related to a given reference."""
    base_ref: str
    commentaries: List[RelatedText]    # Rashi, Tosfos, etc.
    links: List[RelatedText]           # Cross-references to other texts
    sheets: int                         # Number of source sheets (popularity indicator)


# ==========================================
#  CATEGORY MAPPING
# ==========================================

def determine_source_level(categories: List[str], ref: str = "") -> SourceLevel:
    """
    Map Sefaria categories to our source levels.
    
    Sefaria categories look like:
    - ["Talmud", "Bavli", "Seder Nashim", "Kesubos"]
    - ["Tanakh", "Torah", "Genesis"]
    - ["Commentary", "Talmud", "Rashi"]
    - ["Halakhah", "Shulchan Arukh", "Orach Chaim"]
    """
    if not categories:
        return SourceLevel.OTHER
    
    cat_str = " ".join(categories).lower()
    ref_lower = ref.lower()
    
    # Chumash / Tanakh
    if "tanakh" in cat_str or "torah" in cat_str:
        if "commentary" in cat_str:
            # Commentary on Tanakh
            if "rashi" in cat_str:
                return SourceLevel.RASHI
            return SourceLevel.RISHONIM
        return SourceLevel.CHUMASH
    
    # Mishna
    if "mishnah" in cat_str or "mishna" in cat_str:
        if "commentary" in cat_str:
            return SourceLevel.RISHONIM
        return SourceLevel.MISHNA
    
    # Talmud
    if "talmud" in cat_str:
        if "commentary" in cat_str:
            if "rashi" in cat_str:
                return SourceLevel.RASHI
            if "tosafot" in cat_str or "tosfos" in cat_str:
                return SourceLevel.TOSFOS
            # Other Talmud commentaries are Rishonim/Acharonim
            if any(name in cat_str for name in ["ritva", "rashba", "ran", "ramban", "rosh"]):
                return SourceLevel.RISHONIM
            if any(name in cat_str for name in ["pnei yehoshua", "maharsha", "maharam"]):
                return SourceLevel.ACHARONIM
            return SourceLevel.RISHONIM  # Default for Talmud commentary
        return SourceLevel.GEMARA
    
    # Rambam - special handling
    if "rambam" in cat_str or "mishneh torah" in cat_str:
        return SourceLevel.RAMBAM
    
    # Shulchan Aruch
    if "shulchan" in cat_str or "shulkhan" in cat_str:
        return SourceLevel.SHULCHAN_ARUCH
    
    # Tur
    if "tur" in cat_str and "arba" in cat_str:
        return SourceLevel.TUR
    
    # Nosei Keilim on Shulchan Aruch
    if any(name in cat_str for name in ["shakh", "taz", "magen avraham", "mishnah berurah"]):
        return SourceLevel.NOSEI_KEILIM
    
    # Rishonim (general)
    if "rishonim" in cat_str:
        return SourceLevel.RISHONIM
    
    # Acharonim (general)
    if "acharonim" in cat_str or "responsa" in cat_str:
        return SourceLevel.ACHARONIM
    
    # Halakhah general
    if "halakhah" in cat_str or "halacha" in cat_str:
        return SourceLevel.SHULCHAN_ARUCH  # Default for halakha
    
    return SourceLevel.OTHER


# ==========================================
#  MASECHTA DETECTION
# ==========================================

# Mapping of masechta names (various spellings) to canonical names
MASECHTOT = {
    # Seder Zeraim
    "berachot": "Berakhot", "berachos": "Berakhot", "brachos": "Berakhot",
    
    # Seder Moed
    "shabbat": "Shabbat", "shabbos": "Shabbat",
    "eruvin": "Eruvin",
    "pesachim": "Pesachim",
    "shekalim": "Shekalim",
    "yoma": "Yoma",
    "sukkah": "Sukkah", "sukkos": "Sukkah", "sukka": "Sukkah",
    "beitzah": "Beitzah", "beitza": "Beitzah",
    "rosh hashanah": "Rosh Hashanah", "rosh hashana": "Rosh Hashanah",
    "taanit": "Taanit", "taanis": "Taanit",
    "megillah": "Megillah", "megila": "Megillah",
    "moed katan": "Moed Katan",
    "chagigah": "Chagigah", "chagiga": "Chagigah",
    
    # Seder Nashim
    "yevamot": "Yevamot", "yevamos": "Yevamot",
    "ketubot": "Ketubot", "ketubos": "Ketubot", "kesubos": "Ketubot", "kesuvos": "Ketubot",
    "nedarim": "Nedarim",
    "nazir": "Nazir",
    "sotah": "Sotah", "sota": "Sotah",
    "gittin": "Gittin", "gitin": "Gittin",
    "kiddushin": "Kiddushin", "kidushin": "Kiddushin",
    
    # Seder Nezikin
    "bava kamma": "Bava Kamma", "bava kama": "Bava Kamma",
    "bava metzia": "Bava Metzia", "bava metziah": "Bava Metzia",
    "bava batra": "Bava Batra", "bava basra": "Bava Batra",
    "sanhedrin": "Sanhedrin",
    "makkot": "Makkot", "makkos": "Makkot", "makos": "Makkot",
    "shevuot": "Shevuot", "shevuos": "Shevuot",
    "avodah zarah": "Avodah Zarah", "avoda zara": "Avodah Zarah",
    "horayot": "Horayot", "horayos": "Horayot",
    
    # Seder Kodashim
    "zevachim": "Zevachim",
    "menachot": "Menachot", "menachos": "Menachot",
    "chullin": "Chullin", "chulin": "Chullin", "hullin": "Chullin",
    "bechorot": "Bechorot", "bechoros": "Bechorot",
    "arachin": "Arachin", "erchin": "Arachin",
    "temurah": "Temurah",
    "keritot": "Keritot", "kerisos": "Keritot", "kerisus": "Keritot",
    "meilah": "Meilah", "meila": "Meilah",
    "tamid": "Tamid",
    
    # Seder Taharot
    "niddah": "Niddah", "nidah": "Niddah",
}

def extract_masechta_from_ref(ref: str) -> Optional[str]:
    """
    Extract the masechta name from a Sefaria reference.
    
    Examples:
    - "Ketubot 9a" → "Ketubot"
    - "Rashi on Ketubot 9a:1" → "Ketubot"
    - "Tosafot on Pesachim 10a:2:1" → "Pesachim"
    """
    ref_lower = ref.lower()
    
    # Check each masechta name
    for variant, canonical in MASECHTOT.items():
        if variant in ref_lower:
            return canonical
    
    return None


def extract_masechta_from_path(path: List[str]) -> Optional[str]:
    """
    Extract masechta from Sefaria category path.
    
    Example path: ["Talmud", "Bavli", "Seder Nashim", "Ketubot"]
    """
    if len(path) >= 4 and path[0].lower() == "talmud":
        return path[3]  # The masechta name
    return None


# ==========================================
#  SIMPLE FILE CACHE
# ==========================================

class FileCache:
    """Simple file-based cache for Sefaria API responses."""
    
    def __init__(self, cache_dir: str = "cache/sefaria_v2", ttl_hours: int = 168):
        self.cache_dir = Path(__file__).parent.parent / cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = timedelta(hours=ttl_hours)
    
    def _get_cache_path(self, key: str) -> Path:
        """Generate cache file path from key."""
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.json"
    
    def get(self, key: str) -> Optional[Dict]:
        """Get cached value if exists and not expired."""
        cache_path = self._get_cache_path(key)
        
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check expiration
            cached_time = datetime.fromisoformat(data.get('_cached_at', '2000-01-01'))
            if datetime.now() - cached_time > self.ttl:
                cache_path.unlink()
                return None
            
            return data.get('value')
        except Exception as e:
            logger.warning(f"Cache read error: {e}")
            return None
    
    def set(self, key: str, value: Dict):
        """Save value to cache."""
        cache_path = self._get_cache_path(key)
        
        try:
            data = {
                '_cached_at': datetime.now().isoformat(),
                '_key': key,
                'value': value
            }
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Cache write error: {e}")


# ==========================================
#  SEFARIA CLIENT
# ==========================================

class SefariaClient:
    """
    Main client for interacting with Sefaria's API.
    
    Usage:
        client = SefariaClient()
        
        # Search for a term
        results = await client.search("חזקת הגוף")
        
        # Get text content
        text = await client.get_text("Ketubot 9a")
        
        # Get related content (commentaries, links)
        related = await client.get_related("Ketubot 9a")
    """
    
    BASE_URL = "https://www.sefaria.org"
    
    def __init__(self, timeout: float = 30.0, use_cache: bool = True):
        self.timeout = timeout
        self.cache = FileCache() if use_cache else None
        logger.info("SefariaClient initialized")
    
    async def _request(
        self, 
        method: str, 
        endpoint: str, 
        params: Dict = None,
        json_data: Dict = None,
        cache_key: str = None
    ) -> Optional[Dict]:
        """
        Make an HTTP request to Sefaria API.
        
        Args:
            method: HTTP method (GET or POST)
            endpoint: API endpoint (without base URL)
            params: Query parameters
            json_data: JSON body for POST requests
            cache_key: Key for caching (if None, no caching)
        
        Returns:
            JSON response as dict, or None on error
        """
        # Check cache first
        if cache_key and self.cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit: {cache_key[:50]}...")
                return cached
        
        url = f"{self.BASE_URL}{endpoint}"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout, verify=False) as client:
                if method.upper() == "GET":
                    response = await client.get(url, params=params)
                elif method.upper() == "POST":
                    response = await client.post(url, json=json_data)
                else:
                    raise ValueError(f"Unsupported method: {method}")
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Cache successful response
                    if cache_key and self.cache:
                        self.cache.set(cache_key, data)
                    
                    return data
                else:
                    logger.warning(f"Sefaria API error: {response.status_code} for {endpoint}")
                    return None
                    
        except httpx.TimeoutException:
            logger.error(f"Sefaria API timeout: {endpoint}")
            return None
        except Exception as e:
            logger.error(f"Sefaria API error: {e}")
            return None
    
    # ------------------------------------------
    #  SEARCH API
    # ------------------------------------------
    
    async def search(
        self, 
        query: str, 
        size: int = 100,
        filters: List[str] = None
    ) -> SearchResults:
        """
        Search for a term across Sefaria's corpus.
        
        Uses Sefaria's ElasticSearch proxy.
        
        Args:
            query: Hebrew or English term to search for
            size: Number of results to return (max 100)
            filters: Category filters (e.g., ["Talmud", "Midrash"])
        
        Returns:
            SearchResults with hits and aggregations
        """
        logger.info(f"Searching Sefaria for: '{query}'")
        
        # Build ElasticSearch query
        es_query = {
            "size": size,
            "query": {
                "query_string": {
                    "query": query,
                    "default_operator": "AND"
                }
            },
            "sort": [{"_score": {"order": "desc"}}]
        }
        
        if filters:
            es_query["query"] = {
                "bool": {
                    "must": es_query["query"],
                    "filter": {
                        "terms": {"categories": filters}
                    }
                }
            }
        
        cache_key = f"search:{query}:{size}:{filters}"
        
        response = await self._request(
            "POST",
            "/api/search/text/_search",
            json_data=es_query,
            cache_key=cache_key
        )
        
        if not response:
            return SearchResults(
                query=query,
                total_hits=0,
                hits=[],
                hits_by_category={},
                hits_by_masechta={},
                top_refs=[]
            )
        
        # Parse response
        total_hits = response.get("hits", {}).get("total", {})
        if isinstance(total_hits, dict):
            total_hits = total_hits.get("value", 0)
        
        hits = []
        hits_by_category = {}
        hits_by_masechta = {}
        
        for hit in response.get("hits", {}).get("hits", []):
            source = hit.get("_source", {})
            
            ref = source.get("ref", "")
            path = source.get("path", "").split("/") if source.get("path") else []
            
            # Extract text snippets
            highlight = hit.get("highlight", {})
            text_snippet = ""
            if highlight.get("exact"):
                text_snippet = highlight["exact"][0]
            elif source.get("exact"):
                text_snippet = source["exact"][:300]
            
            search_hit = SearchHit(
                ref=ref,
                he_ref=source.get("heRef", ref),
                text_snippet=text_snippet,
                english_snippet="",  # Would need separate query for English
                score=hit.get("_score", 0),
                category=path[0] if path else "",
                path=path
            )
            
            hits.append(search_hit)
            
            # Aggregate by category
            if path:
                cat = path[0]
                hits_by_category[cat] = hits_by_category.get(cat, 0) + 1
            
            # Aggregate by masechta (for Talmud refs)
            masechta = extract_masechta_from_ref(ref) or extract_masechta_from_path(path)
            if masechta:
                hits_by_masechta[masechta] = hits_by_masechta.get(masechta, 0) + 1
        
        # Get top refs (unique, in order of relevance)
        seen_refs = set()
        top_refs = []
        for hit in hits:
            if hit.ref not in seen_refs:
                seen_refs.add(hit.ref)
                top_refs.append(hit.ref)
            if len(top_refs) >= 10:
                break
        
        logger.info(f"  Found {total_hits} total hits, {len(hits)} returned")
        logger.info(f"  By category: {hits_by_category}")
        logger.info(f"  By masechta: {hits_by_masechta}")
        
        return SearchResults(
            query=query,
            total_hits=total_hits,
            hits=hits,
            hits_by_category=hits_by_category,
            hits_by_masechta=hits_by_masechta,
            top_refs=top_refs
        )
    
    # ------------------------------------------
    #  TEXT API
    # ------------------------------------------
    
    async def get_text(
        self, 
        ref: str,
        with_context: bool = False,
        context_padding: int = 0
    ) -> Optional[TextContent]:
        """
        Fetch the text content for a specific reference.
        
        Args:
            ref: Sefaria reference (e.g., "Ketubot 9a", "Rashi on Ketubot 9a:1")
            with_context: Include surrounding context
            context_padding: Number of segments before/after to include
        
        Returns:
            TextContent with Hebrew and English text
        """
        logger.debug(f"Fetching text: {ref}")
        
        # URL-encode the ref
        encoded_ref = ref.replace(" ", "%20")
        
        cache_key = f"text:{ref}:{with_context}:{context_padding}"
        
        params = {}
        if with_context:
            params["context"] = 1
            params["pad"] = context_padding
        
        response = await self._request(
            "GET",
            f"/api/v3/texts/{encoded_ref}",
            params=params,
            cache_key=cache_key
        )
        
        if not response:
            # Try legacy API
            response = await self._request(
                "GET",
                f"/api/texts/{encoded_ref}",
                params=params,
                cache_key=cache_key + "_legacy"
            )
        
        if not response:
            logger.warning(f"Could not fetch text: {ref}")
            return None
        
        # Extract text - can be string or list depending on text structure
        hebrew = response.get("he", "")
        english = response.get("text", "")
        
        # Flatten if it's a nested list
        if isinstance(hebrew, list):
            hebrew = self._flatten_text(hebrew)
        if isinstance(english, list):
            english = self._flatten_text(english)
        
        categories = response.get("categories", [])
        
        return TextContent(
            ref=response.get("ref", ref),
            he_ref=response.get("heRef", ref),
            hebrew=hebrew,
            english=english,
            categories=categories,
            level=determine_source_level(categories, ref),
            section_names=response.get("sectionNames", []),
            is_complex=response.get("isComplex", False)
        )
    
    def _flatten_text(self, text: Any, separator: str = "\n") -> str:
        """Flatten nested lists of text into a single string."""
        if isinstance(text, str):
            return text
        if isinstance(text, list):
            parts = []
            for item in text:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, list):
                    parts.append(self._flatten_text(item, separator))
            return separator.join(parts)
        return str(text) if text else ""
    
    # ------------------------------------------
    #  RELATED API
    # ------------------------------------------
    
    async def get_related(
        self, 
        ref: str,
        with_text: bool = True
    ) -> RelatedContent:
        """
        Get all content related to a reference.
        
        This is the key API for trickle-up - it returns all commentaries,
        links, and related texts for a given passage.
        
        Args:
            ref: Sefaria reference
            with_text: Include text snippets in response
        
        Returns:
            RelatedContent with commentaries and links
        """
        logger.info(f"Fetching related content for: {ref}")
        
        encoded_ref = ref.replace(" ", "%20")
        
        cache_key = f"related:{ref}:{with_text}"
        
        params = {
            "with_text": 1 if with_text else 0
        }
        
        response = await self._request(
            "GET",
            f"/api/related/{encoded_ref}",
            params=params,
            cache_key=cache_key
        )
        
        if not response:
            return RelatedContent(
                base_ref=ref,
                commentaries=[],
                links=[],
                sheets=0
            )
        
        commentaries = []
        links = []
        
        # Process links
        for link in response.get("links", []):
            link_ref = link.get("ref", "")
            categories = link.get("category", "").split("/") if link.get("category") else []
            categories_list = link.get("categories", categories)
            
            # Get text snippet
            text_snippet = ""
            if with_text:
                he_text = link.get("he", "")
                if isinstance(he_text, list):
                    text_snippet = " ".join(str(t) for t in he_text[:3])
                else:
                    text_snippet = str(he_text)[:200] if he_text else ""
            
            level = determine_source_level(categories_list, link_ref)
            
            related_text = RelatedText(
                ref=link_ref,
                he_ref=link.get("heRef", link_ref),
                text_snippet=text_snippet,
                relationship=link.get("type", "reference"),
                source_ref=ref,
                level=level,
                category=link.get("collectiveTitle", {}).get("en", categories_list[0] if categories_list else "")
            )
            
            # Separate commentaries from other links
            if link.get("type") == "commentary":
                commentaries.append(related_text)
            else:
                links.append(related_text)
        
        # Sort commentaries by level (Rashi before Tosfos, etc.)
        commentaries.sort(key=lambda x: get_level_order(x.level))
        
        sheets_count = len(response.get("sheets", []))
        
        logger.info(f"  Found {len(commentaries)} commentaries, {len(links)} links")
        
        return RelatedContent(
            base_ref=ref,
            commentaries=commentaries,
            links=links,
            sheets=sheets_count
        )
    
    # ------------------------------------------
    #  SPECIALIZED QUERIES
    # ------------------------------------------
    
    async def find_primary_sugya(
        self, 
        term: str,
        prefer_bavli: bool = True
    ) -> Optional[str]:
        """
        Find the primary (most referenced) sugya for a term.
        
        This is useful for concepts like "חזקת הגוף" which appear
        in multiple places - we want to find the main discussion.
        
        Args:
            term: Hebrew term to search for
            prefer_bavli: Prefer Talmud Bavli over other sources
        
        Returns:
            The ref of the primary sugya, or None
        """
        results = await self.search(term, size=50)
        
        if not results.hits:
            return None
        
        # If we have masechta hits, prefer the one with most hits
        if results.hits_by_masechta and prefer_bavli:
            top_masechta = max(
                results.hits_by_masechta.items(),
                key=lambda x: x[1]
            )[0]
            
            # Find the first ref from that masechta
            for hit in results.hits:
                if extract_masechta_from_ref(hit.ref) == top_masechta:
                    # Clean up the ref to get the daf level
                    return self._get_daf_ref(hit.ref)
        
        # Otherwise, return top result
        if results.top_refs:
            return self._get_daf_ref(results.top_refs[0])
        
        return None
    
    def _get_daf_ref(self, ref: str) -> str:
        """
        Convert a segment ref to a daf ref.
        
        "Ketubot 9a:5" → "Ketubot 9a"
        """
        # Remove segment numbers
        parts = ref.split(":")
        if len(parts) > 1:
            return parts[0]
        return ref
    
    async def get_sugya_sources(
        self, 
        gemara_ref: str,
        depth: str = "standard"
    ) -> Dict[SourceLevel, List[TextContent]]:
        """
        Get all sources for a sugya organized by level.
        
        This is the main function for Step 3 - given a Gemara reference,
        fetch all related texts and organize them in trickle-up order.
        
        Args:
            gemara_ref: Reference to the Gemara (e.g., "Ketubot 9a")
            depth: "basic" (gemara only), "standard" (+ rashi/tosfos), 
                   "expanded" (+ rishonim), "full" (everything)
        
        Returns:
            Dict mapping SourceLevel to list of TextContent
        """
        logger.info(f"Getting sugya sources for: {gemara_ref} (depth: {depth})")
        
        sources: Dict[SourceLevel, List[TextContent]] = {
            level: [] for level in SourceLevel
        }
        
        # Get the Gemara text
        gemara = await self.get_text(gemara_ref)
        if gemara:
            sources[SourceLevel.GEMARA].append(gemara)
        
        # Get related content
        related = await self.get_related(gemara_ref)
        
        # Determine which levels to include based on depth
        levels_to_include = {SourceLevel.GEMARA}
        
        if depth in ["standard", "expanded", "full"]:
            levels_to_include.update({
                SourceLevel.RASHI,
                SourceLevel.TOSFOS
            })
        
        if depth in ["expanded", "full"]:
            levels_to_include.update({
                SourceLevel.RISHONIM,
                SourceLevel.RAMBAM
            })
        
        if depth == "full":
            levels_to_include.update({
                SourceLevel.TUR,
                SourceLevel.SHULCHAN_ARUCH,
                SourceLevel.NOSEI_KEILIM,
                SourceLevel.ACHARONIM
            })
        
        # Fetch commentaries
        for commentary in related.commentaries:
            if commentary.level in levels_to_include:
                text = await self.get_text(commentary.ref)
                if text:
                    sources[text.level].append(text)
        
        # Log what we found
        for level, texts in sources.items():
            if texts:
                logger.info(f"  {level.name}: {len(texts)} texts")
        
        return sources


# ==========================================
#  GLOBAL INSTANCE
# ==========================================

_client: Optional[SefariaClient] = None


def get_sefaria_client() -> SefariaClient:
    """Get global Sefaria client instance."""
    global _client
    if _client is None:
        _client = SefariaClient()
    return _client


# ==========================================
#  TESTING
# ==========================================

async def test_client():
    """Test the Sefaria client."""
    
    print("=" * 70)
    print("SEFARIA CLIENT TEST")
    print("=" * 70)
    
    client = get_sefaria_client()
    
    # Test 1: Search
    print("\n--- Test 1: Search for 'חזקת הגוף' ---")
    results = await client.search("חזקת הגוף")
    print(f"Total hits: {results.total_hits}")
    print(f"By masechta: {results.hits_by_masechta}")
    print(f"Top refs: {results.top_refs[:5]}")
    
    # Test 2: Get text
    print("\n--- Test 2: Get text for 'Ketubot 9a' ---")
    text = await client.get_text("Ketubot 9a")
    if text:
        print(f"Ref: {text.ref}")
        print(f"Hebrew (first 200 chars): {text.hebrew[:200]}...")
        print(f"Level: {text.level.name}")
    
    # Test 3: Get related
    print("\n--- Test 3: Get related for 'Ketubot 9a' ---")
    related = await client.get_related("Ketubot 9a")
    print(f"Commentaries: {len(related.commentaries)}")
    for c in related.commentaries[:5]:
        print(f"  - {c.ref} ({c.level.name})")
    print(f"Links: {len(related.links)}")
    
    # Test 4: Find primary sugya
    print("\n--- Test 4: Find primary sugya for 'מיגו' ---")
    primary = await client.find_primary_sugya("מיגו")
    print(f"Primary sugya: {primary}")
    
    print("\n" + "=" * 70)
    print("Tests complete!")
    print("=" * 70)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%H:%M:%S'
    )
    
    asyncio.run(test_client())