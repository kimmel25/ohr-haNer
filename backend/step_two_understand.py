# step_two_understand.py
"""
Step 2: UNDERSTAND - Query Analysis & Strategy (UPDATED)
==============================================

This version improves Step 2 by:
 - Adding contextual depth mapping
 - Allowing multiple primary_sources (list) while keeping primary_source for backwards compatibility
 - Adding deterministic shortcuts to avoid Claude where possible (saves cost)
 - Adding a small in-memory cache for Claude outputs (fingerprinted by term + sefaria profile)
 - Hardened JSON parsing / repair logic for LLM output
 - Hail-Mary mode: controlled, schema-constrained fallback when analysis is uncertain
 - Minimal changes to external interfaces (SearchStrategy.to_dict remains)
"""
import asyncio
import json
import os
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
from datetime import datetime, timedelta

# Claude client (Anthropic)
from anthropic import Anthropic

logger = logging.getLogger(__name__)

# ==========================================
#  CONFIG & RUNTIME FLAGS
# ==========================================
USE_CLAUDE = os.environ.get("USE_CLAUDE", "1") not in ("0", "false", "False")
# Cache TTL (seconds)
_CLAUDE_CACHE_TTL = int(os.environ.get("CLAUDE_CACHE_TTL", "3600"))
# Deterministic concentration threshold to skip Claude
_SEFARIA_DOMINANT_THRESHOLD = float(os.environ.get("SEFARIA_DOMINANT_THRESHOLD", "0.7"))

# ==========================================
#  DATA STRUCTURES
# ==========================================


class QueryType(Enum):
    """Types of Torah queries we can handle."""
    SUGYA_CONCEPT = "sugya_concept"
    HALACHA_TERM = "halacha_term"
    DAF_REFERENCE = "daf_reference"
    MASECHTA = "masechta"
    PERSON = "person"
    PASUK = "pasuk"
    KLAL = "klal"
    AMBIGUOUS = "ambiguous"
    UNKNOWN = "unknown"

    # Flexible / catch-all types
    SUGYA_CROSS_REFERENCE = "sugya_cross_reference"
    FREEFORM_TORAH_QUERY = "freeform_torah_query"


class FetchStrategy(Enum):
    """How to fetch and organize sources."""
    TRICKLE_UP = "trickle_up"
    TRICKLE_DOWN = "trickle_down"
    DIRECT = "direct"
    SURVEY = "survey"
    HYBRID = "hybrid"
    HAIL_MARY = "hail_mary"


@dataclass
class RelatedSugya:
    """A sugya related to the main one."""
    ref: str
    he_ref: str
    connection: str        # How it relates (e.g., "also discusses", "contrasts with")
    importance: str        # "primary", "secondary", "tangential"


