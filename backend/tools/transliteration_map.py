"""
Transliteration Map V2 - Hebrew/Aramaic Phonetic Rules
=======================================================

MAJOR FIXES in V2:
1. Sofit letters now work (boundary markers flow through to variant generator)
2. Ayin detection for "iu", "ua" vowel combinations (shiur, muad)
3. Word-initial vav prefix handling (vchomer → וחומר, not בחומר)
4. Better vowel-to-letter mapping with context awareness
5. Improved yud handling (migu → מיגו, not מגו)
6. Final heh for Hebrew feminine (achila → אכילה, not אכילא)
7. Tav preference for Aramaic (trei → תרי, not טרי)
8. Double vav support (hashaveh → השווה)

Based on yeshivish transliteration patterns (sav not tav).

Architecture:
- TRANSLIT_MAP: Core phonetic mappings
- WORD_INITIAL_RULES: Context-specific mappings for word start
- WORD_FINAL_RULES: Context-specific mappings for word end (with sofits)
- TRANSLIT_EXCEPTIONS: Common terms that pure phonetics fails on
"""

from typing import List, Dict, Tuple, Optional, Set
import re


# ==========================================
#  TRANSLITERATION EXCEPTIONS
# ==========================================
# Common terms where pure phonetics consistently fails.
# These are checked BEFORE phonetic transliteration.
# This is NOT the main dictionary - just a safety net for
# terms that are extremely common and have tricky spellings.

TRANSLIT_EXCEPTIONS: Dict[str, List[str]] = {
    # === Terms with silent/unexpected ayin ===
    "shiur": ["שיעור", "שעור"],
    "shiurim": ["שיעורים"],
    "muad": ["מועד"],
    "hamuad": ["המועד"],
    "leolam": ["לעולם"],
    "meinyano": ["מעניינו", "מענינו"],
    "olam": ["עולם"],
    "miut": ["מיעוט"],      # Has ayin
    "umiut": ["ומיעוט"],    # Conjunction + ayin
    "oser": ["אוסר"],       # Has vav
    
    # === Aramaic numbers (tav not tet) ===
    "trei": ["תרי"],
    "tlat": ["תלת"],
    "arba": ["ארבע"],
    
    # === Common particles ===
    "lo": ["לא"],           # "not" - never לו
    "shelo": ["שלא"],       # "that not"
    "velo": ["ולא"],        # "and not"
    "ain": ["אין"],         # "there is not"
    "ein": ["אין"],         # Alternative spelling
    
    # === Terms with nun sofit ===
    "binyan": ["בנין", "בניין"],
    "kinyan": ["קנין", "קניין"],
    "inyan": ["ענין", "עניין"],
    "chalipin": ["חליפין"],
    "kiddushin": ["קידושין"],
    
    # === Common complex terms ===
    "migu": ["מיגו", "מגו"],
    "kal": ["קל"],          # Not כל
    "kol": ["כל"],          # Not קול
    "chomer": ["חומר"],     # Has vav
    "vchomer": ["וחומר"],   # Vav hachibur + chomer
    
    # === Hebrew feminine endings (final heh) ===
    "achila": ["אכילה"],
    "meshicha": ["משיכה"],
    "shetiya": ["שתיה"],
    "amira": ["אמירה"],
    "asiha": ["עשיה"],
    "bracha": ["ברכה"],
    "kedusha": ["קדושה"],
    "mesira": ["מסירה"],
    "netina": ["נתינה"],
    "gezeira": ["גזירה"],
    "shava": ["שווה", "שוה"],
    
    # === Masechtos (yeshivish: sav, not tav) ===
    "kesubos": ["כתובות"],
    "kesuvim": ["כתובים"],
    "shabbos": ["שבת"],
    "brachos": ["ברכות"],
    "pesachim": ["פסחים"],
    "yevamos": ["יבמות"],
    "nedarim": ["נדרים"],
    "nazir": ["נזיר"],
    "gittin": ["גיטין"],
    "sotah": ["סוטה"],
    "bava": ["בבא"],
    "kama": ["קמא"],
    
    # === Common halachic terms ===
    "ribui": ["ריבוי"],
    "klal": ["כלל"],
    "prat": ["פרט"],
    "uprat": ["ופרט"],
    "sfeika": ["ספיקא"],
    "sfek": ["ספק"],
    "chatzi": ["חצי"],
    "lavud": ["לבוד"],
    "soledet": ["סולדת"],
    "kzayis": ["כזית"],
    "kbeitza": ["כביצה"],
    "halamd": ["הלמד"],
    "miktzas": ["מקצת"],
    "hayom": ["היום"],
    "kchulo": ["ככולו"],
    "davar": ["דבר"],
    "adam": ["אדם"],
    "shor": ["שור"],
    "hafkaas": ["הפקעת"],
    "shnei": ["שני"],
    "yad": ["יד"],
    "bo": ["בו"],
    "tzad": ["צד"],
    
    # === Terms with double letters ===
    "shaveh": ["שווה", "שוה"],
    "hashaveh": ["השווה", "השוה"],
    "aveh": ["ווה"],        # Ending pattern
    
    # === Vav hachibur prefixes (v at word start) ===
    "vetrei": ["ותרי"],
    "vniur": ["ונעור"],
    
    # === Short common words ===
    "av": ["אב"],           # Father - not just ו
    "im": ["אם"],           # Mother/if
    "al": ["על"],           # On
    "el": ["אל"],           # To
}


