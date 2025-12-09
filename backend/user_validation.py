"""
User Validation Module for Transliteration
===========================================

This module provides intelligent user validation when the transliteration
system is uncertain. It's designed to be UI-agnostic so it can be used
by both console and frontend applications.

TWO VALIDATION SCENARIOS:

1. "Did you mean?" (CLARIFY)
   - We have 2-3 strong candidates that are close
   - Example: "Do you mean כתובות (Kesubos) or כתובים (Kesuvim)?"
   
2. "Pick an option" (CHOOSE)  
   - We're uncertain, here are our best guesses
   - Example: "We found multiple possibilities. Please select: 1. X  2. Y  3. Z"

3. "Unknown term" (UNKNOWN)
   - We really have no idea
   - Example: "We couldn't recognize this term. Did you mean one of these?"

USAGE:
    from user_validation import analyze_query, ValidationResult
    
    result = analyze_query("chezkas haguf")
    
    if result.needs_validation:
        if result.validation_type == "CLARIFY":
            # Show "Did you mean X or Y?"
        elif result.validation_type == "CHOOSE":
            # Show numbered options 1-5
        elif result.validation_type == "UNKNOWN":
            # Show "We couldn't understand..."
    else:
        # Use result.best_match directly
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import re


class ValidationType(Enum):
    """Types of validation prompts."""
    NONE = "NONE"           # No validation needed, high confidence
    CLARIFY = "CLARIFY"     # "Did you mean X or Y?" - 2-3 close options
    CHOOSE = "CHOOSE"       # "Pick from these options" - multiple guesses
    UNKNOWN = "UNKNOWN"     # "We don't recognize this" - very low confidence


@dataclass
class WordValidation:
    """Validation info for a single word."""
    original: str
    normalized: str
    best_match: str
    alternatives: List[str]
    confidence: float  # 0.0 to 1.0
    needs_validation: bool
    validation_type: ValidationType
    is_exception: bool  # Was this word found in exceptions?
    rules_applied: List[str]  # Which rules fired


@dataclass 
class ValidationResult:
    """
    Complete validation result for a query.
    This is the main object returned to UI layers.
    """
    # Original query info
    query: str
    normalized: str
    
    # Best result (use if no validation needed)
    best_match: str
    all_variants: List[str]
    
    # Overall confidence
    confidence: str  # "high", "medium", "low"
    confidence_score: float  # 0.0 to 1.0
    
    # Validation info
    needs_validation: bool
    validation_type: ValidationType
    
    # For CLARIFY type: the close alternatives
    clarify_options: List[Tuple[str, str]]  # [(hebrew, description), ...]
    
    # For CHOOSE type: numbered options
    choose_options: List[str]  # Up to 5 options
    
    # Per-word breakdown (for multi-word queries)
    word_validations: List[WordValidation]
    
    # Which specific word(s) need validation (0-indexed)
    uncertain_word_indices: List[int]
    
    # Metadata for frontend
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization (frontend use)."""
        return {
            "query": self.query,
            "normalized": self.normalized,
            "best_match": self.best_match,
            "all_variants": self.all_variants,
            "confidence": self.confidence,
            "confidence_score": self.confidence_score,
            "needs_validation": self.needs_validation,
            "validation_type": self.validation_type.value,
            "clarify_options": [{"hebrew": h, "description": d} for h, d in self.clarify_options],
            "choose_options": self.choose_options,
            "uncertain_word_indices": self.uncertain_word_indices,
            "word_validations": [
                {
                    "original": wv.original,
                    "best_match": wv.best_match,
                    "alternatives": wv.alternatives,
                    "confidence": wv.confidence,
                    "needs_validation": wv.needs_validation,
                    "validation_type": wv.validation_type.value,
                }
                for wv in self.word_validations
            ],
            "metadata": self.metadata,
        }


