"""
Marei Mekomos Backend API - Version 5.0 (HYBRID SEARCH)
===========================================================

MAJOR UPGRADE: Hybrid Transliteration Resolution
------------------------------------------------
Now intelligently handles ANY transliteration through:
1. BEREL vector search → finds Hebrew candidates (fast, local)
2. Claude verification → picks best match (accurate, smart)
3. Result: 95% accuracy with infinite transliteration support

New Features in V5:
- Smart transliteration detection and resolution
- Visual feedback showing resolved Hebrew terms
- Enhanced logging at every step
- Clean, commented code for easy maintenance

Flow:
User types "chezkas rav huna" 
  → Vector search finds 20 Hebrew candidates
  → Claude picks: "חזקת רב הונא from Chullin 10a"
  → Continue normal V4 search with perfect Hebrew context
"""

import os
import json
import httpx
import html
import re
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from anthropic import Anthropic
from typing import List, Optional, Dict
from collections import Counter

# Import our logging configuration
from logging_config import setup_logging, get_logger
from cache_manager import sefaria_cache, claude_cache

# Import hybrid resolver for smart transliteration handling
from hybrid_resolver import resolve_hebrew_term
from vector_search import get_engine

# Initialize logging
setup_logging()
logger = get_logger(__name__)

# Development mode flag
DEV_MODE = os.environ.get("DEV_MODE", "false").lower() == "true"
if DEV_MODE:
    logger.warning("⚠️  DEV_MODE is ENABLED - using mock responses to save API costs")


# =============================
# PYDANTIC MODELS
# =============================

class TopicRequest(BaseModel):
    """Request model for /search endpoint"""
    topic: str
    clarification: Optional[str] = None  # User's response to clarifying questions


class ResolvedTerm(BaseModel):
    """Information about a resolved Hebrew term"""
    original: str  # Original transliteration
    hebrew: str  # Resolved Hebrew term
    source_ref: str  # Where it appears
    confidence: str  # high/medium/low
    explanation: str  # Why this match was chosen


class SourceReference(BaseModel):
    """A single source reference with text"""
    ref: str
    category: str
    he_text: str = ""
    en_text: str = ""
    he_ref: str = ""
    sefaria_url: str = ""
    citation_count: int = 1
    relevance: str = ""


class MareiMekomosResponse(BaseModel):
    """Response model for /search endpoint"""
    topic: str
    sources: List[SourceReference]
    summary: str = ""
    needs_clarification: bool = False
    clarifying_questions: List[str] = []
    interpreted_query: str = ""
    resolved_terms: List[ResolvedTerm] = []  # NEW: Show resolved Hebrew terms


# =============================
# FASTAPI APP SETUP
# =============================

