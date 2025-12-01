"""
Marei Mekomos Backend - V5 "Flexible Thinking"

Philosophy: Resources teach HOW TO THINK, not what to do.
No rigid rules. No routing tables. Just smart, flexible source discovery.
"""

import os
import json
import httpx
import html
import re
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from anthropic import Anthropic
from typing import List, Optional
from logging_config import setup_logging, get_logger
from cache_manager import sefaria_cache

setup_logging()
logger = get_logger(__name__)

# Paths
BASE_DIR = Path(__file__).parent
RESOURCES_DIR = BASE_DIR / "resources"

# FastAPI
app = FastAPI(title="Marei Mekomos API v5", version="5.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Anthropic
api_key = os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    raise RuntimeError("ANTHROPIC_API_KEY required")
client = Anthropic(api_key=api_key)


# =============================
# MODELS
# =============================

class TopicRequest(BaseModel):
    topic: str
    clarification: Optional[str] = None


class SourceReference(BaseModel):
    ref: str
    he_text: str = ""
    en_text: str = ""
    he_ref: str = ""
    sefaria_url: str = ""
    relevance: str = ""


class Response(BaseModel):
    topic: str
    sources: List[SourceReference]
    summary: str = ""
    needs_clarification: bool = False
    clarifying_questions: List[str] = []
    interpreted_query: str = ""


# =============================
# RESOURCE LOADING
# =============================

def load_resources() -> dict:
    """Load ALL resources - they're tiny, just read everything"""
    resources = {}
    
    # Read thinking patterns
    thinking_file = RESOURCES_DIR / "thinking_patterns.md"
    if thinking_file.exists():
        with open(thinking_file, 'r', encoding='utf-8') as f:
            resources['thinking_patterns'] = f.read()
    
    # Read learning examples
    examples_file = RESOURCES_DIR / "learning_examples.md"
    if examples_file.exists():
        with open(examples_file, 'r', encoding='utf-8') as f:
            resources['learning_examples'] = f.read()
    
    # Read translations
    trans_file = RESOURCES_DIR / "translations.json"
    if trans_file.exists():
        with open(trans_file, 'r', encoding='utf-8') as f:
            resources['translations'] = json.load(f)
    
    logger.info(f"Loaded {len(resources)} resource files")
    return resources


def translate_slug(ref: str, translations: dict) -> str:
    """Translate yeshivish → Sefaria using translations.json"""
    if not translations:
        return ref
    
    ref_lower = ref.lower()
    
    # Masechta translations
    for yeshivish, sefaria in translations.get('masechta_translations', {}).items():
        if yeshivish in ref_lower:
            ref = re.sub(re.escape(yeshivish), sefaria, ref, flags=re.IGNORECASE)
    
    # Rambam translations  
    if 'rambam' in ref_lower or 'mishneh torah' in ref_lower:
        for heb, eng in translations.get('rambam_translations', {}).items():
            if heb in ref_lower:
                ref = ref.replace(heb, eng)
                ref = ref.replace('Rambam', 'Mishneh Torah,')
    
    # SA translations
    if 'shulchan' in ref_lower or 's"a' in ref_lower:
        for heb, eng in translations.get('shulchan_aruch_translations', {}).items():
            if heb in ref_lower or heb in ref:
                ref = ref.replace(heb, eng)
                if 'shulchan' not in ref.lower():
                    ref = 'Shulchan Arukh, ' + ref
    
    return ref


# =============================
# SEFARIA VALIDATION (VGR)
# =============================

def clean_html(text: str) -> str:
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def flatten_text(text_data) -> str:
    """Handle nested arrays from Sefaria"""
    if isinstance(text_data, str):
        return text_data
    elif isinstance(text_data, list):
        parts = [flatten_text(item) for item in text_data if item]
        return " ".join(parts)
    return ""


async def validate_source(ref: str, translations: dict) -> dict:
    """
    VGR Protocol: Validate against Sefaria.
    If Sefaria returns 404 → it's a hallucination.
    """
    ref = translate_slug(ref, translations)
    
    # Check cache
    cached = sefaria_cache.get(f"text:{ref}")
    if cached:
        logger.info(f"  ✓ Cache hit: {ref}")
        return cached
    
    logger.info(f"  Fetching: {ref}")
    
    encoded_ref = ref.replace(" ", "%20").replace(",", "%2C")
    url = f"https://www.sefaria.org/api/v3/texts/{encoded_ref}"
    
    async with httpx.AsyncClient(verify=False, timeout=15.0) as http_client:
        try:
            response = await http_client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                
                he_text = ""
                en_text = ""
                he_ref = data.get("heRef", "")
                
                for version in data.get("versions", []):
                    lang = version.get("language", "")
                    text = version.get("text", "")
                    
                    if isinstance(text, list):
                        text = flatten_text(text)
                    
                    if lang == "he" and not he_text:
                        he_text = clean_html(text)
                    elif lang == "en" and not en_text:
                        en_text = clean_html(text)
                
                result = {
                    "found": True,
                    "he_text": he_text[:2000] if he_text else "",
                    "en_text": en_text[:1500] if en_text else "",
                    "he_ref": he_ref,
                    "sefaria_url": f"https://www.sefaria.org/{encoded_ref}",
                }
                
                sefaria_cache.set(f"text:{ref}", result)
                logger.info(f"  ✓ Validated: {ref}")
                return result
            else:
                logger.warning(f"  ✗ Not found: {ref} (HTTP {response.status_code})")
                return {"found": False}
                
        except Exception as e:
            logger.error(f"  ✗ Error: {ref} - {e}")
            return {"found": False}


# =============================
# PROMPT BUILDING
# =============================

def build_prompt(topic: str, clarification: Optional[str], resources: dict) -> str:
    """
    Build ONE smart prompt with resources as context.
    No rigid rules - just examples and thinking patterns.
    """
    
    thinking = resources.get('thinking_patterns', '')
    examples = resources.get('learning_examples', '')
    
    prompt = f"""You are a Torah learning chavrusa helping find marei mekomos (source references).

# YOUR RESOURCES (Use as inspiration, not rigid rules)

{thinking}

---

{examples}

# THE TASK

User's query: "{topic}"
"""
    
    if clarification:
        prompt += f'\nUser clarification: "{clarification}"\n'
    
    prompt += """
# YOUR JOB

1. **Understand the query** - What are they really asking?
2. **Think flexibly** - Which approach makes sense? (archaeology, direct sugya, machlokes, etc.)
3. **Find sources** - Use your judgment about what will HELP them learn
4. **Be specific** - Give exact references (masechta, daf, commentators)

# OUTPUT FORMAT (JSON)

Return JSON with this structure:

{
  "needs_clarification": false,
  "clarifying_questions": [],
  "interpreted_query": "Clear statement of what they're asking",
  "sources": [
    {
      "ref": "Exact Sefaria reference (e.g., 'Ketubot 4a', 'Mishneh Torah, Marriage 10:11')",
      "relevance": "Why this source matters for THIS specific question"
    }
  ],
  "summary": "Brief overview of the topic and what the sources discuss"
}

**CRITICAL:**
- Give 8-15 sources that directly address the question
- Use EXACT Sefaria format for refs (they'll be validated)
- If query is unclear, set needs_clarification: true and ask questions
- Think like a chavrusa - what would actually help?

**EXAMPLES of good refs:**
- "Ketubot 4a" (not "Kesubos 4a" - use Sefaria spelling)
- "Mishneh Torah, Marriage 10:11" (not "Rambam Ishus 10:11")
- "Shulchan Arukh, Even HaEzer 61:1" (not "SA EH 61:1")
- "Rashi on Shabbat 2a:1" (for specific Rashi)

Now find sources - think flexibly!
"""
    
    return prompt


# =============================
# MAIN SEARCH
# =============================

async def search(topic: str, clarification: Optional[str] = None) -> Response:
    """
    Main search pipeline:
    1. Load resources
    2. Build flexible prompt
    3. Claude thinks and suggests sources
    4. Validate EACH source against Sefaria (VGR)
    5. Return only validated sources
    """
    logger.info("="*80)
    logger.info(f"SEARCH: '{topic}'")
    if clarification:
        logger.info(f"CLARIFICATION: '{clarification}'")
    logger.info("="*80)
    
    # Load resources
    resources = load_resources()
    
    # Build prompt
    system_prompt = build_prompt(topic, clarification, resources)
    
    # Call Claude
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2500,
            system=system_prompt,
            messages=[{"role": "user", "content": f"Find sources for: {topic}"}],
        )
        
        response_text = response.content[0].text
        
        # Parse JSON
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        
        response_text = response_text.strip()
        if not response_text.startswith("{"):
            brace_idx = response_text.find("{")
            if brace_idx != -1:
                response_text = response_text[brace_idx:]
        
        result = json.loads(response_text)
        
        # Check clarification
        if result.get("needs_clarification") and not clarification:
            return Response(
                topic=topic,
                sources=[],
                needs_clarification=True,
                clarifying_questions=result.get("clarifying_questions", []),
                interpreted_query=result.get("interpreted_query", "")
            )
        
        # Validate sources (VGR)
        validated_sources = []
        hallucinations = 0
        
        for source in result.get("sources", []):
            ref = source.get("ref", "")
            relevance = source.get("relevance", "")
            
            if not ref:
                continue
            
            sefaria_result = await validate_source(ref, resources.get('translations', {}))
            
            if sefaria_result.get("found"):
                validated_sources.append(SourceReference(
                    ref=ref,
                    he_text=sefaria_result.get("he_text", ""),
                    en_text=sefaria_result.get("en_text", ""),
                    he_ref=sefaria_result.get("he_ref", ""),
                    sefaria_url=sefaria_result.get("sefaria_url", ""),
                    relevance=relevance
                ))
            else:
                hallucinations += 1
                logger.warning(f"  ✗ HALLUCINATION: {ref}")
        
        logger.info(f"Validated {len(validated_sources)} sources, caught {hallucinations} hallucinations")
        
        return Response(
            topic=topic,
            sources=validated_sources,
            summary=result.get("summary", ""),
            interpreted_query=result.get("interpreted_query", topic)
        )
        
    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =============================
# ENDPOINTS
# =============================

@app.get("/")
async def root():
    return {
        "message": "Marei Mekomos V5 - Flexible Thinking",
        "philosophy": "Resources teach how to think, not what to do"
    }


@app.post("/search", response_model=Response)
async def search_endpoint(request: TopicRequest):
    return await search(request.topic, request.clarification)


@app.get("/health")
async def health():
    return {"status": "healthy", "version": "5.0.0"}


@app.get("/cache/stats")
async def cache_stats():
    return {
        "sefaria_cache": sefaria_cache.stats(),
    }


if __name__ == "__main__":
    import uvicorn
    logger.info("🚀 Starting Marei Mekomos V5 - Flexible Thinking")
    uvicorn.run(app, host="0.0.0.0", port=8000)
