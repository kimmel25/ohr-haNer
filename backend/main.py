"""
Marei Mekomos V5: "Sugya Archaeology"
======================================

ZERO MAPPINGS. Dynamic discovery through citation networks.
Acharonim → Rishonim → Gemara (like a ben torah learns)

Architecture:
- Phase 0: Query Interpretation (ASK if unclear)
- Phase 1: Masechta Identification
- Phase 2: Acharon Discovery (Sefaria search)
- Phase 3: Citation Extraction (archaeology)
- Phase 4: Validation (prevent hallucinations)
- Phase 5: Chronological Assembly
"""

import json
import os
import httpx
import html
import re
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from anthropic import Anthropic
from typing import List, Optional
from collections import Counter

from logging_config import setup_logging, get_logger
from cache_manager import sefaria_cache

# Initialize
setup_logging()
logger = get_logger(__name__)

app = FastAPI(title="Marei Mekomos V5: Sugya Archaeology")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


# ============================================================================
# MODELS
# ============================================================================

class TopicRequest(BaseModel):
    topic: str
    clarification: Optional[str] = None


class SourceReference(BaseModel):
    ref: str
    category: str
    he_text: str = ""
    en_text: str = ""
    he_ref: str = ""
    sefaria_url: str = ""
    citation_count: int = 0
    relevance: str = ""


class SearchResponse(BaseModel):
    topic: str
    sources: List[SourceReference]
    summary: str = ""
    needs_clarification: bool = False
    clarifying_questions: List[str] = []
    interpreted_query: str = ""


# ============================================================================
# PROMPTS
# ============================================================================

PHASE_0_PROMPT = """You are a chavrusa (Torah study partner), not a search engine.

Your job: Interpret the user's query and decide if you need clarification.

HANDLE TRANSLITERATIONS (Yeshivish conventions):
- Use sav not tav: "Kesubos" not "Ketubot", "Shabbos" not "Shabbat"
- Common variations: "chuppa/chuppah/huppa" → "chuppah"
- Hebrew/English mixed: normalize to English transliteration

ENTROPY DETECTION - When to ASK:
HIGH ENTROPY (need clarification):
- Single terms: "niddah", "chometz", "chuppah" → Could mean many things
- Ambiguous scope: User might want different applications

LOW ENTROPY (proceed):
- Specific queries: "machlokes ketzos nesivos chuppas niddah"
- Clear topics: "bitul chametz", "bedikas chometz derabanan"
- Named authorities: "ran on sfek sfeika"

CRITICAL: Only ask if GENUINELY unclear. If you can reasonably determine what they want, PROCEED.

Return JSON:
{
  "needs_clarification": true/false,
  "clarifying_questions": ["Question 1?", "Question 2?"],  // Max 2, natural language
  "interpreted_query": "Normalized query in standard yeshivish transliteration",
  "confidence": 85  // 0-100
}

If confidence > 70, set needs_clarification = false even if topic is broad."""


PHASE_1_PROMPT = """You are a Torah scholar identifying which area of Torah this topic belongs to.

Given a query, identify:
1. Which masechta/sefer this primarily appears in
2. Related masechtot/areas
3. Whether this is a lomdus topic (conceptual) or psak topic (practical halacha)

Return JSON:
{
  "primary_masechta": "Kesubos" or "Choshen Mishpat" or "Orach Chayim" etc,
  "related_areas": ["Kiddushin", "Gittin"],
  "topic_type": "lomdus" or "psak" or "mixed",
  "search_terms": ["term1", "term2"]  // Hebrew and English terms to search Sefaria
}

Use proper yeshivish transliterations (Kesubos not Ketubot, etc)."""


PHASE_3_PROMPT = """You are analyzing Acharon commentaries to extract earlier source citations.

You'll receive texts from Acharonim (later authorities) discussing a topic.

Your job: Extract which EARLIER sources they cite.

Look for:
- Gemara citations (e.g., "Kesubos 9a", "פסחים ב:")
- Rishon citations (e.g., "Rashi", "Tosafos", "Ran", "Rashba")
- Earlier Acharon citations

For each citation:
- Note which Acharon cited it
- Extract why it's relevant to THIS topic

Return JSON:
{
  "citations": [
    {
      "ref": "Kesubos 9a-b",
      "category": "Gemara",
      "cited_by": ["Ketzos HaChoshen 28:1", "Nesivos HaMishpat"],
      "relevance": "The foundational sugya discussing the principle"
    }
  ],
  "summary": "Brief summary of what the Acharonim say about this topic"
}

IMPORTANT: 
- Only include sources DIRECTLY relevant to the query
- Don't include tangential citations
- Prefer Gemara and Rishonim over later Acharonim"""


