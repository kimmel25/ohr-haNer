"""
Transliteration Map - Hebrew/Aramaic Phonetic Rules
====================================================

Maps English letter combinations to possible Hebrew letters.
This is NOT a word dictionary - it's a phonetic rules engine.

Based on yeshivish transliteration patterns (sav not tav).
"""

from typing import List, Dict
import re


# ==========================================
#  CORE TRANSLITERATION MAP
# ==========================================

# ==========================================
#  SMART TRANSLITERATION WITH PRIORITIES
# ==========================================
#
# Each pattern now has options ordered by FREQUENCY (most common first).
# This allows us to generate smarter variants by preferring common mappings.

TRANSLIT_MAP = {
    # =======================
    # MULTI-CHAR PHONEMES (check these FIRST - longer patterns have priority)
    # =======================

    # Consonant clusters - ORDERED BY FREQUENCY
    "sch": ["ש"],         # yeshivish spelling (schule, meschorah)
    "sh": ["ש"],          # always shin
    "ch": ["ח", "כ"],     # 80% ח at word start, 50/50 in middle (chalitza vs mechila)
    "kh": ["כ", "ח"],     # prefer khaf (khakham)
    "th": ["ת"],          # ashkenazi (talmid → תלמיד)
    "ph": ["פ"],          # philosophy
    "gh": ["ע"],          # ayin in scholarly transliteration
    
    # Tzadi variants
    "tz": ["צ"],
    "ts": ["צ"],          # tosefta, tsimtsum
    "tzh": ["צ"],
    
    # Other
    "zh": ["ז"],          # rare but in Persian loanwords
    
    # Double consonants (often just emphasis)
    "bb": ["ב"],
    "dd": ["ד"],
    "gg": ["ג"],
    "kk": ["כ", "ק"],
    "ll": ["ל"],
    "mm": ["מ"],
    "nn": ["נ"],
    "pp": ["פ"],
    "rr": ["ר"],
    "ss": ["ס", "ש"],
    "tt": ["ת", "ט"],
    
    # =======================
    # VOWEL COMBINATIONS (high ambiguity)
    # =======================
    
    # Yeshivish diphthongs
    "ai": ["אי", "עי", "י"],
    "ei": ["אי", "עי", "י"],
    "oi": ["וי", "עי"],
    "ui": ["וי"],
    "oy": ["וי", "עי"],      # oy vey
    "ay": ["י", "אי"],
    "ey": ["י", "אי"],
    
    # Long vowels
    "aa": ["א", "ע", "ה"],
    "ee": ["י", "אי"],
    "ii": ["י"],
    "oo": ["ו"],
    "uu": ["ו"],
    
    # Shva-like endings
    "eh": ["ה", "ע"],
    "ah": ["ה", "א", "ע"],
    "oh": ["ו", "ה"],
    "ih": ["י", "ה"],
    "uh": ["ו", "ה"],
    
    # =======================
    # SINGLE CONSONANTS - ORDERED BY FREQUENCY
    # =======================

    "b": ["ב"],
    "v": ["ב", "ו"],      # Usually vet (90%), sometimes vav
    "w": ["ו"],

    "g": ["ג"],
    "d": ["ד"],
    "z": ["ז"],

    "h": ["ה", "ח"],      # At word end: 90% ה, in middle: 60% ח

    "t": ["ת", "ט"],      # Yeshivish: prefer ת (sav not tav), 80% ת
    "s": ["ס", "ש"],      # Prefer ס (60%), unless before h

    "k": ["כ", "ק"],      # Prefer כ (70%)
    "q": ["ק"],           # Always kuf in scholarly

    "l": ["ל"],
    "m": ["מ"],
    "n": ["נ"],
    "r": ["ר"],

    "p": ["פ"],
    "f": ["פ"],           # Always peh/feh

    "x": ["כס"],          # maseches → מסכת

    "j": ["י", "ג"],      # Prefer yud (70%)
    "c": ["כ", "ק"],      # Prefer כ
    "y": ["י"],
    
    # =======================
    # VOWELS (SINGLE) - DRASTICALLY REDUCED FOR SMART GENERATION
    # =======================
    #
    # KEY INSIGHT: Most vowels in transliteration are IMPLICIT in Hebrew.
    # We only need explicit vowel letters in specific positions.
    # This reduces combinatorial explosion from 50+ variants to 10-15.

    "a": [""],            # 90% implicit! Only use א/ע at word START
    "e": [""],            # 90% implicit
    "i": ["י", ""],       # 50/50: explicit י or implicit
    "o": ["ו", ""],       # 60% ו, 40% implicit
    "u": ["ו"],           # Usually explicit ו
    
    # =======================
    # WORD-FINAL FORMS (CRITICAL)
    # =======================
    
    # Use boundary marker: \0 means end of word
    "m\0": ["ם"],         # sofi mem
    "n\0": ["ן"],         # sofi nun
    "tz\0": ["ץ"],        # sofi tzadi
    "p\0": ["ף"],         # sofi peh
    "k\0": ["ך"],         # sofi khaf
    
    # Common Aramaic endings
    "in\0": ["ין"],
    "an\0": ["ן", "אן"],
    "un\0": ["ון"],
    "on\0": ["ון", "ן"],
    "os\0": ["ות", "וס"],
    "us\0": ["וס"],
    
    # =======================
    # ARAMAIC PARTICLES & PREFIXES
    # =======================
    
    # Relative pronoun
    "d'": ["ד", "דה"],     # d'oraisa
    "de": ["ד", "דה"],
    "da": ["ד", "דה"],
    "di": ["די"],
    "du": ["דו"],
    
    # Conjunctions
    "u": ["ו"],           # u'mishum
    # NOTE: "v" mapping removed - conflicts with "v" = vet in consonants
    # Use "ve" or "va" for vav hachibur
    "ve": ["ו"],
    "va": ["ו"],
    
    # Prepositions
    "min": ["מן", "מ"],
    "mi": ["מ", "מי"],
    "b": ["ב"],           # b'dieved
    "be": ["ב"],
    "l": ["ל"],           # l'chatchila
    "le": ["ל"],
    
    # Articles
    "ha": ["ה"],
    "he": ["ה"],
}


