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

# Import our logging configuration
from logging_config import setup_logging, get_logger
from cache_manager import claude_cache, sefaria_cache

# Initialize logging
setup_logging()
logger = get_logger(__name__)

# Development mode flag - set to True to avoid API calls during testing
DEV_MODE = os.environ.get("DEV_MODE", "false").lower() == "true"
if DEV_MODE:
    logger.warning("⚠️  DEV_MODE is ENABLED - using mock responses to save API costs")


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

CLAUDE_SYSTEM_PROMPT = """You are a Torah scholar assistant that helps find marei mekomos (source references) for any Torah topic.

When given a topic, you will return a JSON object with relevant sources organized by category.

IMPORTANT RULES:
1. Return ONLY valid Sefaria references. Use the exact format Sefaria expects.
2. Be conservative - only suggest sources you are confident exist.
3. Organize sources in this order: Chumash → Nach → Mishna → Gemara (Bavli) → Rishonim → Shulchan Aruch/Acharonim
4. For Gemara, use format like "Kiddushin 31a" or "Berakhot 6b"
5. For Chumash, use format like "Shemot 20:12" or "Bereishit 1:1"
6. For Mishna, use format like "Mishnah Kiddushin 1:7"
7. For Rashi on Chumash, use "Rashi on Shemot 20:12"
8. For Rambam, use "Mishneh Torah, Hilchot Mamrim 6:1" 
9. For Shulchan Aruch, use "Shulchan Arukh, Yoreh De'ah 240:1"
10. Include the most important/foundational sources first within each category.

Return your response as valid JSON in this exact format:
{
  "sources": [
    {"ref": "Shemot 20:12", "category": "Chumash"},
    {"ref": "Kiddushin 31a", "category": "Gemara"},
    ...
  ],
  "summary": "Brief 1-2 sentence summary of the topic"
}

Only return the JSON, no other text."""


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
    Ask Claude to suggest relevant Torah sources for a given topic.

    Returns a dict like {"sources": [...], "summary": "..."}
    """
    # Check cache first
    cache_key = f"{topic}|{level}"
    cached_response = claude_cache.get(cache_key)
    if cached_response:
        logger.info(f"💰 Using CACHED Claude response for '{topic}' (saved API call!)")
        return cached_response

    # If in dev mode, return mock data instead of calling API
    if DEV_MODE:
        logger.warning(f"🧪 DEV_MODE: Returning mock response for '{topic}'")
        return {
            "sources": [
                {"ref": "Shemot 20:12", "category": "Chumash"},
                {"ref": "Kiddushin 31a", "category": "Gemara"},
            ],
            "summary": f"Mock summary for {topic} (DEV_MODE)"
        }

    logger.info(
        f"Requesting sources from Claude for topic='{topic}' level='{level}'")

    # Customize the prompt based on user's level
    level_instructions = {
        "beginner": "Return 3-5 basic sources: primarily Chumash and well-known pesukim.",
        "intermediate": "Return 5-15 sources: Include Chumash, main sugyos in Gemara, key Rishonim, and Shulchan Aruch.",
        "advanced": "Return 10-20 sources: Include lesser-known gemaras, multiple Rishonim, Acharonim, and nuanced applications."
    }

    instruction = level_instructions.get(
        level, level_instructions["intermediate"])
    user_message = (
        f"Find marei mekomos for the topic: {topic}\n\n"
        f"Level: {level} - {instruction}\n\n"
        f"Return 5-15 sources depending on the level, organized by category."
    )

    logger.debug(f"User message to Claude: {user_message}")

    # Send request to Claude
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=CLAUDE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        logger.debug(f"Claude API response received. Usage: {response.usage}")
    except Exception as e:
        logger.error(f"Error calling Claude API: {e}", exc_info=True)
        raise

    response_text = response.content[0].text
    logger.debug(
        f"Claude response text length: {len(response_text)} characters")
    preview = response_text[:800].replace("\n", " ")
    logger.info(
        f"Claude response preview: {preview}{'...' if len(response_text) > 800 else ''}")

    # Parse JSON from the AI response (it may be wrapped in markdown fences)
    try:
        original_text = response_text
        if "```json" in response_text:
            logger.debug("Extracting JSON from markdown json fence")
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            logger.debug("Extracting JSON from generic markdown fence")
            response_text = response_text.split("```")[1].split("```")[0]

        parsed_data = json.loads(response_text.strip())
        logger.info(
            f"Successfully parsed Claude response. Found {len(parsed_data.get('sources', []))} sources")
        logger.debug(f"Parsed data: {parsed_data}")

        # Save to cache for future requests
        claude_cache.set(cache_key, parsed_data)
        logger.debug(f"Saved Claude response to cache")

        return parsed_data
    except json.JSONDecodeError as e:
        logger.error(
            f"JSON parse error while decoding Claude response: {e}", exc_info=True)
        logger.error(f"Full response text (raw): {original_text}")
        return {"sources": [], "summary": "Error parsing sources from Claude"}


async def fetch_text_from_sefaria(ref: str) -> dict:
    """
    Fetch actual text from the Sefaria API for a given reference string.

    Returns a dict with `found`, `he_text`, `en_text`, `he_ref`, `sefaria_url`.
    """
    # Check cache first (Sefaria data doesn't change, so we cache for 1 week)
    cached_response = sefaria_cache.get(ref)
    if cached_response:
        logger.info(f"💰 Using CACHED Sefaria response for '{ref}'")
        return cached_response

    logger.info(f"Fetching text from Sefaria for ref='{ref}'")

    # URL-encode spaces simply by replacing them with %20. For more robust
    # encoding use urllib.parse.quote(ref, safe='').
    encoded_ref = ref.replace(" ", "%20")
    url = f"https://www.sefaria.org/api/v3/texts/{encoded_ref}"
    logger.debug(f"Sefaria API URL: {url}")

    async with httpx.AsyncClient(verify=False) as client:
        try:
            response = await client.get(url, timeout=10.0)

            logger.info(
                f"Sefaria HTTP status code: {response.status_code} for ref='{ref}'")
            if response.status_code == 200:
                data = response.json()
                logger.debug(
                    f"Sefaria response data keys: {list(data.keys())}")

                # Extract Hebrew and English text
                he_text = ""
                en_text = ""
                he_ref = data.get("heRef", "")

                versions = data.get("versions", [])
                logger.debug(
                    f"Sefaria returned {len(versions)} version(s) for '{ref}'")

                for idx, version in enumerate(versions):
                    lang = version.get("language", "")
                    text = version.get("text", "")
                    version_title = version.get("versionTitle", "")
                    logger.debug(
                        f"Version {idx}: lang={lang}, title={version_title}, text_type={type(text).__name__}")

                    # Handle nested arrays (common in Sefaria responses)
                    if isinstance(text, list):
                        text = flatten_text(text)

                    if lang == "he" and not he_text:
                        he_text = text
                        logger.debug(
                            f"Hebrew text captured (before cleaning): {len(he_text)} characters")
                    elif lang == "en" and not en_text:
                        en_text = text
                        logger.debug(
                            f"English text captured (before cleaning): {len(en_text)} characters")

                # Clean HTML from both Hebrew and English text
                he_text = clean_html_from_text(he_text)
                en_text = clean_html_from_text(en_text)

                logger.debug(
                    f"Hebrew text after cleaning: {len(he_text)} characters")
                logger.debug(
                    f"English text after cleaning: {len(en_text)} characters")

                logger.info(
                    f"Sefaria fetch result for '{ref}': he_text={'yes' if he_text else 'no'} en_text={'yes' if en_text else 'no'}")

                result = {
                    "found": True,
                    "he_text": he_text[:1000] if he_text else "",
                    "en_text": en_text[:1000] if en_text else "",
                    "he_ref": he_ref,
                    "sefaria_url": f"https://www.sefaria.org/{encoded_ref}",
                }

                # Save to cache
                sefaria_cache.set(ref, result)
                logger.debug(f"Saved Sefaria response to cache")

                return result
            else:
                logger.warning(
                    f"Sefaria returned status {response.status_code} for '{ref}'")
                logger.debug(f"Response content: {response.text[:500]}")
                return {"found": False}

        except Exception as e:
            logger.error(
                f"Exception while fetching from Sefaria for '{ref}': {e}", exc_info=True)
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
        logger.debug(
            f"Flattened text array: {len(text_data)} items -> {len(result)} characters")
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
    logger.info(
        f"POST /search -> topic='{request.topic}' level='{request.level}'")
    logger.info("="*80)

    # Step 1: Ask Claude for source suggestions (this may take a couple
    # of seconds depending on network and the AI model).
    try:
        claude_response = await get_sources_from_claude(request.topic, request.level)
    except Exception as e:
        logger.error(f"Failed to get sources from Claude: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error communicating with Claude API: {str(e)}")

    # `claude_response` is expected to be a dict like {"sources": [...], "summary": "..."}
    suggested = claude_response.get("sources", [])
    logger.info(
        f"Claude suggested {len(suggested)} sources (before Sefaria lookup)")
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

        logger.info(
            f"[{idx}/{len(suggested)}] Looking up: '{ref}' (category: {category})")

        # Fetch the text from Sefaria
        sefaria_data = await fetch_text_from_sefaria(ref)

        was_found = sefaria_data.get("found", False)
        logger.info(
            f"[{idx}/{len(suggested)}] Sefaria lookup result for '{ref}': found={was_found}")

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
        logger.debug(
            f"Added source: {ref}, has_he={bool(source_ref.he_text)}, has_en={bool(source_ref.en_text)}")

    # Remove any sources Sefaria didn't return so the frontend doesn't
    # display broken links or missing texts.
    valid_sources = [s for s in sources if s.found]
    invalid_count = len(sources) - len(valid_sources)

    if invalid_count > 0:
        logger.warning(f"Filtered out {invalid_count} invalid/unfound sources")
        invalid_refs = [s.ref for s in sources if not s.found]
        logger.debug(f"Invalid references: {invalid_refs}")

    logger.info("="*80)
    logger.info(
        f"Request complete: Returning {len(valid_sources)} valid sources to client")
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


@app.get("/cache/stats")
async def cache_stats():
    """Get cache statistics to see how much money you're saving"""
    claude_stats = claude_cache.stats()
    sefaria_stats = sefaria_cache.stats()

    logger.info("GET /cache/stats -> returning cache statistics")

    return {
        "claude_cache": {
            "entries": claude_stats['total_entries'],
            "size_kb": claude_stats['total_size_kb'],
            "ttl_hours": 24
        },
        "sefaria_cache": {
            "entries": sefaria_stats['total_entries'],
            "size_kb": sefaria_stats['total_size_kb'],
            "ttl_hours": 168
        },
        "dev_mode": DEV_MODE,
        "message": f"💰 Cached {claude_stats['total_entries']} Claude responses (saving ${claude_stats['total_entries'] * 0.02:.2f}+)"
    }


@app.post("/cache/clear")
async def clear_cache():
    """Clear all caches - use this if you want fresh results"""
    logger.warning("POST /cache/clear -> clearing all caches")

    claude_cache.clear()
    sefaria_cache.clear()

    return {
        "status": "success",
        "message": "All caches cleared. Next requests will hit the APIs."
    }


if __name__ == "__main__":
    # When you run this file directly (python main.py) we'll start the
    # development server and also log a friendly startup message so you
    # can see that the process began.
    import uvicorn
    logger.info("Starting Marei Mekomos API on http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