# Import transliteration functions
try:
    from .tools.transliteration_map import (
        generate_smart_variants,
        generate_word_variants,
        normalize_input,
        detect_ayin_patterns,
        detect_aramaic_ending,
        detect_smichut_ending,
        detect_feminine_ending,
        detect_final_bet,
        detect_double_consonants,
        split_all_prefixes,
        MINIMAL_EXCEPTIONS,
    )
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    from tools.transliteration_map import (
        generate_smart_variants,
        generate_word_variants,
        normalize_input,
        detect_ayin_patterns,
        detect_aramaic_ending,
        detect_smichut_ending,
        detect_feminine_ending,
        detect_final_bet,
        detect_double_consonants,
        split_all_prefixes,
        MINIMAL_EXCEPTIONS,
    )


# ==========================================
#  CONFIDENCE CALCULATION
# ==========================================

def calculate_word_confidence(word: str) -> Tuple[float, List[str], bool]:
    """
    Calculate confidence score for a single word.
    
    Returns: (confidence_score, rules_applied, is_exception)
    """
    word_lower = word.lower().strip()
    rules_applied = []
    
    # Check if it's an exception (highest confidence)
    if word_lower in MINIMAL_EXCEPTIONS:
        return (1.0, ["EXCEPTION"], True)
    
    # Check prefix
    prefix_heb, root = split_all_prefixes(word_lower)
    if prefix_heb:
        rules_applied.append(f"PREFIX:{prefix_heb}")
        # Check if root is exception
        if root in MINIMAL_EXCEPTIONS:
            return (0.95, rules_applied + ["EXCEPTION"], True)
    
    # Detect patterns and accumulate confidence
    base_confidence = 0.5  # Start at medium
    
    # Ayin patterns add confidence
    ayin = detect_ayin_patterns(word_lower)
    if ayin:
        for p in ayin:
            rules_applied.append(f"AYIN:{p.pattern_type}")
            base_confidence += p.confidence * 0.2
    
    # Aramaic ending
    aramaic = detect_aramaic_ending(word_lower)
    if aramaic:
        rules_applied.append("ARAMAIC_ENDING")
        base_confidence += aramaic.confidence * 0.15
    
    # Smichut ending (saf)
    smichut = detect_smichut_ending(word_lower)
    if smichut:
        rules_applied.append("SMICHUT_SAF")
        base_confidence += smichut.confidence * 0.15
    
    # Feminine ending
    feminine = detect_feminine_ending(word_lower)
    if feminine:
        rules_applied.append("FEMININE_HEY")
        base_confidence += feminine.confidence * 0.1
    
    # Final bet
    final_b = detect_final_bet(word_lower)
    if final_b:
        rules_applied.append("FINAL_BET")
        base_confidence += final_b.confidence * 0.1
    
    # Double consonants
    doubles = detect_double_consonants(word_lower)
    if doubles:
        for p in doubles:
            rules_applied.append(f"DOUBLE:{p.likely_hebrew[0]}")
            base_confidence += p.confidence * 0.1
    
    # Penalize ambiguous patterns
    # Count vowels - more vowels = more ambiguity
    vowel_count = sum(1 for c in word_lower if c in 'aeiou')
    vowel_ratio = vowel_count / len(word_lower) if word_lower else 0
    if vowel_ratio > 0.5:
        base_confidence -= 0.15
        rules_applied.append("HIGH_VOWEL_AMBIGUITY")
    
    # Cap confidence
    confidence = min(0.95, max(0.2, base_confidence))
    
    return (confidence, rules_applied, False)


