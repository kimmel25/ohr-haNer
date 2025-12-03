# ==========================================
#  Talmudic Hebrew + Aramaic Transliteration
#  MAAREI MAKOMOS SEARCH PROJECT
#  (Drop straight into Python)
# ==========================================

TRANSLIT_MAP = {

    # =======================
    # MULTI-CHAR PHONEMES
    # =======================

    "sh": ["ש"],
    "sch": ["ש"],         # yeshivish spelling
    "ts": ["צ"],          # tosefta, mtsiya
    "tz": ["צ"],
    "tzh": ["צ"],
    "zh": ["ז"],          # rare but in Persian-influenced Aramaic
    "ch": ["ח"],          # chalitza, hilchos
    "kh": ["כ", "ח"],     # aramaic prefers ח sometimes
    "th": ["ת"],          # ashkenazi (e.g. "Shboises" -> שביתת)
    "ph": ["פ"],          # "tzephila" variants
    "bb": ["ב"],
    "kk": ["כ", "ק"],
    "ss": ["ס", "ש"],
    "rr": ["ר"],
    "mm": ["מ"],
    "nn": ["נ"],

    # =======================
    # CONSONANTS (SINGLE)
    # =======================

    "b": ["ב"],
    "v": ["ו", "ב"],      # vet ambiguity
    "w": ["ו"],

    "g": ["ג"],
    "d": ["ד"],
    "z": ["ז"],

    "h": ["ה", "ח"],      # ambiguous in Aramaic searches

    "t": ["ט", "ת"],      # talmudic often flips ט/ת
    "s": ["ס", "ש"],

    "k": ["כ", "ק"],
    "q": ["ק"],           # scholarly transcription

    "l": ["ל"],
    "m": ["מ"],
    "n": ["נ"],
    "r": ["ר"],

    "p": ["פ"],
    "f": ["פ", "ף"],      # final form useful for matching inside words

    "x": ["כ", "קס"],     # "maseches" weird spellings

    "j": ["ג", "י"],      # Yemenite/Ashkenazi input "gaiva" -> גאוה, גאווה

    "c": ["כ", "ק", "צ"], # hard european influence

    # =======================
    # VOWELS / GUTTURALS
    # =======================

    "a": ["א", "ע", "ה"],    # biggest ambiguity in Aramaic
    "e": ["א", "ה"],
    "i": ["י", "א"],
    "o": ["ו", "א"],
    "u": ["ו"],

    # Yeshivish Swaps
    "ai": ["אי", "עי"],
    "ei": ["אי", "עי"],
    "oi": ["וי", "עי"],
    "ui": ["וי"],
    "aa": ["א", "ע", "ה"],
    "ee": ["י"],
    "oo": ["ו"],

    # Shva-ish endings
    "eh": ["ה"],
    "ah": ["ה", "א"],
    "oh": ["ו", "ה"],
    "uh": ["ו"],

    # =======================
    # ENDINGS (POWERFUL)
    # =======================

    # Hebrew final forms – important for database hits
    "m\0": ["ם"],
    "n\0": ["ן"],
    "tz\0": ["ץ"],
    "tzs\0": ["ץ"],
    "p\0": ["ף"],
    "k\0": ["ך"],

    # Common Aramaic suffixes
    "in\0": ["ין", "ין"],
    "an\0": ["ן", "אן"],
    "un\0": ["ון"],
    "on\0": ["ון", "ן"],

    # =======================
    # ARAMAIC PARTICLES
    # =======================

    "d'": ["ד", "דה"],     # d'oraisa, devar
    "de": ["ד", "דה"],
    "da": ["ד", "דה"],
    "di": ["די"],         # aramaic formal
    "du": ["דו"],

    "u": ["ו"],           # u'mishum, uman
    "ve": ["ו"],          # ve-im, ve-hu
    "va": ["ו"],

    "min": ["מן", "מ"],   # Aramaic preposition
    "mi": ["מ"],

    # =======================
    # GUTTURALS
    # =======================

    # Big ones that are impossible to guess exactly
    "aa": ["א", "ע", "ה"],
    "ah": ["ה", "א"],
    "eh": ["ה", "א"],
    "ih": ["י", "א"],
    "oh": ["ו", "א"],
    "uh": ["ו", "ה"]
}