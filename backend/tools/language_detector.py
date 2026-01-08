"""
Language Detector for Marei Mekomos
===================================

Determines if a word/query is English vs Hebrew transliteration.

Strategy: Instead of trying to identify all English words (impossible),
we identify what looks like Hebrew transliteration. Everything else
is assumed to be English.

Hebrew transliterations have specific patterns:
- Phonetic spellings: "ch" (ח), "tz" (צ), "sh" (ש), etc.
- Vowel patterns: "ei", "ai", "oi", double vowels
- Common endings: -os, -is, -ah, -eh, -im, -ot
- Uncommon consonant clusters for English

We also use pyenchant for spell-checking if available.
"""

import re
import logging
from typing import Tuple, Optional
from functools import lru_cache

logger = logging.getLogger(__name__)

# =============================================================================
#  ENCHANT SPELL CHECKER (Optional)
# =============================================================================

_enchant_dict = None
_enchant_available = False

try:
    import enchant
    _enchant_dict = enchant.Dict("en_US")
    _enchant_available = True
    logger.info("[LANG_DETECT] pyenchant available - using spell checker")
except ImportError:
    logger.info("[LANG_DETECT] pyenchant not available - using heuristics only")
except Exception as e:
    logger.warning(f"[LANG_DETECT] pyenchant error: {e} - using heuristics only")


def is_english_word_enchant(word: str) -> Optional[bool]:
    """
    Check if a word is English using pyenchant.
    Returns None if enchant is not available.
    """
    if not _enchant_available or not _enchant_dict:
        return None

    word_clean = word.lower().strip()
    if len(word_clean) < 2:
        return None

    # Direct check
    if _enchant_dict.check(word_clean):
        return True

    # Check if it's close to an English word (typo)
    suggestions = _enchant_dict.suggest(word_clean)
    if suggestions:
        # If the top suggestion is very close (1-2 edits), treat as English
        top = suggestions[0].lower()
        if _edit_distance(word_clean, top) <= 2:
            return True

    return False


def _edit_distance(s1: str, s2: str) -> int:
    """Simple Levenshtein edit distance."""
    if len(s1) < len(s2):
        return _edit_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


# =============================================================================
#  HEBREW TRANSLITERATION PATTERNS
# =============================================================================

# Patterns that strongly indicate Hebrew transliteration
HEBREW_START_PATTERNS = [
    'tz',    # צ - tzedek, tzniyus
    'ch',    # ח - chassid, chometz (but watch for "child", "change")
    'sh',    # ש - shabbos, shema (but watch for "she", "should")
    'kh',    # כ soft - but rare in transliteration start
]

HEBREW_CONTAINS_PATTERNS = [
    'tz',    # צ anywhere
    'chl',   # in words like "machlokes" but not "child"
    'chm',   # chometz
    'chr',   # not common in English
    'chz',   # chazakah
    'chk',   # not common
    'shv',   # shvuos
    'shm',   # shema (but not "cashmore")
]

HEBREW_END_PATTERNS = [
    'os',    # tosfos, malkos - but also "chaos", "pathos"
    'ot',    # mitzvot, brachos
    'im',    # rishonim, acharonim
    'is',    # but common in English too
    'ah',    # torah, halacha
    'eh',    # kedushah variants
    'us',    # common in English too
]

# Additional Hebrew/Yiddish structural patterns (more specific)
HEBREW_STRUCTURE_PATTERNS = [
    # Hebrew noun endings
    (r'ut$', 4),      # kashrut, malchut, galut - Hebrew abstract nouns
    (r'an$', 4),      # minyan, chazzan, korban - Hebrew pattern
    (r'on$', 4),      # aron, tikkun, chidon - Hebrew pattern
    (r'en$', 4),      # daven (Yiddish), though "en" is also English

    # Yiddish patterns
    (r'^shm', 3),     # shmooze, shmutz, shmaltz
    (r'^shn', 3),     # schnorr, etc
    (r'^schl', 4),    # schlepp, schlep
    (r'tch$', 3),     # bentch, kvetch, klatsch
    (r'sch$', 4),     # mensch, kitsch (but also English)

    # Hebrew consonant patterns rarely in English
    (r'(^|[aeiou])v[aeiou]n', 4),  # daven, maven
    (r'yi$', 4),      # yomi ending
    (r'ei$', 4),      # bei, rei patterns
    (r'ai$', 4),      # adonai pattern
]

# Words that pyenchant incorrectly identifies as English
# These are Yiddish/Hebrew origin words in English dictionaries
# Use pattern matching, not just listing them
YIDDISH_ENGLISH_CROSSOVER_PATTERNS = [
    # Short words with specific structures that are Hebrew/Yiddish
    r'^sh[aeiou]l$',   # shul, etc.
    r'^d[aeiou]f$',    # daf
    r'^d[aeiou]ven$',  # daven
    r'^min[yi]an$',    # minyan, minian
]

