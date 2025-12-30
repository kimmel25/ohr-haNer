"""
Step 3: SEARCH - V2 Complete Rewrite
=====================================

V2 PHILOSOPHY:
Claude's suggested refs are our starting point. We verify them, then trickle.

FLOW:
1. Get Claude's suggested_refs from Step 2
2. For each ref: fetch text + surrounding context (buffer)
3. Claude verifies/pinpoints exact location within buffer
4. Verified refs = "foundation stones"
5. Trickle UP: Use Sefaria /related API to get commentaries
6. Trickle DOWN: Look for earlier sources (mishna, pasuk)
7. Filter to only include target_sources from Step 2
8. Return organized sources

KEY INSIGHT:
The old approach tried to find sources through keyword search and citation extraction.
The new approach trusts Claude's semantic understanding and just verifies/fetches.
"""

import logging
import re
import json
import asyncio
import aiohttp
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Any

from anthropic import Anthropic

# Initialize logging
try:
    from logging.logging_config import setup_logging
    setup_logging()
except ImportError:
    # Fallback to basic logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

# Imports
try:
    from config import get_settings
    settings = get_settings()
except ImportError:
    import os
    class Settings:
        anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        sefaria_base_url = "https://www.sefaria.org/api"
    settings = Settings()

try:
    from step_two_understand import (
        QueryAnalysis, FoundationType, TrickleDirection, ConfidenceLevel
    )
except ImportError:
    # Fallback definitions
    class FoundationType(str, Enum):
        GEMARA = "gemara"
        MISHNA = "mishna"
        CHUMASH = "chumash"
        HALACHA_SA = "halacha_sa"
        HALACHA_RAMBAM = "halacha_rambam"
        MIDRASH = "midrash"
        UNKNOWN = "unknown"
    
    class TrickleDirection(str, Enum):
        UP = "up"
        DOWN = "down"
        BOTH = "both"
        NONE = "none"
    
    class ConfidenceLevel(str, Enum):
        HIGH = "high"
        MEDIUM = "medium"
        LOW = "low"

logger = logging.getLogger(__name__)


# ==============================================================================
#  CONFIGURATION
# ==============================================================================

SEFARIA_BASE_URL = getattr(settings, 'sefaria_base_url', "https://www.sefaria.org/api")
BUFFER_DAPIM = 1  # How many dapim before/after to fetch for verification
MAX_CONCURRENT_REQUESTS = 5


# ==============================================================================
#  DATA STRUCTURES
# ==============================================================================

class SourceLevel(str, Enum):
    """Source levels in trickle-up order."""
    PASUK = "pasuk"
    TARGUM = "targum"
    MISHNA = "mishna"
    TOSEFTA = "tosefta"
    GEMARA = "gemara"
    RASHI = "rashi"
    TOSAFOS = "tosafos"
    RISHONIM = "rishonim"
    RAMBAM = "rambam"
    TUR = "tur"
    SHULCHAN_ARUCH = "shulchan_aruch"
    NOSEI_KEILIM = "nosei_keilim"
    ACHARONIM = "acharonim"
    OTHER = "other"


# Map from Sefaria category to our level
CATEGORY_TO_LEVEL = {
    "Tanakh": SourceLevel.PASUK,
    "Torah": SourceLevel.PASUK,
    "Prophets": SourceLevel.PASUK,
    "Writings": SourceLevel.PASUK,
    "Targum": SourceLevel.TARGUM,
    "Mishnah": SourceLevel.MISHNA,
    "Tosefta": SourceLevel.TOSEFTA,
    "Talmud": SourceLevel.GEMARA,
    "Bavli": SourceLevel.GEMARA,
    "Yerushalmi": SourceLevel.GEMARA,
    "Midrash": SourceLevel.RISHONIM,  # Simplification
    "Rashi": SourceLevel.RASHI,
    "Tosafot": SourceLevel.TOSAFOS,
    "Rishonim": SourceLevel.RISHONIM,
    "Rambam": SourceLevel.RAMBAM,
    "Mishneh Torah": SourceLevel.RAMBAM,
    "Tur": SourceLevel.TUR,
    "Shulchan Arukh": SourceLevel.SHULCHAN_ARUCH,
    "Acharonim": SourceLevel.ACHARONIM,
}