@dataclass
class SearchStrategy:
    """
    The output of Step 2 - tells Step 3 what to do.
    """
    # What type of query is this?
    query_type: QueryType

    # The main source(s) to focus on
    primary_source: Optional[str] = None      # legacy single primary
    primary_sources: List[str] = field(default_factory=list)  # new list form
    primary_source_he: Optional[str] = None   # legacy
    primary_sources_he: List[str] = field(default_factory=list)

    # Why we chose this source
    reasoning: str = ""

    # Other relevant sugyos
    related_sugyos: List[RelatedSugya] = field(default_factory=list)

    # How to fetch sources
    fetch_strategy: FetchStrategy = FetchStrategy.TRICKLE_UP

    # How deep to go (Claude decides based on query)
    # "basic" / "standard" / "expanded" / "full"
    depth: str = "standard"

    # Confidence in our interpretation
    confidence: str = "high"  # "high", "medium", "low"

    # If low confidence, what to ask the user
    clarification_prompt: Optional[str] = None

    # Metadata
    sefaria_hits: int = 0
    hits_by_masechta: Dict[str, int] = field(default_factory=dict)

    # New metadata
    intent_score: float = 0.0               # 0..1 how confident our heuristic+LLM are
    preferred_domains: List[str] = field(default_factory=list)  # e.g., ["gemara","shulchan_aruch"]
    generated_at: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization (backwards compatible)."""
        return {
            "query_type": self.query_type.value,
            "primary_source": self.primary_source,
            "primary_sources": self.primary_sources,
            "primary_source_he": self.primary_source_he,
            "primary_sources_he": self.primary_sources_he,
            "reasoning": self.reasoning,
            "related_sugyos": [
                {
                    "ref": s.ref,
                    "he_ref": s.he_ref,
                    "connection": s.connection,
                    "importance": s.importance
                }
                for s in self.related_sugyos
            ],
            "fetch_strategy": self.fetch_strategy.value,
            "depth": self.depth,
            "confidence": self.confidence,
            "clarification_prompt": self.clarification_prompt,
            "sefaria_hits": self.sefaria_hits,
            "hits_by_masechta": self.hits_by_masechta,
            "intent_score": self.intent_score,
            "preferred_domains": self.preferred_domains,
            "generated_at": self.generated_at,
        }


# ==========================================
#  CONTEXTUAL DEPTH MAP (internal, used to interpret "basic"/etc)
# ==========================================
DEPTH_MAP = {
    QueryType.SUGYA_CONCEPT: {
        "basic": ["Gemara"],
        "standard": ["Gemara", "Rashi", "Tosafot"],
        "expanded": ["Rishonim", "Acharonim"],
        "full": ["All available commentaries"]
    },
    QueryType.HALACHA_TERM: {
        "basic": ["Shulchan Aruch"],
        "standard": ["Shulchan Aruch", "Mishnah Berurah", "Rishonim"],
        "expanded": ["Acharonim", "Teshuvot"],
        "full": ["Comprehensive halachic survey"]
    },
    QueryType.FREEFORM_TORAH_QUERY: {
        "basic": ["High-level sources"],
        "standard": ["Closest canonical sources"],
        "expanded": ["Survey across Shas"],
        "full": ["Comprehensive multi-source research"]
    }
}


# ==========================================
#  SEFARIA DATA GATHERING
# ==========================================


async def gather_sefaria_data(hebrew_term: str) -> Dict:
    """
    Phase 1: GATHER - Query Sefaria to understand where term appears.
    Returns raw data for Claude to analyze.
    """
    logger.info(f"[GATHER] Querying Sefaria for: {hebrew_term}")

    try:
        from tools.sefaria_client import get_sefaria_client, SearchResults
        client = get_sefaria_client()

        # Search for the term (cap at reasonable size)
        results = await client.search(hebrew_term, size=100)

        return {
            "query": hebrew_term,
            "total_hits": results.total_hits,
            "hits_by_category": results.hits_by_category,
            "hits_by_masechta": results.hits_by_masechta,
            "top_refs": results.top_refs[:20],
            "sample_hits": [
                {
                    "ref": h.ref,
                    "he_ref": h.he_ref,
                    "category": h.category,
                    "snippet": h.text_snippet[:200] if h.text_snippet else ""
                }
                for h in results.hits[:15]
            ]
        }
    except Exception as e:
        logger.error(f"[GATHER] Sefaria error: {e}", exc_info=True)
        return {
            "query": hebrew_term,
            "total_hits": 0,
            "hits_by_category": {},
            "hits_by_masechta": {},
            "top_refs": [],
            "sample_hits": [],
            "error": str(e)
        }


# ==========================================
#  CLAUDE CLIENT, CACHING, AND HELPERS
# ==========================================
_claude_client = None


def get_claude_client() -> Anthropic:
    """Get/create Claude client instance."""
    global _claude_client
    if _claude_client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        _claude_client = Anthropic(api_key=api_key)
    return _claude_client


# Simple in-memory cache for Claude outputs
# key -> (timestamp, parsed_json)
_claude_cache: Dict[str, Tuple[datetime, Dict]] = {}


def _cache_get(key: str) -> Optional[Dict]:
    entry = _claude_cache.get(key)
    if not entry:
        return None
    ts, value = entry
    if datetime.utcnow() - ts > timedelta(seconds=_CLAUDE_CACHE_TTL):
        _claude_cache.pop(key, None)
        return None
    return value


def _cache_set(key: str, value: Dict):
    _claude_cache[key] = (datetime.utcnow(), value)


def _sefaria_fingerprint(sefaria_data: Dict) -> str:
    """
    Create a simple fingerprint of Sefaria results to key the cache.
    Uses top_refs & hits_by_masechta counts.
    """
    top = ",".join(sefaria_data.get("top_refs", [])[:6])
    hits = json.dumps(sefaria_data.get("hits_by_masechta", {}), sort_keys=True, ensure_ascii=False)
    return f"{top}|{hits}"


def _make_cache_key(hebrew_term: str, sefaria_data: Dict) -> str:
    fp = _sefaria_fingerprint(sefaria_data)
    return f"{hebrew_term}::{fp}"


# ==========================================
#  CLAUDE PROMPTS
# ==========================================
ANALYSIS_SYSTEM_PROMPT = """You are a Torah scholar assistant helping to understand what a user is looking for when they search for a Hebrew term.

