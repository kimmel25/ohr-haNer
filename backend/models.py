"""
Central Data Models for Marei Mekomos V7
========================================

All Pydantic models for type-safe data flow through the pipeline.
Using Pydantic instead of dataclasses provides:
- Runtime validation
- Automatic type coercion
- JSON serialization
- Better IDE support
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum
from datetime import datetime


# ==========================================
#  ENUMS
# ==========================================

class QueryType(str, Enum):
    """Types of Torah queries."""
    SUGYA_CONCEPT = "sugya_concept"
    HALACHA_TERM = "halacha_term"
    DAF_REFERENCE = "daf_reference"
    MASECHTA = "masechta"
    PERSON = "person"
    PASUK = "pasuk"
    KLAL = "klal"
    AMBIGUOUS = "ambiguous"
    UNKNOWN = "unknown"


class FetchStrategy(str, Enum):
    """How to fetch and organize sources."""
    TRICKLE_UP = "trickle_up"
    TRICKLE_DOWN = "trickle_down"
    DIRECT = "direct"
    SURVEY = "survey"


class SourceLevel(str, Enum):
    """Levels in the trickle-up hierarchy."""
    CHUMASH = "chumash"
    MISHNA = "mishna"
    GEMARA = "gemara"
    RASHI = "rashi"
    TOSFOS = "tosfos"
    RISHONIM = "rishonim"
    RAMBAM = "rambam"
    TUR = "tur"
    SHULCHAN_ARUCH = "shulchan_aruch"
    NOSEI_KEILIM = "nosei_keilim"
    ACHARONIM = "acharonim"
    OTHER = "other"


class ValidationMode(str, Enum):
    """Types of user validation needed."""
    NONE = "none"
    CLARIFY = "clarify"
    CHOOSE = "choose"
    UNKNOWN = "unknown"


class ConfidenceLevel(str, Enum):
    """Confidence levels throughout the pipeline."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ==========================================
#  STEP 1 MODELS (Transliteration)
# ==========================================

class WordValidation(BaseModel):
    """Validation info for a single word."""
    original: str
    best_match: str
    alternatives: List[str] = []
    confidence: float = Field(ge=0.0, le=1.0)
    needs_validation: bool = False
    validation_type: ValidationMode = ValidationMode.NONE
    is_exception: bool = False
    rules_applied: List[str] = []


class DecipherResult(BaseModel):
    """Result from Step 1: Transliteration → Hebrew"""

    # Core result
    success: bool
    hebrew_term: Optional[str] = None

    # Metadata
    confidence: ConfidenceLevel
    method: str  # "dictionary", "sefaria", "transliteration", etc.
    message: str = ""

    # Alternatives and validation
    alternatives: List[str] = []
    needs_clarification: bool = False

    # Per-word breakdown (for multi-word queries)
    word_validations: List[WordValidation] = []

    # For validation UI
    needs_validation: bool = False
    validation_type: ValidationMode = ValidationMode.NONE
    choose_options: List[str] = []

    # Optional metadata
    sample_refs: List[str] = []

    class Config:
        use_enum_values = True


# ==========================================
#  STEP 2 MODELS (Understanding)
# ==========================================

class RelatedSugya(BaseModel):
    """A sugya related to the main one."""
    ref: str
    he_ref: str
    connection: str
    importance: str  # "primary", "secondary", "tangential"


class SearchStrategy(BaseModel):
    """
    Result from Step 2: Understanding the query.
    Tells Step 3 what to do.
    """

    # Query classification
    query_type: QueryType

    # Primary source
    primary_source: Optional[str] = None
    primary_source_he: Optional[str] = None

    # Analysis
    reasoning: str = ""

    # Related sugyos
    related_sugyos: List[RelatedSugya] = []

    # Fetch instructions
    fetch_strategy: FetchStrategy = FetchStrategy.TRICKLE_UP
    depth: str = "standard"  # basic, standard, expanded, full

    # Confidence
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    clarification_prompt: Optional[str] = None

    # Metadata
    sefaria_hits: int = 0
    hits_by_masechta: Dict[str, int] = {}

    class Config:
        use_enum_values = True


# ==========================================
#  STEP 3 MODELS (Search Results)
# ==========================================

class Source(BaseModel):
    """A single Torah source."""

    # Reference
    ref: str
    he_ref: str

    # Classification
    level: SourceLevel
    level_hebrew: str = ""
    level_order: int = 99

    # Content
    hebrew_text: str
    english_text: str = ""

    # Metadata
    author: str = ""
    categories: List[str] = []

    # Display
    is_primary: bool = False
    relevance_note: str = ""

    class Config:
        use_enum_values = True