# Map from target_sources names to what to look for in Sefaria
SOURCE_NAME_MAP = {
    "gemara": ["Talmud", "Bavli"],
    "rashi": ["Rashi"],
    "tosafos": ["Tosafot", "Tosafos"],
    "ran": ["Ran"],
    "rashba": ["Rashba"],
    "ritva": ["Ritva"],
    "ramban": ["Ramban"],
    "rambam": ["Rambam", "Mishneh Torah"],
    "rosh": ["Rosh"],
    "rif": ["Rif"],
    "meiri": ["Meiri"],
    "nimukei_yosef": ["Nimukei Yosef"],
    "shulchan_aruch": ["Shulchan Arukh"],
    "mishnah_berurah": ["Mishnah Berurah"],
    "taz": ["Taz", "Turei Zahav"],
    "shach": ["Shakh", "Siftei Kohen"],
    "magen_avraham": ["Magen Avraham"],
    "ketzos": ["Ketzot HaChoshen", "Ketzos"],
    "nesivos": ["Netivot HaMishpat", "Nesivos"],
    "chumash": ["Torah", "Tanakh"],
    "ibn_ezra": ["Ibn Ezra"],
    "sforno": ["Sforno"],
    "ohr_hachaim": ["Or HaChaim"],
    "targum": ["Targum"],
}


@dataclass
class Source:
    """A single source with text and metadata."""
    ref: str
    he_ref: str = ""
    level: SourceLevel = SourceLevel.OTHER
    hebrew_text: str = ""
    english_text: str = ""
    author: str = ""
    categories: List[str] = field(default_factory=list)
    is_foundation: bool = False  # Is this a foundation stone?
    is_verified: bool = False    # Was this verified by Claude?


@dataclass
class SearchResult:
    """Complete search result."""
    original_query: str
    foundation_stones: List[Source] = field(default_factory=list)
    commentary_sources: List[Source] = field(default_factory=list)
    earlier_sources: List[Source] = field(default_factory=list)
    
    all_sources: List[Source] = field(default_factory=list)
    sources_by_level: Dict[str, List[Source]] = field(default_factory=dict)
    
    total_sources: int = 0
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    search_description: str = ""
    
    needs_clarification: bool = False
    clarification_question: Optional[str] = None


# ==============================================================================
#  SEFARIA API HELPERS
# ==============================================================================

async def fetch_text(ref: str, session: aiohttp.ClientSession) -> Optional[Dict]:
    """Fetch text from Sefaria API."""
    try:
        # URL encode the ref
        encoded_ref = ref.replace(" ", "%20")
        url = f"{SEFARIA_BASE_URL}/texts/{encoded_ref}?context=0"
        
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
            if response.status == 200:
                return await response.json()
            else:
                logger.warning(f"Sefaria returned {response.status} for {ref}")
                return None
    except Exception as e:
        logger.error(f"Error fetching {ref}: {e}")
        return None


async def fetch_related(ref: str, session: aiohttp.ClientSession) -> Optional[Dict]:
    """Fetch related texts (commentaries, links) from Sefaria."""
    try:
        encoded_ref = ref.replace(" ", "%20")
        url = f"{SEFARIA_BASE_URL}/related/{encoded_ref}"
        
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
            if response.status == 200:
                return await response.json()
            else:
                logger.warning(f"Sefaria related returned {response.status} for {ref}")
                return None
    except Exception as e:
        logger.error(f"Error fetching related for {ref}: {e}")
        return None


async def fetch_links(ref: str, session: aiohttp.ClientSession) -> Optional[List]:
    """Fetch links for a ref from Sefaria."""
    try:
        encoded_ref = ref.replace(" ", "%20")
        url = f"{SEFARIA_BASE_URL}/links/{encoded_ref}"
        
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
            if response.status == 200:
                return await response.json()
            else:
                return None
    except Exception as e:
        logger.error(f"Error fetching links for {ref}: {e}")
        return None