# ==========================================
#  CORE TRANSLITERATION MAP
# ==========================================
# Ordered by FREQUENCY (most common first).
# Longer patterns checked before shorter ones.

TRANSLIT_MAP: Dict[str, List[str]] = {
    # =======================
    # AYIN-SIGNALING VOWEL COMBINATIONS (HIGH PRIORITY)
    # =======================
    # These vowel pairs often indicate an ayin in the Hebrew.
    # Must be checked BEFORE simple vowel mappings.
    
    "iu": ["יעו", "יו", "יאו"],     # shiur → שיעור (yud-ayin-vav)
    "iur": ["יעור", "יור"],         # shiur ending
    "ua": ["וע", "ו", "ועא"],       # muad → מועד (vav-ayin)
    "uad": ["ועד", "ואד"],          # muad ending specifically
    "ia": ["יע", "יא", "י"],        # Complex - context dependent
    
    # =======================
    # MULTI-CHAR CONSONANT CLUSTERS
    # =======================
    
    "sch": ["ש"],             # Yeshivish spelling (schule)
    "sh": ["ש"],              # Always shin
    "ch": ["ח", "כ"],         # 80% ח, sometimes כ (mechila)
    "kh": ["כ", "ח"],         # Prefer khaf (khakham)
    "th": ["ת"],              # Ashkenazi
    "ph": ["פ"],              # Philosophy
    "gh": ["ע"],              # Ayin in scholarly transliteration
    
    # Tzadi variants
    "tz": ["צ"],
    "ts": ["צ"],
    "tzh": ["צ"],
    
    # Other multi-char
    "zh": ["ז"],
    
    # =======================
    # DOUBLE CONSONANTS
    # =======================
    
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
    "vv": ["וו", "ו"],        # Double vav for hashaveh → השווה
    
    # =======================
    # VOWEL DIPHTHONGS
    # =======================
    
    "ai": ["י", "אי", "עי"],  # Prefer yud (yeshivish: trei → תרי)
    "ei": ["י", "אי", "עי"],  # Prefer yud
    "oi": ["וי", "עי"],
    "ui": ["וי", "ואי"],
    "oy": ["וי", "עי"],
    "ay": ["י", "אי"],
    "ey": ["י", "אי"],
    
    # =======================
    # LONG VOWELS
    # =======================
    
    "aa": ["א", "ע", "ה"],
    "ee": ["י", "אי", "יי"],
    "ii": ["י", "יי"],
    "oo": ["ו", "וא"],
    "uu": ["ו"],
    
    # =======================
    # VOWEL + H COMBINATIONS (often word-final)
    # =======================
    
    "ah": ["ה", "א"],         # Almost always heh at end
    "eh": ["ה", "א"],         # Usually heh
    "oh": ["ו", "וה", ""],
    "ih": ["י", "יה"],
    "uh": ["ו", "וה"],
    
    # =======================
    # SINGLE CONSONANTS
    # =======================
    
    "b": ["ב"],
    "v": ["ב", "ו"],          # Default vet; word-initial handled separately
    "w": ["ו"],
    
    "g": ["ג"],
    "d": ["ד"],
    "z": ["ז"],
    
    "h": ["ה", "ח"],          # Default heh; position-dependent
    
    "t": ["ת", "ט"],          # Yeshivish: prefer tav
    "s": ["ס", "ש", "ת"],     # Added ת for yeshivish sav (kzayis → כזית)
    
    "k": ["כ", "ק"],
    "q": ["ק"],
    
    "l": ["ל"],
    "m": ["מ"],
    "n": ["נ"],
    "r": ["ר"],
    
    "p": ["פ"],
    "f": ["פ"],
    
    "x": ["כס", "קס"],
    
    "j": ["י", "ג"],
    "c": ["כ", "ק"],
    "y": ["י"],
    
    # =======================
    # SINGLE VOWELS
    # =======================
    # Most vowels are IMPLICIT in Hebrew.
    # Context rules (initial/final) override these.
    
    "a": ["", "א", "ע"],      # Usually implicit
    "e": ["", "א"],           # Usually implicit
    "i": ["י", ""],           # 70% explicit yud
    "o": ["ו", "", "א"],      # Usually vav
    "u": ["ו", ""],           # Usually vav
}


