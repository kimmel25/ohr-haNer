"""
Clarification Module
====================

Handles query disambiguation when confidence is low.

PHILOSOPHY:
- Torah is too endless to rely on rigid fixes
- When uncertain, ask the user with clear choices
- Questions should be easy to answer even for someone who doesn't know the topic
- The trick is to have good options

This module is interface-agnostic - works for console, API, or any other interface.
"""

import logging
import json
import uuid
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

import google.generativeai as genai

try:
    from config import get_settings
    settings = get_settings()
except ImportError:
    import os
    class Settings:
        gemini_api_key = os.environ.get("GEMINI_API_KEY", "")
        gemini_model = "gemini-2.0-flash"
        gemini_clarification_max_tokens = 1500
    settings = Settings()

logger = logging.getLogger(__name__)


# ==============================================================================
#  CONFIGURATION
# ==============================================================================

# Confidence thresholds for triggering clarification
CONFIDENCE_THRESHOLD_HIGH = 0.8  # Above this, no clarification needed
CONFIDENCE_THRESHOLD_MEDIUM = 0.5  # Between medium and high, optional clarification
CONFIDENCE_THRESHOLD_LOW = 0.3  # Below this, always ask for clarification

# Maximum options to show user
MAX_CLARIFICATION_OPTIONS = 4


# ==============================================================================
#  DATA STRUCTURES
# ==============================================================================

@dataclass
class ClarificationOption:
    """A single clarification option."""
    id: str
    label: str
    hebrew: Optional[str] = None
    description: str = ""
    focus_terms: List[str] = field(default_factory=list)
    refs_hint: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "hebrew": self.hebrew,
            "description": self.description,
            "focus_terms": self.focus_terms,
            "refs_hint": self.refs_hint,
        }


@dataclass
class ClarificationResult:
    """Result of clarification check."""
    needs_clarification: bool
    question: str = ""
    options: List[ClarificationOption] = field(default_factory=list)
    reason: str = ""
    query_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "needs_clarification": self.needs_clarification,
            "question": self.question,
            "options": [opt.to_dict() for opt in self.options],
            "reason": self.reason,
            "query_id": self.query_id,
        }


class ClarificationReason(str, Enum):
    """Why clarification is needed."""
    LOW_CONFIDENCE = "low_confidence"
    MULTIPLE_INTERPRETATIONS = "multiple_interpretations"
    AMBIGUOUS_AUTHOR = "ambiguous_author"
    AMBIGUOUS_SCOPE = "ambiguous_scope"
    UNKNOWN_TOPIC = "unknown_topic"


# ==============================================================================
#  CLARIFICATION CHECKER
# ==============================================================================

def should_ask_clarification(
    confidence: str,
    landmark_confidence: str = "none",
    query_type: str = "",
    has_qualifiers: bool = False,
    known_sugya_matched: bool = False,
    known_sugya_has_subtopics: bool = False,
) -> Tuple[bool, ClarificationReason]:
    """
    Determine if we should ask the user for clarification.

    Args:
        confidence: Overall confidence level (high/medium/low)
        landmark_confidence: How confident about the landmark source
        query_type: Type of query (topic, machlokes, shittah, etc.)
        has_qualifiers: Whether the query has narrowing qualifiers
        known_sugya_matched: Whether we matched a known sugya
        known_sugya_has_subtopics: Whether the matched sugya has sub_topics defined

    Returns:
        Tuple of (should_ask: bool, reason: ClarificationReason)
    """
    confidence_lower = confidence.lower() if confidence else "low"
    landmark_lower = landmark_confidence.lower() if landmark_confidence else "none"
    query_type_lower = query_type.lower() if query_type else ""

    # Always ask if confidence is low
    if confidence_lower == "low":
        return True, ClarificationReason.LOW_CONFIDENCE

    # Ask if landmark is just a guess and we don't have a known sugya match
    if landmark_lower in ("guessing", "none") and not known_sugya_matched:
        return True, ClarificationReason.LOW_CONFIDENCE

    # KEY FIX: For machlokes/comparison queries, ALWAYS check for clarification
    # even with high confidence, because the topic may have multiple sub-discussions
    # Only skip if the query has specific qualifiers that narrow it down
    if query_type_lower in ("machlokes", "comparison", "machloket"):
        if not has_qualifiers:
            # Even if we matched a known sugya, ask for clarification
            # This handles "machlokes abaya rava on tashbisu" where there are multiple disputes
            return True, ClarificationReason.MULTIPLE_INTERPRETATIONS

    # If known sugya has subtopics defined, ask which one they want
    if known_sugya_matched and known_sugya_has_subtopics and not has_qualifiers:
        return True, ClarificationReason.MULTIPLE_INTERPRETATIONS

    # If confidence is medium and it's a complex query type, consider asking
    if confidence_lower == "medium" and query_type_lower in ("sugya", "topic"):
        # Only ask if we don't have a strong known sugya match
        if not known_sugya_matched:
            return True, ClarificationReason.AMBIGUOUS_SCOPE

    return False, ClarificationReason.LOW_CONFIDENCE


