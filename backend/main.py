"""
Marei Mekomos Backend API

This FastAPI server connects Claude AI (for suggesting sources) with Sefaria's API
(for fetching actual Torah texts), allowing users to search for Torah sources on any topic.
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
from typing import List, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import our logging configuration
from logging_config import setup_logging, get_logger
from cache_manager import claude_cache, sefaria_cache

# Initialize logging
setup_logging()
logger = get_logger(__name__)


# =============================
# PYDANTIC MODELS (data validation)
# =============================

class TopicRequest(BaseModel):
    """Request model for /search endpoint"""
    topic: str
    level: str = "intermediate"  # beginner | intermediate | advanced


class SourceReference(BaseModel):
    """A single source reference with text"""
    ref: str
    category: str
    he_text: str = ""
    en_text: str = ""
    he_ref: str = ""
    sefaria_url: str = ""
    found: bool = True


class MareiMekomosResponse(BaseModel):
    """Response model for /search endpoint"""
    topic: str
    sources: List[SourceReference]
    summary: str = ""


# =============================
# FASTAPI APP SETUP
# =============================

app = FastAPI(title="Marei Mekomos API", version="1.0.0")

# Allow requests from frontend running on localhost:5173
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Anthropic client
api_key = os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    logger.critical("ANTHROPIC_API_KEY not found in environment variables!")
    raise RuntimeError("ANTHROPIC_API_KEY environment variable is required. "
                       "Set it before running the server.")
client = Anthropic(api_key=api_key)
logger.info("Anthropic client initialized successfully")


# =============================
# SYSTEM PROMPT FOR CLAUDE
# =============================

CLAUDE_SYSTEM_PROMPT = """You are a Torah scholar assistant that helps find marei mekomos (source references) for any Torah topic using a "sugya archaeology" approach.

METHODOLOGY - WORK BACKWARDS FROM ACHARONIM:
Instead of guessing which sources are important, you will search through later commentaries (acharonim and late rishonim) to discover which earlier sources THEY cite most frequently. This reveals the true "ikkar" (foundation) of the sugya.

STEP 1 - IDENTIFY RELEVANT META-COMMENTARIES:
Based on the topic, determine which acharonim/late rishonim would discuss it:

For Gemara topics:
- Pnei Yehoshua (on most masechtos)
- Rabbi Akiva Eiger
- Late Rishonim who quote earlier sources: Ran, Ritva, Rashba, Nimukei Yosef

For Halachic topics (Orach Chaim/Yoreh Deah):
- Mishnah Berurah
- Shach, Taz
- Beur Halacha

For Even HaEzer/Choshen Mishpat:
- Ketzos HaChoshen, Nesivos HaMishpat
- Chelkas Mechokek, Beis Shmuel

For Rambam:
- Kesef Mishneh, Magid Mishneh, Lechem Mishneh

Always include:
- Shulchan Aruch, Rama, Tur
- Beis Yosef, Darchei Moshe

STEP 2 - SEARCH THESE SOURCES ON SEFARIA:
Return Sefaria references to WHERE these acharonim discuss this topic. For example:
- "Pnei Yehoshua on Kiddushin 5a"
- "Mishnah Berurah 431:1"
- "Ketzos HaChoshen 201:1"

STEP 3 - IDENTIFY CITATION PATTERNS:
You will be given the TEXT of these acharonim. Your job is to:
1. Extract which earlier sources they cite (ignore their lomdus/svara)
2. Count how many times each source appears across multiple acharonim
3. Prioritize sources cited by multiple acharonim - these are the ikkar!

CRITICAL RULES:
1. Use EXACT Sefaria reference formats
2. DO NOT make up sources - only suggest what exists on Sefaria
3. For Gemara: "Kiddushin 5a", "Berakhot 6b"
4. For Chumash: "Shemot 12:15", "Bereishit 1:1"
5. For Rishonim: "Rashi on Kiddushin 5a", "Tosafot on Kiddushin 5a"
6. For Rambam: "Mishneh Torah, Ishut 10:2"
7. For Shulchan Aruch: "Shulchan Arukh, Even HaEzer 55:1"