# Very strong Hebrew indicators (almost never English)
STRONG_HEBREW_PATTERNS = [
    r'\btz\w',           # tzedek, tzniyus (tz at start)
    r'\w+tzk',           # mitzvah patterns
    r'\bch[aeiou]z',     # chazakah, chazon
    r'\bch[aeiou]m',     # chometz, chametz
    r'\bch[aeiou]s',     # chassid, chasunah (but not "chase", "chase")
    r'\bsh[aeiou]b',     # shabbos, shabbat
    r'\bsh[aeiou]m',     # shema, shmita
    r'\bsh[aeiou]v',     # shvuos
    r'[aeiou]ch[aeiou]', # machloket, bracha
    r'kah\b',            # halacha, bracha
    r'vah\b',            # mitzvah
    r'vos\b',            # mitzvos
    r'mos\b',            # yomim tovim patterns
    r'yos\b',            # sugyos
    r'nim\b',            # rishonim, acharonim
    r'ois\b',            # tosfos variants
]

# Common English words that look like Hebrew (false positives to exclude)
ENGLISH_LOOKALIKES = {
    'child', 'children', 'church', 'change', 'changed', 'changes', 'changing',
    'chase', 'chased', 'chasing', 'choose', 'chose', 'chosen', 'choosing',
    'chair', 'chairs', 'chain', 'chains', 'chance', 'chances', 'chapter',
    'character', 'characters', 'charge', 'charged', 'charges', 'charging',
    'chart', 'charts', 'cheap', 'cheaper', 'cheapest', 'check', 'checked',
    'checking', 'checks', 'cheese', 'chemical', 'chemicals', 'chest',
    'chicken', 'chief', 'chiefs', 'china', 'chinese', 'chip', 'chips',
    'chocolate', 'choice', 'choices', 'chorus',
    'she', 'should', 'show', 'shown', 'shows', 'showing', 'shower',
    'shall', 'share', 'shared', 'shares', 'sharing', 'sharp', 'sharper',
    'sheet', 'sheets', 'shelf', 'shell', 'shells', 'shift', 'shifted',
    'shine', 'shines', 'shining', 'ship', 'ships', 'shipping', 'shirt',
    'shock', 'shocked', 'shocking', 'shoe', 'shoes', 'shop', 'shops',
    'shopping', 'shore', 'short', 'shorter', 'shortest', 'shot', 'shots',
    'shoulder', 'shoulders', 'shout', 'shouted', 'shouting',
    'chaos', 'pathos', 'ethos', 'thermos',
    'fish', 'wish', 'dish', 'push', 'rush', 'brush', 'crush', 'flush',
    'fresh', 'trash', 'crash', 'flash', 'splash', 'clash', 'smash', 'dash',
    'wash', 'cash', 'rash', 'bash', 'hash', 'lash', 'mash', 'gash',
    'establish', 'established', 'finish', 'finished', 'finishing',
    'polish', 'polished', 'publish', 'published', 'publishing',
    'british', 'spanish', 'english', 'jewish', 'irish', 'turkish',
}