Your job: Given a Hebrew term and data about where it appears in Sefaria's corpus, determine:
1. What type of query is this?
2. What is the user most likely looking for?
3. What are the primary_source(s) (if any)?
4. Are there other important sugyos the user should know about?

IMPORTANT PRINCIPLES:
- Think like a chavrusa helping a fellow learner
- If multiple reasonable interpretations exist, pick the most common and explain
- If you're unsure, respond with confidence: "low" and provide a clarification_prompt
- Return well-formed JSON only
"""

ANALYSIS_USER_TEMPLATE = """The user searched for: "{hebrew_term}"

Here's what Sefaria found:
- Total hits: {total_hits}
- Hits by category: {hits_by_category}
- Hits by masechta: {hits_by_masechta}
- Top references: {top_refs}

Sample text snippets:
{sample_snippets}

Based on this, analyze:
1. What is the user most likely looking for?
2. What are the primary source(s) for this term (list if multiple)?
3. Are there other important related sugyos?
4. How deep should we go (basic/standard/expanded/full)?
5. How confident are you in this interpretation?

If you're not confident, supply a short clarification prompt.
Return JSON with keys:
 - query_type (one of the known values)
 - primary_sources (list of refs or empty list)
 - primary_sources_he (optional list)
 - reasoning
 - related_sugyos (list of objects)
 - depth
 - confidence
 - clarification_prompt (or null)
 - intent_score (0..1)