def calculate_variant_similarity(v1: str, v2: str) -> float:
    """
    Calculate similarity between two Hebrew variants.
    Returns 0.0 (completely different) to 1.0 (identical).
    """
    if v1 == v2:
        return 1.0
    
    if not v1 or not v2:
        return 0.0
    
    # Simple character-level comparison
    longer = max(len(v1), len(v2))
    matches = sum(1 for a, b in zip(v1, v2) if a == b)
    
    # Also check for similar letters (ק/כ, ת/ט, etc.)
    similar_pairs = [
        ('ק', 'כ'), ('כ', 'ק'),
        ('ת', 'ט'), ('ט', 'ת'),
        ('ס', 'ש'), ('ש', 'ס'),
        ('א', 'ע'), ('ע', 'א'),
        ('ו', 'ב'), ('ב', 'ו'),
        ('ה', 'א'), ('א', 'ה'),
        ('ח', 'כ'), ('כ', 'ח'),
    ]
    
    similar_matches = 0
    for i, (a, b) in enumerate(zip(v1, v2)):
        if a != b and (a, b) in similar_pairs:
            similar_matches += 0.5
    
    return (matches + similar_matches) / longer


# ==========================================
#  VALIDATION ANALYSIS
# ==========================================

def analyze_word(word: str) -> WordValidation:
    """
    Analyze a single word and determine if validation is needed.
    """
    normalized = normalize_input(word)
    confidence, rules, is_exception = calculate_word_confidence(normalized)
    
    # Get variants
    variants = generate_word_variants(normalized)
    if not variants:
        return WordValidation(
            original=word,
            normalized=normalized,
            best_match="",
            alternatives=[],
            confidence=0.0,
            needs_validation=True,
            validation_type=ValidationType.UNKNOWN,
            is_exception=False,
            rules_applied=[]
        )
    
    best_match = variants[0]
    alternatives = variants[1:5] if len(variants) > 1 else []
    
    # Determine validation type based on confidence and variant diversity
    needs_validation = False
    validation_type = ValidationType.NONE
    
    if is_exception:
        # Exceptions don't need validation
        needs_validation = False
        validation_type = ValidationType.NONE
    elif confidence >= 0.85:
        # High confidence - no validation needed
        needs_validation = False
        validation_type = ValidationType.NONE
    elif confidence >= 0.6:
        # Medium confidence - check if alternatives are close
        if alternatives:
            similarity = calculate_variant_similarity(best_match, alternatives[0])
            if similarity >= 0.7:
                # Close alternatives - ask for clarification
                needs_validation = True
                validation_type = ValidationType.CLARIFY
            else:
                # Diverse alternatives - let it pass but flag medium confidence
                needs_validation = False
    else:
        # Low confidence - need user to choose
        needs_validation = True
        if alternatives:
            validation_type = ValidationType.CHOOSE
        else:
            validation_type = ValidationType.UNKNOWN
    
    return WordValidation(
        original=word,
        normalized=normalized,
        best_match=best_match,
        alternatives=alternatives,
        confidence=confidence,
        needs_validation=needs_validation,
        validation_type=validation_type,
        is_exception=is_exception,
        rules_applied=rules
    )


