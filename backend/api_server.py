"""
Marei Mekomos V7 - FastAPI Server
==================================

Serves Step 1 (DECIPHER) to the frontend with full validation support.

Endpoints:
- POST /decipher          - Main transliteration endpoint
- POST /decipher/confirm  - User confirms a selection
- POST /decipher/reject   - User says "not what I meant"
- GET  /health            - Health check

The flow:
1. User submits transliteration via /decipher
2. If high confidence → returns Hebrew term directly
3. If needs validation → returns options for user to choose
4. User selects option via /decipher/confirm
5. System learns from user selection

Based on Architecture.md: "never yes or no questions, leave room for him to say
I'm not sure/I don't know"
"""

import sys
import asyncio
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent))

# Import Step 1 modules
from step_one_decipher import decipher
from user_validation import (
    analyze_query,
    apply_user_selection,
    ValidationResult,
    ValidationType,
)
from tools.word_dictionary import get_dictionary

import logging

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

class DecipherRequest(BaseModel):
    """Request to transliterate a term"""
    query: str
    strict: bool = False  # If True, ask for validation even on medium confidence


class DecipherConfirmRequest(BaseModel):
    """User confirms a selection from options"""
    original_query: str
    selection_index: int  # 1-based index of user's choice (0 = none of these)
    selected_hebrew: Optional[str] = None  # If user typed custom answer


class DecipherRejectRequest(BaseModel):
    """User says the translation wasn't what they meant"""
    original_query: str
    incorrect_hebrew: str
    user_feedback: Optional[str] = None  # Optional free-text feedback


class WordValidationResponse(BaseModel):
    """Response for a single word's validation"""
    original: str
    best_match: str
    alternatives: List[str]
    confidence: float
    needs_validation: bool
    validation_type: str


class DecipherResponse(BaseModel):
    """Full response from decipher endpoint"""
    success: bool
    
    # The transliteration result
    original_query: str
    normalized_query: str
    hebrew_term: Optional[str] = None
    
    # Confidence info
    confidence: str  # "high", "medium", "low"
    confidence_score: float
    method: Optional[str] = None  # "dictionary", "sefaria", "transliteration"
    
    # Validation info
    needs_validation: bool
    validation_type: str  # "NONE", "CLARIFY", "CHOOSE", "UNKNOWN"
    
    # Options for user (if needs_validation)
    clarify_options: List[dict] = []  # For "Did you mean X or Y?"
    choose_options: List[str] = []     # For numbered selection
    
    # Per-word breakdown (for multi-word queries)
    word_validations: List[dict] = []
    uncertain_word_indices: List[int] = []
    
    # Sefaria sample references (if found)
    sample_refs: List[str] = []
    
    # Message for the user
    message: str = ""


class ConfirmResponse(BaseModel):
    """Response after user confirms selection"""
    success: bool
    hebrew_term: str
    message: str
    learned: bool  # Whether we added this to dictionary
    word_validations: List[dict] = []  # Per-word breakdown for multi-word queries


class RejectResponse(BaseModel):
    """Response after user rejects translation"""
    success: bool
    message: str
    suggestions: List[str] = []  # Alternative suggestions


# ==========================================
#  FASTAPI APP
# ==========================================