# ============================================================================
# UTILITIES
# ============================================================================

def clean_html(text: str) -> str:
    """Remove HTML from Sefaria text"""
    if not text:
        return text
    text = html.unescape(text)
    text = re.sub(r'<[^>]+>', '', text)
    return re.sub(r'\s+', ' ', text).strip()


def flatten_text(text_data) -> str:
    """Flatten nested arrays from Sefaria"""
    if isinstance(text_data, str):
        return text_data
    elif isinstance(text_data, list):
        return " ".join(flatten_text(item) for item in text_data)
    return ""


def parse_claude_json(text: str) -> dict:
    """Extract JSON from Claude response"""
    try:
        # Strip markdown fences
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        
        # Find first brace
        text = text.strip()
        if not text.startswith("{"):
            brace_idx = text.find("{")
            if brace_idx != -1:
                text = text[brace_idx:]
        
        return json.loads(text.strip()) if text else {}
    except:
        logger.error(f"Failed to parse JSON: {text[:200]}")
        return {}


# ============================================================================
# SEFARIA API
# ============================================================================

async def fetch_from_sefaria(ref: str) -> dict:
    """Fetch text from Sefaria, with caching"""
    cached = sefaria_cache.get(ref)
    if cached:
        logger.info(f"💰 Cache HIT: {ref}")
        return cached
    
    logger.info(f"📥 Fetching: {ref}")
    encoded = ref.replace(" ", "%20")
    url = f"https://www.sefaria.org/api/v3/texts/{encoded}"
    
    async with httpx.AsyncClient(timeout=15.0, verify=False) as http:
        try:
            resp = await http.get(url)
            if resp.status_code != 200:
                return {"found": False}
            
            data = resp.json()
            versions = data.get("versions", [])
            
            he_text = ""
            en_text = ""
            for v in versions:
                text = flatten_text(v.get("text", ""))
                if v.get("language") == "he" and not he_text:
                    he_text = clean_html(text)
                elif v.get("language") == "en" and not en_text:
                    en_text = clean_html(text)
            
            result = {
                "found": True,
                "he_text": he_text[:2000] if he_text else "",  # Limit length
                "en_text": en_text[:2000] if en_text else "",
                "he_ref": data.get("heRef", ""),
                "sefaria_url": f"https://www.sefaria.org/{encoded}"
            }
            
            sefaria_cache.set(ref, result)
            return result
        except Exception as e:
            logger.error(f"Error fetching {ref}: {e}")
            return {"found": False}


async def search_sefaria(query: str, max_results: int = 20) -> List[dict]:
    """Search Sefaria for texts matching query"""
    logger.info(f"🔍 Searching Sefaria: {query}")
    
    # Check cache
    cache_key = f"search:{query}:{max_results}"
    cached = sefaria_cache.get(cache_key)
    if cached:
        logger.info(f"  💰 Cache HIT: {len(cached)} results")
        return cached
    
    url = "https://www.sefaria.org/api/search-wrapper"
    params = {
        "q": query,
        "tab": "text",
        "tvar": 1,
        "tsort": "relevance",
        "svar": 1,
        "ssort": "relevance"
    }
    
    async with httpx.AsyncClient(timeout=15.0, verify=False) as http:
        try:
            resp = await http.get(url, params=params)
            if resp.status_code != 200:
                return []
            
            data = resp.json()
            hits = data.get("hits", {}).get("hits", [])
            
            results = []
            for hit in hits[:max_results]:
                source = hit.get("_source", {})
                ref = source.get("ref", "")
                if ref:
                    results.append({
                        "ref": ref,
                        "version": source.get("version", ""),
                        "lang": source.get("lang", ""),
                        "score": hit.get("_score", 0)
                    })
            
            logger.info(f"  ✓ Found {len(results)} results")
            sefaria_cache.set(cache_key, results)
            return results
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []


# ============================================================================
# PHASE IMPLEMENTATIONS
# ============================================================================

