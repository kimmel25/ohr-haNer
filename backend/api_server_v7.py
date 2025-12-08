"""
Marei Mekomos V7 - API Server (Full Pipeline)
==============================================

Serves the complete 3-step pipeline to the frontend:
1. DECIPHER: transliteration → Hebrew
2. UNDERSTAND: Hebrew → Intent + Strategy  
3. SEARCH: Strategy → Organized Sources

Endpoints:
- POST /search              - Full pipeline (Steps 1-2-3)
- POST /decipher            - Step 1 only (for validation)
- POST /decipher/confirm    - User confirms transliteration
- POST /decipher/reject     - User rejects transliteration
- GET  /health              - Health check
"""

import sys
import asyncio
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


# ==========================================
#  PYDANTIC MODELS
# ==========================================

class SearchRequest(BaseModel):
    """Request for full search."""
    query: str
    depth: str = "standard"  # basic, standard, expanded, full


class DecipherRequest(BaseModel):
    """Request for Step 1 only."""
    query: str
    strict: bool = False


class ConfirmRequest(BaseModel):
    """Confirm user's transliteration selection."""
    original_query: str
    selection_index: int
    selected_hebrew: Optional[str] = None


class RejectRequest(BaseModel):
    """Reject a transliteration."""
    original_query: str
    incorrect_hebrew: str
    user_feedback: Optional[str] = None


class SourceResponse(BaseModel):
    """A single source in the response."""
    ref: str
    he_ref: str
    level: str
    level_order: int
    level_hebrew: str
    hebrew_text: str
    english_text: str
    author: str
    is_primary: bool


class RelatedSugyaResponse(BaseModel):
    """A related sugya."""
    ref: str
    he_ref: str
    connection: str
    importance: str
    preview_text: str


class SearchResponse(BaseModel):
    """Full response from search."""
    # Status
    success: bool
    message: str
    
    # Query info
    original_query: str
    hebrew_term: Optional[str]
    
    # Interpretation
    query_type: str
    primary_source: Optional[str]
    primary_source_he: Optional[str]
    interpretation: str
    
    # Sources (trickle-up order)
    sources: List[Dict[str, Any]]
    sources_by_level: Dict[str, List[Dict[str, Any]]]
    
    # Related
    related_sugyos: List[Dict[str, Any]]
    
    # Metadata
    total_sources: int
    levels_included: List[str]
    confidence: str
    
    # Clarification (if needed)
    needs_clarification: bool
    clarification_prompt: Optional[str]


class DecipherResponse(BaseModel):
    """Response from Step 1."""
    success: bool
    original_query: str
    hebrew_term: Optional[str]
    confidence: str
    method: str
    needs_validation: bool
    validation_type: str
    choose_options: List[str]
    message: str


# ==========================================
#  FASTAPI APP
# ==========================================

app = FastAPI(
    title="אור הנר - Marei Mekomos V7",
    description="Torah source finder with intelligent understanding",
    version="7.0.0"
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
#  HEALTH CHECK
# ==========================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "7.0.0",
        "pipeline": {
            "step_1": "active",
            "step_2": "active",
            "step_3": "active"
        },
        "timestamp": datetime.now().isoformat()
    }


# ==========================================
#  FULL SEARCH ENDPOINT
# ==========================================

