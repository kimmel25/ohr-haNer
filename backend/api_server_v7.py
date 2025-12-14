"""
Marei Mekomos V7 - API Server (Full Pipeline)
==============================================

Serves the complete 3-step pipeline to the frontend:
1. DECIPHER: transliteration -> Hebrew
2. UNDERSTAND: Hebrew -> Intent + Strategy
3. SEARCH: Strategy -> Organized Sources

Endpoints:
- POST /search              - Full pipeline (Steps 1-2-3)
- POST /decipher            - Step 1 only (for validation)
- POST /decipher/confirm    - User confirms transliteration
- POST /decipher/reject     - User rejects transliteration
- GET  /health              - Health check
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Ensure backend/ is on the path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Import centralized models and config
from config import get_settings
from models import (
    ConfirmRequest,
    DecipherRequest,
    DecipherResult,
    MareiMekomosResult,
    RejectRequest,
    SearchRequest,
    ConfidenceLevel,
    ValidationMode,
)
from utils.serialization import enum_value, serialize_word_validations


# ==========================================
#  LOGGING
# ==========================================

settings = get_settings()


def _configure_logging() -> None:
    """Configure root logging only once (uvicorn may configure its own)."""
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return

    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format=settings.log_format,
        datefmt=settings.log_date_format,
    )


_configure_logging()
logger = logging.getLogger("api_server")


# ==========================================
#  FASTAPI APP
# ==========================================

app = FastAPI(
    title=f"{settings.app_name} API",
    description="Torah source finder with intelligent understanding",
    version=settings.app_version,
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
async def health_check() -> Dict[str, Any]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.app_version,
        "environment": settings.environment,
        "pipeline": {
            "step_1": "active",
            "step_2": "active",
            "step_3": "active",
        },
        "timestamp": datetime.utcnow().isoformat(),
    }


# ==========================================
#  FULL SEARCH ENDPOINT
# ==========================================

@app.post("/search")
async def search_endpoint(request: SearchRequest) -> Dict[str, Any]:
    """
    Full search pipeline: Steps 1 -> 2 -> 3.

    Takes a query and returns organized Torah sources.
    """
    start = datetime.utcnow()
    logger.info("[/search] query=%s", request.query)

    try:
        from main_pipeline import search_sources

        result: MareiMekomosResult = await search_sources(request.query)
        duration = (datetime.utcnow() - start).total_seconds()
        conf = enum_value(result.confidence)

        logger.info(
            "[/search] %s sources | confidence=%s | %.2fs",
            result.total_sources,
            conf,
            duration,
        )

        return result.model_dump()

    except Exception as exc:  # noqa: BLE001
        logger.exception("[/search] error")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ==========================================
#  DECIPHER ENDPOINT (Step 1 only)
# ==========================================

@app.post("/decipher")
async def decipher_endpoint(request: DecipherRequest) -> Dict[str, Any]:
    """
    Step 1 only: transliteration -> Hebrew.

    For when you just need to validate the transliteration.
    """
    logger.info("[/decipher] query=%s | strict=%s", request.query, request.strict)

    try:
        from step_one_decipher import decipher
        from user_validation import analyze_query

        result: DecipherResult = await decipher(request.query)
        result_confidence = enum_value(result.confidence)
        logger.info(
            "[/decipher] method=%s | confidence=%s | term=%s",
            result.method,
            result_confidence,
            result.hebrew_term,
        )

        # Skip validation if we are confident and have a full term
        if result.hebrew_term and result_confidence == ConfidenceLevel.HIGH.value:
            validation = analyze_query(request.query, strict=False)

            response = result.model_copy(
                update={
                    "hebrew_term": result.hebrew_term,
                    "needs_validation": False,
                    "validation_type": ValidationMode.NONE.value,
                    "choose_options": [],
                    "word_validations": serialize_word_validations(
                        validation.word_validations
                    ),
                    "message": "High-confidence dictionary hit. No validation needed.",
                }
            )

            response_dict = response.model_dump()
            response_dict["original_query"] = request.query
            return response_dict

        # Otherwise, perform validation and rebuild the Hebrew phrase if needed
        validation = analyze_query(request.query, strict=request.strict)

        if result.hebrew_term and result.method == "dictionary":
            complete_hebrew = result.hebrew_term
        elif validation.word_validations:
            complete_hebrew = " ".join(
                wv.best_match for wv in validation.word_validations
            )
        else:
            complete_hebrew = result.hebrew_term

        response = result.model_copy(
            update={
                "hebrew_term": complete_hebrew,
                "needs_validation": validation.needs_validation,
                "validation_type": validation.validation_type.value
                if hasattr(validation.validation_type, "value")
                else validation.validation_type,
                "choose_options": validation.choose_options,
                "word_validations": serialize_word_validations(
                    validation.word_validations
                ),
            }
        )

        response_dict = response.model_dump()
        response_dict["original_query"] = request.query
        return response_dict

    except ImportError as exc:
        logger.warning("[/decipher] step 1 unavailable: %s", exc)
        error_result = DecipherResult(
            success=False,
            hebrew_term=None,
            confidence=ConfidenceLevel.LOW,
            method="unavailable",
            needs_validation=True,
            validation_type=ValidationMode.UNKNOWN,
            choose_options=[],
            message="Transliteration service not available",
        )
        return error_result.model_dump()

    except Exception as exc:  # noqa: BLE001
        logger.exception("[/decipher] error")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ==========================================
#  CONFIRM/REJECT ENDPOINTS
# ==========================================

@app.post("/decipher/confirm")
async def confirm_selection(request: ConfirmRequest) -> Dict[str, Any]:
    """Confirm user's transliteration selection and store it in the dictionary."""
    logger.info(
        "[/decipher/confirm] index=%s | manual=%s",
        request.selection_index,
        bool(request.selected_hebrew),
    )

    try:
        from user_validation import analyze_query, apply_user_selection
        from tools.word_dictionary import get_dictionary

        validation = analyze_query(request.original_query)

        if request.selected_hebrew:
            selected = request.selected_hebrew
        elif request.selection_index > 0:
            selected = apply_user_selection(validation, request.selection_index)
        else:
            logger.warning("[/decipher/confirm] no selection provided")
            return {"success": False, "message": "No selection made"}

        if not selected:
            logger.warning("[/decipher/confirm] invalid selection")
            return {"success": False, "message": "Invalid selection"}

        dictionary = get_dictionary()
        dictionary.add_entry(
            transliteration=validation.normalized,
            hebrew=selected,
            confidence="high",
            source="user_confirmed",
        )

        updated_word_validations = []
        hebrew_words = []

        if validation.word_validations:
            for idx, word_val in enumerate(validation.word_validations):
                if idx in validation.uncertain_word_indices:
                    hebrew_words.append(selected)
                    updated_word_validations.append(
                        {
                            "original": word_val.original,
                            "best_match": selected,
                            "alternatives": word_val.alternatives,
                            "confidence": 1.0,
                            "needs_validation": False,
                            "validation_type": ValidationMode.NONE.value,
                        }
                    )
                else:
                    hebrew_words.append(word_val.best_match)
                    updated_word_validations.append(
                        {
                            "original": word_val.original,
                            "best_match": word_val.best_match,
                            "alternatives": word_val.alternatives,
                            "confidence": word_val.confidence,
                            "needs_validation": word_val.needs_validation,
                            "validation_type": word_val.validation_type.value
                            if hasattr(word_val.validation_type, "value")
                            else word_val.validation_type,
                        }
                    )
            full_hebrew_phrase = " ".join(hebrew_words)
        else:
            full_hebrew_phrase = selected

        logger.info("[/decipher/confirm] confirmed term=%s", full_hebrew_phrase)

        return {
            "success": True,
            "hebrew_term": full_hebrew_phrase,
            "word_validations": updated_word_validations,
            "message": f"Got it! Using: {full_hebrew_phrase}",
            "learned": True,
        }

    except Exception as exc:  # noqa: BLE001
        logger.exception("[/decipher/confirm] error")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/decipher/reject")