"""


# ==========================================
#  JSON PARSING / REPAIR
# ==========================================
def _repair_and_parse_json(text: str) -> Dict:
    """
    Attempt robust extraction and minor repairs to parse JSON from LLM output.
    Handles markdown fences, incomplete responses, and common JSON issues.
    """
    original = text
    original_length = len(text)
    
    try:
        # Step 1: Remove common markdown fences
        if "```json" in text:
            parts = text.split("```json", 1)
            if len(parts) > 1:
                text = parts[1].split("```", 1)[0]
        elif "```" in text:
            parts = text.split("```", 1)
            if len(parts) > 1:
                text = parts[1].split("```", 1)[0]

        # Step 2: Find the first { and last } to extract JSON block
        first = text.find("{")
        last = text.rfind("}")
        
        if first == -1 or last == -1 or last <= first:
            logger.error(f"[PARSE] No valid JSON braces found in response")
            logger.debug(f"[PARSE] Original text ({original_length} chars):\n{original}")
            return {}
            
        candidate = text[first:last+1]
        logger.debug(f"[PARSE] Extracted JSON candidate ({len(candidate)} chars)")

        # Step 3: Quick fixes for common issues
        # Replace smart quotes & single quotes
        candidate = candidate.replace("\u201c", '"').replace("\u201d", '"')
        candidate = candidate.replace("\u2018", "'").replace("\u2019", "'")
        candidate = candidate.replace("'", '"')  # Replace single quotes with double
        
        # Remove trailing commas before closing brackets/braces
        candidate = re.sub(r",\s*([\]}])", r"\1", candidate)

        # Step 4: Try to parse
        try:
            parsed = json.loads(candidate)
            logger.info(f"[PARSE] Successfully parsed JSON on first attempt")
            return parsed
        except json.JSONDecodeError as e:
            logger.warning(f"[PARSE] Initial JSON parse failed: {e}")
            logger.debug(f"[PARSE] Failed candidate:\n{candidate}")
            
            # Step 5: Progressive trimming attempts (handle truncated responses)
            for i in range(1, 6):
                trim_length = i * 10  # Try trimming 10, 20, 30, 40, 50 chars
                if len(candidate) <= trim_length:
                    break
                    
                trimmed = candidate[:-trim_length]
                # Try to close any unclosed braces
                open_count = trimmed.count("{") - trimmed.count("}")
                if open_count > 0:
                    trimmed += "}" * open_count
                    
                try:
                    parsed = json.loads(trimmed)
                    logger.warning(f"[PARSE] Succeeded after trimming {trim_length} chars")
                    return parsed
                except json.JSONDecodeError:
                    continue
            
            # Step 6: Failed all attempts
            logger.error("[PARSE] All JSON parse attempts failed")
            logger.error(f"[PARSE] Original response ({original_length} chars):\n{original}")
            logger.error(f"[PARSE] Extracted candidate ({len(candidate)} chars):\n{candidate[:500]}...")
            return {}
            
    except Exception as e:
        logger.error(f"[PARSE] Unexpected error parsing JSON: {e}", exc_info=True)
        logger.error(f"[PARSE] Original text:\n{original}")
        return {}


# ==========================================
#  DETERMINISTIC SHORT-CIRCUIT (skip Claude where possible)
# ==========================================
def _detect_explicit_daf(hebrew_term: str, sefaria_data: Dict) -> Optional[str]:
    """
    Detect explicit daf-like references in the user term or in top_refs.
    Returns a single top ref (string) if found.
    """
    # crude regex for "מקום שם 9א" or "כתובות ט" or "kesubos 9a"
    # We check both the hebrew_term and the top_refs list
    daf_pattern = re.compile(r"\b\d+[אב]\b|\b\d+[ab]\b", re.IGNORECASE)
    # check top_refs first
    top_refs = sefaria_data.get("top_refs", [])
    if len(top_refs) == 1:
        return top_refs[0]
    # check hebrew_term for digits with hebrew/english amud letter
    if daf_pattern.search(hebrew_term):
        # If term contains a daf token, return it as directive (let analyze decide exact ref)
        return hebrew_term
    return None


def deterministic_strategy_from_sefaria(hebrew_term: str, sefaria_data: Dict) -> Optional[SearchStrategy]:
    """
    When Sefaria signals a dominant primary, create a deterministic strategy and skip Claude.
    Rules:
      - If total_hits == 1 -> deterministic
      - If one masechta contains > _SEFARIA_DOMINANT_THRESHOLD fraction -> deterministic
      - If explicit daf detected -> deterministic (DIRECT)
    """
    total = sefaria_data.get("total_hits", 0)
    hits_by_masechta = sefaria_data.get("hits_by_masechta", {}) or {}
    top_refs = sefaria_data.get("top_refs", []) or []

    # 1) single hit
    if total == 1 and top_refs:
        primary = top_refs[0]
        s = SearchStrategy(
            query_type=QueryType.SUGYA_CONCEPT,
            primary_source=primary,
            primary_sources=[primary],
            reasoning="Deterministic: single Sefaria hit",
            fetch_strategy=FetchStrategy.DIRECT,
            depth="standard",
            confidence="high",
            sefaria_hits=total,
            hits_by_masechta=hits_by_masechta,
            intent_score=0.95,
            generated_at=datetime.utcnow().isoformat()
        )
        return s

    # 2) dominant masechta
    if total > 0 and hits_by_masechta:
        max_masechta, max_hits = max(hits_by_masechta.items(), key=lambda x: x[1])
        if (max_hits / total) >= _SEFARIA_DOMINANT_THRESHOLD and top_refs:
            primary = top_refs[0]
            s = SearchStrategy(
                query_type=QueryType.SUGYA_CONCEPT,
                primary_source=primary,
                primary_sources=[primary],
                reasoning=f"Deterministic: {max_masechta} contains {(max_hits/total):.0%} of hits",
                fetch_strategy=FetchStrategy.TRICKLE_UP,
                depth="standard",
                confidence="high",
                sefaria_hits=total,
                hits_by_masechta=hits_by_masechta,
                intent_score=0.9,
                generated_at=datetime.utcnow().isoformat()
            )
            return s

    # 3) explicit daf
    explicit = _detect_explicit_daf(hebrew_term, sefaria_data)
    if explicit:
        # We treat as a direct fetch but still let Step 3 parse exact ref
        s = SearchStrategy(
            query_type=QueryType.DAF_REFERENCE,
            primary_source=explicit,
            primary_sources=[explicit],
            reasoning="Deterministic: explicit daf detected",
            fetch_strategy=FetchStrategy.DIRECT,
            depth="basic",
            confidence="high",
            sefaria_hits=total,
            hits_by_masechta=hits_by_masechta,
            intent_score=0.95,
            generated_at=datetime.utcnow().isoformat()
        )
        return s

    return None


# ==========================================
#  CLAUDE ANALYSIS (main)
# ==========================================
async def analyze_with_claude(hebrew_term: str, sefaria_data: Dict) -> SearchStrategy:
    """
    Phase 2: ANALYZE - Have Claude interpret the query.
    Uses caching and deterministic shortcuts to minimize API calls.
    """
    logger.info(f"[ANALYZE] Starting analysis for: {hebrew_term}")

    # 0) Quick deterministic short-circuit
    try:
        deterministic = deterministic_strategy_from_sefaria(hebrew_term, sefaria_data)
        if deterministic:
            logger.info("[ANALYZE] Deterministic strategy decided - skipping Claude.")
            return deterministic
    except Exception as e:
        logger.warning(f"[ANALYZE] deterministic shortcut failed: {e}", exc_info=True)

    # 1) Check cache
    cache_key = _make_cache_key(hebrew_term, sefaria_data)
    cached = _cache_get(cache_key)
    if cached:
        logger.info("[ANALYZE] Using cached Claude analysis.")
        return _make_strategy_from_parsed_analysis(cached, sefaria_data)

    # 2) If Claude disabled by env, fallback
    if not USE_CLAUDE:
        logger.info("[ANALYZE] USE_CLAUDE disabled - using fallback strategy.")
        return _fallback_strategy(hebrew_term, sefaria_data)

    # 3) Build prompt and call Claude
    client = get_claude_client()

    sample_snippets = ""
    for i, hit in enumerate(sefaria_data.get("sample_hits", [])[:8], 1):
        sample_snippets += f"{i}. {hit['ref']}: {hit['snippet'][:150]}...\n"
    if not sample_snippets:
        sample_snippets = "(No sample text available)"

    user_message = ANALYSIS_USER_TEMPLATE.format(
        hebrew_term=hebrew_term,
        total_hits=sefaria_data.get("total_hits", 0),
        hits_by_category=json.dumps(sefaria_data.get("hits_by_category", {}), ensure_ascii=False),
        hits_by_masechta=json.dumps(sefaria_data.get("hits_by_masechta", {}), ensure_ascii=False),
        top_refs=sefaria_data.get("top_refs", [])[:10],
        sample_snippets=sample_snippets
    )

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2500,
            system=ANALYSIS_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}]
        )

        # The SDK returns content in that path
        response_text = response.content[0].text
        # CRITICAL: Log FULL response for debugging parse failures
        logger.info(f"[ANALYZE] Claude response length: {len(response_text)} characters")
        logger.debug(f"[ANALYZE] Claude FULL response:\n{response_text}")

        # Parse with robust repair
        parsed = _repair_and_parse_json(response_text)

        # If parsed empty, try fallback
        if not parsed:
            logger.warning("[ANALYZE] Claude parse returned empty - falling back.")
            return _fallback_strategy(hebrew_term, sefaria_data)

        # Cache parsed analysis
        _cache_set(cache_key, parsed)

        # Convert parsed analysis into SearchStrategy
        return _make_strategy_from_parsed_analysis(parsed, sefaria_data)

    except Exception as e:
        logger.error(f"[ANALYZE] Claude error: {e}", exc_info=True)
        # On any error, return fallback strategy
        return _fallback_strategy(hebrew_term, sefaria_data)


def _make_strategy_from_parsed_analysis(analysis: Dict, sefaria_data: Dict) -> SearchStrategy:
    """
    Convert parsed JSON (from Claude or cache) to SearchStrategy with validation.
    """
    # Validate & normalize query_type
    qtype_raw = (analysis.get("query_type") or "").lower()
    qtype = QueryType.UNKNOWN
    for qt in QueryType:
        if qt.value == qtype_raw:
            qtype = qt
            break
    # If unknown but there are many top_refs, treat as cross reference
    if qtype == QueryType.UNKNOWN and len(sefaria_data.get("top_refs", [])) > 3:
        qtype = QueryType.SUGYA_CROSS_REFERENCE

    primary_sources = analysis.get("primary_sources") or []
    if isinstance(primary_sources, str):
        primary_sources = [primary_sources]
    primary_sources_he = analysis.get("primary_sources_he") or []
    if isinstance(primary_sources_he, str):
        primary_sources_he = [primary_sources_he]

    # Build strategy
    strategy = SearchStrategy(
        query_type=qtype,
        primary_source=analysis.get("primary_source") or (primary_sources[0] if primary_sources else None),
        primary_sources=primary_sources,
        primary_source_he=analysis.get("primary_source_he"),
        primary_sources_he=primary_sources_he,
        reasoning=analysis.get("reasoning", ""),
        depth=analysis.get("depth", "standard"),
        confidence=analysis.get("confidence", "medium"),
        clarification_prompt=analysis.get("clarification_prompt"),
        sefaria_hits=sefaria_data.get("total_hits", 0),
        hits_by_masechta=sefaria_data.get("hits_by_masechta", {}),
        intent_score=float(analysis.get("intent_score", 0.0)),
        preferred_domains=analysis.get("preferred_domains", []),
        generated_at=datetime.utcnow().isoformat()
    )

    # Related sugyos
    for sug in analysis.get("related_sugyos", []):
        try:
            strategy.related_sugyos.append(RelatedSugya(
                ref=sug.get("ref", ""),
                he_ref=sug.get("he_ref", ""),
                connection=sug.get("connection", ""),
                importance=sug.get("importance", "secondary")
            ))
        except Exception:
            continue

    # Map some query types to fetch strategy defaults
    if strategy.query_type == QueryType.DAF_REFERENCE:
        strategy.fetch_strategy = FetchStrategy.DIRECT
        strategy.depth = strategy.depth or "basic"
    elif strategy.query_type == QueryType.HALACHA_TERM:
        strategy.fetch_strategy = FetchStrategy.SURVEY
    elif strategy.query_type == QueryType.KLAL:
        strategy.fetch_strategy = FetchStrategy.TRICKLE_UP
        strategy.depth = strategy.depth or "expanded"
    else:
        # default mapping
        if strategy.depth == "full":
            strategy.fetch_strategy = FetchStrategy.HYBRID

    # Hail-Mary check: if confidence low and no primaries found -> tag HAIL_MARY
    if strategy.confidence == "low" and not strategy.primary_sources:
        strategy.fetch_strategy = FetchStrategy.HAIL_MARY

    return strategy


# ==========================================
#  FALLBACK STRATEGY
# ==========================================
def _fallback_strategy(hebrew_term: str, sefaria_data: Dict) -> SearchStrategy:
    """
    Create an intelligent fallback strategy when Claude analysis fails.
    Uses Torah scholarship principles to identify Gemara sources vs commentaries.
    """
    logger.info("[ANALYZE] Using intelligent fallback strategy")
    
    total_hits = sefaria_data.get("total_hits", 0)
    hits_by_masechta = sefaria_data.get("hits_by_masechta", {}) or {}
    hits_by_category = sefaria_data.get("hits_by_category", {}) or {}
    top_refs = sefaria_data.get("top_refs", []) or []
    
    # Identify primary masechta
    primary_masechta = None
    masechta_hits = 0
    if hits_by_masechta:
        primary_masechta, masechta_hits = max(hits_by_masechta.items(), key=lambda x: x[1])
    
    # CRITICAL: Prefer Gemara sources over commentaries
    # A yeshiva bochur wants the Gemara, not R' Akiva Eiger's commentary
    gemara_source = None
    commentary_source = None
    
    # Categories that indicate actual Gemara text
    gemara_categories = {"Talmud", "Mishnah", "Tosefta"}
    # Categories that are commentaries
    commentary_categories = {"Talmud Commentary", "Mishnah Commentary", "Rishonim", "Acharonim", "Halakhah", "Responsa"}
    
    for ref in top_refs:
        ref_lower = ref.lower()
        
        # Check if it's actual Gemara/Mishnah
        # Gemara refs typically look like: "Ketubot 9a" or "Pesachim 10a"
        # Commentary refs look like: "Rashi on Ketubot 9a" or "Tosafot on Pesachim 10a"
        is_gemara = False
        is_commentary = False
        
        # Simple heuristic: if ref contains " on " it's a commentary
        if " on " in ref or "Chiddushei" in ref or "Commentary" in ref:
            is_commentary = True
            if not commentary_source:
                commentary_source = ref
        else:
            # Check if it matches a direct masechta reference pattern
            # Look for masechtot names without commentary markers
            masechtot = ["Pesachim", "Ketubot", "Niddah", "Kiddushin", "Chullin", "Bava Kamma", 
                        "Bava Metzia", "Bava Batra", "Sanhedrin", "Shabbat", "Eruvin", "Gittin"]
            for masechta in masechtot:
                if masechta in ref and not any(x in ref for x in ["Rashi", "Tosafot", "Chiddushei", "Commentary"]):
                    is_gemara = True
                    break
        
        if is_gemara and not gemara_source:
            gemara_source = ref
        
        # If we have both, we can stop looking
        if gemara_source and commentary_source:
            break
    
    # Choose primary source: Gemara first, then commentary, then first result
    primary_source = gemara_source or commentary_source or (top_refs[0] if top_refs else None)
    
    # Determine confidence based on hit patterns
    confidence = "low"
    reasoning_parts = []
    
    if total_hits == 0:
        confidence = "very_low"
        reasoning_parts.append("No Sefaria hits found")
    elif gemara_source:
        confidence = "medium"
        reasoning_parts.append(f"Identified Gemara source: {gemara_source}")
    elif primary_masechta and masechta_hits > 5:
        confidence = "medium"
        reasoning_parts.append(f"Strong concentration in {primary_masechta} ({masechta_hits} hits)")
    else:
        reasoning_parts.append(f"Found {total_hits} hits across multiple sources")
    
    if primary_masechta:
        reasoning_parts.append(f"Primary masechta: {primary_masechta}")
    
    reasoning = " | ".join(reasoning_parts) + " | (Fallback: Claude failed)"
    
    # Determine query type based on hit distribution
    query_type = QueryType.SUGYA_CONCEPT
    if "Halakhah" in hits_by_category and hits_by_category.get("Halakhah", 0) > total_hits * 0.5:
        query_type = QueryType.HALACHA_TERM
    elif len(hits_by_masechta) == 1:
        query_type = QueryType.SUGYA_CONCEPT
    else:
        query_type = QueryType.FREEFORM_TORAH_QUERY
    
    logger.info(f"[FALLBACK] Selected {query_type.value}, primary: {primary_source}, confidence: {confidence}")
    
    s = SearchStrategy(
        query_type=query_type,
        primary_source=primary_source,
        primary_sources=[primary_source] if primary_source else [],
        reasoning=reasoning,
        fetch_strategy=FetchStrategy.TRICKLE_UP,
        depth="standard",
        confidence=confidence,
        clarification_prompt=f"I found {total_hits} references. Could you tell me more about what you're looking for?",
        sefaria_hits=total_hits,
        hits_by_masechta=hits_by_masechta,
        intent_score=0.4 if confidence == "medium" else 0.2,
        generated_at=datetime.utcnow().isoformat()
    )
    return s


# ==========================================
#  MAIN STEP 2 FUNCTION
# ==========================================
async def understand(hebrew_term: str, original_query: str = None) -> SearchStrategy:
    """
    Main entry point for Step 2: UNDERSTAND
    """
    logger.info("=" * 80)
    logger.info("STEP 2: UNDERSTAND")
    logger.info("=" * 80)
    logger.info(f"  Hebrew term: {hebrew_term}")
    if original_query:
        logger.info(f"  Original query: {original_query}")

    # Phase 1: GATHER - Get Sefaria data
    logger.info("\n[Phase 1: GATHER]")
    sefaria_data = await gather_sefaria_data(hebrew_term)

    logger.info(f"  Sefaria hits: {sefaria_data.get('total_hits', 0)}")
    logger.info(f"  By masechta: {sefaria_data.get('hits_by_masechta', {})}")

    # Phase 2: ANALYZE - deterministic shortcut + Claude
    logger.info("\n[Phase 2: ANALYZE]")
    strategy = await analyze_with_claude(hebrew_term, sefaria_data)

    # Phase 3: DECIDE (implicit in strategy creation)
    logger.info("\n[Phase 3: DECIDE]")
    logger.info(f"  Query type: {strategy.query_type.value}")
    logger.info(f"  Primary sources: {strategy.primary_sources or strategy.primary_source}")
    logger.info(f"  Fetch strategy: {strategy.fetch_strategy.value}")
    logger.info(f"  Depth: {strategy.depth}")
    logger.info(f"  Confidence: {strategy.confidence}")
    logger.info(f"  Intent score: {strategy.intent_score}")

    if strategy.related_sugyos:
        logger.info(f"  Related sugyos: {len(strategy.related_sugyos)}")
        for s in strategy.related_sugyos:
            logger.info(f"    - {s.ref} ({s.importance}): {s.connection}")

    if strategy.clarification_prompt:
        logger.info(f"  Clarification needed: {strategy.clarification_prompt}")

    logger.info("=" * 80)
    return strategy


# ==========================================
#  TESTING
# ==========================================
async def test_understand():
    """Test the understand function (quick smoke tests)."""
    print("=" * 70)
    print("STEP 2 TEST: UNDERSTAND")
    print("=" * 70)

    test_cases = [
        ("חזקת הגוף", "chezkas haguf"),
        ("מיגו", "migu"),
        ("ברי ושמא", "bari vishma"),
        ("כתובות ט", "kesubos 9"),
    ]

    for hebrew, original in test_cases:
        print(f"\n{'='*60}")
        print(f"Testing: {hebrew} ({original})")
        print("=" * 60)

        strategy = await understand(hebrew, original)

        print(f"\nResult:")
        print(f"  Type: {strategy.query_type.value}")
        print(f"  Primary(s): {strategy.primary_sources or strategy.primary_source}")
        print(f"  Reasoning: {strategy.reasoning[:100]}...")
        print(f"  Confidence: {strategy.confidence}")

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%H:%M:%S'
    )

    asyncio.run(test_understand())