@app.post("/search", response_model=SearchResponse)
async def search_endpoint(request: SearchRequest):
    """
    Full search pipeline: Steps 1 → 2 → 3
    
    Takes a query and returns organized Torah sources.
    """
    logger.info(f"[/search] Query: '{request.query}'")
    
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    try:
        from main_pipeline import search_sources
        
        result = await search_sources(request.query)
        
        # Convert to response format
        response = SearchResponse(
            success=result.success,
            message=result.message,
            original_query=result.original_query,
            hebrew_term=result.hebrew_term,
            query_type=result.query_type,
            primary_source=result.primary_source,
            primary_source_he=result.primary_source_he,
            interpretation=result.interpretation,
            sources=[
                s.to_dict() if hasattr(s, 'to_dict') else s 
                for s in result.sources
            ],
            sources_by_level={
                level: [s.to_dict() if hasattr(s, 'to_dict') else s for s in sources]
                for level, sources in result.sources_by_level.items()
            },
            related_sugyos=[
                s.to_dict() if hasattr(s, 'to_dict') else s
                for s in result.related_sugyos
            ],
            total_sources=result.total_sources,
            levels_included=result.levels_included,
            confidence=result.confidence,
            needs_clarification=result.needs_clarification,
            clarification_prompt=result.clarification_prompt
        )
        
        logger.info(f"[/search] Result: {result.total_sources} sources, "
                   f"confidence={result.confidence}")
        
        return response
        
    except Exception as e:
        logger.error(f"[/search] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
#  DECIPHER ENDPOINT (Step 1 only)
# ==========================================

@app.post("/decipher", response_model=DecipherResponse)
async def decipher_endpoint(request: DecipherRequest):
    """
    Step 1 only: transliteration → Hebrew
    
    For when you just need to validate the transliteration.
    """
    logger.info(f"[/decipher] Query: '{request.query}'")
    
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    try:
        from step_one_decipher import decipher
        from user_validation import analyze_query
        
        # Run Step 1
        result = await decipher(request.query)
        
        # Get validation info
        validation = analyze_query(request.query, strict=request.strict)
        
        return DecipherResponse(
            success=result.get("success", False),
            original_query=request.query,
            hebrew_term=result.get("hebrew_term"),
            confidence=result.get("confidence", "medium"),
            method=result.get("method", "unknown"),
            needs_validation=validation.needs_validation,
            validation_type=validation.validation_type.value,
            choose_options=validation.choose_options,
            message=result.get("message", "")
        )
        
    except ImportError as e:
        logger.warning(f"Step 1 module not available: {e}")
        return DecipherResponse(
            success=False,
            original_query=request.query,
            hebrew_term=None,
            confidence="low",
            method="unavailable",
            needs_validation=True,
            validation_type="UNKNOWN",
            choose_options=[],
            message="Transliteration service not available"
        )
    except Exception as e:
        logger.error(f"[/decipher] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
#  CONFIRM/REJECT ENDPOINTS
# ==========================================

@app.post("/decipher/confirm")
async def confirm_selection(request: ConfirmRequest):
    """Confirm user's transliteration selection."""
    logger.info(f"[/decipher/confirm] Selection: {request.selection_index}")
    
    try:
        from user_validation import analyze_query, apply_user_selection
        from tools.word_dictionary import get_dictionary
        
        validation = analyze_query(request.original_query)
        
        if request.selected_hebrew:
            selected = request.selected_hebrew
        elif request.selection_index > 0:
            selected = apply_user_selection(validation, request.selection_index)
        else:
            return {"success": False, "message": "No selection made"}
        
        if selected:
            # Learn this for future
            dictionary = get_dictionary()
            dictionary.add_entry(
                transliteration=validation.normalized,
                hebrew=selected,
                confidence="high",
                source="user_confirmed"
            )

            # Reconstruct the full Hebrew phrase
            full_hebrew_phrase = validation.reconstruct_phrase(selected)

            return {
                "success": True,
                "hebrew_term": full_hebrew_phrase,
                "message": f"Got it! Using: {full_hebrew_phrase}",
                "learned": True
            }
        
        return {"success": False, "message": "Invalid selection"}
        
    except Exception as e:
        logger.error(f"[/decipher/confirm] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/decipher/reject")
async def reject_translation(request: RejectRequest):
    """Reject a transliteration and get alternatives."""
    logger.info(f"[/decipher/reject] Rejected: '{request.incorrect_hebrew}'")
    
    try:
        from user_validation import analyze_query
        
        validation = analyze_query(request.original_query, strict=True)
        
        suggestions = [
            opt for opt in validation.choose_options
            if opt != request.incorrect_hebrew
        ][:5]
        
        return {
            "success": True,
            "message": "Thanks for the feedback! Here are other options:",
            "suggestions": suggestions
        }
        
    except Exception as e:
        logger.error(f"[/decipher/reject] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
#  SOURCES ENDPOINT (for expanding)
# ==========================================

@app.get("/sources/{ref:path}")
async def get_source_text(ref: str):
    """
    Get the full text for a specific source reference.
    
    Used for expanding/collapsing sources in the UI.
    """
    logger.info(f"[/sources] Ref: '{ref}'")
    
    try:
        from tools.sefaria_client import get_sefaria_client
        
        client = get_sefaria_client()
        text = await client.get_text(ref)
        
        if text:
            return {
                "success": True,
                "ref": text.ref,
                "he_ref": text.he_ref,
                "hebrew_text": text.hebrew,
                "english_text": text.english,
                "level": text.level.name,
                "categories": text.categories
            }
        
        return {
            "success": False,
            "message": f"Could not fetch text for: {ref}"
        }
        
    except Exception as e:
        logger.error(f"[/sources] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
#  RELATED ENDPOINT
# ==========================================

@app.get("/related/{ref:path}")
async def get_related(ref: str):
    """
    Get related content for a reference.
    
    Returns commentaries and cross-references.
    """
    logger.info(f"[/related] Ref: '{ref}'")
    
    try:
        from tools.sefaria_client import get_sefaria_client
        
        client = get_sefaria_client()
        related = await client.get_related(ref)
        
        return {
            "success": True,
            "base_ref": ref,
            "commentaries": [
                {
                    "ref": c.ref,
                    "he_ref": c.he_ref,
                    "level": c.level.name,
                    "category": c.category,
                    "snippet": c.text_snippet[:200]
                }
                for c in related.commentaries
            ],
            "links": [
                {
                    "ref": l.ref,
                    "relationship": l.relationship
                }
                for l in related.links[:10]
            ],
            "sheets_count": related.sheets
        }
        
    except Exception as e:
        logger.error(f"[/related] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
#  MAIN
# ==========================================

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 80)
    print("אור הנר - Marei Mekomos V7 API Server")
    print("=" * 80)
    print()
    print("Pipeline Status:")
    print("  ✓ Step 1 (DECIPHER): Active")
    print("  ✓ Step 2 (UNDERSTAND): Active")
    print("  ✓ Step 3 (SEARCH): Active")
    print()
    print("Endpoints:")
    print("  POST /search              - Full pipeline")
    print("  POST /decipher            - Step 1 only")
    print("  POST /decipher/confirm    - Confirm selection")
    print("  POST /decipher/reject     - Reject translation")
    print("  GET  /sources/{ref}       - Get source text")
    print("  GET  /related/{ref}       - Get related content")
    print("  GET  /health              - Health check")
    print()
    print("Starting server on http://localhost:8000")
    print("=" * 80)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