# ==========================================
#  YESHIVISH OVERRIDES - MOVED TO word_dictionary.json
# ==========================================
#
# All exact-match yeshivish terms (masechtos, common phrases) are now in
# word_dictionary.json for centralized management. This keeps Tool 2 as a
# pure phonetic algorithm without special cases.


# ==========================================
#  CONTEXT-AWARE RULES FOR SMART GENERATION
# ==========================================

# Special mappings for WORD-INITIAL positions (more vowel letters needed)
WORD_INITIAL_VOWELS = {
    "a": ["א", "ע"],      # At word start, usually explicit: אמת, עסק
    "e": ["א", ""],       # Often explicit: אמת
    "i": ["י", "א"],      # Usually explicit: ישראל
    "o": ["א", "ו"],      # Often explicit: אוכל
    "u": ["או", "ו"],     # Usually explicit: אומן
}

# Special mappings for WORD-FINAL positions
WORD_FINAL_PATTERNS = {
    "ah": ["ה"],          # 95% ends with ה: תורה, ברכה
    "eh": ["ה"],          # Usually ה
    "oh": ["ו", ""],      # Sometimes ו: שלו
    "a": ["א", "ה", ""], # Could be א (סבא) or ה (תורה) or implicit
    "e": [""],            # Usually implicit at end
}


# ==========================================
#  HELPER FUNCTIONS
# ==========================================

def normalize_query(query: str) -> str:
    """
    Normalize the input query:
    - lowercase
    - remove punctuation (except apostrophes for d', etc.)
    - standardize spaces
    """
    query = query.lower().strip()
    
    # Keep apostrophes but remove other punctuation
    query = re.sub(r"[^\w\s']", "", query)
    
    # Standardize multiple spaces
    query = re.sub(r"\s+", " ", query)
    
    return query