# Known Hebrew terms and roots (for positive identification)
KNOWN_HEBREW_ROOTS = {
    # Common Torah/halacha terms
    'torah', 'halacha', 'halachos', 'halachot', 'gemara', 'mishna', 'mishnah',
    'talmud', 'midrash', 'targum', 'chumash', 'tanach', 'nach',
    'bracha', 'brachos', 'brachot', 'tefila', 'tefilah', 'tefilos',
    'shabbos', 'shabbat', 'yomtov', 'pesach', 'sukkos', 'sukkot',
    'shavuos', 'shavuot', 'purim', 'chanukah', 'chanuka', 'hannukah',

    # Legal/halachic concepts
    'issur', 'issurim', 'heter', 'mutar', 'assur', 'asur',
    'chiyuv', 'patur', 'kasher', 'kosher', 'treif', 'tahor', 'tamei',
    'mamzer', 'ger', 'gerim', 'nochri', 'akum', 'goy', 'goyim',

    # Common sugya terms
    'chazakah', 'chazaka', 'chezkas', 'chezkat', 'hazakah',
    'rov', 'ruba', 'roba', 'safek', 'safeik', 'vadai',
    'bari', 'shema', 'migu', 'migo',
    'anan', 'sahadei', 'modeh', 'kofer',

    # Kesubos/Pesachim specific
    'kesubah', 'ketubah', 'ketubot', 'kesubos',
    'chometz', 'chametz', 'matzah', 'matza', 'matzos', 'matzot',
    'bedikah', 'bedikas', 'bitul', 'biur',
    'besulah', 'besulim', 'almanah',

    # Common modifiers
    'gadol', 'katan', 'rishon', 'acharon',
    'deoraisa', 'doraisa', 'derabbanan', 'drabbanan',
    'lechatchila', 'bediavad', 'bdieved',

    # Actions/verbs
    'lishma', 'shelo', 'leshem',
    'mekayem', 'mevatel', 'koneh', 'makneh',

    # Talmudic sages (Amoraim)
    'rava', 'abaye', 'rav', 'shmuel', 'rebbi', 'rabbi',
    'rashi', 'tosafos', 'tosfos', 'rambam', 'ramban', 'rashba',
    'ritva', 'ran', 'rosh', 'tur', 'mechaber', 'rama',
    'hillel', 'shammai', 'akiva', 'meir', 'yehuda', 'shimon',
    'yochanan', 'lakish', 'resh', 'zeira', 'chisda', 'nachman',
    'pappa', 'huna', 'yosef', 'kahana',

    # Body/physical terms
    'guf', 'haguf', 'dam', 'nefesh', 'lev', 'yad', 'regel',
    'rosh', 'panim', 'einayim', 'oznayim', 'peh',

    # Property/money terms
    'mammon', 'kesef', 'shtar', 'karka', 'metaltelin',
    'kinyan', 'meshicha', 'hagbaha', 'chazaka',

    # Time terms
    'zman', 'shaah', 'yom', 'layla', 'boker', 'erev',
    'shaos', 'shaot', 'yamim',

    # More halachic terms
    'niddah', 'nidah', 'mikvah', 'mikva', 'tevilah', 'tevila',
    'kiddushin', 'nisuin', 'gittin', 'get', 'chalitzah',
    'yibum', 'sotah', 'nazir', 'nedarim', 'shvuos',

    # Common Hebrew words often used
    'sugya', 'sugyos', 'sugyas', 'inyan', 'inyonim',
    'bris', 'milah', 'mohel', 'sandek',
    'aliyah', 'aliya', 'aliyos', 'oleh',
    'seder', 'sedarim', 'sedra', 'parsha', 'parshas',
    'dvar', 'divrei', 'shiur', 'shiurim',
    'minhag', 'minhagim', 'mesorah', 'masorah',

    # Common Yiddish terms
    'kvell', 'kvetch', 'kvetching', 'schmaltz', 'schmalzy',
    'chutzpah', 'mensch', 'maven', 'mavin',
    'shpiel', 'shlep', 'schlepp', 'nosh', 'noshing',
    'tchotchke', 'bubbe', 'zayde', 'zaide',
}


# =============================================================================
#  CORE DETECTION FUNCTIONS
# =============================================================================

@lru_cache(maxsize=1000)
def is_hebrew_transliteration(word: str) -> Tuple[bool, str]:
    """
    Determine if a word is likely a Hebrew transliteration.

    Returns (is_hebrew, reason)
    """
    word_lower = word.lower().strip()

    if len(word_lower) < 2:
        return (False, "too_short")

    # Check known English lookalikes first
    if word_lower in ENGLISH_LOOKALIKES:
        return (False, "english_lookalike")

    # Check known Hebrew roots
    if word_lower in KNOWN_HEBREW_ROOTS:
        return (True, "known_hebrew_term")

    # Check for Hebrew root within the word
    for root in KNOWN_HEBREW_ROOTS:
        if len(root) >= 4 and root in word_lower:
            return (True, f"contains_hebrew_root:{root}")

    # Check strong Hebrew patterns (regex)
    for pattern in STRONG_HEBREW_PATTERNS:
        if re.search(pattern, word_lower):
            return (True, f"strong_pattern:{pattern}")

    # Check Yiddish/Hebrew crossover patterns (words enchant thinks are English)
    for pattern in YIDDISH_ENGLISH_CROSSOVER_PATTERNS:
        if re.search(pattern, word_lower):
            return (True, f"yiddish_crossover:{pattern}")

    # Check Hebrew structural patterns (endings, etc.)
    # IMPORTANT: Only apply if enchant doesn't verify as English
    for pattern, min_len in HEBREW_STRUCTURE_PATTERNS:
        if len(word_lower) >= min_len and re.search(pattern, word_lower):
            # If enchant recognizes it as English, skip structural pattern matching
            if _enchant_available and _enchant_dict and _enchant_dict.check(word_lower):
                continue  # It's a valid English word, don't flag as Hebrew

            # Extra validation for patterns that are common in English
            if pattern == r'en$':
                # -en is very common in English - only flag if has Hebrew indicators
                if not any(h in word_lower for h in ['ch', 'tz', 'sh', 'kh']):
                    continue
            if pattern == r'on$':
                # -on is common in English - need other Hebrew indicators
                if not any(h in word_lower for h in ['ch', 'tz', 'sh', 'kh']):
                    continue
            if pattern == r'an$':
                # -an is common in English - need other Hebrew indicators
                if not any(h in word_lower for h in ['ch', 'tz', 'sh', 'kh']):
                    continue

            return (True, f"hebrew_structure:{pattern}")

    # Check start patterns (with English exclusion)
    for pat in HEBREW_START_PATTERNS:
        if word_lower.startswith(pat):
            # Exclude common English words starting with these
            if word_lower in ENGLISH_LOOKALIKES:
                continue
            # "ch" is tricky - need more context
            if pat == 'ch' and len(word_lower) > 3:
                # Check if it's followed by a Hebrew-like pattern
                rest = word_lower[2:]
                if rest[0] in 'aeiou' and any(h in rest for h in ['z', 'k', 'm', 'v', 'n']):
                    return (True, f"start_pattern:{pat}_with_hebrew_follow")
            elif pat in ['tz', 'kh']:
                return (True, f"start_pattern:{pat}")

    # Check end patterns
    if len(word_lower) > 3:
        for pat in HEBREW_END_PATTERNS:
            if word_lower.endswith(pat):
                # -os, -im, -ah are strong indicators if word has other Hebrew features
                if pat in ['im', 'ot'] and len(word_lower) > 4:
                    return (True, f"end_pattern:{pat}")
                if pat == 'ah' and any(c in word_lower for c in ['ch', 'sh', 'tz']):
                    return (True, f"end_pattern:{pat}_with_hebrew_chars")

    # Check contains patterns
    for pat in HEBREW_CONTAINS_PATTERNS:
        if pat in word_lower and word_lower not in ENGLISH_LOOKALIKES:
            return (True, f"contains_pattern:{pat}")

    # Not identified as Hebrew
    return (False, "no_hebrew_pattern")