# ==============================================================================
#  OPTION GENERATION (Claude-based)
# ==============================================================================

CLARIFICATION_PROMPT = """You are helping clarify a Torah query that could have multiple interpretations.

QUERY: {query}
HEBREW TERMS: {hebrew_terms}
TOPIC DETECTED: {topic}
CONTEXT: {context}

The user's query is ambiguous. Generate 3-4 possible interpretations as clarification options.

CRITICAL RULES:
1. Be SPECIFIC - don't just offer "General overview" vs "Specific question"
2. For MACHLOKES queries, offer options like:
   - The specific gemara location where the machlokes appears (e.g., "Machlokes on Pesachim 4b-5a")
   - Each side's specific shittah (e.g., "Rava's shittah on X", "Abaye's shittah on X")
   - Related sugyos where this machlokes is discussed
   - The halachic implications of the machlokes
3. Each option should be a DISTINCT, VALID interpretation
4. Keep labels SHORT (3-6 words) but MEANINGFUL
5. Include the DAPIM (folios) in the options when you know them
6. Include focus_terms that would help narrow the search for each option
7. Include refs_hint with specific gemara references like "Pesachim 4b", "Pesachim 5a"

EXAMPLE FOR "machlokes rava abaye on tashbisu":
```json
{{
  "question": "Which aspect of the machlokes Rava/Abaye on tashbisu?",
  "options": [
    {{
      "id": "sugya_4b_5a",
      "label": "Main sugya on Pesachim 4b-5a",
      "hebrew": "סוגיית תשביתו בפסחים ד-ה",
      "description": "The core machlokes about when and how to eliminate chametz",
      "focus_terms": ["תשביתו", "ביעור", "אביי", "רבא"],
      "refs_hint": ["Pesachim 4b", "Pesachim 5a"]
    }},
    {{
      "id": "rava_shittah",
      "label": "Rava's shittah specifically",
      "hebrew": "שיטת רבא בתשביתו",
      "description": "Focus on Rava's view and his derivation",
      "focus_terms": ["רבא", "תשביתו", "לא תשחט"],
      "refs_hint": ["Pesachim 5a"]
    }},
    {{
      "id": "abaye_shittah",
      "label": "Abaye's shittah specifically",
      "hebrew": "שיטת אביי בתשביתו",
      "description": "Focus on Abaye's view and his derivation from two pesukim",
      "focus_terms": ["אביי", "תשביתו", "שני קראי"],
      "refs_hint": ["Pesachim 4b", "Pesachim 5a"]
    }},
    {{
      "id": "rishonim_view",
      "label": "Rishonim on this machlokes",
      "hebrew": "ראשונים על מחלוקת זו",
      "description": "How Rashi, Tosafos, and other Rishonim explain this dispute",
      "focus_terms": ["תשביתו", "אביי", "רבא"],
      "refs_hint": ["Rashi on Pesachim 4b", "Tosafot on Pesachim 5a"]
    }}
  ]
}}
```

Return ONLY valid JSON (no markdown code blocks):
"""