def tokenize_with_boundaries(query: str) -> List[str]:
    """
    Tokenize query and mark word boundaries.
    
    "chezkas haguf" → ["chezkas\0", " ", "haguf\0"]
    
    This allows the map to handle final forms correctly.
    """
    words = query.split()
    tokens = []
    
    for i, word in enumerate(words):
        # Add boundary marker to end of word
        tokens.append(word + "\0")
        
        # Add space between words (except after last word)
        if i < len(words) - 1:
            tokens.append(" ")
    
    return tokens


def get_matching_pattern(text: str, pos: int) -> tuple:
    """
    Find the longest matching pattern in TRANSLIT_MAP starting at pos.
    
    Returns: (matched_pattern, hebrew_options, length)
    """
    # Try patterns from longest to shortest
    # This ensures "sh" matches before "s" and "h" separately
    
    max_len = 10  # Longest pattern in map
    
    for length in range(max_len, 0, -1):
        pattern = text[pos:pos+length]
        
        if pattern in TRANSLIT_MAP:
            return (pattern, TRANSLIT_MAP[pattern], length)
    
    # No match found
    return (None, [], 0)


# check_yeshivish_override() removed - now handled by word_dictionary.json


# ==========================================
#  MAIN FUNCTIONS
# ==========================================

def generate_smart_variants(query: str, max_variants: int = 15) -> List[str]:
    """
    SMART variant generation using frequency-based priorities.

    Instead of trying ALL possible combinations (50+ variants),
    this generates 10-15 HIGH-QUALITY variants by:
    1. Using most common mappings first (consonants)
    2. Context-aware vowel handling (word-initial, word-final)
    3. Only trying alternatives for highly ambiguous letters

    Args:
        query: English transliteration (e.g., "bereirah")
        max_variants: Limit (default 15 for smart generation)

    Returns:
        List of 10-15 high-quality Hebrew spellings

    Example:
        generate_smart_variants("bereirah")
        → ["ברירה", "בריראה", "ברירא", ...] (10-15 variants, not 50)
    """
    query = normalize_query(query)
    words = query.split()

    all_variants = []

    # Process each word separately
    for word in words:
        # Generate more variants per word for better matching
        word_variants = _generate_smart_word_variants(word, max_variants=15)
        all_variants.append(word_variants)

    # Combine word variants
    if len(all_variants) == 0:
        return []
    elif len(all_variants) == 1:
        return all_variants[0][:max_variants]
    else:
        # Combine multi-word variants
        # For multi-word phrases, we need to be smart about combinations
        # to avoid exponential explosion while still covering all words

        num_words = len(all_variants)
        combined = []

        if num_words == 2:
            # 2 words: try all combinations of top 3 variants from each
            for v1 in all_variants[0][:3]:
                for v2 in all_variants[1][:3]:
                    combined.append(v1 + " " + v2)
                    if len(combined) >= max_variants:
                        return combined

        elif num_words <= 4:
            # 3-4 words: use top 2 from each word
            # Generate combinations recursively
            def combine_words(word_idx, current_phrase):
                if word_idx >= num_words:
                    combined.append(current_phrase.strip())
                    return len(combined) >= max_variants

                for variant in all_variants[word_idx][:2]:
                    new_phrase = current_phrase + " " + variant if current_phrase else variant
                    if combine_words(word_idx + 1, new_phrase):
                        return True
                return False

            combine_words(0, "")

        else:
            # 5+ words: use best variant for each word (too many combinations)
            # Generate a few variations by trying alternatives for key words
            # 1. Best variant for all words
            combined.append(" ".join(w[0] for w in all_variants))

            # 2-4. Try alternative for first, second, and third word
            for word_idx in [0, 1, 2]:
                if word_idx < num_words and len(all_variants[word_idx]) > 1:
                    phrase_parts = [w[0] for w in all_variants]
                    phrase_parts[word_idx] = all_variants[word_idx][1]  # Use alternative
                    combined.append(" ".join(phrase_parts))
                    if len(combined) >= max_variants:
                        break

        return combined[:max_variants]