def extract_text_content(sefaria_response: Dict) -> Tuple[str, str]:
    """Extract Hebrew and English text from Sefaria response."""
    he_text = ""
    en_text = ""
    
    if not sefaria_response:
        return he_text, en_text
    
    # Hebrew text
    he = sefaria_response.get("he", "")
    if isinstance(he, list):
        he_text = " ".join(flatten_text(he))
    else:
        he_text = str(he) if he else ""
    
    # English text
    en = sefaria_response.get("text", "")
    if isinstance(en, list):
        en_text = " ".join(flatten_text(en))
    else:
        en_text = str(en) if en else ""
    
    return he_text, en_text


def flatten_text(text_obj) -> List[str]:
    """Flatten nested text arrays from Sefaria."""
    result = []
    if isinstance(text_obj, str):
        if text_obj.strip():
            result.append(text_obj.strip())
    elif isinstance(text_obj, list):
        for item in text_obj:
            result.extend(flatten_text(item))
    return result


def determine_level(categories: List[str], ref: str) -> SourceLevel:
    """Determine source level from Sefaria categories."""
    if not categories:
        return SourceLevel.OTHER
    
    # Check ref for common patterns
    ref_lower = ref.lower()
    if "rashi" in ref_lower:
        return SourceLevel.RASHI
    if "tosafot" in ref_lower or "tosafos" in ref_lower:
        return SourceLevel.TOSAFOS
    
    # Check categories
    for cat in categories:
        if cat in CATEGORY_TO_LEVEL:
            return CATEGORY_TO_LEVEL[cat]
    
    return SourceLevel.OTHER


# ==============================================================================
#  REF PARSING AND MANIPULATION
# ==============================================================================

def parse_gemara_ref(ref: str) -> Optional[Tuple[str, int, str]]:
    """Parse a gemara ref into (masechta, daf_number, amud)."""
    # Handle refs like "Ketubot 12b" or "Bava Kamma 46a"
    match = re.match(r'^([A-Za-z\s]+)\s+(\d+)([ab])$', ref.strip())
    if match:
        return (match.group(1).strip(), int(match.group(2)), match.group(3))
    return None


def get_adjacent_refs(ref: str, buffer: int = BUFFER_DAPIM) -> List[str]:
    """Get refs for surrounding dapim (for verification buffer)."""
    parsed = parse_gemara_ref(ref)
    if not parsed:
        return [ref]  # Can't parse, just return original
    
    masechta, daf, amud = parsed
    refs = []
    
    # Generate refs for buffer before and after
    # Each daf has a and b sides
    current_pos = daf * 2 + (0 if amud == 'a' else 1)
    
    for offset in range(-buffer * 2, buffer * 2 + 1):
        pos = current_pos + offset
        if pos < 4:  # Skip before daf 2a
            continue
        
        new_daf = pos // 2
        new_amud = 'a' if pos % 2 == 0 else 'b'
        refs.append(f"{masechta} {new_daf}{new_amud}")
    
    return refs


# ==============================================================================
#  PHASE 1: FETCH FOUNDATION STONES WITH BUFFER
# ==============================================================================

async def fetch_with_buffer(
    suggested_refs: List[str],
    foundation_type: FoundationType,
    session: aiohttp.ClientSession
) -> Dict[str, Dict]:
    """
    Fetch each suggested ref plus surrounding context (buffer).
    Returns dict mapping ref -> {text, buffer_text, all_refs}
    """
    logger.info("[PHASE 1] Fetching foundation stones with buffer")
    
    results = {}
    
    for ref in suggested_refs:
        logger.info(f"  Fetching: {ref}")
        
        # Get adjacent refs for buffer
        if foundation_type == FoundationType.GEMARA:
            all_refs = get_adjacent_refs(ref, BUFFER_DAPIM)
        else:
            # For non-gemara, just fetch the ref itself
            all_refs = [ref]
        
        # Fetch all refs
        texts = {}
        tasks = [fetch_text(r, session) for r in all_refs]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        for r, resp in zip(all_refs, responses):
            if isinstance(resp, Exception):
                logger.warning(f"    Error fetching {r}: {resp}")
                continue
            if resp:
                he_text, en_text = extract_text_content(resp)
                texts[r] = {
                    "he": he_text,
                    "en": en_text,
                    "he_ref": resp.get("heRef", r),
                    "categories": resp.get("categories", [])
                }
        
        # Combine buffer text
        buffer_text = ""
        for r in all_refs:
            if r in texts and texts[r]["he"]:
                buffer_text += f"\n--- {r} ---\n{texts[r]['he']}\n"
        
        results[ref] = {
            "primary_text": texts.get(ref, {}).get("he", ""),
            "buffer_text": buffer_text,
            "all_refs": all_refs,
            "texts": texts,
            "he_ref": texts.get(ref, {}).get("he_ref", ref),
            "categories": texts.get(ref, {}).get("categories", [])
        }
        
        logger.info(f"    Fetched {len(texts)} refs, buffer length: {len(buffer_text)} chars")
    
    return results