RESPONSE FORMAT:
Return TWO JSON objects:

First - the acharonim to search:
{
  "acharonim_to_search": [
    {"ref": "Pnei Yehoshua on Kiddushin 5a", "category": "Acharonim"},
    {"ref": "Ketzos HaChoshen 201:1", "category": "Acharonim"},
    ...
  ]
}

After analyzing their texts, return the final sources:
{
  "sources": [
    {"ref": "Kiddushin 5a", "category": "Gemara", "citation_count": 5},
    {"ref": "Rashi on Kiddushin 5a", "category": "Rishonim", "citation_count": 4},
    ...
  ],
  "summary": "Brief summary of the sugya"
}

Only return valid JSON, no other text."""


# =============================
# HELPER FUNCTIONS
# =============================

def clean_html_from_text(text: str) -> str:
    """
    Clean HTML entities and tags from Sefaria text.
    
    Sefaria returns text with HTML formatting like:
    - HTML entities: &thinsp; &nbsp; etc.
    - HTML tags: <b>, <i>, <br>, etc.
    
    This function removes them to get clean plain text.
    """
    if not text:
        return text
    
    # First, decode HTML entities like &thinsp; &nbsp; etc.
    text = html.unescape(text)
    
    # Then remove all HTML tags like <b>, <i>, <br>, etc.
    text = re.sub(r'<[^>]+>', '', text)
    
    # Clean up any extra whitespace that might have been created
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


async def get_sources_from_claude(topic: str, level: str) -> dict:
    """
    Ask Claude to suggest relevant Torah sources using the "sugya archaeology" method.
    
    This is a two-step process:
    1. Ask Claude which acharonim/late rishonim discuss this topic
    2. Fetch those texts from Sefaria (with caching)
    3. Have Claude analyze what sources THEY cite
    
    Returns a dict like {"sources": [...], "summary": "..."}
    """
    # Check cache first for final results
    cache_key = f"{topic}|{level}"
    cached_response = claude_cache.get(cache_key)
    if cached_response:
        logger.info(f"💰 Using CACHED final results for '{topic}' (saved API call!)")
        return cached_response

    # ============================================================
    # STAGE 0: Interpret the user's query first
    # This prevents mistakes like searching Issurei Biah when they mean Ishut
    # ============================================================
    logger.info(f"STAGE 0: Interpreting query '{topic}'")
    
    interpretation_prompt = f"""The user searched for: "{topic}"

This might be a shorthand query that needs interpretation. Your job is to figure out what they're REALLY asking about.

Examples:
- "rav huna chuppas niddah rambam" → They want sources about whether chuppah creates kiddushin when the woman is a niddah (Rav Huna's position and Rambam's ruling in Hilchos Ishut, NOT Issurei Biah)
- "bedikas chometz" → They want sources about the obligation to search for chometz before Pesach (Orach Chaim)  
- "kibud av" → They want sources about the mitzvah to honor parents (Yoreh Deah)

Think carefully about:
1. What is the MAIN TOPIC? (e.g., kiddushin/marriage, chometz, kibud av)
2. What SPECIFIC ASPECT? (e.g., chuppah as kinyan, bedikah obligation, honoring father)
3. Which seforim/chapters would discuss this? (Be precise - Hilchos Ishut vs. Issurei Biah matters!)
4. Are specific people/positions mentioned? (e.g., Rav Huna, Rambam, Rashi)

CRITICAL: Don't get confused by keywords! "chuppas niddah" is about KIDDUSHIN (marriage), not about niddah laws.