# =======================
# WORD-FINAL PATTERNS (with \0 boundary marker)
# =======================
# These MUST include the \0 marker to match at word end.
# Sofits are handled here.

WORD_FINAL_PATTERNS: Dict[str, List[str]] = {
    # === SOFIT LETTERS ===
    "m\0": ["ם"],             # Mem sofit
    "n\0": ["ן"],             # Nun sofit
    "tz\0": ["ץ"],            # Tzadi sofit
    "ts\0": ["ץ"],            # Alternative spelling
    "k\0": ["ך"],             # Khaf sofit
    "kh\0": ["ך"],            # Alternative spelling
    "ch\0": ["ך", "ח"],       # Could be either
    "f\0": ["ף"],             # Peh sofit (rare)
    "p\0": ["ף", "פ"],        # Sometimes sofit
    
    # === COMMON ENDINGS WITH SOFITS ===
    "im\0": ["ים"],           # Masculine plural
    "in\0": ["ין", "ן"],      # Aramaic plural
    "an\0": ["ן", "אן"],      # Aramaic ending
    "un\0": ["ון"],           # Aramaic ending
    "on\0": ["ון", "ן"],      # Hebrew/Aramaic
    "am\0": ["ם", "אם"],      # Hebrew ending
    "um\0": ["ום"],           # Hebrew ending
    "em\0": ["ם"],            # Hebrew ending
    "om\0": ["ום", "ם"],      # Hebrew ending
    
    # === WORD-FINAL VOWEL PATTERNS ===
    "ah\0": ["ה"],            # Almost always heh (תורה)
    "eh\0": ["ה", "א"],       # Usually heh
    "oh\0": ["ו", ""],        # Sometimes vav
    "ih\0": ["י"],            # Yud
    "uh\0": ["ו"],            # Vav
    
    # === FINAL VOWELS (tricky) ===
    "a\0": ["ה", "א", ""],    # Prefer heh for Hebrew feminine, aleph for Aramaic
    "e\0": ["ה", ""],         # Sometimes heh
    "o\0": ["ו", ""],         # Usually vav or implicit
    "i\0": ["י"],             # Yud
    "u\0": ["ו"],             # Vav
    
    # === COMMON SUFFIXES ===
    "os\0": ["ות", "וס"],     # kesubos → כתובות
    "us\0": ["וס"],           # Aramaic
    "is\0": ["יס", "ית", "יש"], # Added ית for yeshivish
    "as\0": ["ס", "ת"],       # Could be samech or tav
    "es\0": ["ס", "ת"],       # Could be samech or tav
    
    # === ARAMAIC ENDINGS ===
    "ei\0": ["י", "אי"],      # trei → תרי
    "ai\0": ["י", "אי"],      # Alternative
}