async def phase_0_interpret(topic: str, clarification: Optional[str] = None) -> dict:
    """Phase 0: Query interpretation with entropy detection"""
    logger.info("=" * 80)
    logger.info("PHASE 0: QUERY INTERPRETATION")
    logger.info(f"  Topic: {topic}")
    if clarification:
        logger.info(f"  Clarification: {clarification}")
    
    cache_key = f"p0:{topic}:{clarification or ''}"
    # cached = claude_cache.get(cache_key)
    # if cached:
    #     return cached
    
    message = f"User's query: \"{topic}\""
    if clarification:
        message += f"\nUser's clarification: \"{clarification}\""
        message += "\n\nNow interpret the full query with clarification."
    
    try:
        import json
        resp = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=800,
            system=PHASE_0_PROMPT,
            messages=[{"role": "user", "content": message}]
        )
        
        result = parse_claude_json(resp.content[0].text)
        logger.info(f"  ✓ Interpreted: {result.get('interpreted_query', '')}")
        logger.info(f"  Confidence: {result.get('confidence', 0)}%")
        
        # claude_cache.set(cache_key, result)
        return result
    except Exception as e:
        logger.error(f"Phase 0 error: {e}")
        return {"needs_clarification": False, "interpreted_query": topic, "confidence": 50}


async def phase_1_identify_masechta(interpreted_query: str) -> dict:
    """Phase 1: Identify masechta/area"""
    logger.info("=" * 80)
    logger.info("PHASE 1: MASECHTA IDENTIFICATION")
    
    cache_key = f"p1:{interpreted_query}"
    # cached = claude_cache.get(cache_key)
    # if cached:
    #     return cached
    
    try:
        import json
        resp = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            system=PHASE_1_PROMPT,
            messages=[{"role": "user", "content": f"Query: {interpreted_query}"}]
        )
        
        result = parse_claude_json(resp.content[0].text)
        logger.info(f"  ✓ Masechta: {result.get('primary_masechta', '')}")
        logger.info(f"  Search terms: {result.get('search_terms', [])}")
        
        # claude_cache.set(cache_key, result)
        return result
    except Exception as e:
        logger.error(f"Phase 1 error: {e}")
        return {"primary_masechta": "Unknown", "search_terms": [interpreted_query]}


async def phase_2_discover_acharonim(search_terms: List[str]) -> List[dict]:
    """Phase 2: Search Sefaria for Acharonim discussing this topic"""
    logger.info("=" * 80)
    logger.info("PHASE 2: ACHARON DISCOVERY")
    
    all_results = []
    for term in search_terms[:3]:  # Limit to 3 terms
        results = await search_sefaria(term, max_results=15)
        all_results.extend(results)
    
    # Deduplicate by ref
    seen = set()
    unique = []
    for r in all_results:
        if r["ref"] not in seen:
            seen.add(r["ref"])
            unique.append(r)
    
    logger.info(f"  ✓ Found {len(unique)} unique sources")
    return unique[:20]  # Top 20


async def phase_3_extract_citations(
    original_query: str,
    interpreted_query: str,
    acharon_sources: List[dict]
) -> dict:
    """Phase 3: Extract citations from Acharon texts"""
    logger.info("=" * 80)
    logger.info("PHASE 3: CITATION EXTRACTION")
    
    # Fetch texts for top Acharon sources
    logger.info(f"  Fetching {len(acharon_sources)} Acharon texts...")
    
    acharon_texts = []
    for source in acharon_sources[:10]:  # Limit to 10 to avoid token issues
        ref = source["ref"]
        text_data = await fetch_from_sefaria(ref)
        
        if text_data.get("found"):
            combined = f"{text_data.get('he_text', '')}\n{text_data.get('en_text', '')}"
            if combined.strip():
                acharon_texts.append({
                    "ref": ref,
                    "text": combined[:1500]  # Limit each text
                })
    
    if not acharon_texts:
        logger.warning("  No Acharon texts retrieved")
        return {"citations": [], "summary": ""}
    
    logger.info(f"  Analyzing {len(acharon_texts)} texts for citations...")
    
    # Build prompt with texts
    texts_str = "\n\n".join([
        f"=== {t['ref']} ===\n{t['text']}"
        for t in acharon_texts
    ])
    
    message = (
        f"Topic: {interpreted_query}\n\n"
        f"Acharon texts:\n{texts_str}\n\n"
        f"Extract earlier source citations relevant to: {interpreted_query}"
    )
    
    try:
        import json
        resp = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=PHASE_3_PROMPT,
            messages=[{"role": "user", "content": message}]
        )
        
        result = parse_claude_json(resp.content[0].text)
        citations = result.get("citations", [])
        
        logger.info(f"  ✓ Extracted {len(citations)} citations")
        for c in citations[:5]:
            logger.info(f"    - {c.get('ref', '')} (cited {len(c.get('cited_by', []))}x)")
        
        return result
    except Exception as e:
        logger.error(f"Phase 3 error: {e}")
        return {"citations": [], "summary": ""}