async def generate_clarification_options(
    query: str,
    hebrew_terms: List[str],
    topic: str = "",
    context: str = "",
    known_sugya_data: Optional[Dict] = None,
) -> ClarificationResult:
    """
    Generate clarification options using Claude.

    Args:
        query: Original user query
        hebrew_terms: Hebrew terms extracted from query
        topic: Detected topic (if any)
        context: Additional context about the query
        known_sugya_data: If we matched a known sugya, its data

    Returns:
        ClarificationResult with question and options
    """
    logger.info(f"[CLARIFICATION] Generating options for: {query}")

    # First, check if known_sugya has sub_topics we can use directly
    if known_sugya_data:
        options_from_sugya = _extract_options_from_sugya(known_sugya_data)
        if options_from_sugya:
            logger.info(f"[CLARIFICATION] Using {len(options_from_sugya)} options from known sugya")
            return ClarificationResult(
                needs_clarification=True,
                question=f"Which aspect of {topic or 'this topic'} are you asking about?",
                options=options_from_sugya,
                reason="Options from known sugya database",
            )

    # Otherwise, ask Gemini to generate options
    try:
        # Configure Gemini
        genai.configure(api_key=settings.gemini_api_key)

        # Build the full prompt with system context
        system_context = "You are a Torah learning assistant. Help clarify ambiguous queries by generating distinct interpretation options."
        prompt_text = CLARIFICATION_PROMPT.format(
            query=query,
            hebrew_terms=hebrew_terms,
            topic=topic,
            context=context,
        )
        full_prompt = f"{system_context}\n\n{prompt_text}"

        model_name = getattr(settings, "gemini_model", "gemini-2.0-flash")
        max_tokens = min(
            getattr(settings, "gemini_clarification_max_tokens", 1500),
            1500,
        )
        model = genai.GenerativeModel(
            model_name=model_name,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=0.3,  # Slight creativity for diverse options
            )
        )

        response = model.generate_content(full_prompt)
        raw_text = response.text.strip()

        # Parse JSON
        json_text = raw_text
        if "```json" in raw_text:
            json_text = raw_text.split("```json")[1].split("```")[0].strip()
        elif "```" in raw_text:
            json_text = raw_text.split("```")[1].split("```")[0].strip()

        data = json.loads(json_text)

        options = []
        for opt_data in data.get("options", [])[:MAX_CLARIFICATION_OPTIONS]:
            opt = ClarificationOption(
                id=opt_data.get("id", f"option_{len(options)+1}"),
                label=opt_data.get("label", ""),
                hebrew=opt_data.get("hebrew"),
                description=opt_data.get("description", ""),
                focus_terms=opt_data.get("focus_terms", []),
                refs_hint=opt_data.get("refs_hint", []),
            )
            options.append(opt)

        logger.info(f"[CLARIFICATION] Generated {len(options)} options from Gemini")

        return ClarificationResult(
            needs_clarification=True,
            question=data.get("question", "Which interpretation did you mean?"),
            options=options,
            reason="Generated by Gemini",
        )

    except Exception as e:
        logger.error(f"[CLARIFICATION] Error generating options: {e}")
        # Return a fallback result
        return ClarificationResult(
            needs_clarification=True,
            question="Could you clarify what you're looking for?",
            options=[
                ClarificationOption(
                    id="general",
                    label="General overview",
                    description="Show me all sources on this topic",
                ),
                ClarificationOption(
                    id="specific",
                    label="Specific question",
                    description="I have a specific question about this topic",
                ),
            ],
            reason=f"Fallback due to error: {e}",
        )


def _extract_options_from_sugya(sugya_data: Dict) -> List[ClarificationOption]:
    """
    Extract clarification options from known sugya sub_topics.

    Args:
        sugya_data: Raw data from known_sugyos database

    Returns:
        List of ClarificationOption from sub_topics
    """
    options = []
    sub_topics = sugya_data.get("sub_topics", {})

    for sub_id, sub_data in sub_topics.items():
        if isinstance(sub_data, dict):
            opt = ClarificationOption(
                id=sub_id,
                label=sub_data.get("label", sub_id.replace("_", " ").title()),
                hebrew=sub_data.get("hebrew"),
                description=sub_data.get("description", ""),
                focus_terms=sub_data.get("focus_terms", []),
                refs_hint=sub_data.get("primary_refs", []),
            )
            options.append(opt)

    return options[:MAX_CLARIFICATION_OPTIONS]