Return ONLY a JSON object:
{{
  "interpreted_query": "A clear, detailed description of what the user is asking",
  "main_topic": "The primary subject area",
  "relevant_areas": ["Specific Rambam chapters, SA sections, or masechtos"],
  "specific_question": "The exact question or case being asked about"
}}
"""
    
    try:
        interp_response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            system="You are a Torah scholar who interprets user queries to understand what they're really asking about. Pay close attention to context, not just keywords.",
            messages=[{"role": "user", "content": interpretation_prompt}],
        )
        interpretation = parse_claude_json(interp_response.content[0].text)
        interpreted_query = interpretation.get('interpreted_query', topic)
        logger.info(f"✓ Interpreted query as: {interpreted_query}")
        logger.debug(f"Full interpretation: {interpretation}")
    except Exception as e:
        logger.warning(f"Failed to interpret query, using original: {e}")
        interpreted_query = topic
    
    # ============================================================
    # STAGE 1: Now use the interpreted query to find acharonim
    # ============================================================
    logger.info(f"STAGE 1: Requesting acharonim to search")

    # Customize the prompt based on user's level
    level_instructions = {
        "beginner": "Focus on the most basic, foundational sources - return 3-5 core sources.",
        "intermediate": "Include the main sugya and key rishonim - return 5-15 sources.",
        "advanced": "Include comprehensive coverage with multiple shittos - return 10-20 sources."
    }

    instruction = level_instructions.get(level, level_instructions["intermediate"])
    
    # STEP 1: Ask Claude which acharonim to search (using interpreted query)
    step1_message = (
        f"User's original query: \"{topic}\"\n\n"
        f"INTERPRETED QUERY: {interpreted_query}\n\n"
        f"Level: {level} - {instruction}\n\n"
        f"STEP 1: Based on the INTERPRETED QUERY above, identify which acharonim and late rishonim "
        f"on Sefaria would discuss THIS SPECIFIC TOPIC.\n\n"
        f"Return a JSON object with 'acharonim_to_search' containing 5-10 relevant sources.\n\n"
        f"CRITICAL REMINDERS:\n"
        f"- Use the INTERPRETED QUERY to understand what the user wants\n"
        f"- Be specific about WHERE in each acharon (e.g., 'Pnei Yehoshua on Kiddushin 5a', not just 'Pnei Yehoshua')\n"
        f"- Don't be fooled by keywords - understand the actual topic (e.g., 'chuppas niddah' is about kiddushin, not niddah laws)\n"
        f"- Choose acharonim that discuss the SPECIFIC QUESTION asked, not just the general topic"
    )

    logger.debug(f"Step 1 message to Claude: {step1_message}")

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            system=CLAUDE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": step1_message}],
        )
        logger.debug(f"Claude Step 1 response received. Usage: {response.usage}")
    except Exception as e:
        logger.error(f"Error calling Claude API (Step 1): {e}", exc_info=True)
        raise

    response_text = response.content[0].text
    logger.debug(f"Step 1 response length: {len(response_text)} characters")
    
    # Parse the acharonim list
    acharonim_data = parse_claude_json(response_text)
    if not acharonim_data or "acharonim_to_search" not in acharonim_data:
        logger.error("Failed to get acharonim list from Claude")
        return {"sources": [], "summary": "Error: Could not identify relevant acharonim"}
    
    acharonim_list = acharonim_data["acharonim_to_search"]
    logger.info(f"Claude identified {len(acharonim_list)} acharonim to search")
    
    # STEP 2: Fetch texts from Sefaria for each acharon (with caching)
    acharon_texts = []
    for acharon in acharonim_list[:10]:  # Limit to 10 to avoid too many API calls
        ref = acharon.get("ref", "")
        if not ref:
            continue
            
        logger.info(f"Fetching acharon text: {ref}")
        # Sefaria cache already handles this in fetch_text_from_sefaria
        sefaria_data = await fetch_text_from_sefaria(ref)
        
        if sefaria_data.get("found"):
            text_content = sefaria_data.get("he_text", "") or sefaria_data.get("en_text", "")
            if text_content:
                acharon_texts.append({
                    "ref": ref,
                    "text": text_content[:2000]  # Limit text length to avoid token overflow
                })
                logger.debug(f"Successfully fetched text for {ref}")
        else:
            logger.warning(f"Could not fetch text for {ref}")
    
    if not acharon_texts:
        logger.warning("No acharon texts found - falling back to direct source search")
        # Fallback: just ask Claude directly
        result = await get_sources_from_claude_fallback(topic, level)
        # Cache the fallback result
        claude_cache.set(cache_key, result)
        return result
    
    # STEP 3: Have Claude analyze the acharon texts to extract citations
    logger.info(f"STAGE 2: Analyzing {len(acharon_texts)} acharon texts to extract citations")
    
    acharon_texts_formatted = "\n\n".join([
        f"=== {item['ref']} ===\n{item['text']}"
        for item in acharon_texts
    ])
    
    step2_message = (
        f"Topic: {topic}\n"
        f"Level: {level} - {instruction}\n\n"
        f"STEP 2: Below are texts from acharonim discussing this topic.\n"
        f"Extract which EARLIER SOURCES they cite (ignore their lomdus).\n"
        f"Count how many acharonim cite each source.\n"
        f"Return the sources cited by multiple acharonim as the 'ikkar' of the sugya.\n\n"
        f"Acharon texts:\n{acharon_texts_formatted}\n\n"
        f"Return final JSON with 'sources' and 'summary'."
    )
    
    logger.debug(f"Step 2 message length: {len(step2_message)} characters")
    
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=CLAUDE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": step2_message}],
        )
        logger.debug(f"Claude Step 2 response received. Usage: {response.usage}")
    except Exception as e:
        logger.error(f"Error calling Claude API (Step 2): {e}", exc_info=True)
        raise

    response_text = response.content[0].text
    logger.debug(f"Step 2 response length: {len(response_text)} characters")
    
    parsed_data = parse_claude_json(response_text)
    if not parsed_data or "sources" not in parsed_data:
        logger.error("Failed to parse final sources from Claude")
        return {"sources": [], "summary": "Error parsing final sources"}
    
    logger.info(f"Successfully extracted {len(parsed_data.get('sources', []))} sources from acharon analysis")
    
    # Cache the final result
    claude_cache.set(cache_key, parsed_data)
    logger.debug(f"Saved final result to cache")
    
    return parsed_data


async def get_sources_from_claude_fallback(topic: str, level: str) -> dict:
    """
    Fallback method if acharon search fails - direct source suggestion.
    """
    logger.warning("Using fallback direct source search")
    
    level_instructions = {
        "beginner": "Return 3-5 basic sources: primarily Chumash and well-known pesukim.",
        "intermediate": "Return 5-15 sources: Include Chumash, main sugyos in Gemara, key Rishonim, and Shulchan Aruch.",
        "advanced": "Return 10-20 sources: Include lesser-known gemaras, multiple Rishonim, Acharonim, and nuanced applications."
    }
    
    instruction = level_instructions.get(level, level_instructions["intermediate"])
    user_message = (
        f"Find marei mekomos for the topic: {topic}\n\n"
        f"Level: {level} - {instruction}\n\n"
        f"Return sources organized by category in JSON format."
    )
    
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=CLAUDE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
    except Exception as e:
        logger.error(f"Error in fallback Claude call: {e}", exc_info=True)
        return {"sources": [], "summary": "Error in fallback search"}
    
    response_text = response.content[0].text
    return parse_claude_json(response_text)


def parse_claude_json(response_text: str) -> dict:
    """
    Parse JSON from Claude's response, handling markdown fences and commentary text.
    """
    try:
        original_text = response_text
        
        # First try to extract from markdown fences
        if "```json" in response_text:
            logger.debug("Extracting JSON from markdown json fence")
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            logger.debug("Extracting JSON from generic markdown fence")
            response_text = response_text.split("```")[1].split("```")[0]
        
        # If parsing fails, try to find the JSON by locating the first {
        response_text = response_text.strip()
        
        # If there's text before the JSON, strip it
        if not response_text.startswith("{"):
            logger.debug("Response has text before JSON, finding first brace")
            brace_index = response_text.find("{")
            if brace_index != -1:
                response_text = response_text[brace_index:]
                logger.debug(f"Stripped text before JSON, starting from position {brace_index}")
            else:
                logger.error("No opening brace found in response")
                return {}

        parsed_data = json.loads(response_text.strip())
        logger.debug(f"Successfully parsed JSON")
        return parsed_data
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}", exc_info=True)
        logger.error(f"Full response text: {original_text[:500]}")
        return {}


async def fetch_text_from_sefaria(ref: str, max_retries: int = 2) -> dict:
    """
    Fetch actual text from the Sefaria API for a given reference string.
    Retries up to max_retries times on timeout.

    Returns a dict with `found`, `he_text`, `en_text`, `he_ref`, `sefaria_url`.
    """

    logger.info(f"Fetching text from Sefaria for ref='{ref}'")

    # URL-encode spaces simply by replacing them with %20. For more robust
    # encoding use urllib.parse.quote(ref, safe='').
    encoded_ref = ref.replace(" ", "%20")
    url = f"https://www.sefaria.org/api/v3/texts/{encoded_ref}"
    logger.debug(f"Sefaria API URL: {url}")

    async with httpx.AsyncClient(verify=False) as client:
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    logger.info(f"Retry attempt {attempt} for '{ref}'")
                
                response = await client.get(url, timeout=30.0)

                logger.info(f"Sefaria HTTP status code: {response.status_code} for ref='{ref}'")
                if response.status_code == 200:
                    data = response.json()
                    logger.debug(f"Sefaria response data keys: {list(data.keys())}")

                    # Extract Hebrew and English text
                    he_text = ""
                    en_text = ""
                    he_ref = data.get("heRef", "")

                    versions = data.get("versions", [])
                    logger.debug(f"Sefaria returned {len(versions)} version(s) for '{ref}'")

                    for idx, version in enumerate(versions):
                        lang = version.get("language", "")
                        text = version.get("text", "")
                        version_title = version.get("versionTitle", "")
                        logger.debug(f"Version {idx}: lang={lang}, title={version_title}, text_type={type(text).__name__}")

                        # Handle nested arrays (common in Sefaria responses)
                        if isinstance(text, list):
                            text = flatten_text(text)

                        if lang == "he" and not he_text:
                            he_text = text
                            logger.debug(f"Hebrew text captured (before cleaning): {len(he_text)} characters")
                        elif lang == "en" and not en_text:
                            en_text = text
                            logger.debug(f"English text captured (before cleaning): {len(en_text)} characters")

                    # Clean HTML from both Hebrew and English text
                    he_text = clean_html_from_text(he_text)
                    en_text = clean_html_from_text(en_text)
                    
                    logger.debug(f"Hebrew text after cleaning: {len(he_text)} characters")
                    logger.debug(f"English text after cleaning: {len(en_text)} characters")

                    logger.info(f"Sefaria fetch result for '{ref}': he_text={'yes' if he_text else 'no'} en_text={'yes' if en_text else 'no'}")
                    return {
                        "found": True,
                        "he_text": he_text[:1000] if he_text else "",
                        "en_text": en_text[:1000] if en_text else "",
                        "he_ref": he_ref,
                        "sefaria_url": f"https://www.sefaria.org/{encoded_ref}",
                    }
                else:
                    logger.warning(f"Sefaria returned status {response.status_code} for '{ref}'")
                    logger.debug(f"Response content: {response.text[:500]}")
                    return {"found": False}

            except httpx.ReadTimeout:
                if attempt < max_retries:
                    logger.warning(f"Timeout fetching '{ref}', retrying... (attempt {attempt + 1}/{max_retries})")
                    continue  # Retry
                else:
                    logger.error(f"Failed to fetch '{ref}' after {max_retries + 1} attempts (timeout)")
                    return {"found": False}
                    
            except Exception as e:
                logger.error(f"Exception while fetching from Sefaria for '{ref}': {e}", exc_info=True)
                return {"found": False}


def flatten_text(text_data) -> str:
    """Flatten nested arrays from Sefaria into a single string"""
    if isinstance(text_data, str):
        return text_data
    elif isinstance(text_data, list):
        parts = []
        for item in text_data:
            parts.append(flatten_text(item))
        result = " ".join(parts)
        logger.debug(f"Flattened text array: {len(text_data)} items -> {len(result)} characters")
        return result
    logger.debug(f"Unexpected text_data type: {type(text_data)}")
    return ""


# =============================
# API ENDPOINTS
# =============================

@app.get("/")
async def root():
    # Simple root endpoint. We also log so beginners see an incoming
    # request in the server logs when the frontend or curl hits '/'.
    logger.info("GET / -> root endpoint called")
    return {"message": "Marei Mekomos API - Use POST /search to find sources"}


@app.post("/search", response_model=MareiMekomosResponse)
async def search_sources(request: TopicRequest):
    """Main endpoint: takes a topic and returns organized sources with texts"""
    # Log the incoming request so you can follow along in the logs.
    logger.info("="*80)
    logger.info(f"POST /search -> topic='{request.topic}' level='{request.level}'")
    logger.info("="*80)

    # Step 1: Ask Claude for source suggestions (this may take a couple
    # of seconds depending on network and the AI model).
    try:
        claude_response = await get_sources_from_claude(request.topic, request.level)
    except Exception as e:
        logger.error(f"Failed to get sources from Claude: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error communicating with Claude API: {str(e)}")

    # `claude_response` is expected to be a dict like {"sources": [...], "summary": "..."}
    suggested = claude_response.get("sources", [])
    logger.info(f"Claude suggested {len(suggested)} sources (before Sefaria lookup)")
    logger.debug(f"Suggested sources: {suggested}")

    sources = []

    # Step 2: For each suggested source, ask Sefaria for the actual texts.
    # Note: Claude may suggest references that don't exist; we detect this
    # by checking `found` in the result from Sefaria.
    for idx, source in enumerate(suggested, 1):
        ref = source.get("ref", "")
        category = source.get("category", "")

        # Skip any incomplete suggestions
        if not ref:
            logger.warning(f"Skipping empty suggestion at index {idx}")
            continue

        logger.info(f"[{idx}/{len(suggested)}] Looking up: '{ref}' (category: {category})")

        # Fetch the text from Sefaria
        sefaria_data = await fetch_text_from_sefaria(ref)

        was_found = sefaria_data.get("found", False)
        logger.info(f"[{idx}/{len(suggested)}] Sefaria lookup result for '{ref}': found={was_found}")

        source_ref = SourceReference(
            ref=ref,
            category=category,
            he_text=sefaria_data.get("he_text", ""),
            en_text=sefaria_data.get("en_text", ""),
            he_ref=sefaria_data.get("he_ref", ""),
            sefaria_url=sefaria_data.get("sefaria_url", ""),
            found=was_found
        )
        sources.append(source_ref)
        logger.debug(f"Added source: {ref}, has_he={bool(source_ref.he_text)}, has_en={bool(source_ref.en_text)}")

    # Remove any sources Sefaria didn't return so the frontend doesn't
    # display broken links or missing texts.
    valid_sources = [s for s in sources if s.found]
    invalid_count = len(sources) - len(valid_sources)

    if invalid_count > 0:
        logger.warning(f"Filtered out {invalid_count} invalid/unfound sources")
        invalid_refs = [s.ref for s in sources if not s.found]
        logger.debug(f"Invalid references: {invalid_refs}")

    logger.info("="*80)
    logger.info(f"Request complete: Returning {len(valid_sources)} valid sources to client")
    logger.info("="*80)

    return MareiMekomosResponse(
        topic=request.topic,
        sources=valid_sources,
        summary=claude_response.get("summary", "")
    )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    logger.info("GET /health -> health check called")
    return {"status": "healthy"}


if __name__ == "__main__":
    # When you run this file directly (python main.py) we'll start the
    # development server and also log a friendly startup message so you
    # can see that the process began.
    import uvicorn
    logger.info("Starting Marei Mekomos API on http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)