async def reject_translation(request: RejectRequest) -> Dict[str, Any]:
    """Reject a transliteration and return alternative options."""
    logger.info("[/decipher/reject] rejected='%s'", request.incorrect_hebrew)

    try:
        from user_validation import analyze_query

        validation = analyze_query(request.original_query, strict=True)
        suggestions = [
            option
            for option in validation.choose_options
            if option != request.incorrect_hebrew
        ][:5]

        return {
            "success": True,
            "message": "Thanks for the feedback! Here are other options:",
            "suggestions": suggestions,
        }

    except Exception as exc:  # noqa: BLE001
        logger.exception("[/decipher/reject] error")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ==========================================
#  SOURCES ENDPOINT (for expanding)
# ==========================================

@app.get("/sources/{ref:path}")
async def get_source_text(ref: str) -> Dict[str, Any]:
    """
    Get the full text for a specific source reference.

    Used for expanding/collapsing sources in the UI.
    """
    logger.info("[/sources] ref=%s", ref)

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
                "categories": text.categories,
            }

        return {"success": False, "message": f"Could not fetch text for: {ref}"}

    except Exception as exc:  # noqa: BLE001
        logger.exception("[/sources] error")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ==========================================
#  RELATED ENDPOINT
# ==========================================

@app.get("/related/{ref:path}")
async def get_related(ref: str) -> Dict[str, Any]:
    """
    Get related content for a reference.

    Returns commentaries and cross-references.
    """
    logger.info("[/related] ref=%s", ref)

    try:
        from tools.sefaria_client import get_sefaria_client

        client = get_sefaria_client()
        related = await client.get_related(ref)

        return {
            "success": True,
            "base_ref": ref,
            "commentaries": [
                {
                    "ref": commentary.ref,
                    "he_ref": commentary.he_ref,
                    "level": commentary.level.name,
                    "category": commentary.category,
                    "snippet": commentary.text_snippet[:200],
                }
                for commentary in related.commentaries
            ],
            "links": [
                {"ref": link.ref, "relationship": link.relationship}
                for link in related.links[:10]
            ],
            "sheets_count": related.sheets,
        }

    except Exception as exc:  # noqa: BLE001
        logger.exception("[/related] error")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ==========================================
#  MAIN
# ==========================================

if __name__ == "__main__":
    import uvicorn

    print("=" * 80)
    print("Marei Mekomos V7 - API Server")
    print("=" * 80)
    print("Endpoints:")
    print("  POST /search              - Full pipeline")
    print("  POST /decipher            - Step 1 only")
    print("  POST /decipher/confirm    - Confirm selection")
    print("  POST /decipher/reject     - Reject translation")
    print("  GET  /sources/{ref}       - Get source text")
    print("  GET  /related/{ref}       - Get related content")
    print("  GET  /health              - Health check")
    print()
    print("Starting server on http://%s:%s" % (settings.host, settings.port))
    print("=" * 80)

    uvicorn.run(app, host=settings.host, port=settings.port)