# ==============================================================================
#  PROCESS USER SELECTION
# ==============================================================================

def process_clarification_selection(
    original_query: str,
    selected_option: ClarificationOption,
    original_hebrew_terms: List[str],
) -> Dict[str, Any]:
    """
    Process user's clarification selection and return enriched query context.

    This provides the information needed to re-run the search with
    the user's clarified intent.

    Args:
        original_query: The original user query
        selected_option: The option the user selected
        original_hebrew_terms: Hebrew terms from original Step 1

    Returns:
        Dict with enriched context for resuming the search
    """
    # Combine original terms with option's focus terms
    enriched_terms = list(original_hebrew_terms)
    for term in selected_option.focus_terms:
        if term not in enriched_terms:
            enriched_terms.append(term)

    # Build the clarified query context
    return {
        "original_query": original_query,
        "clarified_intent": selected_option.label,
        "hebrew_terms": enriched_terms,
        "focus_terms": selected_option.focus_terms,
        "refs_hint": selected_option.refs_hint,
        "description": selected_option.description,
        # Flag to skip clarification on retry
        "skip_clarification": True,
    }


# ==============================================================================
#  CONVENIENCE FUNCTIONS
# ==============================================================================

def _detect_qualifiers(query: str) -> bool:
    """
    Detect if the query has specific qualifiers that narrow down the topic.

    Qualifiers are things like:
    - "beissurin" (in prohibitions)
    - "bemamonos" (in monetary matters)
    - "lehalacha" (for practical law)
    - "leshitaso" (according to his view)
    - Specific daf references like "on daf 12"
    """
    query_lower = query.lower()

    # Common qualifiers that narrow down a topic
    qualifiers = [
        "beissurin", "be'issurin", "b'issurin",
        "bemamonos", "be'mamonos", "b'mamonos",
        "behalacha", "lehalacha", "l'halacha",
        "leshitaso", "l'shitaso",
        "specifically", "particularly", "regarding the",
        "on daf", "in perek",
        # Hebrew qualifiers
        "באיסורין", "במאמונות", "להלכה", "לשיטתו",
    ]

    for q in qualifiers:
        if q in query_lower:
            return True

    return False


def _build_label_options(labels: List[Any]) -> List[ClarificationOption]:
    options: List[ClarificationOption] = []
    for raw in labels:
        if raw is None:
            continue
        if isinstance(raw, dict):
            label = raw.get("label") or raw.get("id") or ""
        else:
            label = str(raw)
        label = label.strip()
        if not label:
            continue
        options.append(
            ClarificationOption(
                id=f"option_{len(options) + 1}",
                label=label,
                description="",
            )
        )
        if len(options) >= MAX_CLARIFICATION_OPTIONS:
            break
    return options


def _ensure_minimum_options(options: List[ClarificationOption]) -> List[ClarificationOption]:
    if len(options) >= 2:
        return options
    if len(options) == 0:
        return [
            ClarificationOption(
                id="general",
                label="General overview",
                description="Show me all sources on this topic",
            ),
            ClarificationOption(
                id="specific",
                label="Specific question",
                description="I have a specific question about this topic",
            ),
        ]
    options.append(
        ClarificationOption(
            id="other",
            label="Something else",
            description="A different interpretation",
        )
    )
    return options