# ==============================================================================
#  PHASE 2: CLAUDE VERIFICATION
# ==============================================================================

VERIFICATION_PROMPT = """You are verifying if a Torah text contains a specific topic.

QUERY: {query}
TOPIC: {inyan}
SUGGESTED REF: {ref}

Here is the text around that ref:
{buffer_text}

TASK: Does this text discuss the topic "{inyan}"?

If YES: Return the EXACT ref where the main discussion is (might be the suggested ref or an adjacent one).
If NO: Say "NOT_FOUND" and briefly explain why.

Return ONLY a JSON object:
{{
    "found": true/false,
    "exact_ref": "The exact ref like 'Ketubot 12b'",
    "reason": "Brief explanation"
}}"""


async def verify_refs_with_claude(
    ref_data: Dict[str, Dict],
    query: str,
    inyan_description: str
) -> List[Tuple[str, bool, str]]:
    """
    Have Claude verify each suggested ref and pinpoint exact location.
    Returns list of (verified_ref, is_verified, reason).
    """
    logger.info("[PHASE 2] Claude verification of refs")
    
    if not ref_data:
        return []
    
    client = Anthropic(api_key=settings.anthropic_api_key)
    verified = []
    
    for ref, data in ref_data.items():
        buffer_text = data.get("buffer_text", "")
        
        if not buffer_text or len(buffer_text) < 50:
            logger.warning(f"  {ref}: No text found, skipping verification")
            verified.append((ref, False, "No text available"))
            continue
        
        prompt = VERIFICATION_PROMPT.format(
            query=query,
            inyan=inyan_description or query,
            ref=ref,
            buffer_text=buffer_text[:8000]  # Limit for context window
        )
        
        try:
            response = client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=500,
                temperature=0,
                messages=[{"role": "user", "content": prompt}]
            )
            
            raw = response.content[0].text.strip()
            
            # Parse JSON response
            try:
                # Handle markdown code blocks
                if "```json" in raw:
                    raw = raw.split("```json")[1].split("```")[0].strip()
                elif "```" in raw:
                    raw = raw.split("```")[1].split("```")[0].strip()
                
                result = json.loads(raw)
                found = result.get("found", False)
                exact_ref = result.get("exact_ref", ref)
                reason = result.get("reason", "")
                
                if found:
                    logger.info(f"  ✓ {ref} -> {exact_ref}: {reason[:50]}...")
                    verified.append((exact_ref, True, reason))
                else:
                    logger.info(f"  ✗ {ref}: NOT FOUND - {reason[:50]}...")
                    verified.append((ref, False, reason))
                    
            except json.JSONDecodeError:
                # Try to extract meaning from non-JSON response
                if "NOT_FOUND" in raw.upper():
                    verified.append((ref, False, raw[:100]))
                else:
                    # Assume found if no clear NOT_FOUND
                    verified.append((ref, True, "Verification unclear, assuming valid"))
                    
        except Exception as e:
            logger.error(f"  Error verifying {ref}: {e}")
            # On error, keep the ref but mark as unverified
            verified.append((ref, False, f"Verification error: {e}"))
    
    return verified


# ==============================================================================
#  PHASE 3: TRICKLE UP - GET COMMENTARIES
# ==============================================================================