def analyze_query(query: str, strict: bool = False) -> ValidationResult:
    """
    Main entry point: Analyze a query and determine validation needs.
    
    Args:
        query: The user's transliteration query
        strict: If True, be more aggressive about requesting validation
        
    Returns:
        ValidationResult with all analysis info
    """
    normalized = normalize_input(query)
    
    if not normalized:
        return ValidationResult(
            query=query,
            normalized="",
            best_match="",
            all_variants=[],
            confidence="low",
            confidence_score=0.0,
            needs_validation=True,
            validation_type=ValidationType.UNKNOWN,
            clarify_options=[],
            choose_options=[],
            word_validations=[],
            uncertain_word_indices=[],
        )
    
    # Check if entire query is an exception
    if normalized in MINIMAL_EXCEPTIONS:
        best = MINIMAL_EXCEPTIONS[normalized][0]
        return ValidationResult(
            query=query,
            normalized=normalized,
            best_match=best,
            all_variants=MINIMAL_EXCEPTIONS[normalized],
            confidence="high",
            confidence_score=1.0,
            needs_validation=False,
            validation_type=ValidationType.NONE,
            clarify_options=[],
            choose_options=[],
            word_validations=[],
            uncertain_word_indices=[],
            metadata={"source": "exception"}
        )
    
    # Split into words and analyze each
    words = normalized.split()
    word_validations: List[WordValidation] = []
    uncertain_indices: List[int] = []
    
    for i, word in enumerate(words):
        wv = analyze_word(word)
        word_validations.append(wv)
        if wv.needs_validation:
            uncertain_indices.append(i)
    
    # Get full phrase variants
    all_variants = generate_smart_variants(normalized)
    best_match = all_variants[0] if all_variants else ""
    
    # Calculate overall confidence
    if word_validations:
        avg_confidence = sum(wv.confidence for wv in word_validations) / len(word_validations)
        min_confidence = min(wv.confidence for wv in word_validations)
        # Use weighted average favoring the minimum
        overall_confidence = 0.6 * avg_confidence + 0.4 * min_confidence
    else:
        overall_confidence = 0.0
    
    # Determine overall confidence level
    if overall_confidence >= 0.85:
        confidence_level = "high"
    elif overall_confidence >= 0.6:
        confidence_level = "medium"
    else:
        confidence_level = "low"
    
    # Determine if validation is needed and what type
    needs_validation = len(uncertain_indices) > 0
    
    if strict:
        # In strict mode, also validate medium confidence
        needs_validation = overall_confidence < 0.85
    
    # Determine validation type
    if not needs_validation:
        validation_type = ValidationType.NONE
        clarify_options = []
        choose_options = []
    elif len(uncertain_indices) == 1:
        # Single uncertain word
        uncertain_wv = word_validations[uncertain_indices[0]]
        validation_type = uncertain_wv.validation_type
        
        if validation_type == ValidationType.CLARIFY:
            # Build clarify options for the uncertain word
            clarify_options = [(uncertain_wv.best_match, "")]
            for alt in uncertain_wv.alternatives[:2]:
                clarify_options.append((alt, ""))
            choose_options = []
        else:
            clarify_options = []
            choose_options = [uncertain_wv.best_match] + uncertain_wv.alternatives[:4]
    else:
        # Multiple uncertain words - use CHOOSE for whole phrase
        validation_type = ValidationType.CHOOSE
        clarify_options = []
        choose_options = all_variants[:5]
    
    return ValidationResult(
        query=query,
        normalized=normalized,
        best_match=best_match,
        all_variants=all_variants,
        confidence=confidence_level,
        confidence_score=overall_confidence,
        needs_validation=needs_validation,
        validation_type=validation_type,
        clarify_options=clarify_options,
        choose_options=choose_options,
        word_validations=word_validations,
        uncertain_word_indices=uncertain_indices,
        metadata={
            "word_count": len(words),
            "exception_words": sum(1 for wv in word_validations if wv.is_exception),
        }
    )


# ==========================================
#  PROMPT GENERATION (for UI)
# ==========================================

def get_validation_prompt(result: ValidationResult, format: str = "console") -> str:
    """
    Generate a user-facing prompt based on validation result.
    
    Args:
        result: The ValidationResult from analyze_query
        format: "console" or "html" or "json"
        
    Returns:
        A formatted string prompt for the user
    """
    if not result.needs_validation:
        return ""
    
    if result.validation_type == ValidationType.CLARIFY:
        if format == "console":
            options_str = " or ".join(f"'{opt[0]}'" for opt in result.clarify_options[:3])
            return f"Did you mean {options_str}?"
        elif format == "html":
            buttons = " ".join(
                f'<button class="clarify-option" data-value="{opt[0]}">{opt[0]}</button>'
                for opt in result.clarify_options[:3]
            )
            return f'<div class="clarify-prompt">Did you mean: {buttons}</div>'
    
    elif result.validation_type == ValidationType.CHOOSE:
        if format == "console":
            lines = ["Please select the correct option:"]
            for i, opt in enumerate(result.choose_options[:5], 1):
                lines.append(f"  {i}. {opt}")
            lines.append("  0. None of these")
            return "\n".join(lines)
        elif format == "html":
            options = "".join(
                f'<li><button class="choose-option" data-index="{i}" data-value="{opt}">{i}. {opt}</button></li>'
                for i, opt in enumerate(result.choose_options[:5], 1)
            )
            return f'<div class="choose-prompt"><p>Please select:</p><ol>{options}</ol></div>'
    
    elif result.validation_type == ValidationType.UNKNOWN:
        uncertain_word = ""
        if result.uncertain_word_indices:
            idx = result.uncertain_word_indices[0]
            if idx < len(result.word_validations):
                uncertain_word = result.word_validations[idx].original
        
        if format == "console":
            if result.choose_options:
                lines = [f"We couldn't confidently recognize '{uncertain_word or result.query}'."]
                lines.append("Did you mean one of these?")
                for i, opt in enumerate(result.choose_options[:5], 1):
                    lines.append(f"  {i}. {opt}")
                lines.append("  0. None of these / try different spelling")
                return "\n".join(lines)
            else:
                return f"We couldn't recognize '{uncertain_word or result.query}'. Please try a different spelling."
    
    return ""