def is_english_word(word: str) -> Tuple[bool, str]:
    """
    Determine if a word is likely English.

    Returns (is_english, reason)
    """
    word_lower = word.lower().strip()

    if len(word_lower) < 2:
        return (True, "too_short_assume_english")

    # Check known English lookalikes
    if word_lower in ENGLISH_LOOKALIKES:
        return (True, "known_english")

    # Try enchant if available
    enchant_result = is_english_word_enchant(word_lower)
    if enchant_result is True:
        return (True, "enchant_verified")
    elif enchant_result is False:
        # Enchant says no, but let's not immediately say it's Hebrew
        pass

    # Check if it's Hebrew
    is_hebrew, reason = is_hebrew_transliteration(word_lower)
    if is_hebrew:
        return (False, f"identified_as_hebrew:{reason}")

    # Default: assume English if not identified as Hebrew
    return (True, "default_assume_english")


def classify_word(word: str) -> Tuple[str, str]:
    """
    Classify a word as 'english', 'hebrew', or 'unknown'.

    Returns (classification, reason)
    """
    word_lower = word.lower().strip()

    if len(word_lower) < 2:
        return ("english", "too_short")

    # Check if it's clearly Hebrew
    is_hebrew, hebrew_reason = is_hebrew_transliteration(word_lower)
    if is_hebrew:
        return ("hebrew", hebrew_reason)

    # Check if it's clearly English
    is_eng, eng_reason = is_english_word(word_lower)
    if is_eng:
        return ("english", eng_reason)

    # Unknown - default to English in ambiguous cases
    return ("english", "default")


def analyze_query(query: str) -> dict:
    """
    Analyze a full query and classify each word.

    Returns dict with:
    - words: list of (word, classification, reason)
    - english_count: int
    - hebrew_count: int
    - is_pure_english: bool
    - is_mixed: bool
    - is_pure_hebrew: bool
    """
    words = query.lower().split()
    clean_words = [re.sub(r'[?,.\'"!;:]', '', w) for w in words]

    results = []
    english_count = 0
    hebrew_count = 0

    for word in clean_words:
        if not word or len(word) <= 1:
            continue

        classification, reason = classify_word(word)
        results.append((word, classification, reason))

        if classification == "hebrew":
            hebrew_count += 1
        else:
            english_count += 1

    total = english_count + hebrew_count
    if total == 0:
        return {
            "words": results,
            "english_count": 0,
            "hebrew_count": 0,
            "is_pure_english": False,
            "is_mixed": False,
            "is_pure_hebrew": False,
        }

    english_ratio = english_count / total

    return {
        "words": results,
        "english_count": english_count,
        "hebrew_count": hebrew_count,
        "is_pure_english": english_ratio >= 0.9 and hebrew_count == 0,
        "is_mixed": 0 < hebrew_count < total,
        "is_pure_hebrew": english_count == 0 and hebrew_count > 0,
    }


# =============================================================================
#  EXPORTS
# =============================================================================

__all__ = [
    'is_hebrew_transliteration',
    'is_english_word',
    'classify_word',
    'analyze_query',
    'KNOWN_HEBREW_ROOTS',
    'ENGLISH_LOOKALIKES',
]