async def trickle_up(
    foundation_refs: List[str],
    target_sources: List[str],
    session: aiohttp.ClientSession
) -> List[Source]:
    """
    Get commentaries on the foundation stones using Sefaria /related API.
    Filter to only include requested target_sources.
    """
    logger.info("[PHASE 3] Trickle UP - Getting commentaries")
    logger.info(f"  Target sources: {target_sources}")
    
    sources = []
    seen_refs = set()
    
    # Build list of categories to look for based on target_sources
    wanted_categories = set()
    for source_name in target_sources:
        if source_name.lower() in SOURCE_NAME_MAP:
            wanted_categories.update(SOURCE_NAME_MAP[source_name.lower()])
    
    logger.info(f"  Looking for categories: {wanted_categories}")
    
    for foundation_ref in foundation_refs:
        logger.info(f"  Getting related for: {foundation_ref}")
        
        related = await fetch_related(foundation_ref, session)
        if not related:
            logger.warning(f"    No related data for {foundation_ref}")
            continue
        
        # Process links
        links = related.get("links", [])
        logger.info(f"    Found {len(links)} links")
        
        for link in links:
            ref = link.get("ref", "")
            if not ref or ref in seen_refs:
                continue
            
            categories = link.get("collectiveTitle", {})
            if isinstance(categories, dict):
                cat_en = categories.get("en", "")
            else:
                cat_en = str(categories)
            
            # Check if this matches our wanted sources
            should_include = False
            for wanted in wanted_categories:
                if wanted.lower() in cat_en.lower() or wanted.lower() in ref.lower():
                    should_include = True
                    break
            
            if not should_include:
                continue
            
            seen_refs.add(ref)
            
            # Fetch the actual text
            text_data = await fetch_text(ref, session)
            if text_data:
                he_text, en_text = extract_text_content(text_data)
                
                source = Source(
                    ref=ref,
                    he_ref=text_data.get("heRef", ref),
                    level=determine_level(text_data.get("categories", []), ref),
                    hebrew_text=he_text,
                    english_text=en_text,
                    author=cat_en,
                    categories=text_data.get("categories", []),
                    is_foundation=False,
                    is_verified=True
                )
                sources.append(source)
                logger.info(f"    ✓ Added: {ref} ({cat_en})")
    
    logger.info(f"  Total commentary sources: {len(sources)}")
    return sources


# ==============================================================================
#  PHASE 4: TRICKLE DOWN - GET EARLIER SOURCES
# ==============================================================================

async def trickle_down(
    foundation_refs: List[str],
    foundation_type: FoundationType,
    session: aiohttp.ClientSession
) -> List[Source]:
    """
    Get earlier sources that the foundation is based on.
    For gemara -> find mishna, pasuk
    For halacha -> find gemara sources
    """
    logger.info("[PHASE 4] Trickle DOWN - Getting earlier sources")
    
    sources = []
    seen_refs = set()
    
    for foundation_ref in foundation_refs:
        links = await fetch_links(foundation_ref, session)
        if not links:
            continue
        
        for link in links:
            ref = link.get("ref", "")
            if not ref or ref in seen_refs:
                continue
            
            # Determine if this is an "earlier" source
            categories = link.get("category", "")
            link_type = link.get("type", "")
            
            # We want: Tanakh, Mishnah for gemara foundation
            # We want: Talmud for halacha foundation
            is_earlier = False
            
            if foundation_type == FoundationType.GEMARA:
                if any(c in str(categories) for c in ["Tanakh", "Torah", "Mishnah"]):
                    is_earlier = True
            elif foundation_type in [FoundationType.HALACHA_SA, FoundationType.HALACHA_RAMBAM]:
                if any(c in str(categories) for c in ["Talmud", "Bavli", "Mishnah"]):
                    is_earlier = True
            
            if not is_earlier:
                continue
            
            seen_refs.add(ref)
            
            # Fetch text
            text_data = await fetch_text(ref, session)
            if text_data:
                he_text, en_text = extract_text_content(text_data)
                
                source = Source(
                    ref=ref,
                    he_ref=text_data.get("heRef", ref),
                    level=determine_level(text_data.get("categories", []), ref),
                    hebrew_text=he_text,
                    english_text=en_text,
                    categories=text_data.get("categories", []),
                    is_foundation=False,
                    is_verified=True
                )
                sources.append(source)
                logger.info(f"    ✓ Earlier source: {ref}")
    
    logger.info(f"  Total earlier sources: {len(sources)}")
    return sources