def _generate_smart_word_variants(word: str, max_variants: int = 15) -> List[str]:
    """
    Generate smart variants for a SINGLE WORD using context-aware rules.

    Returns up to 15 high-quality variants per word.
    """
    variants = []
    word_len = len(word)

    # Strategy: Generate 1 "best guess" + multiple alternatives for ambiguous letters
    def generate_variant(use_alternatives: Dict[str, bool]) -> str:
        """Generate one variant based on whether to use alternative mappings"""
        result = ""
        i = 0

        while i < word_len:
            # Check for multi-char patterns first (longest match)
            matched = False

            for length in range(min(4, word_len - i), 0, -1):
                pattern = word[i:i+length]

                # Check if this is word-initial position
                is_initial = (i == 0)
                # Check if this is word-final position
                is_final = (i + length >= word_len)

                # Special handling for word-initial vowels (try alternatives too!)
                if is_initial and pattern in WORD_INITIAL_VOWELS:
                    options = WORD_INITIAL_VOWELS[pattern]
                    use_alt = use_alternatives.get(pattern, False)
                    # Try second option if requested
                    if use_alt and len(options) > 1:
                        result += options[1]
                    else:
                        result += options[0]  # Use first (most common)
                    matched = True
                    i += length
                    break

                # Special handling for word-final patterns
                if is_final and pattern in WORD_FINAL_PATTERNS:
                    options = WORD_FINAL_PATTERNS[pattern]
                    use_alt = use_alternatives.get(pattern, False)
                    if use_alt and len(options) > 1:
                        result += options[1]
                    else:
                        result += options[0]  # Use first (most common)
                    matched = True
                    i += length
                    break

                # Check regular TRANSLIT_MAP
                if pattern in TRANSLIT_MAP:
                    options = TRANSLIT_MAP[pattern]

                    # Decide whether to use alternative
                    use_alt = use_alternatives.get(pattern, False)

                    # For highly ambiguous patterns, try second option
                    # EXPANDED: Now includes vowels and more consonants
                    if use_alt and len(options) > 1:
                        result += options[1]
                    else:
                        result += options[0]  # Use most common

                    matched = True
                    i += length
                    break

            if not matched:
                # Skip unknown character
                i += 1

        return result

    # Generate variants:
    # 1. Best guess (all most-common mappings)
    variants.append(generate_variant({}))

    # 2-15. Try alternatives for ambiguous patterns
    # EXPANDED: Now includes vowels and more consonants
    ambiguous_patterns = [
        "ch", "k", "s", "t", "h",  # Original consonants
        "a", "e", "i", "o", "u",    # Vowels (important for short words!)
        "ai", "ei", "oi",           # Diphthongs
        "sh", "tz", "kh",           # Multi-char consonants
    ]

    for pattern in ambiguous_patterns:
        if pattern in word and len(variants) < max_variants:
            variant = generate_variant({pattern: True})
            if variant and variant not in variants:
                variants.append(variant)

    # 3. For short words (≤5 chars), try combinations of two alternatives
    if word_len <= 5 and len(variants) < max_variants:
        # Try pairs of ambiguous letters
        found_patterns = [p for p in ambiguous_patterns if p in word]
        for i, p1 in enumerate(found_patterns[:3]):  # Limit to avoid explosion
            for p2 in found_patterns[i+1:4]:
                if len(variants) >= max_variants:
                    break
                variant = generate_variant({p1: True, p2: True})
                if variant and variant not in variants:
                    variants.append(variant)

    return variants[:max_variants]


