"""
Marei Mekomos - Backend API

This file implements a small FastAPI backend that does two main things:
1) Asks an AI (Claude) to suggest relevant "marei mekomos" (Torah source
    references) for a given topic.
2) Looks up those suggested references on Sefaria (via its public API) and
    returns the found texts (Hebrew / English) together with the references.

The edits in this file add beginner-friendly comments (for dummies) and
print statements so you can see what the server is doing when you run it.

Read this file top-to-bottom and follow the printed messages in the console
to understand the runtime flow.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import os
import json
from anthropic import Anthropic

app = FastAPI(title="Marei Mekomos API")

# Allow React frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Anthropic client - reads ANTHROPIC_API_KEY from environment
# Initialize the Anthropic client.
# NOTE for beginners: The Anthropic library expects an environment variable
# named `ANTHROPIC_API_KEY` to be set. If you haven't set it, the client may
# raise an error when used. We keep the constructor call here like before.
client = Anthropic()


class TopicRequest(BaseModel):
    topic: str
    level: str = "intermediate"  # beginner, intermediate, advanced


class SourceReference(BaseModel):
    ref: str           # Sefaria reference format, e.g., "Shemot 20:12"
    category: str      # e.g., "Chumash", "Gemara", "Rishonim"
    he_text: str = ""
    en_text: str = ""
    he_ref: str = ""   # Hebrew reference
    sefaria_url: str = ""
    found: bool = True


class MareiMekomosResponse(BaseModel):
    topic: str
    sources: list[SourceReference]
    summary: str = ""


# The prompt that tells Claude how to find sources
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


async def get_sources_from_claude(topic: str, level: str) -> dict:
    """
    Ask Claude (the AI) to suggest relevant sources for a topic.

    Returns a dict with keys `sources` (a list) and `summary` (string).
    """

    print(f"[Claude] Requesting sources for topic='{topic}' level='{level}'")

    level_instruction = {
        "beginner": "Focus on basic sources: main pesukim and a key gemara or two.",
        "intermediate": "Include Chumash, main sugyos in Gemara, key Rishonim, and Shulchan Aruch.",
        "advanced": "Be comprehensive: include lesser-known sources, multiple Rishonim, and Acharonim."
    }

    user_message = (
        f"Find marei mekomos for the topic: {topic}\n\n"
        f"Level: {level} - {level_instruction.get(level, level_instruction['intermediate'])}\n\n"
        "Return 5-15 sources depending on the level, organized by category."
    )

    # Send request to Claude
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        system=CLAUDE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    response_text = response.content[0].text
    preview = response_text[:800].replace("\n", " ")
    print(f"[Claude] Response preview: {preview}{'...' if len(response_text) > 800 else ''}")

    # Parse JSON from the AI response (it may be wrapped in markdown fences)
    try:
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]

        return json.loads(response_text.strip())
    except json.JSONDecodeError as e:
        print("[Claude] JSON parse error while decoding response:", e)
        print("[Claude] Full response text (raw):")
        print(response_text)
        return {"sources": [], "summary": "Error parsing sources from Claude"}


async def fetch_text_from_sefaria(ref: str) -> dict:
    """
    Fetch actual text from the Sefaria API for a given reference string.

    Returns a dict with `found`, `he_text`, `en_text`, `he_ref`, `sefaria_url`.
    """

    print(f"[Sefaria] Fetching text for ref='{ref}'")

    # URL-encode spaces simply by replacing them with %20. For more robust
    # encoding use urllib.parse.quote(ref, safe='').
    encoded_ref = ref.replace(" ", "%20")
    url = f"https://www.sefaria.org/api/v3/texts/{encoded_ref}"

    async with httpx.AsyncClient(verify=False) as client:
        try:
            response = await client.get(url, timeout=10.0)

            print(f"[Sefaria] HTTP status code: {response.status_code}")
            if response.status_code == 200:
                data = response.json()

                # Extract Hebrew and English text
                he_text = ""
                en_text = ""
                he_ref = data.get("heRef", "")

                versions = data.get("versions", [])
                for version in versions:
                    lang = version.get("language", "")
                    text = version.get("text", "")

                    # Handle nested arrays (common in Sefaria responses)
                    if isinstance(text, list):
                        text = flatten_text(text)

                    if lang == "he" and not he_text:
                        he_text = text
                    elif lang == "en" and not en_text:
                        en_text = text

                print(f"[Sefaria] Found he_text={'yes' if he_text else 'no'} en_text={'yes' if en_text else 'no'}")
                return {
                    "found": True,
                    "he_text": he_text[:1000] if he_text else "",
                    "en_text": en_text[:1000] if en_text else "",
                    "he_ref": he_ref,
                    "sefaria_url": f"https://www.sefaria.org/{encoded_ref}",
                }
            else:
                print(f"[Sefaria] No text found for '{ref}', status {response.status_code}")
                return {"found": False}

        except Exception as e:
            print(f"[Sefaria] Exception while fetching '{ref}': {e}")
            return {"found": False}


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


@app.get("/")
async def root():
    # Simple root endpoint. We also print so beginners see an incoming
    # request in the server logs when the frontend or curl hits '/'.
    print("[HTTP] GET / -> root endpoint called")
    return {"message": "Marei Mekomos API - Use POST /search to find sources"}


@app.post("/search", response_model=MareiMekomosResponse)
async def search_sources(request: TopicRequest):
    """Main endpoint: takes a topic and returns organized sources with texts"""
    # Print the incoming request so you can follow along in the logs.
    print(f"[HTTP] POST /search -> topic='{request.topic}' level='{request.level}'")

    # Step 1: Ask Claude for source suggestions (this may take a couple
    # of seconds depending on network and the AI model).
    claude_response = await get_sources_from_claude(request.topic, request.level)

    # `claude_response` is expected to be a dict like {"sources": [...], "summary": "..."}
    suggested = claude_response.get("sources", [])
    print(f"[Claude] Suggested {len(suggested)} sources (before lookup)")

    sources = []

    # Step 2: For each suggested source, ask Sefaria for the actual texts.
    # Note: Claude may suggest references that don't exist; we detect this
    # by checking `found` in the result from Sefaria.
    for source in suggested:
        ref = source.get("ref", "")
        category = source.get("category", "")

        # Skip any incomplete suggestions
        if not ref:
            print("[Claude] Skipping empty suggestion")
            continue

        print(f"[Workflow] Looking up: '{ref}' (category: {category})")

        # Fetch the text from Sefaria
        sefaria_data = await fetch_text_from_sefaria(ref)

        was_found = sefaria_data.get("found", False)
        print(f"[Workflow] Sefaria returned found={was_found} for '{ref}'")

        sources.append(SourceReference(
            ref=ref,
            category=category,
            he_text=sefaria_data.get("he_text", ""),
            en_text=sefaria_data.get("en_text", ""),
            he_ref=sefaria_data.get("he_ref", ""),
            sefaria_url=sefaria_data.get("sefaria_url", ""),
            found=was_found
        ))

    # Remove any sources Sefaria didn't return so the frontend doesn't
    # display broken links or missing texts.
    valid_sources = [s for s in sources if s.found]
    print(f"[Workflow] Returning {len(valid_sources)} valid sources to client")

    return MareiMekomosResponse(
        topic=request.topic,
        sources=valid_sources,
        summary=claude_response.get("summary", "")
    )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    print("[HTTP] GET /health -> health check called")
    return {"status": "healthy"}


if __name__ == "__main__":
    # When you run this file directly (python main.py) we'll start the
    # development server and also print a friendly startup message so you
    # can see that the process began.
    import uvicorn
    print("[Server] Starting Marei Mekomos API on http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