app = FastAPI(
    title="אור הנר - Marei Mekomos V7",
    description="Torah source finder with intelligent transliteration",
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
    """Health check endpoint"""
    dictionary = get_dictionary()
    stats = dictionary.get_stats()
    
    return {
        "status": "healthy",
        "version": "7.0.0",
        "step_1_status": "active",
        "step_2_status": "coming_soon",
        "step_3_status": "coming_soon",
        "dictionary_entries": stats["total_entries"],
        "timestamp": datetime.now().isoformat()
    }


# ==========================================
#  MAIN DECIPHER ENDPOINT
# ==========================================

@app.post("/decipher", response_model=DecipherResponse)
async def decipher_endpoint(request: DecipherRequest):
    """
    Main transliteration endpoint.
    
    Takes user's English transliteration and returns Hebrew with confidence info.
    
    If high confidence: returns hebrew_term directly
    If needs validation: returns options for user to choose from
    """
    logger.info(f"[/decipher] Query: '{request.query}' (strict={request.strict})")
    
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    try:
        # First, run through user_validation to get structured result
        validation_result = analyze_query(request.query, strict=request.strict)
        
        # Also run the full decipher for Sefaria validation
        decipher_result = await decipher(request.query)
        
        # Build response
        response = DecipherResponse(
            success=decipher_result.get("success", False),
            original_query=request.query,
            normalized_query=validation_result.normalized,
            hebrew_term=decipher_result.get("hebrew_term"),
            confidence=validation_result.confidence,
            confidence_score=validation_result.confidence_score,
            method=decipher_result.get("method"),
            needs_validation=validation_result.needs_validation,
            validation_type=validation_result.validation_type.value,
            clarify_options=[
                {"hebrew": h, "description": d} 
                for h, d in validation_result.clarify_options
            ],
            choose_options=validation_result.choose_options,
            word_validations=[
                {
                    "original": wv.original,
                    "best_match": wv.best_match,
                    "alternatives": wv.alternatives,
                    "confidence": wv.confidence,
                    "needs_validation": wv.needs_validation,
                    "validation_type": wv.validation_type.value,
                }
                for wv in validation_result.word_validations
            ],
            uncertain_word_indices=validation_result.uncertain_word_indices,
            sample_refs=decipher_result.get("sample_refs", []),
            message=_build_user_message(validation_result, decipher_result)
        )
        
        logger.info(f"[/decipher] Result: {response.hebrew_term} "
                   f"(confidence={response.confidence}, "
                   f"needs_validation={response.needs_validation})")
        
        return response
        
    except Exception as e:
        logger.error(f"[/decipher] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


def _build_user_message(validation: ValidationResult, decipher_result: dict) -> str:
    """Build a friendly message for the user based on results"""
    
    if not validation.needs_validation:
        # High confidence - just show what we found
        hebrew = decipher_result.get("hebrew_term", "")
        method = decipher_result.get("method", "")
        
        if method == "dictionary":
            return f"Found: {hebrew}"
        else:
            return f"Found: {hebrew}"
    
    # Needs validation - explain why
    if validation.validation_type == ValidationType.CLARIFY:
        return "I found a few close matches. Which did you mean?"
    
    elif validation.validation_type == ValidationType.CHOOSE:
        return "I'm not certain about this term. Please select the correct one:"
    
    elif validation.validation_type == ValidationType.UNKNOWN:
        if validation.choose_options:
            return "I couldn't confidently recognize this term. Did you mean one of these?"
        else:
            return "I couldn't recognize this term. Try a different spelling?"
    
    return ""


# ==========================================
#  CONFIRM SELECTION ENDPOINT
# ==========================================

@app.post("/decipher/confirm", response_model=ConfirmResponse)
async def confirm_selection(request: DecipherConfirmRequest):
    """
    User confirms their selection from the options presented.
    
    This helps the system learn and improves future lookups.
    """
    logger.info(f"[/decipher/confirm] Query: '{request.original_query}', "
               f"Selection: {request.selection_index}")
    
    if request.selection_index == 0 and not request.selected_hebrew:
        # User said "none of these" without providing alternative
        return ConfirmResponse(
            success=False,
            hebrew_term="",
            message="No selection made. Try a different spelling?",
            learned=False
        )
    
    try:
        # Get the validation result again to apply selection
        validation_result = analyze_query(request.original_query)
        
        # Determine selected Hebrew
        if request.selected_hebrew:
            # User provided custom answer
            selected_hebrew = request.selected_hebrew
        elif request.selection_index > 0:
            # User selected from options
            selected_hebrew = apply_user_selection(
                validation_result, 
                request.selection_index
            )
        else:
            return ConfirmResponse(
                success=False,
                hebrew_term="",
                message="Invalid selection",
                learned=False
            )
        
        if not selected_hebrew:
            return ConfirmResponse(
                success=False,
                hebrew_term="",
                message="Could not apply selection",
                learned=False
            )
        
        # Learn this mapping for future use
        dictionary = get_dictionary()
        dictionary.add_entry(
            transliteration=validation_result.normalized,
            hebrew=selected_hebrew,
            confidence="high",  # User confirmed it
            source="user_confirmed"
        )
        
        logger.info(f"[/decipher/confirm] Learned: '{validation_result.normalized}' → '{selected_hebrew}'")
        
        # Update word_validations with the selected term
        word_validations = [
            {
                "original": wv.original,
                "best_match": wv.best_match,
                "alternatives": wv.alternatives,
                "confidence": wv.confidence,
                "needs_validation": wv.needs_validation,
                "validation_type": wv.validation_type.value,
            }
            for wv in validation_result.word_validations
        ]
        
        # If this was a multi-word query and user selected a word, update that word
        if len(validation_result.word_validations) > 1 and validation_result.uncertain_word_indices:
            uncertain_idx = validation_result.uncertain_word_indices[0]
            if uncertain_idx < len(word_validations):
                word_validations[uncertain_idx]["best_match"] = selected_hebrew
                word_validations[uncertain_idx]["confidence"] = 1.0
                word_validations[uncertain_idx]["needs_validation"] = False
        
        # Build complete Hebrew term from all words
        complete_hebrew = " ".join(wv["best_match"] for wv in word_validations) if word_validations else selected_hebrew
        
        return ConfirmResponse(
            success=True,
            hebrew_term=complete_hebrew,
            message=f"Got it! Using: {complete_hebrew}",
            learned=True,
            word_validations=word_validations
        )
        
    except Exception as e:
        logger.error(f"[/decipher/confirm] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
#  REJECT TRANSLATION ENDPOINT
# ==========================================

@app.post("/decipher/reject", response_model=RejectResponse)
async def reject_translation(request: DecipherRejectRequest):
    """
    User says the suggested Hebrew wasn't correct.
    
    This is valuable feedback - we DON'T want to learn wrong mappings.
    Following Architecture.md: "better annoy him with asking than getting it wrong"
    """
    logger.info(f"[/decipher/reject] Query: '{request.original_query}', "
               f"Rejected: '{request.incorrect_hebrew}'")
    
    try:
        # Log the rejection for analysis (could be used to improve the system)
        logger.warning(f"USER REJECTED: '{request.original_query}' was NOT '{request.incorrect_hebrew}'")
        
        if request.user_feedback:
            logger.info(f"User feedback: {request.user_feedback}")
        
        # Generate new suggestions by running decipher again with more alternatives
        validation_result = analyze_query(request.original_query, strict=True)
        
        # Filter out the rejected option
        suggestions = [
            opt for opt in validation_result.choose_options 
            if opt != request.incorrect_hebrew
        ]
        
        # Also add alternatives from word validations
        for wv in validation_result.word_validations:
            for alt in wv.alternatives:
                if alt not in suggestions and alt != request.incorrect_hebrew:
                    suggestions.append(alt)
        
        # Limit suggestions
        suggestions = suggestions[:5]
        
        return RejectResponse(
            success=True,
            message="Thanks for the feedback! Here are some other possibilities:",
            suggestions=suggestions
        )
        
    except Exception as e:
        logger.error(f"[/decipher/reject] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
#  LEGACY /search ENDPOINT (for existing frontend)
# ==========================================

class LegacySearchRequest(BaseModel):
    """Legacy request format for backwards compatibility"""
    topic: str
    clarification: Optional[str] = None


@app.post("/search")
async def legacy_search(request: LegacySearchRequest):
    """
    Legacy endpoint for backwards compatibility with existing frontend.
    
    Transforms the old format to new decipher format and back.
    """
    logger.info(f"[/search] Legacy request: '{request.topic}'")
    
    # Call decipher
    decipher_request = DecipherRequest(query=request.topic)
    result = await decipher_endpoint(decipher_request)
    
    # Transform to legacy format expected by frontend
    legacy_response = {
        "topic": request.topic,
        "success": result.success,
        "interpreted_query": result.hebrew_term,
        "needs_clarification": result.needs_validation,
        "clarifying_questions": [],
        "sources": [],  # Steps 2 and 3 not implemented yet
        "summary": result.message,
    }
    
    # Add resolved terms if successful
    if result.success and result.hebrew_term:
        legacy_response["resolved_terms"] = [{
            "original": result.original_query,
            "hebrew": result.hebrew_term,
            "confidence": result.confidence,
            "source_ref": result.sample_refs[0] if result.sample_refs else "Dictionary",
            "explanation": f"Found via {result.method}" if result.method else "Transliteration"
        }]
    
    # Add clarification options if needed
    if result.needs_validation:
        if result.clarify_options:
            legacy_response["clarifying_questions"] = [
                f"Did you mean '{opt['hebrew']}'?" 
                for opt in result.clarify_options
            ]
        elif result.choose_options:
            legacy_response["clarifying_questions"] = [
                f"Please select: " + ", ".join(
                    f"{i+1}. {opt}" for i, opt in enumerate(result.choose_options)
                )
            ]
    
    return legacy_response


# ==========================================
#  MAIN
# ==========================================

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 80)
    print("אור הנר - Marei Mekomos V7 API Server")
    print("=" * 80)
    print()
    print("Step 1 (DECIPHER): ✓ Active")
    print("Step 2 (UNDERSTAND): ⏳ Coming Soon")
    print("Step 3 (SEARCH): ⏳ Coming Soon")
    print()
    print("Endpoints:")
    print("  POST /decipher         - Main transliteration")
    print("  POST /decipher/confirm - Confirm user selection")
    print("  POST /decipher/reject  - Reject wrong translation")
    print("  POST /search           - Legacy endpoint")
    print("  GET  /health           - Health check")
    print()
    print("Starting server on http://localhost:8000")
    print("=" * 80)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)