def generate_hebrew_variants(query: str, max_variants: int = 100) -> List[str]:
    """
    Generate all possible Hebrew spellings from transliteration.

    Args:
        query: English transliteration (e.g., "chezkas haguf")
        max_variants: Limit to prevent combinatorial explosion

    Returns:
        List of possible Hebrew strings

    Example:
        generate_hebrew_variants("bari vishma")
        → ["ברי ושמא", "ברי וסמא", "בארי ושמא", ...]

    Note: Exact-match terms (masechtos, common phrases) are now handled by
    word_dictionary.json BEFORE this function is called, so this is now a
    pure phonetic transliteration algorithm.
    """
    # Normalize and tokenize
    query = normalize_query(query)
    tokens = tokenize_with_boundaries(query)

    # Generate variants recursively
    variants = _generate_variants_recursive(tokens, 0, "", max_variants)

    # Remove duplicates and empty strings
    variants = list(set(v for v in variants if v))

    return variants[:max_variants]


def _generate_variants_recursive(
    tokens: List[str], 
    token_idx: int,
    current_variant: str,
    max_variants: int,
    variants_collected: List[str] = None
) -> List[str]:
    """
    Recursive helper to generate all Hebrew variants.
    """
    if variants_collected is None:
        variants_collected = []
    
    # Stop if we've collected enough variants
    if len(variants_collected) >= max_variants:
        return variants_collected
    
    # Base case: processed all tokens
    if token_idx >= len(tokens):
        variants_collected.append(current_variant)
        return variants_collected
    
    token = tokens[token_idx]
    
    # Handle spaces (keep them)
    if token == " ":
        return _generate_variants_recursive(
            tokens, token_idx + 1, current_variant + " ", 
            max_variants, variants_collected
        )
    
    # Process the token character by character
    pos = 0
    
    def process_from_pos(pos: int, variant_so_far: str):
        """Inner function to handle character processing"""
        if len(variants_collected) >= max_variants:
            return
        
        # Reached end of token
        if pos >= len(token):
            # Move to next token
            _generate_variants_recursive(
                tokens, token_idx + 1, variant_so_far,
                max_variants, variants_collected
            )
            return
        
        # Try to match a pattern
        pattern, hebrew_options, length = get_matching_pattern(token, pos)
        
        if not hebrew_options:
            # No match - skip this character or fail
            # For now, let's just skip unknown characters
            process_from_pos(pos + 1, variant_so_far)
            return
        
        # Try each Hebrew option
        for hebrew in hebrew_options:
            new_variant = variant_so_far + hebrew
            process_from_pos(pos + length, new_variant)
    
    process_from_pos(0, current_variant)
    return variants_collected


def transliteration_confidence(query: str) -> str:
    """
    Estimate confidence in transliteration mapping.

    Returns: "high", "medium", or "low"

    High confidence:
    - Simple, unambiguous letters (mostly consonants)

    Low confidence:
    - Many ambiguous vowels (a, e, h)
    - Unusual letter combinations

    Note: Known yeshivish phrases are now handled by word_dictionary.json
    BEFORE transliteration, so this function now only evaluates phonetic
    complexity.
    """
    query = normalize_query(query)

    # Count ambiguous characters
    ambiguous_chars = "aeiouh"
    ambiguous_count = sum(1 for c in query if c in ambiguous_chars)

    total_chars = len(query.replace(" ", ""))

    if total_chars == 0:
        return "low"

    ambiguity_ratio = ambiguous_count / total_chars

    # More than 60% ambiguous → low confidence
    if ambiguity_ratio > 0.6:
        return "low"
    # 40-60% → medium
    elif ambiguity_ratio > 0.4:
        return "medium"
    else:
        return "high"


# ==========================================
#  TESTING
# ==========================================

if __name__ == "__main__":
    # Quick test
    test_queries = [
        "chezkas haguf",
        "bari vishma",
        "sfek sfeika",
        "kesubos",
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        variants = generate_hebrew_variants(query, max_variants=5)
        print(f"Variants: {variants}")
        print(f"Confidence: {transliteration_confidence(query)}")