def _fallback_clarification_result(question: str, reason: str, query: str = "") -> ClarificationResult:
    """
    Generate fallback clarification options based on query type.

    V6.1: More specific fallback options based on detected query patterns.
    """
    query_lower = query.lower() if query else ""

    # Detect machlokes queries
    if any(kw in query_lower for kw in ["machlokes", "machloket", "מחלוקת", "dispute"]):
        return ClarificationResult(
            needs_clarification=True,
            question=question,
            options=[
                ClarificationOption(
                    id="main_sugya",
                    label="Main sugya (primary discussion)",
                    hebrew="סוגיא עיקרית",
                    description="The primary gemara where this machlokes appears",
                ),
                ClarificationOption(
                    id="one_side",
                    label="One specific shittah",
                    hebrew="שיטה אחת בפרט",
                    description="Focus on one side of the machlokes",
                ),
                ClarificationOption(
                    id="rishonim",
                    label="Rishonim on this machlokes",
                    hebrew="ראשונים",
                    description="How the Rishonim explain this dispute",
                ),
                ClarificationOption(
                    id="halacha",
                    label="Halachic conclusion",
                    hebrew="למעשה",
                    description="The practical halachic ruling",
                ),
            ],
            reason=reason,
        )

    # Default fallback
    return ClarificationResult(
        needs_clarification=True,
        question=question,
        options=[
            ClarificationOption(
                id="core_sugya",
                label="Core sugya / main source",
                hebrew="סוגיא עיקרית",
                description="The primary gemara discussing this topic",
            ),
            ClarificationOption(
                id="commentaries",
                label="With Rishonim & Acharonim",
                hebrew="עם מפרשים",
                description="Include commentaries and later sources",
            ),
            ClarificationOption(
                id="halacha",
                label="Halachic application",
                hebrew="להלכה",
                description="Focus on practical halacha in Shulchan Aruch",
            ),
        ],
        reason=reason,
    )


async def check_and_generate_clarification(
    query: str,
    hebrew_terms: List[str],
    confidence: str,
    landmark_confidence: str = "none",
    query_type: str = "",
    topic: str = "",
    known_sugya_data: Optional[Dict] = None,
    context: str = "",
    clarification_question: Optional[str] = None,
    clarification_options: Optional[List[str]] = None,
    possible_interpretations: Optional[List[Dict]] = None,  # V7: From Step 2 Claude call
) -> Optional[ClarificationResult]:
    """
    Convenience function: Check if clarification needed and generate options if so.

    This is the main entry point for the clarification system.

    V7 OPTIMIZATION: If possible_interpretations is provided (from Step 2 Claude call),
    we use those directly instead of making another Claude API call.

    Args:
        query: User's original query
        hebrew_terms: Hebrew terms from Step 1
        confidence: Overall confidence level
        landmark_confidence: Confidence about landmark source
        query_type: Type of query
        topic: Detected topic
        known_sugya_data: Known sugya data if matched
        context: Additional context
        clarification_question: Question text from Step 2 if available
        clarification_options: Option labels from Step 2 if available
        possible_interpretations: Pre-computed interpretations from Step 2 Claude call

    Returns:
        ClarificationResult if clarification needed, None otherwise
    """
    # Detect if query has qualifiers that narrow it down
    has_qualifiers = _detect_qualifiers(query)

    # Check if known sugya has sub_topics defined
    has_subtopics = bool(known_sugya_data and known_sugya_data.get("sub_topics"))

    # Detect machlokes/comparison from query text if query_type doesn't indicate it
    # This catches "machlokes abaya rava on X" even if Claude classified it as "topic"
    query_lower = query.lower()
    effective_query_type = query_type
    machlokes_keywords = ["machlokes", "machloket", "מחלוקת", "dispute", "argument between"]
    for kw in machlokes_keywords:
        if kw in query_lower:
            effective_query_type = "machlokes"
            logger.info(f"[CLARIFICATION] Detected machlokes query from keyword: {kw}")
            break

    logger.debug(f"[CLARIFICATION] has_qualifiers={has_qualifiers}, has_subtopics={has_subtopics}, effective_type={effective_query_type}")

    # First check if we should ask
    should_ask, reason = should_ask_clarification(
        confidence=confidence,
        landmark_confidence=landmark_confidence,
        query_type=effective_query_type,
        has_qualifiers=has_qualifiers,
        known_sugya_matched=bool(known_sugya_data),
        known_sugya_has_subtopics=has_subtopics,
    )

    if not should_ask:
        return None

    logger.info(f"[CLARIFICATION] Clarification needed: {reason.value}")

    question = clarification_question or f"Which aspect of {topic or 'this topic'} are you asking about?"

    # V7: Use possible_interpretations from Step 2 if available (no extra API call!)
    if possible_interpretations:
        logger.info(f"[CLARIFICATION] Using {len(possible_interpretations)} interpretations from Step 2 (no extra API call)")
        options = []
        for interp in possible_interpretations[:MAX_CLARIFICATION_OPTIONS]:
            opt = ClarificationOption(
                id=interp.get("id", f"option_{len(options)+1}"),
                label=interp.get("label", ""),
                hebrew=interp.get("hebrew"),
                description=interp.get("description", ""),
                focus_terms=interp.get("focus_terms", []),
                refs_hint=interp.get("refs_hint", []),
            )
            options.append(opt)
        options = _ensure_minimum_options([opt for opt in options if opt.label])
        if options:
            return ClarificationResult(
                needs_clarification=True,
                question=question,
                options=options,
                reason=reason.value,
            )

    # Use Step 2 clarification options if provided (no extra API call)
    if clarification_options:
        options = _build_label_options(clarification_options)
        options = _ensure_minimum_options(options)
        if options:
            return ClarificationResult(
                needs_clarification=True,
                question=question,
                options=options,
                reason=reason.value,
            )

    # Check if known_sugya has sub_topics we can use
    if known_sugya_data:
        options_from_sugya = _extract_options_from_sugya(known_sugya_data)
        if options_from_sugya:
            logger.info(f"[CLARIFICATION] Using {len(options_from_sugya)} options from known sugya (no extra API call)")
            return ClarificationResult(
                needs_clarification=True,
                question=question,
                options=options_from_sugya,
                reason=reason.value,
            )

    # Fallback: Skip extra Claude call unless explicitly enabled
    if not getattr(settings, "clarification_use_llm", False):
        logger.info("[CLARIFICATION] No pre-computed options; using generic fallback (no extra API call)")
        return _fallback_clarification_result(question, reason.value, query=query)

    logger.info("[CLARIFICATION] No pre-computed options, falling back to Gemini API call")
    result = await generate_clarification_options(
        query=query,
        hebrew_terms=hebrew_terms,
        topic=topic,
        context=context,
        known_sugya_data=known_sugya_data,
    )

    result.reason = reason.value
    return result