def apply_user_selection(result: ValidationResult, selection: int) -> str:
    """
    Apply user's selection to get final Hebrew result.
    
    Args:
        result: The ValidationResult
        selection: User's choice (1-5 for options, 0 for "none")
        
    Returns:
        The selected Hebrew string, or empty if selection invalid
    """
    if result.validation_type == ValidationType.CLARIFY:
        if 1 <= selection <= len(result.clarify_options):
            return result.clarify_options[selection - 1][0]
    
    elif result.validation_type in (ValidationType.CHOOSE, ValidationType.UNKNOWN):
        if 1 <= selection <= len(result.choose_options):
            return result.choose_options[selection - 1]
    
    return ""


# ==========================================
#  WORD-BY-WORD VALIDATION (for complex queries)
# ==========================================

def validate_word_by_word(query: str) -> List[ValidationResult]:
    """
    For complex multi-word queries, validate each word separately.
    Returns a list of ValidationResults, one per word.
    
    This is useful when you want to let the user correct
    individual words rather than the whole phrase.
    """
    normalized = normalize_input(query)
    words = normalized.split()
    
    results = []
    for word in words:
        result = analyze_query(word)
        results.append(result)
    
    return results


def reconstruct_phrase(word_results: List[ValidationResult]) -> str:
    """
    Reconstruct a phrase from validated word results.
    """
    return " ".join(r.best_match for r in word_results if r.best_match)


# ==========================================
#  TESTING
# ==========================================

if __name__ == "__main__":
    print("=" * 60)
    print("USER VALIDATION MODULE TEST")
    print("=" * 60)
    
    test_queries = [
        # High confidence (exceptions)
        "es",
        "yaakov", 
        "bittul bealma sagi",
        
        # Medium confidence (rules apply)
        "chazakah",
        "tosefes kesubah",
        
        # Potentially ambiguous
        "kesuba",  # כתובה or כסובה?
        "tana",    # תנא or טנא?
        
        # Unknown/difficult
        "xyzabc",
    ]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: '{query}'")
        print("-" * 40)
        
        result = analyze_query(query)
        
        print(f"Best match: {result.best_match}")
        print(f"Confidence: {result.confidence} ({result.confidence_score:.2f})")
        print(f"Needs validation: {result.needs_validation}")
        print(f"Validation type: {result.validation_type.value}")
        
        if result.needs_validation:
            print(f"\n{get_validation_prompt(result, 'console')}")
        
        if result.word_validations:
            print(f"\nWord breakdown:")
            for i, wv in enumerate(result.word_validations):
                marker = "⚠️" if wv.needs_validation else "✓"
                print(f"  {marker} '{wv.original}' → {wv.best_match} (conf: {wv.confidence:.2f})")
                if wv.rules_applied:
                    print(f"      Rules: {', '.join(wv.rules_applied)}")