class RelatedSugyaResult(BaseModel):
    """A related sugya with preview."""
    ref: str
    he_ref: str
    connection: str
    importance: str
    preview_text: str = ""


class SearchResult(BaseModel):
    """
    Result from Step 3: Organized sources.
    """

    # Query info
    original_query: str
    hebrew_term: str

    # Primary source
    primary_source: Optional[str] = None
    primary_source_he: Optional[str] = None

    # Sources (organized)
    sources: List[Source] = []
    sources_by_level: Dict[str, List[Source]] = {}
    related_sugyos: List[RelatedSugyaResult] = []

    # Metadata
    total_sources: int = 0
    levels_included: List[str] = []

    # Analysis
    interpretation: str = ""
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM

    # Clarification
    needs_clarification: bool = False
    clarification_prompt: Optional[str] = None

    class Config:
        use_enum_values = True


# ==========================================
#  COMPLETE PIPELINE RESULT
# ==========================================

class MareiMekomosResult(BaseModel):
    """
    Complete result from the full pipeline.
    Combines outputs from all 3 steps.
    """

    # Input
    original_query: str

    # Step 1: Transliteration
    hebrew_term: Optional[str] = None
    transliteration_confidence: ConfidenceLevel
    transliteration_method: str

    # Step 2: Understanding
    query_type: QueryType
    primary_source: Optional[str] = None
    primary_source_he: Optional[str] = None
    interpretation: str = ""

    # Step 3: Sources
    sources: List[Source] = []
    sources_by_level: Dict[str, List[Source]] = {}
    related_sugyos: List[RelatedSugyaResult] = []

    # Metadata
    total_sources: int = 0
    levels_included: List[str] = []

    # Overall status
    success: bool
    confidence: ConfidenceLevel
    needs_clarification: bool = False
    clarification_prompt: Optional[str] = None
    message: str = ""

    # Timestamp
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        use_enum_values = True

    @validator('transliteration_confidence', 'confidence', pre=True)
    def convert_confidence_str(cls, v):
        """Convert string confidence to enum."""
        if isinstance(v, str):
            return ConfidenceLevel(v)
        return v


# ==========================================
#  API REQUEST/RESPONSE MODELS
# ==========================================

class SearchRequest(BaseModel):
    """Request for full search."""
    query: str = Field(..., min_length=1, description="User's query")
    depth: str = Field("standard", description="Search depth")

    @validator('query')
    def query_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Query cannot be empty')
        return v.strip()


class DecipherRequest(BaseModel):
    """Request for Step 1 only."""
    query: str = Field(..., min_length=1)
    strict: bool = False


class ConfirmRequest(BaseModel):
    """Confirm user's transliteration selection."""
    original_query: str
    selection_index: int = Field(..., ge=0)
    selected_hebrew: Optional[str] = None


class RejectRequest(BaseModel):
    """Reject a transliteration."""
    original_query: str
    incorrect_hebrew: str
    user_feedback: Optional[str] = None


# ==========================================
#  DICTIONARY ENTRY MODEL
# ==========================================

class DictionaryEntry(BaseModel):
    """Entry in the word dictionary."""
    hebrew: str
    confidence: ConfidenceLevel
    usage_count: int = 0
    source: str = "manual"  # manual, sefaria, user_confirmed, etc.
    last_used: Optional[str] = None

    class Config:
        use_enum_values = True


# ==========================================
#  SEFARIA API MODELS
# ==========================================

class SefariaText(BaseModel):
    """A text fetched from Sefaria."""
    ref: str
    he_ref: str
    hebrew: str = ""
    english: str = ""
    categories: List[str] = []
    author: str = ""

    # Metadata
    level: Optional[SourceLevel] = None
    text_type: str = ""


class SefariaSearchResult(BaseModel):
    """Result from Sefaria search."""
    query: str
    total_hits: int = 0
    results: List[Dict[str, Any]] = []

    # Aggregations
    hits_by_category: Dict[str, int] = {}
    hits_by_masechta: Dict[str, int] = {}

    # Top result
    top_ref: Optional[str] = None
    top_ref_he: Optional[str] = None


# ==========================================
#  UTILITY FUNCTIONS
# ==========================================

def confidence_to_enum(value: Any) -> ConfidenceLevel:
    """Convert any confidence value to ConfidenceLevel enum."""
    if isinstance(value, ConfidenceLevel):
        return value
    if isinstance(value, str):
        return ConfidenceLevel(value.lower())
    # Default for unknown types
    return ConfidenceLevel.MEDIUM