# ==============================================================================
#  MAIN SEARCH FUNCTION
# ==============================================================================

async def search(analysis: "QueryAnalysis") -> SearchResult:
    """
    Main entry point for Step 3: SEARCH (V2).
    
    1. Fetch suggested refs with buffer
    2. Claude verifies/pinpoints exact locations
    3. Build foundation stones
    4. Trickle up/down based on direction
    5. Return organized sources
    """
    logger.info("\n" + "=" * 70)
    logger.info("STEP 3: SEARCH [V2 - Foundation Stones + Trickle]")
    logger.info("=" * 70)
    logger.info(f"  Query: {analysis.original_query}")
    logger.info(f"  Suggested refs: {analysis.suggested_refs}")
    logger.info(f"  Foundation type: {analysis.foundation_type}")
    logger.info(f"  Trickle direction: {analysis.trickle_direction}")
    logger.info(f"  Target sources: {analysis.target_sources}")
    
    result = SearchResult(
        original_query=analysis.original_query
    )
    
    # Handle clarification case
    if analysis.needs_clarification:
        result.needs_clarification = True
        result.clarification_question = analysis.clarification_question
        result.confidence = ConfidenceLevel.LOW
        result.search_description = "Needs clarification before searching"
        return result
    
    # Handle no refs case
    if not analysis.suggested_refs:
        logger.warning("No suggested refs from Step 2")
        result.needs_clarification = True
        result.clarification_question = "I couldn't identify specific sources. Could you provide more details about what you're looking for?"
        result.confidence = ConfidenceLevel.LOW
        return result
    
    async with aiohttp.ClientSession() as session:
        # =====================================================================
        # PHASE 1: Fetch suggested refs with buffer
        # =====================================================================
        ref_data = await fetch_with_buffer(
            analysis.suggested_refs,
            analysis.foundation_type,
            session
        )
        
        # =====================================================================
        # PHASE 2: Claude verification
        # =====================================================================
        verified_results = await verify_refs_with_claude(
            ref_data,
            analysis.original_query,
            analysis.inyan_description
        )
        
        # Build foundation stones from verified refs
        verified_refs = []
        for verified_ref, is_verified, reason in verified_results:
            if is_verified:
                verified_refs.append(verified_ref)
                
                # Get the text data for this ref
                original_ref = None
                for orig in analysis.suggested_refs:
                    if orig in ref_data:
                        # Check if verified_ref matches original or is in buffer
                        if verified_ref == orig or verified_ref in ref_data[orig].get("all_refs", []):
                            original_ref = orig
                            break
                
                if original_ref and original_ref in ref_data:
                    data = ref_data[original_ref]
                    text_dict = data.get("texts", {}).get(verified_ref, {})
                    
                    source = Source(
                        ref=verified_ref,
                        he_ref=text_dict.get("he_ref", verified_ref),
                        level=determine_level(text_dict.get("categories", []), verified_ref),
                        hebrew_text=text_dict.get("he", ""),
                        english_text=text_dict.get("en", ""),
                        categories=text_dict.get("categories", []),
                        is_foundation=True,
                        is_verified=True
                    )
                    result.foundation_stones.append(source)
        
        logger.info(f"  Verified foundation stones: {len(result.foundation_stones)}")
        for s in result.foundation_stones:
            logger.info(f"    ✓ {s.ref}")
        
        # If no verified refs, try with original suggested refs anyway
        if not verified_refs and analysis.suggested_refs:
            logger.warning("No refs verified, using suggested refs as fallback")
            verified_refs = analysis.suggested_refs
        
        # =====================================================================
        # PHASE 3: Trickle UP (if requested)
        # =====================================================================
        if analysis.trickle_direction in [TrickleDirection.UP, TrickleDirection.BOTH]:
            commentary_sources = await trickle_up(
                verified_refs,
                analysis.target_sources,
                session
            )
            result.commentary_sources = commentary_sources
        
        # =====================================================================
        # PHASE 4: Trickle DOWN (if requested)
        # =====================================================================
        if analysis.trickle_direction in [TrickleDirection.DOWN, TrickleDirection.BOTH]:
            earlier_sources = await trickle_down(
                verified_refs,
                analysis.foundation_type,
                session
            )
            result.earlier_sources = earlier_sources
    
    # =========================================================================
    # Organize results
    # =========================================================================
    
    # Combine all sources
    all_sources = (
        result.foundation_stones +
        result.commentary_sources +
        result.earlier_sources
    )
    result.all_sources = all_sources
    result.total_sources = len(all_sources)
    
    # Group by level
    by_level: Dict[str, List[Source]] = defaultdict(list)
    for s in all_sources:
        by_level[s.level.value].append(s)
    result.sources_by_level = dict(by_level)
    
    # Set confidence
    if len(result.foundation_stones) >= 2:
        result.confidence = ConfidenceLevel.HIGH
    elif len(result.foundation_stones) >= 1:
        result.confidence = ConfidenceLevel.MEDIUM
    else:
        result.confidence = ConfidenceLevel.LOW
    
    # Summary
    result.search_description = (
        f"Found {len(result.foundation_stones)} foundation stones, "
        f"{len(result.commentary_sources)} commentaries, "
        f"{len(result.earlier_sources)} earlier sources. "
        f"Total: {result.total_sources} sources."
    )
    
    # =========================================================================
    # Log summary
    # =========================================================================
    logger.info("\n" + "=" * 70)
    logger.info("                    SEARCH COMPLETE (V2)")
    logger.info("=" * 70)
    logger.info(f"  Foundation stones: {[s.ref for s in result.foundation_stones]}")
    logger.info(f"  Commentaries: {len(result.commentary_sources)}")
    logger.info(f"  Earlier sources: {len(result.earlier_sources)}")
    logger.info(f"  Total: {result.total_sources}")
    logger.info(f"  Confidence: {result.confidence}")
    logger.info("=" * 70 + "\n")
    
    return result