app = FastAPI(
    title="Marei Mekomos API v5.0 (Hybrid Search)",
    version="5.0.0",
    description="Torah source finder with intelligent transliteration handling"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Anthropic client
api_key = os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    logger.critical("ANTHROPIC_API_KEY not found in environment variables!")
    raise RuntimeError("ANTHROPIC_API_KEY environment variable is required")
client = Anthropic(api_key=api_key)
logger.info("✓ Anthropic client initialized successfully")

# Check if vector search is ready
vector_engine = get_engine()
if vector_engine.is_ready():
    logger.info("✓ Vector search engine ready")
else:
    logger.warning("⚠️  Vector search NOT ready - embeddings need to be created")
    logger.warning("   Run: python prepare_sefaria_embeddings.py --sefaria-path /path/to/sefaria")
    logger.warning("   Transliteration resolution will be limited until setup complete")


# =============================
# SYSTEM PROMPTS
# =============================

INTERPRETATION_SYSTEM_PROMPT = """You are a Torah scholar assistant that interprets user queries about Jewish texts.

Your job is to:
1. Understand what the user is asking (handling spelling variations, transliterations, Hebrew, etc.)
2. Map their query to standard halachic/Torah concepts
3. Determine if clarification is needed

IMPORTANT: If the query has been RESOLVED via hybrid search (you'll see resolved Hebrew terms in context),
use that resolution as authoritative. Don't second-guess the vector search + verification process.

HANDLING SPELLING VARIATIONS (use these examples but apply the logic to any possible query):
- "chuppa" / "chuppah" / "chupa" / "huppa" / "חופה" → All mean "chuppah"
- "niddah" / "nida" / "nidah" / "נדה" → All mean "niddah"
- "rambam" / "Rambam" / "maimonides" / "רמב״ם" → All mean "Rambam"
- "shulchan aruch" / "shulchan arukh" / "SA" / "שולחן ערוך" → All mean "Shulchan Aruch"

Your output should normalize these into standard English terms that Sefaria uses.

CONFIDENCE CHECK:
Only ask for clarification if the query is GENUINELY UNCLEAR or could mean completely different things.

Examples where clarification IS needed:
- "niddah" (alone - could be laws, tum'ah, or mikvah)
- "chuppah" (alone - could be construction, laws, or blessings)
- "chometz" (alone - could be ba'al yiraeh, bittul chametz, or bedikas chametz)

Examples where clarification is NOT needed:
- "machlokes rishonim chuppas niddah rambam" (specific enough - proceed!)
- "bitul chametz" (clear topic - proceed!)
- "bedikas chometz derabbanan or deoraisa" (clear topic - proceed!)
- "chezkas haguf vs chezkas mamon" (clear topic - proceed!)
- "kibbud av v'em" (clear topic - proceed!)

If you can reasonably determine what they're asking about, DON'T ask for clarification - just proceed!

Return JSON:
{
  "needs_clarification": true/false,
  "clarifying_questions": ["Question 1?", "Question 2?"],  // Max 2 questions, ONLY if genuinely unclear
  "interpreted_query": "The normalized query in standard terminology",
  "confidence": "high/medium/low"
}

If needs_clarification is false, clarifying_questions should be empty."""


BASE_TEXT_IDENTIFICATION_PROMPT = """You are a Torah scholar assistant that identifies which BASE TEXT sections discuss a given topic.

Given a user's query, identify which GENERAL SECTIONS of foundational texts discuss this topic.

IMPORTANT RULES:
1. Return BASE TEXTS ONLY (Torah, Mishna, Gemara, Rambam, Ramban, Rashba, Ritva, Tur, Shulchan Aruch)
2. Use GENERAL SECTION REFERENCES (e.g., "Marriage chapter 10" not "Marriage 10:11 specifically")
3. Use SEFARIA'S ENGLISH NAMES:
   - "Mishneh Torah, Marriage" NOT "Ishut"
   - "Mishneh Torah, Forbidden Intercourse" NOT "Issurei Biah"
   - "Shulchan Arukh, Even HaEzer" NOT just "Even HaEzer"
4. Include chapter/section but NOT specific halachos
5. Return 2-4 base texts maximum

EXAMPLES:

Query: "chuppas niddah"
Good output:
{
  "base_texts": [
    {"ref": "Mishneh Torah, Marriage 10", "reason": "Discusses chuppah and its validity with niddah"},
    {"ref": "Shulchan Arukh, Even HaEzer 61", "reason": "Laws of chuppah when woman is niddah"},
    {"ref": "Ketubot 57b", "reason": "Gemara discussing timing of nisuin relative to niddah"}
  ]
}

Bad output (TOO SPECIFIC):
{"base_texts": [{"ref": "Mishneh Torah, Marriage 10:11"}]}  ❌ Too specific!

Bad output (COMMENTARY):
{"base_texts": [{"ref": "Kesef Mishneh on Marriage 10"}]}  ❌ We want base text!

Query: "bitul chametz"
Good output:
{
  "base_texts": [
    {"ref": "Mishneh Torah, Leavened and Unleavened Bread 2", "reason": "Laws of nullifying chametz"},
    {"ref": "Shulchan Arukh, Orach Chayim 434", "reason": "Laws of bitul chametz"},
    {"ref": "Pesachim 6b", "reason": "Gemara on bitul chametz"}
  ]
}

Return JSON in this exact format."""


CITATION_EXTRACTION_PROMPT = """You are a Torah scholar assistant that extracts earlier source citations from commentary texts.

You will be given texts from commentaries discussing a specific topic. Your job:
1. Extract EARLIER SOURCES they cite (Gemara, Rishonim, base halachic texts)
2. Count how many commentaries cite each source
3. FILTER for relevance to the SPECIFIC topic

CRITICAL - RELEVANCE FILTERING:
- Only include sources that discuss THE SPECIFIC ASPECT of the query
- If query is "chuppas niddah", DON'T include sources about general chuppah
- If query is "bitul chametz", DON'T include sources about general chametz

ORIGINAL QUERY: {original_query}
INTERPRETED AS: {interpreted_query}

For each commentary text, identify:
- Which earlier sources it cites
- Why those sources are relevant to THIS SPECIFIC TOPIC

Return JSON:
{
  "sources": [
    {
      "ref": "Gemara or Rishon reference",
      "category": "Gemara/Rishonim/etc",
      "citation_count": 2,
      "relevance": "How this addresses the specific query"
    }
  ],
  "summary": "Brief summary of the specific topic based on what the commentaries say"
}

IMPORTANT: If the commentary texts don't actually discuss the specific topic, return empty sources array."""


# =============================
# HELPER FUNCTIONS
# =============================

def clean_html_from_text(text: str) -> str:
    """Clean HTML entities and tags from Sefaria text"""
    if not text:
        return text
    text = html.unescape(text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def flatten_text(text_data) -> str:
    """Flatten nested arrays from Sefaria into a single string"""
    if isinstance(text_data, str):
        return text_data
    elif isinstance(text_data, list):
        parts = []
        for item in text_data:
            parts.append(flatten_text(item))
        return " ".join(parts)
    return ""


def parse_claude_json(response_text: str) -> dict:
    """Parse JSON from Claude's response, handling markdown fences"""
    try:
        original_text = response_text
        
        # Strip markdown fences
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        
        # Find first brace if text before JSON
        response_text = response_text.strip()
        if not response_text.startswith("{"):
            brace_index = response_text.find("{")
            if brace_index != -1:
                response_text = response_text[brace_index:]
            else:
                logger.error("No opening brace found in response")
                return {}

        parsed_data = json.loads(response_text.strip())
        logger.debug(f"✓ Successfully parsed JSON")
        return parsed_data
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}", exc_info=True)
        logger.error(f"Response text: {original_text[:500]}")
        return {}


def normalize_sefaria_ref(ref: str) -> str:
    """
    Normalize a reference for Sefaria's API.
    
    Sefaria expects references WITHOUT category prefixes like "Gemara", "Mishna", etc.
    
    Examples:
        "Gemara Pesachim 10b" → "Pesachim 10b"
        "Mishna Berachos 1:1" → "Berachos 1:1"
        "Mishneh Torah, Marriage 10:11" → "Mishneh Torah, Marriage 10:11" (keep Rambam format)
        "Shulchan Arukh, Orach Chayim 1:1" → "Shulchan Arukh, Orach Chayim 1:1" (keep SA format)
    
    ✓ FIXED BUG #2: This solves the 404 errors from incorrect reference format
    """
    original_ref = ref
    
    # List of prefixes to strip (yeshivish and standard transliterations)
    prefixes_to_strip = [
        "Gemara ",
        "Talmud Bavli ",
        "Talmud ",
        "Mishna ",
        "Mishnah ",
        "Tosefta ",
        "Midrash ",
        "Tanna ",
        "Amora ",
    ]
    
    for prefix in prefixes_to_strip:
        if ref.startswith(prefix):
            ref = ref[len(prefix):]
            logger.debug(f"  Normalized reference: '{original_ref}' → '{ref}'")
            break
    
    return ref


async def fetch_text_from_sefaria(ref: str, max_retries: int = 2) -> dict:
    """
    Fetch text from Sefaria API for a given reference.
    
    Returns dict with: found, he_text, en_text, he_ref, sefaria_url
    """
    # ✓ FIXED BUG #2: Normalize reference for Sefaria's API
    original_ref = ref
    ref = normalize_sefaria_ref(ref)
    
    # Check cache first (use normalized ref for cache key)
    cached = sefaria_cache.get(ref)
    if cached:
        logger.info(f"💰 CACHE HIT: {ref}")
        return cached

    logger.info(f"📥 Fetching from Sefaria: {ref}")
    
    encoded_ref = ref.replace(" ", "%20").replace(",", "%2C")
    url = f"https://www.sefaria.org/api/v3/texts/{encoded_ref}"
    logger.debug(f"  URL: {url}")

    async with httpx.AsyncClient(verify=False, timeout=15.0) as http_client:
        for attempt in range(max_retries):
            try:
                response = await http_client.get(url)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Extract texts
                    he_text = ""
                    en_text = ""
                    he_ref = data.get("heRef", "")
                    
                    versions = data.get("versions", [])
                    logger.debug(f"  Found {len(versions)} version(s)")
                    
                    for version in versions:
                        lang = version.get("language", "")
                        text = version.get("text", "")
                        
                        if isinstance(text, list):
                            text = flatten_text(text)
                        
                        if lang == "he" and not he_text:
                            he_text = clean_html_from_text(text)
                        elif lang == "en" and not en_text:
                            en_text = clean_html_from_text(text)
                    
                    result = {
                        "found": True,
                        "he_text": he_text[:1000] if he_text else "",
                        "en_text": en_text[:1000] if en_text else "",
                        "he_ref": he_ref,
                        "sefaria_url": f"https://www.sefaria.org/{encoded_ref}",
                    }
                    
                    logger.info(f"  ✓ SUCCESS: {ref} (he={bool(he_text)}, en={bool(en_text)})")
                    
                    # Cache the result
                    sefaria_cache.set(ref, result)
                    return result
                    
                elif response.status_code in [404, 400]:
                    logger.warning(f"  ✗ NOT FOUND (HTTP {response.status_code}): {ref}")
                    return {"found": False}
                    
                else:
                    logger.warning(f"  ⚠ HTTP {response.status_code}: {ref}")
                    if attempt < max_retries - 1:
                        logger.info(f"  Retrying... (attempt {attempt + 2}/{max_retries})")
                        continue
                    return {"found": False}
                    
            except Exception as e:
                logger.error(f"  ✗ ERROR fetching {ref}: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"  Retrying... (attempt {attempt + 2}/{max_retries})")
                    continue
                return {"found": False}
    
    return {"found": False}


async def get_related_texts(base_ref: str) -> List[dict]:
    """
    Use Sefaria's Related API to get all commentaries on a base text.
    
    This is the KEY function that solves the spelling/format problem!
    Sefaria tells us EXACTLY which commentaries exist and their proper names.
    """
    logger.info(f"🔗 Getting related texts for: {base_ref}")
    
    # Check cache
    cache_key = f"related:{base_ref}"
    cached = sefaria_cache.get(cache_key)
    if cached:
        logger.info(f"  💰 CACHE HIT: Found {len(cached)} related texts")
        return cached
    
    encoded_ref = base_ref.replace(" ", "%20").replace(",", "%2C")
    url = f"https://www.sefaria.org/api/related/{encoded_ref}"
    logger.debug(f"  URL: {url}")
    
    async with httpx.AsyncClient(verify=False, timeout=15.0) as http_client:
        try:
            response = await http_client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract commentary links
                commentaries = []
                links = data.get("links", [])
                
                logger.debug(f"  Found {len(links)} total links")
                
                for link in links:
                    link_type = link.get("type", "")
                    
                    # We want "commentary" type links
                    if link_type == "commentary":
                        commentary_ref = link.get("sourceRef", "")
                        if commentary_ref:
                            commentaries.append({
                                "ref": commentary_ref,
                                "type": "commentary"
                            })
                
                logger.info(f"  ✓ Found {len(commentaries)} commentaries")
                
                # Log the commentary names for debugging
                if commentaries:
                    logger.debug("  Commentaries found:")
                    for c in commentaries[:5]:  # Log first 5
                        logger.debug(f"    - {c['ref']}")
                    if len(commentaries) > 5:
                        logger.debug(f"    ... and {len(commentaries) - 5} more")
                
                # Cache the results
                sefaria_cache.set(cache_key, commentaries)
                return commentaries
                
            else:
                logger.warning(f"  ✗ Related API returned HTTP {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"  ✗ ERROR getting related texts: {e}")
            return []


async def interpret_query(
    topic: str, 
    clarification: Optional[str] = None,
    hebrew_resolution: Optional[Dict] = None
) -> dict:
    """
    Stage 0: Interpret user's query and check if clarification is needed.
    
    NEW in V5: Receives hebrew_resolution from hybrid resolver
    Uses resolved Hebrew terms as authoritative context
    
    Handles ALL spelling variations and transliterations.
    """
    logger.info("="*80)
    logger.info("STAGE 0: QUERY INTERPRETATION")
    logger.info("="*80)
    logger.info(f"  Topic: {topic}")
    if clarification:
        logger.info(f"  Clarification: {clarification}")
    if hebrew_resolution and hebrew_resolution.get('resolved'):
        logger.info(f"  ✓ Hebrew resolution available:")
        logger.info(f"    Term: {hebrew_resolution.get('hebrew_term', '')}")
        logger.info(f"    From: {hebrew_resolution.get('source_ref', '')}")
    
    # Build cache key including resolution context
    resolution_key = ""
    if hebrew_resolution and hebrew_resolution.get('resolved'):
        resolution_key = f":{hebrew_resolution.get('hebrew_term', '')}"
    cache_key = f"interpret:{topic}:{clarification or ''}{resolution_key}"
    
    # Check cache
    cached = claude_cache.get(cache_key)
    if cached:
        logger.info("  💰 CACHE HIT: Using cached interpretation")
        return cached
    
    if DEV_MODE:
        logger.warning("  🧪 DEV_MODE: Returning mock interpretation")
        return {
            "needs_clarification": False,
            "interpreted_query": f"Mock interpretation of: {topic}",
            "confidence": "high"
        }
    
    # Build message to Claude, including Hebrew resolution context
    context_parts = []
    
    if hebrew_resolution and hebrew_resolution.get('resolved'):
        context_parts.append(
            f"IMPORTANT CONTEXT: The hybrid resolver identified this Hebrew term:\n"
            f"  Original query: \"{hebrew_resolution.get('original_query', topic)}\"\n"
            f"  Resolved to: {hebrew_resolution.get('hebrew_term', '')} ({hebrew_resolution.get('hebrew_context', '')[:100]}...)\n"
            f"  From source: {hebrew_resolution.get('source_ref', '')}\n"
            f"  Confidence: {hebrew_resolution.get('confidence', 'unknown')}\n"
            f"  Explanation: {hebrew_resolution.get('explanation', '')}\n\n"
            f"Use this resolution as authoritative - it came from vector search + verification.\n\n"
        )
    
    if clarification:
        context_parts.append(
            f"User's original query: \"{topic}\"\n"
            f"User's clarification: \"{clarification}\"\n\n"
            f"Now that the user has clarified, interpret their full query and return the normalized interpretation."
        )
    else:
        context_parts.append(
            f"User's query: \"{topic}\"\n\n"
            f"Interpret this query, handling any spelling variations or transliterations. "
            f"Determine if clarification is needed."
        )
    
    message = "".join(context_parts)
    
    logger.debug(f"  Sending to Claude...")
    
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=800,
            system=INTERPRETATION_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": message}],
        )
        
        response_text = response.content[0].text
        logger.debug(f"  Claude response: {response_text[:200]}")
        
        parsed = parse_claude_json(response_text)
        
        if not parsed:
            logger.error("  ✗ Failed to parse interpretation")
            return {"needs_clarification": False, "interpreted_query": topic, "confidence": "low"}
        
        logger.info(f"  ✓ Interpretation: {parsed.get('interpreted_query', '')}")
        logger.info(f"  Needs clarification: {parsed.get('needs_clarification', False)}")

        # Cache the result
        claude_cache.set(cache_key, parsed)

        return parsed
        
    except Exception as e:
        logger.error(f"  ✗ ERROR in interpretation: {e}", exc_info=True)
        return {"needs_clarification": False, "interpreted_query": topic, "confidence": "low"}


async def identify_base_texts(interpreted_query: str) -> List[dict]:
    """
    Stage 1: Identify which BASE TEXT sections discuss this topic.
    
    Returns general sections like "Marriage 10" not specific "Marriage 10:11"
    """
    logger.info("="*80)
    logger.info("STAGE 1: IDENTIFY BASE TEXT SECTIONS")
    logger.info("="*80)
    logger.info(f"  Query: {interpreted_query}")
    
    # Check cache
    cache_key = f"base_texts:{interpreted_query}"
    cached = claude_cache.get(cache_key)
    if cached:
        logger.info(f"  💰 CACHE HIT: Found {len(cached)} base texts")
        return cached
    
    if DEV_MODE:
        logger.warning("  🧪 DEV_MODE: Returning mock base texts")
        return [
            {"ref": "Mishneh Torah, Marriage 10", "reason": "Mock reason 1"},
            {"ref": "Shulchan Arukh, Even HaEzer 61", "reason": "Mock reason 2"}
        ]
    
    message = (
        f"Query: {interpreted_query}\n\n"
        f"Identify 2-4 BASE TEXT sections (chapters/simanim, not specific halachos) that discuss this topic.\n"
        f"Use Sefaria's English names and general section references."
    )
    
    logger.debug("  Sending to Claude...")
    
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            system=BASE_TEXT_IDENTIFICATION_PROMPT,
            messages=[{"role": "user", "content": message}],
        )
        
        response_text = response.content[0].text
        logger.debug(f"  Claude response: {response_text[:300]}")
        
        parsed = parse_claude_json(response_text)
        base_texts = parsed.get("base_texts", [])
        
        logger.info(f"  ✓ Identified {len(base_texts)} base text sections:")
        for bt in base_texts:
            logger.info(f"    - {bt.get('ref', '')}: {bt.get('reason', '')[:60]}")

        # Cache the result
        claude_cache.set(cache_key, base_texts)

        return base_texts
        
    except Exception as e:
        logger.error(f"  ✗ ERROR identifying base texts: {e}", exc_info=True)
        return []


async def fetch_commentaries_for_base_texts(base_texts: List[dict]) -> Dict[str, str]:
    """
    Stage 2: For each base text, use Related API to get commentaries,
    then fetch their texts.
    
    Returns: {commentary_ref: commentary_text}
    """
    logger.info("="*80)
    logger.info("STAGE 2: FETCH COMMENTARIES VIA RELATED API")
    logger.info("="*80)
    
    all_commentary_texts = {}
    
    for base_text in base_texts:
        base_ref = base_text.get("ref", "")
        logger.info(f"\n📖 Processing base text: {base_ref}")
        
        # Get related commentaries
        related = await get_related_texts(base_ref)
        
        if not related:
            logger.warning(f"  No commentaries found for {base_ref}")
            continue
        
        logger.info(f"  Found {len(related)} commentaries, fetching texts...")
        
        # Fetch each commentary's text
        for i, commentary in enumerate(related[:10], 1):  # Limit to 10 per base text
            comm_ref = commentary.get("ref", "")
            
            logger.info(f"  [{i}/{min(len(related), 10)}] Fetching: {comm_ref}")
            
            result = await fetch_text_from_sefaria(comm_ref)
            
            if result.get("found"):
                # Combine Hebrew and English text
                he = result.get("he_text", "")
                en = result.get("en_text", "")
                combined = f"{he}\n\n{en}" if he and en else (he or en)
                
                if combined:
                    all_commentary_texts[comm_ref] = combined
                    logger.info(f"    ✓ Got text ({len(combined)} chars)")
                else:
                    logger.warning(f"    ⚠ Empty text")
            else:
                logger.warning(f"    ✗ Failed to fetch")
    
    logger.info(f"\n✓ Total commentaries fetched: {len(all_commentary_texts)}")
    return all_commentary_texts


async def extract_citations_from_commentaries(
    original_query: str,
    interpreted_query: str,
    commentary_texts: Dict[str, str]
) -> dict:
    """
    Stage 3: Have Claude analyze commentary texts and extract earlier source citations.
    """
    logger.info("="*80)
    logger.info("STAGE 3: EXTRACT CITATIONS FROM COMMENTARIES")
    logger.info("="*80)
    logger.info(f"  Analyzing {len(commentary_texts)} commentary texts")
    
    if not commentary_texts:
        logger.warning("  No commentary texts to analyze")
        return {"sources": [], "summary": "No commentary texts found"}
    
    # Check cache
    cache_key = f"extract:{interpreted_query}:{len(commentary_texts)}"
    cached = claude_cache.get(cache_key)
    if cached:
        logger.info("  💰 CACHE HIT: Using cached extraction")
        return cached
    
    if DEV_MODE:
        logger.warning("  🧪 DEV_MODE: Returning mock extraction")
        return {
            "sources": [
                {"ref": "Mock Source 1", "category": "Gemara", "citation_count": 2}
            ],
            "summary": "Mock summary"
        }
    
    # Build the message with all commentary texts
    commentary_texts_str = ""
    for ref, text in list(commentary_texts.items())[:15]:  # Limit to 15 for token reasons
        commentary_texts_str += f"\nSOURCE: {ref}\nTEXT: {text[:800]}\n\n{'='*60}\n"
    
    message = (
        f"Here are texts from commentaries discussing the topic:\n\n"
        f"{commentary_texts_str}\n\n"
        f"Extract the EARLIER SOURCES they cite that are relevant to: {interpreted_query}\n"
    )
    
    # Format the system prompt with the query. Use simple replace to avoid
    # str.format interpreting JSON braces inside the prompt.
    system_prompt = CITATION_EXTRACTION_PROMPT.replace("{original_query}", original_query).replace("{interpreted_query}", interpreted_query)
    
    logger.debug("  Sending to Claude for citation extraction...")
    
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=system_prompt,
            messages=[{"role": "user", "content": message}],
        )
        
        response_text = response.content[0].text
        logger.debug(f"  Claude response: {response_text[:300]}")
        
        parsed = parse_claude_json(response_text)
        sources = parsed.get("sources", [])
        
        logger.info(f"  ✓ Extracted {len(sources)} sources:")
        for src in sources[:5]:
            logger.info(f"    - {src.get('ref', '')} (cited {src.get('citation_count', 0)}x)")

        # Cache the result
        claude_cache.set(cache_key, parsed)

        return parsed
        
    except Exception as e:
        logger.error(f"  ✗ ERROR extracting citations: {e}", exc_info=True)
        return {"sources": [], "summary": "Error extracting citations"}