# ==============================================================================
#  SESSION STORAGE (for stateless API)
# ==============================================================================

# In-memory storage for clarification sessions
# In production, this should be Redis or similar
_clarification_sessions: Dict[str, Dict] = {}


def store_clarification_session(
    query_id: str,
    original_query: str,
    hebrew_terms: List[str],
    options: List[ClarificationOption],
    analysis: Optional[Any] = None,
    partial_analysis: Optional[Dict] = None,
) -> None:
    """Store a clarification session for later retrieval."""
    _clarification_sessions[query_id] = {
        "original_query": original_query,
        "hebrew_terms": hebrew_terms,
        "options": {opt.id: opt for opt in options},
        "analysis": analysis,
        "partial_analysis": partial_analysis,
    }


def get_clarification_session(query_id: str) -> Optional[Dict]:
    """Retrieve a stored clarification session."""
    return _clarification_sessions.get(query_id)


def get_selected_option(query_id: str, option_id: str) -> Optional[ClarificationOption]:
    """Get a specific option from a stored session."""
    session = get_clarification_session(query_id)
    if not session:
        return None
    return session.get("options", {}).get(option_id)


def clear_clarification_session(query_id: str) -> None:
    """Clear a clarification session after it's used."""
    _clarification_sessions.pop(query_id, None)


# ==============================================================================
#  EXPORTS
# ==============================================================================

__all__ = [
    # Core classes
    "ClarificationOption",
    "ClarificationResult",
    "ClarificationReason",
    # Main functions
    "should_ask_clarification",
    "generate_clarification_options",
    "process_clarification_selection",
    "check_and_generate_clarification",
    # Session management
    "store_clarification_session",
    "get_clarification_session",
    "get_selected_option",
    "clear_clarification_session",
    # Constants
    "CONFIDENCE_THRESHOLD_HIGH",
    "CONFIDENCE_THRESHOLD_MEDIUM",
    "CONFIDENCE_THRESHOLD_LOW",
    "MAX_CLARIFICATION_OPTIONS",
]
