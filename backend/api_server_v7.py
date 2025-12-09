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

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent))

# Import centralized models and config
from models import (
    DecipherResult,
    SearchRequest,
    DecipherRequest,
    ConfirmRequest,
    RejectRequest,
    MareiMekomosResult,
    ConfidenceLevel
)
from config import get_settings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


# Note: Models are now imported from models.py
# Configuration loaded from config.py


# ==========================================
#  FASTAPI APP
# ==========================================

# Load settings
settings = get_settings()

app = FastAPI(
    title=f"אור הנר - {settings.app_name}",
    description="Torah source finder with intelligent understanding",
    version=settings.app_version
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
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
        "version": settings.app_version,
        "environment": settings.environment,
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

@app.post("/search")
async def search_endpoint(request: SearchRequest) -> Dict[str, Any]:
    """
    Full search pipeline: Steps 1 → 2 → 3

    Takes a query and returns organized Torah sources.
    """
    logger.info(f"[/search] Query: '{request.query}'")

    try:
        from main_pipeline import search_sources

        result: MareiMekomosResult = await search_sources(request.query)

        # Convert Pydantic model to dict for JSON response
        response = result.model_dump()

        logger.info(f"[/search] Result: {result.total_sources} sources, "
                   f"confidence={result.confidence.value}")

        return response

    except Exception as e:
        logger.error(f"[/search] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
#  DECIPHER ENDPOINT (Step 1 only)
# ==========================================

@app.post("/decipher")
async def decipher_endpoint(request: DecipherRequest) -> Dict[str, Any]:
    """
    Step 1 only: transliteration → Hebrew

    For when you just need to validate the transliteration.
    """
    logger.info(f"[/decipher] Query: '{request.query}'")

    try:
        from step_one_decipher import decipher
        from user_validation import analyze_query

        # Run Step 1 - now returns DecipherResult (Pydantic model)
        result: DecipherResult = await decipher(request.query)

        # Skip validation if confidence is high
        if result.confidence == ConfidenceLevel.HIGH and result.hebrew_term:
            # Use the dictionary result directly for complete phrases
            # Don't re-analyze word-by-word as that breaks multi-word phrases
            complete_hebrew = result.hebrew_term

            # Still get validation to extract word_validations for display purposes only
            validation = analyze_query(request.query, strict=False)

            response = result.model_copy(update={
                "hebrew_term": complete_hebrew,
                "needs_validation": False,
                "validation_type": "NONE",
                "choose_options": [],
                "word_validations": [
                    {
                        "original": wv.original,
                        "best_match": wv.best_match,
                        "alternatives": wv.alternatives,
                        "confidence": wv.confidence,
                        "needs_validation": wv.needs_validation,
                        "validation_type": wv.validation_type.value,
                    }
                    for wv in validation.word_validations
                ],
                "message": "High-confidence dictionary hit. No validation needed."
            })

            return response.model_dump()

        # Get validation info
        validation = analyze_query(request.query, strict=request.strict)

        # If Step 1 found a complete result, use it; otherwise reconstruct from words
        if result.hebrew_term and result.method == "dictionary":
            # Dictionary has the complete phrase, don't reconstruct word-by-word
            complete_hebrew = result.hebrew_term
        elif validation.word_validations:
            # Build from word validations
            complete_hebrew = " ".join(wv.best_match for wv in validation.word_validations)
        else:
            complete_hebrew = result.hebrew_term

        response = result.model_copy(update={
            "hebrew_term": complete_hebrew,
            "needs_validation": validation.needs_validation,
            "validation_type": validation.validation_type.value,
            "choose_options": validation.choose_options,
            "word_validations": [
                {
                    "original": wv.original,
                    "best_match": wv.best_match,
                    "alternatives": wv.alternatives,
                    "confidence": wv.confidence,
                    "needs_validation": wv.needs_validation,
                    "validation_type": wv.validation_type.value,
                }
                for wv in validation.word_validations
            ]
        })

        return response.model_dump()

    except ImportError as e:
        logger.warning(f"Step 1 module not available: {e}")
        error_result = DecipherResult(
            success=False,
            hebrew_term=None,
            confidence=ConfidenceLevel.LOW,
            method="unavailable",
            needs_validation=True,
            validation_type="UNKNOWN",
            choose_options=[],
            message="Transliteration service not available"
        )
        return error_result.model_dump()

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

            # Reconstruct the full Hebrew phrase from word_validations
            # Replace uncertain word(s) with the user's selection
            updated_word_validations = []
            if validation.word_validations:
                hebrew_words = []
                for i, word_val in enumerate(validation.word_validations):
                    if i in validation.uncertain_word_indices:
                        # This word was uncertain, use the selected Hebrew
                        hebrew_words.append(selected)
                        # Update the word validation to reflect the user's selection
                        updated_word_validations.append({
                            "original": word_val.original,
                            "best_match": selected,
                            "alternatives": word_val.alternatives,
                            "confidence": 1.0,  # User confirmed, so high confidence
                            "needs_validation": False,
                            "validation_type": "NONE",
                        })
                    else:
                        # This word was certain, use its best match
                        hebrew_words.append(word_val.best_match)
                        updated_word_validations.append({
                            "original": word_val.original,
                            "best_match": word_val.best_match,
                            "alternatives": word_val.alternatives,
                            "confidence": word_val.confidence,
                            "needs_validation": word_val.needs_validation,
                            "validation_type": word_val.validation_type.value,
                        })
                full_hebrew_phrase = " ".join(hebrew_words)
            else:
                # Single word or no word validations
                full_hebrew_phrase = selected

            return {
                "success": True,
                "hebrew_term": full_hebrew_phrase,
                "word_validations": updated_word_validations,
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