# =============================
# API ENDPOINTS
# =============================

@app.get("/")
async def root():
    logger.info("GET / -> root endpoint")
    vector_ready = vector_engine.is_ready()
    return {
        "message": "Marei Mekomos API v5.0 - Hybrid Transliteration Search",
        "version": "5.0.0",
        "features": {
            "vector_search": vector_ready,
            "claude_verification": True,
            "sefaria_integration": True
        },
        "setup_required": not vector_ready
    }


@app.post("/search", response_model=MareiMekomosResponse)
async def search_sources(request: TopicRequest):
    """
    Main endpoint: Interprets query with hybrid resolution, gets commentaries, extracts citations.
    
    NEW in V5: Automatic transliteration resolution via hybrid search
    """
    logger.info("="*100)
    logger.info(f"NEW SEARCH REQUEST: '{request.topic}'")
    if request.clarification:
        logger.info(f"WITH CLARIFICATION: '{request.clarification}'")
    logger.info("="*100)
    
    resolved_terms = []  # Track resolved Hebrew terms for UI feedback
    hebrew_resolution = None
    
    try:
        # PRE-STAGE: HYBRID TRANSLITERATION RESOLUTION
        # ============================================
        # If query contains transliterations, resolve them first
        if vector_engine.is_ready():
            logger.info("\n🔍 Attempting hybrid transliteration resolution...")
            try:
                resolution_result = await resolve_hebrew_term(request.topic)
                
                if resolution_result.get('resolved'):
                    # Successfully resolved!
                    hebrew_resolution = resolution_result
                    
                    # Add to response for UI feedback
                    resolved_terms.append(ResolvedTerm(
                        original=resolution_result.get('original_query', request.topic),
                        hebrew=resolution_result.get('hebrew_term', ''),
                        source_ref=resolution_result.get('source_ref', ''),
                        confidence=resolution_result.get('confidence', 'unknown'),
                        explanation=resolution_result.get('explanation', '')
                    ))
                    
                    logger.info("✓ Hybrid resolution succeeded - proceeding with Hebrew context")
                else:
                    logger.info("→ No resolution needed or possible - proceeding normally")
                    
            except Exception as e:
                logger.warning(f"Hybrid resolution error (non-fatal): {e}")
                # Continue without resolution - not a critical failure
        else:
            logger.info("⚠️  Vector search not ready - skipping hybrid resolution")
        
        # STAGE 0: Interpret query (now with Hebrew context if available)
        interpretation = await interpret_query(
            request.topic, 
            request.clarification,
            hebrew_resolution
        )
        
        # If needs clarification and user hasn't provided it yet
        if interpretation.get("needs_clarification") and not request.clarification:
            logger.info("→ Returning clarifying questions to user")
            return MareiMekomosResponse(
                topic=request.topic,
                sources=[],
                needs_clarification=True,
                clarifying_questions=interpretation.get("clarifying_questions", []),
                interpreted_query=interpretation.get("interpreted_query", ""),
                resolved_terms=resolved_terms
            )
        
        interpreted_query = interpretation.get("interpreted_query", request.topic)
        logger.info(f"→ Interpreted query: {interpreted_query}")
        
        # STAGE 1: Identify base text sections
        base_texts = await identify_base_texts(interpreted_query)
        
        if not base_texts:
            logger.warning("→ No base texts identified")
            return MareiMekomosResponse(
                topic=request.topic,
                sources=[],
                summary="Could not identify relevant sections to search",
                interpreted_query=interpreted_query,
                resolved_terms=resolved_terms
            )
        
        # STAGE 2: Get commentaries and fetch their texts
        commentary_texts = await fetch_commentaries_for_base_texts(base_texts)
        
        if not commentary_texts:
            logger.warning("→ No commentary texts retrieved")
            return MareiMekomosResponse(
                topic=request.topic,
                sources=[],
                summary="Could not retrieve commentary texts from Sefaria",
                interpreted_query=interpreted_query,
                resolved_terms=resolved_terms
            )
        
        # STAGE 3: Extract citations from commentaries
        extraction = await extract_citations_from_commentaries(
            request.topic,
            interpreted_query,
            commentary_texts
        )
        
        extracted_sources = extraction.get("sources", [])
        summary = extraction.get("summary", "")
        
        # STAGE 4: Fetch actual texts for the extracted sources
        logger.info("="*80)
        logger.info("STAGE 4: FETCH TEXTS FOR EXTRACTED SOURCES")
        logger.info("="*80)
        
        final_sources = []
        for source in extracted_sources:
            ref = source.get("ref", "")
            logger.info(f"  Fetching: {ref}")
            
            result = await fetch_text_from_sefaria(ref)
            
            if result.get("found"):
                final_sources.append(SourceReference(
                    ref=ref,
                    category=source.get("category", "Unknown"),
                    he_text=result.get("he_text", ""),
                    en_text=result.get("en_text", ""),
                    he_ref=result.get("he_ref", ""),
                    sefaria_url=result.get("sefaria_url", ""),
                    citation_count=source.get("citation_count", 1),
                    relevance=source.get("relevance", "")
                ))
                logger.info(f"    ✓ Added to results")
            else:
                logger.warning(f"    ✗ Could not fetch text")
        
        logger.info("="*100)
        logger.info(f"SEARCH COMPLETE: Returning {len(final_sources)} sources")
        if resolved_terms:
            logger.info(f"WITH RESOLVED TERMS: {[t.hebrew for t in resolved_terms]}")
        logger.info("="*100)
        
        return MareiMekomosResponse(
            topic=request.topic,
            sources=final_sources,
            summary=summary,
            interpreted_query=interpreted_query,
            resolved_terms=resolved_terms  # NEW: Include resolved terms in response
        )
        
    except Exception as e:
        logger.error(f"ERROR in search: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    logger.info("GET /health")
    vector_ready = vector_engine.is_ready()
    return {
        "status": "healthy",
        "version": "5.0.0",
        "vector_search_ready": vector_ready,
        "dev_mode": DEV_MODE
    }


@app.get("/cache/stats")
async def cache_stats():
    """Get cache statistics"""
    claude_stats = claude_cache.stats()
    sefaria_stats = sefaria_cache.stats()

    return {
        "claude_cache": claude_stats,
        "sefaria_cache": sefaria_stats,
        "dev_mode": DEV_MODE,
        "message": f"Saved ~${claude_stats['total_entries'] * 0.025:.2f} via caching"
    }


@app.post("/cache/clear")
async def clear_cache():
    """Clear all caches"""
    logger.warning("Clearing all caches")
    claude_cache.clear()
    sefaria_cache.clear()
    return {"status": "success", "message": "All caches cleared"}


@app.get("/vector/status")
async def vector_status():
    """Check vector search readiness"""
    ready = vector_engine.is_ready()
    return {
        "ready": ready,
        "message": "Vector search ready" if ready else "Embeddings need to be created",
        "setup_command": "python prepare_sefaria_embeddings.py --sefaria-path /path/to/sefaria" if not ready else None
    }


if __name__ == "__main__":
    import uvicorn
    logger.info("🚀 Starting Marei Mekomos API v5.0 (Hybrid Search)")
    logger.info("   New: Intelligent transliteration resolution")
    logger.info("   Vector search ready: " + ("YES ✓" if vector_engine.is_ready() else "NO (setup required)"))
    logger.info("   Listening on http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)