async def phase_4_validate(citations: List[dict]) -> List[SourceReference]:
    """Phase 4: Validate citations against Sefaria and fetch texts"""
    logger.info("=" * 80)
    logger.info("PHASE 4: VALIDATION & TEXT RETRIEVAL")
    
    validated = []
    for citation in citations:
        ref = citation.get("ref", "")
        logger.info(f"  Validating: {ref}")
        
        text_data = await fetch_from_sefaria(ref)
        
        if text_data.get("found"):
            validated.append(SourceReference(
                ref=ref,
                category=citation.get("category", "Unknown"),
                he_text=text_data.get("he_text", ""),
                en_text=text_data.get("en_text", ""),
                he_ref=text_data.get("he_ref", ""),
                sefaria_url=text_data.get("sefaria_url", ""),
                citation_count=len(citation.get("cited_by", [])),
                relevance=citation.get("relevance", "")
            ))
            logger.info(f"    ✓ Validated")
        else:
            logger.warning(f"    ✗ Not found (hallucination)")
    
    logger.info(f"  ✓ Validated {len(validated)} / {len(citations)} sources")
    return validated


def phase_5_assemble(sources: List[SourceReference]) -> List[SourceReference]:
    """Phase 5: Sort chronologically"""
    logger.info("=" * 80)
    logger.info("PHASE 5: CHRONOLOGICAL ASSEMBLY")
    
    category_order = {
        "Torah": 0,
        "Tanach": 1,
        "Mishna": 2,
        "Gemara": 3,
        "Rishonim": 4,
        "Shulchan Aruch": 5,
        "Acharonim": 6,
        "Unknown": 7
    }
    
    def sort_key(source: SourceReference):
        return (
            category_order.get(source.category, 7),
            -source.citation_count,  # More citations first
            source.ref
        )
    
    sorted_sources = sorted(sources, key=sort_key)
    
    logger.info(f"  ✓ Assembled {len(sorted_sources)} sources chronologically")
    for s in sorted_sources[:5]:
        logger.info(f"    - {s.category}: {s.ref} ({s.citation_count} citations)")
    
    return sorted_sources


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.post("/search", response_model=SearchResponse)
async def search(request: TopicRequest):
    """Main search endpoint"""
    logger.info("=" * 100)
    logger.info(f"NEW SEARCH: '{request.topic}'")
    if request.clarification:
        logger.info(f"WITH CLARIFICATION: '{request.clarification}'")
    logger.info("=" * 100)
    
    try:
        # Phase 0: Interpret
        interpretation = await phase_0_interpret(request.topic, request.clarification)
        
        if interpretation.get("needs_clarification") and not request.clarification:
            return SearchResponse(
                topic=request.topic,
                sources=[],
                needs_clarification=True,
                clarifying_questions=interpretation.get("clarifying_questions", []),
                interpreted_query=interpretation.get("interpreted_query", "")
            )
        
        interpreted = interpretation.get("interpreted_query", request.topic)
        
        # Phase 1: Identify masechta
        masechta_info = await phase_1_identify_masechta(interpreted)
        search_terms = masechta_info.get("search_terms", [interpreted])
        
        # Phase 2: Discover Acharonim
        acharon_sources = await phase_2_discover_acharonim(search_terms)
        
        if not acharon_sources:
            logger.warning("No sources found")
            return SearchResponse(
                topic=request.topic,
                sources=[],
                summary="No sources found. Try different search terms.",
                interpreted_query=interpreted
            )
        
        # Phase 3: Extract citations
        extraction = await phase_3_extract_citations(
            request.topic,
            interpreted,
            acharon_sources
        )
        
        # Phase 4: Validate
        validated = await phase_4_validate(extraction.get("citations", []))
        
        # Phase 5: Assemble
        final_sources = phase_5_assemble(validated)
        
        logger.info("=" * 100)
        logger.info(f"COMPLETE: {len(final_sources)} sources")
        logger.info("=" * 100)
        
        return SearchResponse(
            topic=request.topic,
            sources=final_sources,
            summary=extraction.get("summary", ""),
            interpreted_query=interpreted
        )
        
    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    return {"message": "Marei Mekomos V5: Sugya Archaeology", "version": "5.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    logger.info("🚀 Starting Marei Mekomos V5: Sugya Archaeology")
    uvicorn.run(app, host="0.0.0.0", port=8000)