# ==============================================================================
#  OUTPUT FORMATTING
# ==============================================================================

def format_sources_text(result: SearchResult) -> str:
    """Format search results as plain text."""
    lines = []
    lines.append("=" * 60)
    lines.append(f"MAREI MEKOMOS: {result.original_query}")
    lines.append("=" * 60)
    lines.append("")
    
    # Foundation stones first
    if result.foundation_stones:
        lines.append("📖 FOUNDATION SOURCES")
        lines.append("-" * 40)
        for s in result.foundation_stones:
            lines.append(f"\n{s.ref} ({s.he_ref})")
            if s.hebrew_text:
                lines.append(s.hebrew_text[:500] + ("..." if len(s.hebrew_text) > 500 else ""))
        lines.append("")
    
    # Commentaries
    if result.commentary_sources:
        lines.append("\n📚 COMMENTARIES")
        lines.append("-" * 40)
        for s in result.commentary_sources:
            lines.append(f"\n{s.ref}")
            if s.author:
                lines.append(f"  Author: {s.author}")
            if s.hebrew_text:
                lines.append(s.hebrew_text[:300] + ("..." if len(s.hebrew_text) > 300 else ""))
        lines.append("")
    
    # Earlier sources
    if result.earlier_sources:
        lines.append("\n📜 EARLIER SOURCES")
        lines.append("-" * 40)
        for s in result.earlier_sources:
            lines.append(f"\n{s.ref}")
            if s.hebrew_text:
                lines.append(s.hebrew_text[:300] + ("..." if len(s.hebrew_text) > 300 else ""))
    
    lines.append("\n" + "=" * 60)
    lines.append(result.search_description)
    lines.append("=" * 60)
    
    return "\n".join(lines)


# ==============================================================================
#  EXPORTS
# ==============================================================================

__all__ = [
    'search',
    'SearchResult',
    'Source',
    'SourceLevel',
    'format_sources_text',
]