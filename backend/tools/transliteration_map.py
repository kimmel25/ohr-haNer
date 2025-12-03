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

TRANSLIT_MAP = {
    # =======================
    # MULTI-CHAR PHONEMES (check these FIRST - longer patterns have priority)
    # =======================
    
    # Consonant clusters
    "sch": ["ש"],         # yeshivish spelling (schule, meschorah)
    "sh": ["ש"],
    "ch": ["ח", "כ"],     # chalitza, mechila (ambiguous!)
    "kh": ["כ", "ח"],     # khakham, khazan
    "th": ["ת"],          # ashkenazi (talmid → תלמיד in some communities)
    "ph": ["פ"],          # philosophy
    "gh": ["ע", "ג"],     # ayin in scholarly transliteration
    
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
    # SINGLE CONSONANTS
    # =======================
    
    "b": ["ב"],
    "v": ["ו", "ב"],      # vet ambiguity (vav vs vet)
    "w": ["ו"],
    
    "g": ["ג"],
    "d": ["ד"],
    "z": ["ז"],
    
    "h": ["ה", "ח"],      # huge ambiguity in Aramaic
    
    "t": ["ת", "ט"],      # talmudic often confuses these
    "s": ["ס", "ש"],      # samekh vs sin
    
    "k": ["כ", "ק"],
    "q": ["ק"],           # scholarly (qahal)
    
    "l": ["ל"],
    "m": ["מ"],
    "n": ["נ"],
    "r": ["ר"],
    
    "p": ["פ"],
    "f": ["פ", "ף"],      # final peh
    
    "x": ["כס", "קס"],    # maseches → מסכת
    
    "j": ["ג", "י", "ז"],  # varies by community
    "c": ["כ", "ק", "צ", "ס"], # European influence
    "y": ["י"],
    
    # =======================
    # VOWELS (SINGLE)
    # =======================
    
    "a": ["א", "ע", "ה", ""],    # often silent or implicit
    "e": ["א", "ה", "ע", ""],
    "i": ["י", "א", ""],
    "o": ["ו", "א", "ע", ""],
    "u": ["ו", ""],
    
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
    "v": ["ו"],           # sometimes vav
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
#  SPECIAL YESHIVISH PATTERNS
# ==========================================

YESHIVISH_OVERRIDES = {
    # Common yeshivish spellings that override general rules
    "kesubos": "כתובות",
    "ketubot": "כתובות",
    "ketubos": "כתובות",
    
    "shabbos": "שבת",
    "shabbat": "שבת",
    
    "pesachim": "פסחים",
    
    "bava kama": "בבא קמא",
    "bava metzia": "בבא מציעא", 
    "bava basra": "בבא בתרא",
    
    # Common phrases
    "bitul chametz": "ביטול חמץ",
    "bitul chometz": "ביטול חמץ",
    
    "sfek sfeika": "ספק ספיקא",
    "safek safeika": "ספק ספיקא",
    
    "eid echad": "עד אחד",
    "ed echad": "עד אחד",
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


def check_yeshivish_override(query: str) -> str:
    """
    Check if query matches a known yeshivish phrase.
    Returns Hebrew string or empty string if no match.
    """
    normalized = normalize_query(query)
    return YESHIVISH_OVERRIDES.get(normalized, "")


# ==========================================
#  MAIN FUNCTIONS
# ==========================================

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
    """
    # First check for yeshivish override
    override = check_yeshivish_override(query)
    if override:
        return [override]
    
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
    - Known yeshivish phrase
    - Simple, unambiguous letters
    
    Low confidence:
    - Many ambiguous vowels (a, e, h)
    - Unusual letter combinations
    """
    # Check for yeshivish override
    if check_yeshivish_override(query):
        return "high"
    
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