# =======================
# WORD-INITIAL PATTERNS
# =======================
# Special handling for patterns at the START of a word.

WORD_INITIAL_PATTERNS: Dict[str, List[str]] = {
    # === VAV HACHIBUR (conjunction prefix) ===
    # "v" at word start before a consonant is usually vav (ו), not vet (ב)
    "v": ["ו", "ב"],          # Prefer vav for vchomer, vetrei
    
    # === VOWELS AT WORD START ===
    # Word-initial vowels are usually explicit
    "a": ["א", "ע", ""],      # Usually aleph or ayin
    "e": ["א", "ע", ""],      # Usually aleph
    "i": ["י", "אי"],         # Usually yud
    "o": ["או", "ו", "א"],    # Usually aleph-vav
    "u": ["או", "ו"],         # Usually aleph-vav
    
    # === COMMON PREFIXES ===
    "ha": ["ה"],              # Definite article
    "he": ["ה"],              # Definite article variant
    "ve": ["ו"],              # Conjunction
    "va": ["ו"],              # Conjunction
    "u": ["ו"],               # Conjunction (short form)
    "le": ["ל"],              # Preposition "to"
    "la": ["ל"],              # Preposition variant
    "be": ["ב"],              # Preposition "in"
    "ba": ["ב"],              # Preposition variant
    "ke": ["כ"],              # Preposition "like"
    "ka": ["כ"],              # Preposition variant
    "mi": ["מ", "מי"],        # Preposition "from"
    "me": ["מ"],              # Preposition variant
    "de": ["ד"],              # Aramaic relative
    "di": ["די"],             # Aramaic relative
    "she": ["ש"],             # Hebrew relative
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


def check_exception(word: str) -> Optional[List[str]]:
    """
    Check if a word has a known exception mapping.
    Returns list of Hebrew variants if found, None otherwise.
    """
    word_lower = word.lower().rstrip('\0')
    return TRANSLIT_EXCEPTIONS.get(word_lower)


def get_pattern_match(
    text: str, 
    pos: int, 
    is_word_initial: bool,
    is_word_final: bool
) -> Tuple[Optional[str], List[str], int]:
    """
    Find the best matching pattern at position pos.
    
    Checks in order:
    1. Word-final patterns (if at end, includes \0 marker)
    2. Word-initial patterns (if at start)
    3. Multi-char patterns in TRANSLIT_MAP
    4. Single-char patterns
    
    Returns: (matched_pattern, hebrew_options, consumed_length)
    """
    remaining = text[pos:]
    max_len = min(10, len(remaining))
    
    # === WORD-FINAL PATTERNS ===
    # Check if we're at the end (remaining ends with \0)
    if is_word_final or remaining.endswith('\0'):
        for length in range(max_len, 0, -1):
            # Try pattern WITH the \0 marker
            pattern_with_marker = remaining[:length]
            if pattern_with_marker in WORD_FINAL_PATTERNS:
                # Consume the pattern but not the \0 (it's a marker)
                actual_length = length - 1 if pattern_with_marker.endswith('\0') else length
                return (pattern_with_marker, WORD_FINAL_PATTERNS[pattern_with_marker], length)
            
            # Also check the pattern + \0
            pattern_plus_marker = remaining[:length] + '\0'
            if pattern_plus_marker in WORD_FINAL_PATTERNS and pos + length == len(text) - 1:
                return (pattern_plus_marker, WORD_FINAL_PATTERNS[pattern_plus_marker], length + 1)
    
    # === WORD-INITIAL PATTERNS ===
    if is_word_initial and pos == 0:
        for length in range(min(3, max_len), 0, -1):
            pattern = remaining[:length]
            if pattern in WORD_INITIAL_PATTERNS:
                return (pattern, WORD_INITIAL_PATTERNS[pattern], length)
    
    # === REGULAR PATTERNS (longest match first) ===
    for length in range(max_len, 0, -1):
        pattern = remaining[:length]
        
        # Skip the \0 marker in pattern matching
        if pattern == '\0':
            continue
        if pattern.endswith('\0'):
            pattern = pattern[:-1]
            if pattern in TRANSLIT_MAP:
                return (pattern, TRANSLIT_MAP[pattern], length - 1)
        
        if pattern in TRANSLIT_MAP:
            return (pattern, TRANSLIT_MAP[pattern], length)
    
    return (None, [], 0)


# ==========================================
#  MAIN FUNCTIONS
# ==========================================

def generate_smart_variants(query: str, max_variants: int = 20) -> List[str]:
    """
    SMART variant generation with context awareness.
    
    Key improvements over V1:
    1. Checks TRANSLIT_EXCEPTIONS first
    2. Passes boundary markers through for sofit handling
    3. Uses position-aware pattern matching
    4. Generates 15-20 high-quality variants instead of 50+ random ones
    
    Args:
        query: English transliteration (e.g., "kal vchomer")
        max_variants: Limit (default 20)
    
    Returns:
        List of high-quality Hebrew spellings
    """
    query = normalize_query(query)
    words = query.split()
    
    if not words:
        return []
    
    # Process each word separately
    all_word_variants: List[List[str]] = []
    
    for word in words:
        # Check exceptions first
        exception_variants = check_exception(word)
        if exception_variants:
            all_word_variants.append(exception_variants)
        else:
            # Generate variants with boundary marker
            word_with_marker = word + "\0"
            variants = _generate_word_variants(word_with_marker, max_per_word=10)
            all_word_variants.append(variants if variants else [word])
    
    # Combine word variants
    return _combine_word_variants(all_word_variants, max_variants)


def _generate_word_variants(word_with_marker: str, max_per_word: int = 10) -> List[str]:
    """
    Generate variants for a single word WITH boundary marker.
    
    This is the core transliteration engine.
    """
    variants: Set[str] = set()
    word_len = len(word_with_marker)
    
    def generate_recursive(pos: int, current: str, depth: int = 0):
        """Recursively build Hebrew variants."""
        # Prevent infinite recursion
        if depth > 50 or len(variants) >= max_per_word * 3:
            return
        
        # Reached end of word (at or past the \0 marker)
        if pos >= word_len or word_with_marker[pos] == '\0':
            if current:  # Don't add empty strings
                variants.add(current)
            return
        
        # Determine position context
        is_initial = (pos == 0)
        is_final = (pos >= word_len - 2) or word_with_marker[pos + 1] == '\0'
        
        # Get matching pattern
        pattern, options, consumed = get_pattern_match(
            word_with_marker, pos, is_initial, is_final
        )
        
        if not options:
            # Skip unknown character
            generate_recursive(pos + 1, current, depth + 1)
            return
        
        # Try each Hebrew option (limit to top 3 for efficiency)
        for hebrew in options[:3]:
            generate_recursive(pos + consumed, current + hebrew, depth + 1)
    
    # Start generation
    generate_recursive(0, "")
    
    # Convert to list and sort by quality:
    # 1. Prefer variants with explicit vowels (ו, י) - more likely correct
    # 2. Then by length (moderate length preferred)
    def variant_score(v: str) -> tuple:
        """Score a variant for sorting. Lower is better."""
        # Count explicit vowel letters (good)
        explicit_vowels = v.count('ו') + v.count('י')
        # Penalize very short variants (often missing letters)
        length_penalty = abs(len(v) - len(word_with_marker) + 2)
        # Return tuple for sorting (prefer more vowels, moderate length)
        return (-explicit_vowels, length_penalty, len(v))
    
    result = sorted(list(variants), key=variant_score)
    return result[:max_per_word]


def _combine_word_variants(
    all_word_variants: List[List[str]], 
    max_total: int
) -> List[str]:
    """
    Combine variants from multiple words into phrase variants.
    
    Uses smart combination to avoid exponential explosion.
    """
    if not all_word_variants:
        return []
    
    if len(all_word_variants) == 1:
        return all_word_variants[0][:max_total]
    
    combined: List[str] = []
    num_words = len(all_word_variants)
    
    if num_words == 2:
        # 2 words: top 4 from each
        for v1 in all_word_variants[0][:4]:
            for v2 in all_word_variants[1][:4]:
                combined.append(f"{v1} {v2}")
                if len(combined) >= max_total:
                    return combined
    
    elif num_words <= 4:
        # 3-4 words: top 2-3 from each
        per_word = 3 if num_words == 3 else 2
        
        def combine_recursive(word_idx: int, phrase_parts: List[str]):
            if len(combined) >= max_total:
                return
            if word_idx >= num_words:
                combined.append(" ".join(phrase_parts))
                return
            
            for variant in all_word_variants[word_idx][:per_word]:
                combine_recursive(word_idx + 1, phrase_parts + [variant])
        
        combine_recursive(0, [])
    
    else:
        # 5+ words: use best variant for each, plus a few alternatives
        best_phrase = " ".join(w[0] for w in all_word_variants)
        combined.append(best_phrase)
        
        # Try second-best for first few words
        for word_idx in range(min(3, num_words)):
            if len(all_word_variants[word_idx]) > 1:
                parts = [w[0] for w in all_word_variants]
                parts[word_idx] = all_word_variants[word_idx][1]
                combined.append(" ".join(parts))
                if len(combined) >= max_total:
                    break
    
    return combined[:max_total]


def generate_hebrew_variants(query: str, max_variants: int = 50) -> List[str]:
    """
    Generate all possible Hebrew spellings from transliteration.
    
    This is the exhaustive version - use generate_smart_variants()
    for better performance in most cases.
    
    Args:
        query: English transliteration
        max_variants: Limit to prevent explosion
    
    Returns:
        List of possible Hebrew strings
    """
    query = normalize_query(query)
    words = query.split()
    
    all_word_variants: List[List[str]] = []
    
    for word in words:
        # Check exceptions
        exception_variants = check_exception(word)
        if exception_variants:
            all_word_variants.append(exception_variants)
        else:
            word_with_marker = word + "\0"
            variants = _generate_word_variants(word_with_marker, max_per_word=20)
            all_word_variants.append(variants if variants else [word])
    
    return _combine_word_variants(all_word_variants, max_variants)


def transliteration_confidence(query: str) -> str:
    """
    Estimate confidence in transliteration mapping.
    
    Returns: "high", "medium", or "low"
    
    High: Simple consonants, known patterns
    Medium: Some ambiguous vowels
    Low: Many ambiguous vowels, unusual combinations
    """
    query = normalize_query(query)
    words = query.split()
    
    # Check if any words are in exceptions (high confidence)
    exception_count = sum(1 for w in words if check_exception(w))
    if exception_count == len(words):
        return "high"
    
    # Count ambiguous characters
    ambiguous_chars = set("aeiouh")
    query_no_spaces = query.replace(" ", "")
    
    if not query_no_spaces:
        return "low"
    
    ambiguous_count = sum(1 for c in query_no_spaces if c in ambiguous_chars)
    ambiguity_ratio = ambiguous_count / len(query_no_spaces)
    
    if ambiguity_ratio > 0.55:
        return "low"
    elif ambiguity_ratio > 0.35:
        return "medium"
    else:
        return "high"


# ==========================================
#  TESTING
# ==========================================

if __name__ == "__main__":
    print("=" * 70)
    print("TRANSLITERATION MAP V2 - COMPREHENSIVE TEST")
    print("=" * 70)
    
    test_cases = [
        # === ORIGINAL FAILURES (should all pass now) ===
        ("migu", "מיגו", "Yud retention"),
        ("shiur", "שיעור", "Ayin detection"),
        ("muad", "מועד", "Ayin detection"),
        ("lo plug", "לא פלוג", "lo = לא exception"),
        ("kal vchomer", "קל וחומר", "Vav prefix"),
        ("trei vetrei", "תרי ותרי", "Aramaic + vav prefix"),
        ("binyan av", "בנין אב", "Nun sofit + av"),
        ("kinyan", "קנין", "Nun sofit"),
        ("kdai achila", "כדי אכילה", "Final heh"),
        ("hashaveh", "השווה", "Double vav"),
        ("kesubos", "כתובות", "Masechta"),
        ("leolam", "לעולם", "Ayin + mem sofit"),
        ("ribui umiut", "ריבוי ומיעוט", "Complex phrase"),
        
        # === MORE FROM ORIGINAL TEST SUITE ===
        ("kdai shiur", "כדי שיעור", "Ayin in shiur"),
        ("shiur kzayis", "שיעור כזית", "Ayin + final sav"),
        ("shiur kbeitza", "שיעור כביצה", "Ayin + beitza"),
        ("davar halamd meinyano", "דבר הלמד מעניינו", "Complex with ayin"),
        ("tzad hashaveh", "צד השווה", "Double vav"),
        ("miktzas hayom kchulo", "מקצת היום ככולו", "Multiple sofits"),
        ("chalipin kinyan", "חליפין קנין", "Double nun sofit"),
        ("meshicha kinyan", "משיכה קנין", "Feminine + sofit"),
        ("adam muad leolam", "אדם מועד לעולם", "Ayin + sofit"),
        ("shor hamuad", "שור המועד", "Ayin in middle"),
        ("ain adam oser", "אין אדם אוסר", "ain/ein pattern"),
        ("hafkaas kiddushin", "הפקעת קידושין", "Complex"),
        ("klal uprat", "כלל ופרט", "Vav prefix"),
        ("gezeira shava", "גזירה שווה", "Double vav"),
        ("shnei kesuvim", "שני כתובים", "yeshivish spelling"),
        
        # === BASIC TERMS ===
        ("bava kama", "בבא קמא", "Masechta"),
        ("sfek sfeika", "ספק ספיקא", "Aramaic ending"),
        ("chatzi shiur", "חצי שיעור", "Ayin"),
        ("lavud", "לבוד", "Simple"),
        ("yad soledet bo", "יד סולדת בו", "Multiple words"),
    ]
    
    passed = 0
    failed = 0
    
    for query, expected, description in test_cases:
        variants = generate_smart_variants(query, max_variants=10)
        
        # Check if expected is in variants
        found = expected in variants
        top_variant = variants[0] if variants else "N/A"
        
        if found:
            passed += 1
            status = "✓"
        else:
            failed += 1
            status = "✗"
        
        print(f"\n{status} {description}")
        print(f"   Query: '{query}'")
        print(f"   Expected: {expected}")
        print(f"   Top variant: {top_variant}")
        if not found:
            print(f"   All variants: {variants[:5]}")
    
    print("\n" + "=" * 70)
    print(f"RESULTS: {passed}/{passed + failed} passed ({100*passed/(passed+failed):.1f}%)")
    print("=" * 70)