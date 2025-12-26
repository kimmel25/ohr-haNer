"""
Marei Mekomos V7 - API Server (Full Pipeline) - FIXED
======================================================

BUGS FIXED:
1. FastAPI app was created twice - lifespan was on first app, but second app overwrote it
2. Logging path was relative - now uses absolute path from settings

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
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Ensure backend/ is on the path for imports
THIS_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(THIS_DIR))

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
#  SETTINGS & LOGGING SETUP
# ==========================================

settings = get_settings()

# FIXED: Use absolute path for logs
LOG_DIR = THIS_DIR / "logs"


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


# Import async-safe logging
from logging.logging_async_safe import setup_logging, stop_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown."""
    # Startup - FIXED: Use absolute path
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    setup_logging(LOG_DIR)
    
    # Get logger after setup
    startup_logger = logging.getLogger("api_server")
    startup_logger.info("=" * 60)
    startup_logger.info("Marei Mekomos API Server Starting")
    startup_logger.info(f"Log directory: {LOG_DIR}")
    startup_logger.info(f"Environment: {settings.environment}")
    startup_logger.info("=" * 60)
    
    yield
    
    # Shutdown
    startup_logger.info("Marei Mekomos API Server Shutting Down")
    stop_logging()


# ==========================================
#  FASTAPI APP - FIXED: Only create ONCE with lifespan
# ==========================================

app = FastAPI(
    title=f"{settings.app_name} API",
    description="Torah source finder with intelligent understanding",
    version=settings.app_version,
    lifespan=lifespan,  # FIXED: Include lifespan here
)

_configure_logging()
logger = logging.getLogger("api_server")

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
        "log_dir": str(LOG_DIR),
        "pipeline": {
            "step_1": "active",
            "step_2": "active",
            "step_3": "active",
        },
        "timestamp": datetime.utcnow().isoformat(),
    }


# ==========================================
#  SESSION STATE (for decipher workflow)
# ==========================================

_pending_sessions: Dict[str, Any] = {}


# ==========================================
#  SEARCH ENDPOINT (Full Pipeline)
# ==========================================

@app.post("/search")
async def search_endpoint(request: SearchRequest) -> MareiMekomosResult:
    """
    Full search pipeline (Steps 1-2-3).
    
    Takes user query, returns organized Torah sources.
    """
    logger.info("=" * 60)
    logger.info(f"[/search] Query: '{request.query}'")
    logger.info("=" * 60)
    
    try:
        from main_pipeline import search_sources
        result = await search_sources(request.query)
        
        logger.info(f"[/search] Complete: {result.total_sources} sources")
        return result
        
    except Exception as e:
        logger.exception(f"[/search] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
#  DECIPHER ENDPOINTS (Step 1)
# ==========================================

@app.post("/decipher")
async def decipher_endpoint(request: DecipherRequest) -> Dict[str, Any]:
    """
    Step 1 only: Transliteration -> Hebrew.
    
    Returns the deciphered Hebrew term(s) for validation.
    """
    logger.info(f"[/decipher] Query: '{request.query}'")
    
    try:
        from step_one_decipher import decipher
        result = await decipher(request.query)
        
        # Store for confirm/reject
        _pending_sessions[request.query] = result
        
        response = {
            "success": result.success,
            "hebrew_term": result.hebrew_term,
            "hebrew_terms": result.hebrew_terms,
            "confidence": enum_value(result.confidence),
            "method": result.method,
            "message": result.message,
            "needs_validation": result.needs_validation,
            "validation_type": enum_value(result.validation_type),
            "alternatives": result.alternatives,
            "choose_options": result.choose_options,
            "word_validations": serialize_word_validations(result.word_validations),
        }
        
        logger.info(f"[/decipher] Result: {result.hebrew_term} ({result.method})")
        return response
        
    except Exception as e:
        logger.exception(f"[/decipher] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/decipher/confirm")
async def confirm_decipher(request: ConfirmRequest) -> Dict[str, Any]:
    """User confirms a transliteration selection."""
    logger.info(f"[/decipher/confirm] '{request.original_query}' -> '{request.selected_hebrew}'")
    
    try:
        # Update dictionary for learning
        try:
            from word_dictionary import get_dictionary
            dictionary = get_dictionary()
            
            words = request.original_query.lower().split()
            if request.word_index is not None and 0 <= request.word_index < len(words):
                word = words[request.word_index]
            else:
                word = request.original_query.lower()
            
            dictionary.add_entry(word, request.selected_hebrew, boost=True)
            logger.info(f"[/decipher/confirm] Dictionary updated: {word} -> {request.selected_hebrew}")
            
        except ImportError:
            logger.warning("[/decipher/confirm] Dictionary not available")
        
        return {
            "success": True,
            "message": f"Confirmed: {request.selected_hebrew}",
            "hebrew_term": request.selected_hebrew,
        }
        
    except Exception as e:
        logger.exception(f"[/decipher/confirm] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/decipher/reject")
async def reject_decipher(request: RejectRequest) -> Dict[str, Any]:
    """User rejected all transliteration options."""
    logger.info(f"[/decipher/reject] Query: '{request.original_query}'")
    if request.feedback:
        logger.info(f"[/decipher/reject] Feedback: {request.feedback}")
    
    _pending_sessions.pop(request.original_query, None)
    
    return {
        "success": True,
        "message": "Thank you for the feedback.",
    }


# ==========================================
#  DEBUG ENDPOINTS (development only)
# ==========================================

if settings.is_development:
    
    @app.get("/debug/pending")
    async def debug_pending():
        """Show pending decipher sessions."""
        return {
            "pending_count": len(_pending_sessions),
            "queries": list(_pending_sessions.keys()),
        }
    
    @app.get("/debug/config")
    async def debug_config():
        """Show current configuration."""
        return {
            "environment": settings.environment,
            "log_level": settings.log_level,
            "log_dir": str(LOG_DIR),
            "cache_dir": str(settings.cache_dir),
            "claude_model": settings.claude_model,
            "sefaria_base_url": settings.sefaria_base_url,
        }
    
    @app.get("/debug/logs")
    async def debug_logs():
        """Check if logs exist."""
        log_files = list(LOG_DIR.glob("*.log")) if LOG_DIR.exists() else []
        return {
            "log_dir": str(LOG_DIR),
            "exists": LOG_DIR.exists(),
            "log_files": [f.name for f in log_files],
        }


# ==========================================
#  MAIN
# ==========================================

if __name__ == "__main__":
    import uvicorn
    
    print(f"\n{'='*60}")
    print(f"Marei Mekomos API Server")
    print(f"{'='*60}")
    print(f"Log directory: {LOG_DIR}")
    print(f"Environment: {settings.environment}")
    print(f"URL: http://{settings.host}:{settings.port}")
    print(f"{'='*60}\n")
    
    uvicorn.run(
        "api_server_v7:app",
        host=settings.host,
        port=settings.port,
        reload=settings.is_development,
    )