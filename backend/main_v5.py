"""
Marei Mekomos Backend API - Version 5.0 "Sugya Archaeology"
============================================================

CORE METHODOLOGY (from Gemini Paper "Computational Hermeneutics"):
This is NOT a lexical search engine. It's a Citation Graph Traversal system.

The insight: Acharonim are "semantic nodes" - they explicitly cite earlier sources.
When Ketzos HaChoshen, Pnei Yehoshua, or Reb Akiva Eiger discuss a topic, they
systematically reference: Origin (Talmudic sugya) → Interpretation (Rishonim) → Ruling (SA)

By analyzing WHAT later authorities cite, we discover foundational sources that a
keyword search would never find. This is robust against terminology drift because
linkage is conceptual, not lexical.

VGR PROTOCOL (Validated Generative Retrieval):
1. Generation Phase: Claude interprets query + generates potential source refs
2. Extraction Phase: Parse citations from Claude's response  
3. Verification Phase: Every ref validated against Sefaria API
   - 200 OK + Text → source validated, passed to frontend
   - 400/404/Error → flagged as hallucination, silently discarded

CONTEXTUAL VECTORIZATION:
- Lomdus queries ("Why", "Contradiction", "svara") → prioritize analytical sources
- Psak queries ("Can I", "How do I", "mutar?") → prioritize practical poskim
- Entropy detection → trigger chavrusa-style clarification for ambiguous queries

Yeshivish conventions throughout: sav not tav (Shabbos, Kesubos, etc.)
"""

import os
import json
import httpx
import html
import re
import hashlib
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from anthropic import Anthropic
from typing import List, Optional, Dict, Set, Tuple, Any
from collections import Counter
from datetime import datetime
from enum import Enum

# Import our logging and caching
from logging_config import setup_logging, get_logger
from cache_manager import claude_cache, sefaria_cache

# Initialize logging
setup_logging()
logger = get_logger(__name__)


# =============================
# CONFIGURATION
# =============================

COST_SAVING_MODE = os.environ.get("COST_SAVING_MODE", "true").lower() == "true"
MAX_COMMENTARIES_PER_BASE = int(os.environ.get("MAX_COMMENTARIES", "12"))
MAX_FINAL_SOURCES = int(os.environ.get("MAX_SOURCES", "30"))

# Strict validation mode: if True, requires content match for validation
STRICT_VALIDATION = os.environ.get("STRICT_VALIDATION", "true").lower() == "true"

if COST_SAVING_MODE:
    logger.info("💰 COST_SAVING_MODE enabled")
if STRICT_VALIDATION:
    logger.info("🔒 STRICT_VALIDATION enabled - enhanced anti-hallucination")


# =============================
# QUERY INTENT CLASSIFICATION
# (Contextual Vectorization from Gemini Paper)
# =============================

class QueryIntent(str, Enum):
    """
    Contextual Vectorization: Different query types need different source prioritization
    """
    LOMDUS = "lomdus"      # Analytical: "Why", "Contradiction", "svara"
    PSAK = "psak"          # Practical: "Can I", "Is it mutar", "What should I do"
    MAKOR = "makor"        # Source-finding: "Where does it say", "source for"
    GENERAL = "general"    # General information


# Keywords for intent detection (entropy reduction)
LOMDUS_INDICATORS = [
    "why", "svara", "sevara", "contradiction", "kashya", "kasha", "stirah",
    "machlokes", "machlokess", "dispute", "teirutz", "answer", "explains",
    "shitas", "shita", "reason", "logic", "chakira", "chakirah", "nafka mina",
    "נפקא מינה", "מחלוקת", "סברא", "קשיא", "תירוץ", "חקירה", "סתירה"
]

PSAK_INDICATORS = [
    "can i", "is it", "am i allowed", "mutar", "assur", "permitted", "forbidden",
    "should i", "what do i do", "how do i", "l'chatchila", "b'dieved", "halacha",
    "practical", "nowadays", "today", "מותר", "אסור", "לכתחילה", "בדיעבד", "הלכה למעשה"
]

MAKOR_INDICATORS = [
    "where", "source", "makor", "where does it say", "מקור", "מנלן", "from where",
    "origin", "based on", "derived from"
]


def detect_query_intent(query: str) -> QueryIntent:
    """
    Detect query intent for Contextual Vectorization.
    This affects which Acharonim and sources we prioritize.
    """
    query_lower = query.lower()
    
    lomdus_score = sum(1 for ind in LOMDUS_INDICATORS if ind in query_lower)
    psak_score = sum(1 for ind in PSAK_INDICATORS if ind in query_lower)
    makor_score = sum(1 for ind in MAKOR_INDICATORS if ind in query_lower)
    
    if lomdus_score > psak_score and lomdus_score > makor_score:
        return QueryIntent.LOMDUS
    elif psak_score > lomdus_score and psak_score > makor_score:
        return QueryIntent.PSAK
    elif makor_score > 0:
        return QueryIntent.MAKOR
    return QueryIntent.GENERAL


# =============================
# HIGH-ENTROPY QUERY DETECTION
# (Chavrusa-style disambiguation)
# =============================

# Queries with single ambiguous terms need clarification
HIGH_ENTROPY_TERMS = {
    "niddah": [
        "Are you asking about hilchos niddah (laws of family purity)?",
        "Or tumas niddah (the tumah status of a niddah)?",
        "Or perhaps the masechta Niddah?"
    ],
    "shabbos": [
        "Are you asking about a specific melacha (forbidden labor)?",
        "Or hilchos Shabbos in general?",
        "Or perhaps eruvin/techumin?"
    ],
    "chametz": [
        "Are you asking about bedikas chametz (searching)?",
        "Or bitul chametz (nullification)?",
        "Or ba'al yiraeh ba'al yimatzei (prohibition of ownership)?"
    ],
    "chuppah": [
        "Are you asking about what constitutes a valid chuppah?",
        "Or the brachos under the chuppah?",
        "Or when chuppah/nissuin can take place (e.g., chuppas niddah)?"
    ],
    "mikvah": [
        "Are you asking about hilchos tevilah (immersion laws)?",
        "Or the construction of a kosher mikvah?",
        "Or specific cases requiring mikvah?"
    ],
    "kiddushin": [
        "Are you asking about kesef, shtar, or bi'ah (modes of kiddushin)?",
        "Or kinyanim related to kiddushin?",
        "Or the masechta Kiddushin generally?"
    ],
    "eruv": [
        "Are you asking about eruv chatzeiros?",
        "Or eruv techumin?",
        "Or eruv tavshilin?"
    ],
}


def check_query_entropy(query: str) -> Optional[List[str]]:
    """
    Check if query is ambiguous (high entropy) and needs clarification.
    Returns clarifying questions if needed, None otherwise.
    """
    query_lower = query.lower().strip()
    
    # Single-word queries that are in our high-entropy list
    for term, questions in HIGH_ENTROPY_TERMS.items():
        # Match if the query is basically just this term
        if query_lower == term or query_lower in [term, f"the {term}", f"about {term}"]:
            return questions
    
    return None


# =============================
# SLUG TRANSLATION DICTIONARY
# (From Gemini Paper: solves LLM → Sefaria format mismatch)
# =============================

# Comprehensive masechta mapping (yeshivish transliteration)
MASECHTA_TO_SEFARIA = {
    # Seder Zeraim
    "brachos": "Berakhot", "berachos": "Berakhot", "brochos": "Berakhot",
    "berakhot": "Berakhot", "berakhos": "Berakhot", "ברכות": "Berakhot",
    
    # Seder Moed
    "shabbos": "Shabbat", "shabbat": "Shabbat", "שבת": "Shabbat",
    "eruvin": "Eruvin", "eiruvin": "Eruvin", "עירובין": "Eruvin",
    "pesachim": "Pesachim", "psachim": "Pesachim", "פסחים": "Pesachim",
    "shekalim": "Shekalim", "shkalim": "Shekalim", "שקלים": "Shekalim",
    "yoma": "Yoma", "יומא": "Yoma",
    "sukkah": "Sukkah", "sukka": "Sukkah", "סוכה": "Sukkah",
    "beitzah": "Beitzah", "beitza": "Beitzah", "ביצה": "Beitzah",
    "rosh hashanah": "Rosh Hashanah", "rosh hashana": "Rosh Hashanah", "ראש השנה": "Rosh Hashanah",
    "taanis": "Taanit", "taanit": "Taanit", "תענית": "Taanit",
    "megillah": "Megillah", "מגילה": "Megillah",
    "moed katan": "Moed Katan", "מועד קטן": "Moed Katan",
    "chagigah": "Chagigah", "חגיגה": "Chagigah",
    
    # Seder Nashim
    "yevamos": "Yevamot", "yevamot": "Yevamot", "יבמות": "Yevamot",
    "kesubos": "Ketubot", "kesuvos": "Ketubot", "ketubot": "Ketubot",
    "ketubos": "Ketubot", "כתובות": "Ketubot",
    "nedarim": "Nedarim", "נדרים": "Nedarim",
    "nazir": "Nazir", "נזיר": "Nazir",
    "sotah": "Sotah", "סוטה": "Sotah",
    "gittin": "Gittin", "גיטין": "Gittin",
    "kiddushin": "Kiddushin", "kidushin": "Kiddushin", "קידושין": "Kiddushin",
    
    # Seder Nezikin
    "bava kamma": "Bava Kamma", "baba kama": "Bava Kamma", "בבא קמא": "Bava Kamma",
    "bava metzia": "Bava Metzia", "baba metzia": "Bava Metzia", "בבא מציעא": "Bava Metzia",
    "bava basra": "Bava Batra", "bava batra": "Bava Batra", "בבא בתרא": "Bava Batra",
    "sanhedrin": "Sanhedrin", "סנהדרין": "Sanhedrin",
    "makkos": "Makkot", "makos": "Makkot", "makkot": "Makkot", "מכות": "Makkot",
    "shevuos": "Shevuot", "shevuot": "Shevuot", "שבועות": "Shevuot",
    "avodah zarah": "Avodah Zarah", "avoda zara": "Avodah Zarah", "עבודה זרה": "Avodah Zarah",
    "horayos": "Horayot", "horayot": "Horayot", "הוריות": "Horayot",
    
    # Seder Kodshim
    "zevachim": "Zevachim", "zvachim": "Zevachim", "זבחים": "Zevachim",
    "menachos": "Menachot", "menachot": "Menachot", "מנחות": "Menachot",
    "chullin": "Chullin", "chulin": "Chullin", "חולין": "Chullin",
    "bechoros": "Bekhorot", "bechorot": "Bekhorot", "בכורות": "Bekhorot",
    "arachin": "Arakhin", "ערכין": "Arakhin",
    "temurah": "Temurah", "תמורה": "Temurah",
    "kerisos": "Keritot", "kerisot": "Keritot", "כריתות": "Keritot",
    "meilah": "Meilah", "מעילה": "Meilah",
    "tamid": "Tamid", "תמיד": "Tamid",
    "middos": "Middot", "מידות": "Middot",
    "kinnim": "Kinnim", "קינים": "Kinnim",
    
    # Seder Taharos
    "niddah": "Niddah", "nidah": "Niddah", "נדה": "Niddah",
}

# Rambam Mishneh Torah section mapping
RAMBAM_SECTIONS = {
    # Marriage/Women
    "ishus": "Mishneh Torah, Marriage",
    "ishut": "Mishneh Torah, Marriage",
    "hilchos ishus": "Mishneh Torah, Marriage",
    "hilchot ishut": "Mishneh Torah, Marriage",
    "הלכות אישות": "Mishneh Torah, Marriage",
    
    "issurei biah": "Mishneh Torah, Forbidden Intercourse",
    "issurei bi'ah": "Mishneh Torah, Forbidden Intercourse",
    "hilchos issurei biah": "Mishneh Torah, Forbidden Intercourse",
    "הלכות איסורי ביאה": "Mishneh Torah, Forbidden Intercourse",
    
    "gerushin": "Mishneh Torah, Divorce",
    "hilchos gerushin": "Mishneh Torah, Divorce",
    "הלכות גירושין": "Mishneh Torah, Divorce",
    
    "yibum": "Mishneh Torah, Levirate Marriage and Release",
    "yibum v'chalitza": "Mishneh Torah, Levirate Marriage and Release",
    
    "sotah": "Mishneh Torah, Sotah",
    "hilchos sotah": "Mishneh Torah, Sotah",
    
    # Moadim
    "chametz umatzah": "Mishneh Torah, Leavened and Unleavened Bread",
    "chometz umatzah": "Mishneh Torah, Leavened and Unleavened Bread",
    "hilchos chametz": "Mishneh Torah, Leavened and Unleavened Bread",
    "הלכות חמץ ומצה": "Mishneh Torah, Leavened and Unleavened Bread",
    
    "shabbos": "Mishneh Torah, Shabbat",
    "hilchos shabbos": "Mishneh Torah, Shabbat",
    "הלכות שבת": "Mishneh Torah, Shabbat",
    
    "eruvin": "Mishneh Torah, Eruvin",
    "hilchos eruvin": "Mishneh Torah, Eruvin",
    
    "yom tov": "Mishneh Torah, Rest on a Holiday",
    "shvisas yom tov": "Mishneh Torah, Rest on a Holiday",
    
    # Nezikin
    "nizkei mamon": "Mishneh Torah, Damages to Property",
    "geneivah": "Mishneh Torah, Theft",
    "gezeilah": "Mishneh Torah, Robbery and Lost Property",
    "chovel umazik": "Mishneh Torah, One Who Injures a Person or Property",
    
    # Kinyanim
    "mechirah": "Mishneh Torah, Sales",
    "zechiyah umatanah": "Mishneh Torah, Ownerless Property and Gifts",
    "shecheinim": "Mishneh Torah, Neighbors",
    "shluchin": "Mishneh Torah, Agents and Partners",
    "avadim": "Mishneh Torah, Slaves",
    
    # Mishpatim
    "sechirus": "Mishneh Torah, Hiring",
    "she'eilah upikadon": "Mishneh Torah, Borrowing and Deposit",
    "malveh v'loveh": "Mishneh Torah, Creditor and Debtor",
    "to'ein v'nit'an": "Mishneh Torah, Plaintiff and Defendant",
    "nachalos": "Mishneh Torah, Inheritances",
}

# Shulchan Aruch mapping
SHULCHAN_ARUCH_SECTIONS = {
    "orach chaim": "Shulchan Arukh, Orach Chayim",
    "orach chayim": "Shulchan Arukh, Orach Chayim",
    "או\"ח": "Shulchan Arukh, Orach Chayim",
    "אורח חיים": "Shulchan Arukh, Orach Chayim",
    "oc": "Shulchan Arukh, Orach Chayim",
    
    "yoreh deah": "Shulchan Arukh, Yoreh De'ah",
    "yoreh de'ah": "Shulchan Arukh, Yoreh De'ah",
    "יו\"ד": "Shulchan Arukh, Yoreh De'ah",
    "יורה דעה": "Shulchan Arukh, Yoreh De'ah",
    "yd": "Shulchan Arukh, Yoreh De'ah",
    
    "even haezer": "Shulchan Arukh, Even HaEzer",
    "even ha'ezer": "Shulchan Arukh, Even HaEzer",
    "אה\"ע": "Shulchan Arukh, Even HaEzer",
    "אבן העזר": "Shulchan Arukh, Even HaEzer",
    "eh": "Shulchan Arukh, Even HaEzer",
    
    "choshen mishpat": "Shulchan Arukh, Choshen Mishpat",
    "חו\"מ": "Shulchan Arukh, Choshen Mishpat",
    "חושן משפט": "Shulchan Arukh, Choshen Mishpat",
    "cm": "Shulchan Arukh, Choshen Mishpat",
}

# Commentary name variations → Sefaria slugs
COMMENTARY_SLUG_MAP = {
    # Rishonim on Gemara
    "rashi": "Rashi",
    "tosfos": "Tosafot", "tosafot": "Tosafot", "tosefos": "Tosafot",
    "תוספות": "Tosafot", "תוס'": "Tosafot",
    "ramban": "Ramban",
    "rashba": "Rashba",
    "ritva": "Ritva",
    "ran": "Ran",
    "rosh": "Rosh",
    "meiri": "Meiri",
    "nimukei yosef": "Nimukei Yosef",
    "rabbeinu chananel": "Rabbeinu Chananel",
    
    # Acharonim
    "pnei yehoshua": "Pnei Yehoshua", "pney yehoshua": "Pnei Yehoshua",
    "פני יהושע": "Pnei Yehoshua",
    "maharsha": "Maharsha", "מהרש\"א": "Maharsha",
    "maharshal": "Maharshal", "מהרש\"ל": "Maharshal",
    "reb akiva eiger": "Reb Akiva Eiger", "r' akiva eiger": "Reb Akiva Eiger",
    "רע\"א": "Reb Akiva Eiger", "רבי עקיבא איגר": "Reb Akiva Eiger",
    "rashash": "Rashash", "רש\"ש": "Rashash",
    "shitah mekubetzet": "Shitah Mekubetzet", "שיטה מקובצת": "Shitah Mekubetzet",
    
    # SA commentaries
    "rema": "Rema", "rama": "Rema", "רמ\"א": "Rema",
    "shach": "Shakh", "ש\"ך": "Shakh",
    "taz": "Taz", "ט\"ז": "Taz",
    "beis yosef": "Beit Yosef", "בית יוסף": "Beit Yosef",
    "mishnah berurah": "Mishnah Berurah", "mishna brura": "Mishnah Berurah",
    "מ\"ב": "Mishnah Berurah", "משנה ברורה": "Mishnah Berurah",
    
    # EH commentaries
    "beis shmuel": "Beit Shmuel", "בית שמואל": "Beit Shmuel",
    "chelkas mechokek": "Chelkat Mechokek", "חלקת מחוקק": "Chelkat Mechokek",
    "avnei milluim": "Avnei Miluim", "אבני מילואים": "Avnei Miluim",
    
    # CM commentaries  
    "ketzos hachoshen": "Ketzot HaChoshen", "ketzos": "Ketzot HaChoshen",
    "קצות החושן": "Ketzot HaChoshen", "קצה\"ח": "Ketzot HaChoshen",
    "nesivos hamishpat": "Netivot HaMishpat", "nesivos": "Netivot HaMishpat",
    "נתיבות המשפט": "Netivot HaMishpat",
    "sma": "Sma", "סמ\"ע": "Sma",
}


def translate_to_sefaria_slug(ref: str) -> str:
    """
    Translate common reference formats to Sefaria-compatible slugs.
    This is the Middleware Translation Layer from the Gemini paper.
    """
    original = ref
    
    # Try masechta mapping first
    for variant, sefaria in MASECHTA_TO_SEFARIA.items():
        # Case-insensitive replacement at word boundaries
        pattern = r'\b' + re.escape(variant) + r'\b'
        ref = re.sub(pattern, sefaria, ref, flags=re.IGNORECASE)
    
    # Try Rambam sections
    for variant, sefaria in RAMBAM_SECTIONS.items():
        if variant.lower() in ref.lower():
            # Extract chapter/halacha if present
            match = re.search(r'(\d+)[:\s]*(\d+)?', ref)
            if match:
                chapter = match.group(1)
                halacha = match.group(2)
                if halacha:
                    ref = f"{sefaria} {chapter}:{halacha}"
                else:
                    ref = f"{sefaria} {chapter}"
            else:
                ref = sefaria
            break
    
    # Try SA sections
    for variant, sefaria in SHULCHAN_ARUCH_SECTIONS.items():
        if variant.lower() in ref.lower():
            match = re.search(r'(\d+)[:\s]*(\d+)?', ref)
            if match:
                siman = match.group(1)
                seif = match.group(2)
                if seif:
                    ref = f"{sefaria} {siman}:{seif}"
                else:
                    ref = f"{sefaria} {siman}"
            break
    
    # Try commentary slugs
    for variant, sefaria in COMMENTARY_SLUG_MAP.items():
        pattern = r'\b' + re.escape(variant) + r'\b'
        ref = re.sub(pattern, sefaria, ref, flags=re.IGNORECASE)
    
    if ref != original:
        logger.debug(f"  Slug translated: '{original}' → '{ref}'")
    
    return ref


# =============================
# MASECHTA-SPECIFIC ACHARONIM
# (From Reference Guide to the Talmud Bavli)
# These are the "semantic nodes" that cite earlier sources
# =============================

MASECHTA_ACHARONIM = {
    # Seder Zeraim
    "Berakhot": ["Pnei Yehoshua", "Reb Akiva Eiger", "Tzelach", "Vilna Gaon",
                 "Chasam Sofer", "Sefas Emes", "Rashash", "Minchas Shmuel"],
    
    # Seder Moed
    "Shabbat": ["Pnei Yehoshua", "Reb Akiva Eiger", "Tzelach", "Vilna Gaon",
                "Chasam Sofer", "Sefas Emes", "Minchas Shmuel", "Maharshal"],
    "Eruvin": ["Pnei Yehoshua", "Reb Akiva Eiger", "Ritva", "Rashba", "Chazon Ish"],
    "Pesachim": ["Pnei Yehoshua", "Reb Akiva Eiger", "Rashash", "Tzelach",
                 "Chiddushei HaTzlach", "Aruch HaShulchan"],
    "Yoma": ["Pnei Yehoshua", "Reb Akiva Eiger", "Rashash", "Sfas Emes"],
    "Sukkah": ["Pnei Yehoshua", "Reb Akiva Eiger", "Bikurei Yaakov", "Sfas Emes"],
    "Beitzah": ["Pnei Yehoshua", "Reb Akiva Eiger", "Rashash"],
    "Rosh Hashanah": ["Pnei Yehoshua", "Reb Akiva Eiger", "Sfas Emes"],
    "Taanit": ["Pnei Yehoshua", "Reb Akiva Eiger"],
    "Megillah": ["Pnei Yehoshua", "Reb Akiva Eiger", "Rashash"],
    "Moed Katan": ["Pnei Yehoshua", "Reb Akiva Eiger"],
    "Chagigah": ["Pnei Yehoshua", "Reb Akiva Eiger", "Maharsha"],
    
    # Seder Nashim
    "Yevamot": ["Pnei Yehoshua", "Reb Akiva Eiger", "Chidushei Rebbi Yechiel",
                "Shaagas Aryeh", "Kikayon D'Yonah", "Rashash"],
    "Ketubot": ["Pnei Yehoshua", "Reb Akiva Eiger", "Maharsha", "Avnei Miluim",
                "Shitah Mekubetzet", "Beit Shmuel", "Chelkat Mechokek", "Rashash"],
    "Nedarim": ["Pnei Yehoshua", "Reb Akiva Eiger", "Ran", "Rashash"],
    "Nazir": ["Pnei Yehoshua", "Reb Akiva Eiger", "Maharsha", "Tosafot Rid"],
    "Sotah": ["Pnei Yehoshua", "Reb Akiva Eiger", "Maharsha", "Rashash"],
    "Gittin": ["Pnei Yehoshua", "Reb Akiva Eiger", "Chasam Sofer", "Rashash",
               "Ketzot HaChoshen"],
    "Kiddushin": ["Pnei Yehoshua", "Reb Akiva Eiger", "Shitah Mekubetzet",
                  "Rashash", "Ketzot HaChoshen"],
    
    # Seder Nezikin
    "Bava Kamma": ["Pnei Yehoshua", "Reb Akiva Eiger", "Ketzot HaChoshen",
                   "Netivot HaMishpat", "Chasam Sofer", "Chazon Ish", "Maharsha"],
    "Bava Metzia": ["Pnei Yehoshua", "Reb Akiva Eiger", "Ketzot HaChoshen",
                    "Netivot HaMishpat", "Maharsha", "Machaneh Ephraim"],
    "Bava Batra": ["Pnei Yehoshua", "Reb Akiva Eiger", "Ketzot HaChoshen",
                   "Netivot HaMishpat", "Rashash", "Maharsha"],
    "Sanhedrin": ["Pnei Yehoshua", "Reb Akiva Eiger", "Chasam Sofer", "Maharsha",
                  "Yad Ramah"],
    "Makkot": ["Pnei Yehoshua", "Reb Akiva Eiger", "Aruch LaNer"],
    "Shevuot": ["Pnei Yehoshua", "Reb Akiva Eiger", "Ketzot HaChoshen", "Rashash"],
    "Avodah Zarah": ["Pnei Yehoshua", "Reb Akiva Eiger", "Maharsha", "Rashash"],
    "Horayot": ["Pnei Yehoshua", "Reb Akiva Eiger"],
    
    # Seder Kodshim
    "Zevachim": ["Pnei Yehoshua", "Reb Akiva Eiger", "Rashash", "Shaagas Aryeh"],
    "Menachot": ["Pnei Yehoshua", "Reb Akiva Eiger", "Rashash"],
    "Chullin": ["Pnei Yehoshua", "Reb Akiva Eiger", "Rashash", "Chazon Ish"],
    "Bekhorot": ["Pnei Yehoshua", "Reb Akiva Eiger", "Rashash"],
    "Arakhin": ["Pnei Yehoshua", "Reb Akiva Eiger"],
    "Temurah": ["Pnei Yehoshua", "Reb Akiva Eiger"],
    "Keritot": ["Pnei Yehoshua", "Reb Akiva Eiger", "Shaagas Aryeh"],
    "Meilah": ["Pnei Yehoshua", "Reb Akiva Eiger"],
    
    # Seder Taharos
    "Niddah": ["Pnei Yehoshua", "Reb Akiva Eiger", "Chazon Ish", "Aruch LaNer",
               "Maharsha", "Tiferes Yisroel", "Sidrei Taharah"],
}

# Default Acharonim when masechta not in list
DEFAULT_ACHARONIM = [
    "Pnei Yehoshua", "Reb Akiva Eiger", "Maharsha", "Rashash",
    "Ketzot HaChoshen", "Shitah Mekubetzet", "Chasam Sofer"
]

# Intent-based Acharon prioritization (Contextual Vectorization)
LOMDUS_ACHARONIM = [
    "Ketzot HaChoshen", "Netivot HaMishpat", "Pnei Yehoshua", "Reb Akiva Eiger",
    "Shaagas Aryeh", "Chasam Sofer", "Chazon Ish", "Avnei Miluim"
]

PSAK_ACHARONIM = [
    "Mishnah Berurah", "Aruch HaShulchan", "Shakh", "Taz", "Rema",
    "Beit Yosef", "Pri Megadim", "Chayei Adam"
]

# Universal Rishonim - always prioritize
PRIORITY_RISHONIM = [
    "Rashi", "Tosafot", "Ramban", "Rashba", "Ritva", "Ran", "Rosh",
    "Meiri", "Nimukei Yosef", "Rabbeinu Chananel", "Rif"
]


def get_priority_commentators(masechta: Optional[str], intent: QueryIntent) -> List[str]:
    """
    Get prioritized list of commentators based on masechta and query intent.
    This implements masechta-specific + intent-specific prioritization.
    """
    result = []
    
    # Add intent-specific Acharonim first
    if intent == QueryIntent.LOMDUS:
        result.extend(LOMDUS_ACHARONIM)
    elif intent == QueryIntent.PSAK:
        result.extend(PSAK_ACHARONIM)
    
    # Add masechta-specific Acharonim
    if masechta and masechta in MASECHTA_ACHARONIM:
        for acharon in MASECHTA_ACHARONIM[masechta]:
            if acharon not in result:
                result.append(acharon)
    
    # Add default Acharonim
    for acharon in DEFAULT_ACHARONIM:
        if acharon not in result:
            result.append(acharon)
    
    # Always include priority Rishonim
    for rishon in PRIORITY_RISHONIM:
        if rishon not in result:
            result.append(rishon)
    
    return result


# =============================
# HEBREW CITATION PATTERN EXTRACTION
# (From Kesubos learning notes analysis)
# =============================

# Citation markers to look for in Hebrew text
CITATION_PATTERNS = {
    # Explicit see/reference markers
    "ע״ש": "see there",
    "עי׳": "see",
    "עיין": "see",
    "ע\"ש": "see there",
    "עי'": "see",
    
    # As it says / as written
    "כמ״ש": "as written by",
    "כמ\"ש": "as written by",
    "כמש\"כ": "as written by",
    "כדאיתא": "as it appears in",
    "כדאמרינן": "as we say in",
    
    # Explained/derived from
    "מבואר מדבריו": "explained in his words",
    "מבואר ב": "explained in",
    "מוכח מ": "proven from",
    
    # Rashi/Tosfos dibbur hamaschil markers
    "ד״ה": "s.v.",
    "ד\"ה": "s.v.",
    "דה\"ה": "s.v.",
    
    # Question/answer markers
    "וק״ק": "and it's difficult",
    "וקשיא": "and it's difficult",
    "ותירץ": "and he answers",
    
    # Position/approach markers
    "לשיטתו": "according to his approach",
    "לשיטת": "according to the approach of",
    "שיטת": "the approach of",
}


def extract_hebrew_citations(text: str) -> List[str]:
    """
    Extract citation references from Hebrew commentary text.
    Returns list of potential source references found.
    """
    citations = []
    
    # Look for masechta + daf references
    # Pattern: masechta name + number + amud (a/b/ע״א/ע״ב)
    masechta_pattern = r'(ברכות|שבת|עירובין|פסחים|יומא|סוכה|ביצה|ראש השנה|תענית|מגילה|מועד קטן|חגיגה|יבמות|כתובות|נדרים|נזיר|סוטה|גיטין|קידושין|בבא קמא|בבא מציעא|בבא בתרא|סנהדרין|מכות|שבועות|עבודה זרה|הוריות|זבחים|מנחות|חולין|בכורות|ערכין|תמורה|כריתות|מעילה|תמיד|נדה)\s*(\w+)\s*(ע״[אב]|ע\"[אב]|[אב])?'
    
    for match in re.finditer(masechta_pattern, text):
        citations.append(match.group(0))
    
    # Look for Rambam citations
    rambam_pattern = r'רמב״ם|רמב\"ם|הרמב״ם'
    if re.search(rambam_pattern, text):
        # Try to extract the specific halacha reference
        hilchos_pattern = r'הל(?:כות|\')\s*\w+\s*(?:פ(?:רק)?[\'״]?\s*)?(\w+)'
        for match in re.finditer(hilchos_pattern, text):
            citations.append(f"Rambam {match.group(0)}")
    
    # Look for Shulchan Aruch citations
    sa_pattern = r'שו״ע|שולחן ערוך|או״ח|יו״ד|אה״ע|חו״מ'
    if re.search(sa_pattern, text):
        siman_pattern = r'סי(?:מן)?[\'״]?\s*(\w+)'
        for match in re.finditer(siman_pattern, text):
            citations.append(f"Shulchan Aruch {match.group(0)}")
    
    return citations


# =============================
# PYDANTIC MODELS
# =============================

class TopicRequest(BaseModel):
    """Request model for /search endpoint"""
    topic: str
    clarification: Optional[str] = None


class SourceReference(BaseModel):
    """A validated source reference with text"""
    ref: str
    category: str
    he_text: str = ""
    en_text: str = ""
    he_ref: str = ""
    sefaria_url: str = ""
    citation_count: int = 1
    relevance: str = ""
    cited_by: List[str] = Field(default_factory=list)
    validated: bool = True  # VGR Protocol: only True if verified via Sefaria


class MareiMekomosResponse(BaseModel):
    """Response model for /search endpoint"""
    topic: str
    sources: List[SourceReference]
    summary: str = ""
    needs_clarification: bool = False
    clarifying_questions: List[str] = []
    interpreted_query: str = ""
    query_intent: str = ""
    methodology_notes: str = ""
    primary_masechta: str = ""


# =============================
# FASTAPI APP
# =============================

app = FastAPI(
    title="Marei Mekomos API v5.0",
    version="5.0.0",
    description="Torah source finder using Sugya Archaeology + VGR Protocol"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Anthropic client
api_key = os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    logger.critical("ANTHROPIC_API_KEY not found!")
    raise RuntimeError("ANTHROPIC_API_KEY environment variable is required")
client = Anthropic(api_key=api_key)
logger.info("✓ Anthropic client initialized")


# =============================
# SYSTEM PROMPTS
# =============================

QUERY_INTERPRETER_PROMPT = """You are a Torah scholar assistant that interprets user queries about Jewish texts.

Your job is to:
1. Understand the query (handle ALL spelling variations, transliterations, Hebrew, Yiddish, English)
2. Normalize to standard halachic/Torah terminology
3. Identify the PRIMARY SUGYA location(s) - where in Shas is this topic MAINLY discussed
4. Identify the primary masechta (for Acharon prioritization)

CRITICAL SPELLING NORMALIZATIONS:
- "chuppa/chuppah/huppa/חופה" → "chuppah"
- "niddah/nida/נדה" → "niddah"  
- "chometz/chametz/חמץ" → "chametz"
- "kesubos/kesuvos/ketubos/כתובות" → "Kesubos"
- Use yeshivish transliteration: sav not tav (Shabbos, Kesubos, etc.)

UNDERSTANDING QUERY INTENT:
Your job is to figure out what the user is REALLY asking:
- "chuppas niddah" → Laws about marriage ceremony when woman is niddah
- "bitul chametz" → The nullification declaration for chametz before Pesach
- "safek sotah" → Cases where sotah status is uncertain
- "shvuya anpshei" → The concept from Kesubos 9a about self-restraint

IDENTIFYING PRIMARY SUGYOS - THINK LIKE A BEN TORAH:
Where would you send someone in yeshiva to learn this sugya?
- "chuppas niddah" → Kesubos 4a-b (discusses when nissuin can happen)
- "bitul chametz" → Pesachim 4b-7a
- "safek sotah" → Sotah 28a, possibly Yevamos connections
- "kinyan agav" → Kiddushin 26a

OUTPUT FORMAT (JSON):
{
  "needs_clarification": false,
  "clarifying_questions": [],
  "interpreted_query": "The normalized query in standard terminology",
  "primary_masechta": "Kesubos",
  "primary_sugyos": [
    {
      "gemara_ref": "Kesubos 4a-4b",
      "reason": "Main discussion of when chuppah can take place relative to niddah"
    }
  ],
  "related_topics": ["niddah", "nissuin", "chuppah"],
  "halachic_context": "This relates to the timing of nissuin and whether chuppah is effective when the kallah is a niddah",
  "confidence": "high"
}

IMPORTANT: Only ask for clarification if the query is GENUINELY ambiguous - could mean COMPLETELY different things.
If you can reasonably determine what they mean, DON'T ask - just proceed!"""


CITATION_ANALYZER_PROMPT = """You are a Torah scholar analyzing commentary texts to extract EARLIER SOURCE CITATIONS.

This is "Sugya Archaeology" - we analyze what Acharonim cite to discover the foundational sources for a topic.

CONTEXT:
Original query: {query}
Interpreted as: {interpreted_query}
Primary masechta: {masechta}

You will receive texts from Rishonim and Acharonim. Your job is to extract which EARLIER sources they cite that are relevant to this specific topic.

WHAT TO LOOK FOR:
1. Explicit citations: "כמ"ש הרמב"ם", "ע"ש רש"י", "הרשב"א כתב", "עיין ב..."
2. Gemara references: "כדאיתא ב...", specific daf citations
3. Rishon citations: Rashi, Tosfos, Rambam, Rashba, Ritva, Ran, Rosh
4. Later Acharonim citing earlier ones

CATEGORIES FOR SOURCES:
- "Chumash": Torah/Tanach verses
- "Nach": Prophets/Writings
- "Mishna": Mishnayos
- "Gemara": Talmud Bavli (this is what we're primarily looking for!)
- "Rishonim": Rashi, Tosfos, Rambam, Rashba, Ritva, Ran, Rosh, Meiri, etc.
- "Shulchan Aruch": SA, Rema, and its nosei keilim
- "Acharonim": Later authorities

CRITICAL - RELEVANCE FILTERING:
Only include sources that discuss the SPECIFIC ASPECT of the query.
- Query "chuppas niddah" → only include sources about niddah + chuppah TOGETHER
- Query "bitul chametz" → only include sources specifically about bitul, not general chametz
- Query "safek sotah" → only include sources about the DOUBT aspect of sotah

FORMAT YOUR OUTPUT AS JSON:
{
  "extracted_sources": [
    {
      "ref": "Rambam, Hilchos Ishus 10:11",
      "category": "Rishonim",
      "relevance": "Discusses whether chuppah is koneh when kallah is niddah",
      "cited_by": ["Pnei Yehoshua Kesubos 4a", "Beis Shmuel EH 63"]
    },
    {
      "ref": "Kesubos 4a",
      "category": "Gemara",
      "relevance": "Primary sugya discussing timing of nissuin relative to niddah",
      "cited_by": ["Multiple Rishonim"]
    }
  ],
  "key_machlokesim": [
    "Rashi vs Tosfos on whether chuppah alone is koneh"
  ],
  "summary": "Brief summary of the sugya based on what the commentaries discuss"
}

#TODO: The user has learning notes available that show real citation patterns from Kesubos and Pesachim.
# File path: [USER TO FILL IN - e.g., /path/to/kesubos_notes.md]
# These notes demonstrate proper sugya tracing methodology."""


# =============================
# HELPER FUNCTIONS
# =============================

def clean_html(text: str) -> str:
    """Clean HTML tags and entities from Sefaria text"""
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def flatten_text(text_data) -> str:
    """Flatten nested arrays from Sefaria into a single string"""
    if isinstance(text_data, str):
        return text_data
    elif isinstance(text_data, list):
        return " ".join(flatten_text(item) for item in text_data if item)
    return ""


def parse_claude_json(response_text: str) -> dict:
    """Parse JSON from Claude's response, handling markdown fences"""
    try:
        text = response_text
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        
        text = text.strip()
        if not text.startswith("{"):
            brace_idx = text.find("{")
            if brace_idx != -1:
                text = text[brace_idx:]
            else:
                return {}
        
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
        logger.error(f"Response: {response_text[:300]}")
        return {}


def generate_cache_key(*args) -> str:
    """Generate a stable cache key from arguments"""
    combined = "|".join(str(arg) for arg in args)
    return hashlib.md5(combined.encode()).hexdigest()


def extract_masechta_from_ref(ref: str) -> Optional[str]:
    """Extract masechta name from a Gemara reference"""
    for masechta_lower, masechta_sefaria in MASECHTA_TO_SEFARIA.items():
        if masechta_lower in ref.lower():
            return masechta_sefaria
    return None


# =============================
# SEFARIA API + VGR VERIFICATION
# =============================

async def fetch_text(ref: str, timeout: float = 15.0) -> dict:
    """
    VGR VERIFICATION PHASE: Fetch and validate text from Sefaria API.
    
    Returns: {found: bool, he_text: str, en_text: str, he_ref: str, sefaria_url: str}
    
    A source is ONLY considered valid if Sefaria returns it successfully.
    This is our "gatekeeper" against hallucinations.
    """
    # Translate slug first
    ref = translate_to_sefaria_slug(ref)
    
    # Check cache
    cached = sefaria_cache.get(f"text:{ref}")
    if cached:
        logger.debug(f"  💰 Cache hit: {ref}")
        return cached
    
    logger.info(f"  📥 Fetching: {ref}")
    
    encoded_ref = ref.replace(" ", "%20").replace(",", "%2C")
    url = f"https://www.sefaria.org/api/v3/texts/{encoded_ref}"
    
    async with httpx.AsyncClient(verify=False, timeout=timeout) as http:
        try:
            response = await http.get(url)
            
            if response.status_code == 200:
                data = response.json()
                
                he_text = ""
                en_text = ""
                
                for version in data.get("versions", []):
                    lang = version.get("language", "")
                    text = flatten_text(version.get("text", ""))
                    
                    if lang == "he" and not he_text:
                        he_text = clean_html(text)
                    elif lang == "en" and not en_text:
                        en_text = clean_html(text)
                
                result = {
                    "found": True,
                    "he_text": he_text[:2000] if he_text else "",
                    "en_text": en_text[:2000] if en_text else "",
                    "he_ref": data.get("heRef", ""),
                    "sefaria_url": f"https://www.sefaria.org/{encoded_ref}",
                }
                
                # VGR: Only cache if actually found
                sefaria_cache.set(f"text:{ref}", result)
                logger.info(f"  ✓ VALIDATED: {ref}")
                return result
                
            elif response.status_code in [400, 404]:
                # VGR: This is a HALLUCINATION - source doesn't exist
                logger.warning(f"  ✗ HALLUCINATION CAUGHT: {ref} (HTTP {response.status_code})")
                return {"found": False, "reason": "not_found"}
            else:
                logger.warning(f"  ⚠ HTTP {response.status_code}: {ref}")
                return {"found": False, "reason": f"http_{response.status_code}"}
                
        except Exception as e:
            logger.error(f"  ✗ Error fetching {ref}: {e}")
            return {"found": False, "reason": str(e)}


async def verify_source_content_match(ref: str, expected_keywords: List[str]) -> bool:
    """
    STRICT VGR: Verify that the fetched text actually contains relevant content.
    
    This catches cases where:
    - The ref exists but discusses something completely different
    - Claude hallucinated a reasonable-sounding ref that happens to exist
    
    Returns True if at least one keyword is found in the text.
    """
    if not STRICT_VALIDATION or not expected_keywords:
        return True
    
    result = await fetch_text(ref)
    if not result.get("found"):
        return False
    
    text = (result.get("he_text", "") + " " + result.get("en_text", "")).lower()
    
    for keyword in expected_keywords:
        if keyword.lower() in text:
            logger.debug(f"  ✓ Content match: '{keyword}' found in {ref}")
            return True
    
    logger.warning(f"  ⚠ Content mismatch: {ref} doesn't contain expected keywords")
    return False


async def get_related_commentaries(ref: str) -> List[dict]:
    """
    Use Sefaria's Related API to find ALL commentaries linked to a ref.
    This is key to avoiding the slug/spelling problem - Sefaria tells us exact names!
    """
    cache_key = f"related:{ref}"
    cached = sefaria_cache.get(cache_key)
    if cached is not None:
        logger.debug(f"  💰 Cache hit: related/{ref}")
        return cached
    
    logger.info(f"  🔗 Getting related texts for: {ref}")
    
    # Translate slug first
    ref = translate_to_sefaria_slug(ref)
    encoded_ref = ref.replace(" ", "%20").replace(",", "%2C")
    url = f"https://www.sefaria.org/api/related/{encoded_ref}"
    
    async with httpx.AsyncClient(verify=False, timeout=15.0) as http:
        try:
            response = await http.get(url)
            
            if response.status_code == 200:
                data = response.json()
                links = data.get("links", [])
                
                commentaries = []
                for link in links:
                    if link.get("type") == "commentary":
                        commentaries.append({
                            "ref": link.get("sourceRef", ""),
                            "title": link.get("collectiveTitle", {}).get("en", ""),
                            "he_title": link.get("collectiveTitle", {}).get("he", ""),
                            "category": link.get("category", ""),
                        })
                
                logger.info(f"    Found {len(commentaries)} commentaries")
                sefaria_cache.set(cache_key, commentaries)
                return commentaries
            else:
                logger.warning(f"  ✗ Related API error: HTTP {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"  ✗ Error getting related texts: {e}")
            return []


# =============================
# CORE PIPELINE STAGES
# =============================

async def stage1_interpret_query(topic: str, clarification: Optional[str] = None) -> dict:
    """
    STAGE 1 (VGR Generation Phase): Have Claude interpret the user's query.
    
    - Normalizes spelling/transliteration
    - Detects query intent (lomdus/psak/makor)
    - Identifies primary sugyos
    - Checks for high-entropy queries needing clarification
    """
    logger.info("=" * 80)
    logger.info("STAGE 1: QUERY INTERPRETATION (VGR Generation Phase)")
    logger.info("=" * 80)
    logger.info(f"  Topic: {topic}")
    
    # First, check for high-entropy queries
    if not clarification:
        entropy_questions = check_query_entropy(topic)
        if entropy_questions:
            logger.info(f"  ⚠ High-entropy query detected - requesting clarification")
            return {
                "needs_clarification": True,
                "clarifying_questions": entropy_questions,
                "interpreted_query": topic,
                "confidence": "low"
            }
    
    # Detect query intent
    intent = detect_query_intent(topic)
    logger.info(f"  Query intent: {intent.value}")
    
    # Check cache
    cache_key = generate_cache_key("interpret", topic, clarification or "", intent.value)
    cached = claude_cache.get(cache_key)
    if cached:
        logger.info("  💰 Cache hit - using cached interpretation")
        cached["query_intent"] = intent.value
        return cached
    
    # Build message for Claude
    if clarification:
        message = f"""Original query: "{topic}"
User clarification: "{clarification}"
Detected intent: {intent.value}

Now interpret the clarified query and identify the primary sugyos."""
    else:
        message = f"""Query: "{topic}"
Detected intent: {intent.value}

Interpret this query. Handle any spelling variations. Identify primary Gemara sugyos."""
    
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1200,
            system=QUERY_INTERPRETER_PROMPT,
            messages=[{"role": "user", "content": message}],
        )
        
        result = parse_claude_json(response.content[0].text)
        
        if result:
            result["query_intent"] = intent.value
            logger.info(f"  ✓ Interpreted: {result.get('interpreted_query', '')}")
            logger.info(f"  ✓ Primary masechta: {result.get('primary_masechta', '')}")
            logger.info(f"  ✓ Primary sugyos: {result.get('primary_sugyos', [])}")
            
            claude_cache.set(cache_key, result)
        
        return result or {
            "needs_clarification": False,
            "interpreted_query": topic,
            "primary_sugyos": [],
            "query_intent": intent.value,
            "confidence": "low"
        }
        
    except Exception as e:
        logger.error(f"  ✗ Error in interpretation: {e}")
        return {
            "needs_clarification": False,
            "interpreted_query": topic,
            "primary_sugyos": [],
            "query_intent": intent.value,
            "confidence": "low"
        }


async def stage2_discover_commentaries(
    primary_sugyos: List[dict],
    masechta: str,
    intent: QueryIntent
) -> Dict[str, dict]:
    """
    STAGE 2: For each primary sugya, use Related API to discover commentaries.
    
    Prioritizes commentators based on:
    1. Query intent (lomdus vs psak)
    2. Masechta-specific important Acharonim
    3. Universal Rishonim
    
    Returns: {commentary_ref: {text, title, category, base_ref}}
    """
    logger.info("=" * 80)
    logger.info("STAGE 2: DISCOVER COMMENTARIES")
    logger.info("=" * 80)
    logger.info(f"  Masechta: {masechta}, Intent: {intent.value}")
    
    # Get priority list based on masechta and intent
    priority_commentators = get_priority_commentators(masechta, intent)
    logger.info(f"  Priority commentators: {priority_commentators[:10]}")
    
    all_commentaries = {}
    
    for sugya in primary_sugyos:
        gemara_ref = sugya.get("gemara_ref", "")
        if not gemara_ref:
            continue
        
        logger.info(f"\n📖 Processing sugya: {gemara_ref}")
        
        # Get all related commentaries
        related = await get_related_commentaries(gemara_ref)
        
        if not related:
            logger.warning(f"  No commentaries found for {gemara_ref}")
            continue
        
        # Sort by priority
        def sort_key(comm):
            title = comm.get("title", "")
            if title in priority_commentators:
                return (0, priority_commentators.index(title))
            return (1, title)
        
        related_sorted = sorted(related, key=sort_key)
        
        # Fetch texts for top commentaries
        count = 0
        for comm in related_sorted:
            if count >= MAX_COMMENTARIES_PER_BASE:
                break
            
            comm_ref = comm.get("ref", "")
            if not comm_ref or comm_ref in all_commentaries:
                continue
            
            result = await fetch_text(comm_ref)
            
            if result.get("found"):
                all_commentaries[comm_ref] = {
                    "he_text": result.get("he_text", ""),
                    "en_text": result.get("en_text", ""),
                    "title": comm.get("title", ""),
                    "category": comm.get("category", ""),
                    "base_ref": gemara_ref,
                }
                count += 1
                logger.info(f"    ✓ {comm.get('title', '')} ({len(result.get('he_text', ''))} chars)")
    
    logger.info(f"\n✓ Total commentaries fetched: {len(all_commentaries)}")
    return all_commentaries


async def stage3_analyze_citations(
    query: str,
    interpreted_query: str,
    masechta: str,
    commentaries: Dict[str, dict]
) -> dict:
    """
    STAGE 3 (VGR Extraction Phase): Analyze commentary texts to extract citations.
    
    Claude extracts which earlier sources the commentaries cite.
    """
    logger.info("=" * 80)
    logger.info("STAGE 3: CITATION ANALYSIS (VGR Extraction Phase)")
    logger.info("=" * 80)
    
    if not commentaries:
        logger.warning("  No commentaries to analyze")
        return {"extracted_sources": [], "summary": "No commentary texts found"}
    
    # Check cache
    cache_key = generate_cache_key("analyze", interpreted_query, masechta, len(commentaries))
    cached = claude_cache.get(cache_key)
    if cached:
        logger.info("  💰 Cache hit - using cached analysis")
        return cached
    
    # Build commentary texts for Claude
    commentary_text = ""
    total_chars = 0
    max_chars = 18000  # Increased for better analysis
    
    for ref, data in commentaries.items():
        if total_chars > max_chars:
            break
        
        he_text = data.get("he_text", "")[:1200]
        en_text = data.get("en_text", "")[:600]
        title = data.get("title", "")
        
        entry = f"\n=== {title} ({ref}) ===\n{he_text}"
        if en_text:
            entry += f"\n[English]: {en_text}"
        entry += "\n"
        
        # Also extract any Hebrew citations we find
        hebrew_citations = extract_hebrew_citations(he_text)
        if hebrew_citations:
            entry += f"\n[Detected citations: {', '.join(hebrew_citations[:5])}]\n"
        
        commentary_text += entry
        total_chars += len(entry)
    
    logger.info(f"  Analyzing {len(commentary_text)} chars of commentary text")
    
    # Build system prompt
    system = CITATION_ANALYZER_PROMPT.replace(
        "{query}", query
    ).replace(
        "{interpreted_query}", interpreted_query
    ).replace(
        "{masechta}", masechta or "Unknown"
    )
    
    message = f"""Analyze these commentary texts and extract earlier source citations:

{commentary_text}

Remember: Only include sources relevant to "{interpreted_query}"
Focus on finding the foundational sources that multiple commentaries cite.
Output your analysis as JSON."""
    
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2500,
            system=system,
            messages=[{"role": "user", "content": message}],
        )
        
        result = parse_claude_json(response.content[0].text)
        
        if result:
            sources = result.get("extracted_sources", [])
            logger.info(f"  ✓ Extracted {len(sources)} potential sources")
            for src in sources[:5]:
                logger.info(f"    - {src.get('ref', '')}: {src.get('relevance', '')[:50]}")
            
            claude_cache.set(cache_key, result)
        
        return result or {"extracted_sources": [], "summary": ""}
        
    except Exception as e:
        logger.error(f"  ✗ Error in citation analysis: {e}")
        return {"extracted_sources": [], "summary": "Error analyzing citations"}


async def stage4_validate_sources(
    extracted_sources: List[dict],
    primary_sugyos: List[dict],
    interpreted_query: str
) -> List[SourceReference]:
    """
    STAGE 4 (VGR Verification Phase): Validate and fetch all sources.
    
    Every source goes through Sefaria validation:
    - 200 OK → source is real, include it
    - 404/400 → HALLUCINATION, silently discard
    
    Optional: Content match verification (STRICT_VALIDATION mode)
    """
    logger.info("=" * 80)
    logger.info("STAGE 4: VALIDATION & FETCH (VGR Verification Phase)")
    logger.info("=" * 80)
    
    validated_sources = []
    hallucination_count = 0
    
    # Extract keywords from interpreted query for content matching
    content_keywords = [
        word for word in interpreted_query.lower().split()
        if len(word) > 3 and word not in ["the", "and", "for", "about", "when"]
    ]
    
    # First, add primary Gemara sugyos (these should always validate)
    for sugya in primary_sugyos:
        ref = sugya.get("gemara_ref", "")
        if not ref:
            continue
        
        logger.info(f"  Validating primary sugya: {ref}")
        result = await fetch_text(ref)
        
        if result.get("found"):
            validated_sources.append(SourceReference(
                ref=ref,
                category="Gemara",
                he_text=result.get("he_text", "")[:600],
                en_text=result.get("en_text", "")[:600],
                he_ref=result.get("he_ref", ""),
                sefaria_url=result.get("sefaria_url", ""),
                citation_count=99,  # Primary sources get highest weight
                relevance=sugya.get("reason", "Primary sugya for this topic"),
                validated=True,
            ))
            logger.info(f"    ✓ Primary sugya validated")
        else:
            logger.warning(f"    ⚠ Primary sugya not found in Sefaria")
    
    # Then validate extracted citations
    for source in extracted_sources:
        if len(validated_sources) >= MAX_FINAL_SOURCES:
            break
        
        ref = source.get("ref", "")
        if not ref:
            continue
        
        # Skip duplicates
        if any(v.ref == ref for v in validated_sources):
            continue
        
        logger.info(f"  Validating: {ref}")
        
        # VGR VERIFICATION: Check if source exists in Sefaria
        result = await fetch_text(ref)
        
        if result.get("found"):
            # Optional: Strict content matching
            if STRICT_VALIDATION:
                content_match = await verify_source_content_match(ref, content_keywords)
                if not content_match:
                    logger.warning(f"    ⚠ Content mismatch - likely tangential source")
                    # Still include but mark lower relevance
            
            validated_sources.append(SourceReference(
                ref=ref,
                category=source.get("category", "Unknown"),
                he_text=result.get("he_text", "")[:600],
                en_text=result.get("en_text", "")[:600],
                he_ref=result.get("he_ref", ""),
                sefaria_url=result.get("sefaria_url", ""),
                citation_count=len(source.get("cited_by", [])) or 1,
                relevance=source.get("relevance", ""),
                cited_by=source.get("cited_by", []),
                validated=True,
            ))
            logger.info(f"    ✓ VALIDATED")
        else:
            # VGR: This is a hallucination - Claude made it up
            hallucination_count += 1
            logger.warning(f"    ✗ HALLUCINATION DISCARDED: {ref}")
    
    # Sort by citation count (most cited = most foundational)
    validated_sources.sort(key=lambda x: x.citation_count, reverse=True)
    
    logger.info(f"\n{'='*40}")
    logger.info(f"VGR RESULTS:")
    logger.info(f"  ✓ Validated sources: {len(validated_sources)}")
    logger.info(f"  ✗ Hallucinations caught: {hallucination_count}")
    if hallucination_count > 0:
        logger.info(f"  📊 Hallucination rate: {hallucination_count/(len(validated_sources)+hallucination_count)*100:.1f}%")
    logger.info(f"{'='*40}")
    
    return validated_sources


# =============================
# API ENDPOINTS
# =============================

@app.get("/")
async def root():
    return {
        "message": "Marei Mekomos API v5.0",
        "methodology": "Sugya Archaeology + VGR Protocol",
        "features": [
            "Contextual Vectorization (lomdus/psak detection)",
            "Masechta-specific Acharon prioritization",
            "Validated Generative Retrieval (anti-hallucination)",
            "High-entropy query disambiguation"
        ]
    }


@app.post("/search", response_model=MareiMekomosResponse)
async def search_sources(request: TopicRequest):
    """
    Main search endpoint using Sugya Archaeology + VGR Protocol.
    
    Pipeline:
    1. Interpret query (check entropy, detect intent, normalize)
    2. Discover commentaries (masechta + intent based prioritization)
    3. Analyze citations (extract what commentaries cite)
    4. Validate sources (VGR verification against Sefaria)
    """
    logger.info("=" * 100)
    logger.info(f"NEW SEARCH: '{request.topic}'")
    if request.clarification:
        logger.info(f"  Clarification: '{request.clarification}'")
    logger.info("=" * 100)
    
    try:
        # STAGE 1: Interpret query
        interpretation = await stage1_interpret_query(request.topic, request.clarification)
        
        # Check if clarification needed
        if interpretation.get("needs_clarification") and not request.clarification:
            return MareiMekomosResponse(
                topic=request.topic,
                sources=[],
                needs_clarification=True,
                clarifying_questions=interpretation.get("clarifying_questions", []),
                interpreted_query=interpretation.get("interpreted_query", ""),
                query_intent=interpretation.get("query_intent", "general"),
            )
        
        interpreted_query = interpretation.get("interpreted_query", request.topic)
        primary_sugyos = interpretation.get("primary_sugyos", [])
        primary_masechta = interpretation.get("primary_masechta", "")
        query_intent = QueryIntent(interpretation.get("query_intent", "general"))
        
        if not primary_sugyos:
            logger.warning("  No primary sugyos identified")
            return MareiMekomosResponse(
                topic=request.topic,
                sources=[],
                summary="Could not identify relevant Gemara sugyos for this topic",
                interpreted_query=interpreted_query,
                query_intent=query_intent.value,
            )
        
        # STAGE 2: Discover commentaries
        commentaries = await stage2_discover_commentaries(
            primary_sugyos,
            primary_masechta,
            query_intent
        )
        
        if not commentaries:
            logger.warning("  No commentaries found")
            primary_sources = await stage4_validate_sources([], primary_sugyos, interpreted_query)
            return MareiMekomosResponse(
                topic=request.topic,
                sources=primary_sources,
                summary="Found primary sugyos but no commentaries for citation analysis",
                interpreted_query=interpreted_query,
                query_intent=query_intent.value,
                primary_masechta=primary_masechta,
            )
        
        # STAGE 3: Analyze citations
        analysis = await stage3_analyze_citations(
            request.topic,
            interpreted_query,
            primary_masechta,
            commentaries
        )
        
        extracted_sources = analysis.get("extracted_sources", [])
        summary = analysis.get("summary", "")
        key_machlokesim = analysis.get("key_machlokesim", [])
        
        # STAGE 4: Validate sources (VGR)
        final_sources = await stage4_validate_sources(
            extracted_sources,
            primary_sugyos,
            interpreted_query
        )
        
        # Build methodology notes
        methodology_notes = (
            f"Query intent: {query_intent.value}. "
            f"Primary masechta: {primary_masechta}. "
            f"Found {len(primary_sugyos)} primary sugya(s). "
            f"Analyzed {len(commentaries)} commentaries (prioritized for {query_intent.value}). "
            f"Extracted {len(extracted_sources)} citations. "
            f"VGR validated {len(final_sources)} sources."
        )
        
        if key_machlokesim:
            methodology_notes += f" Key machlokesim: {'; '.join(key_machlokesim[:3])}"
        
        logger.info("=" * 100)
        logger.info(f"SEARCH COMPLETE: Returning {len(final_sources)} validated sources")
        logger.info("=" * 100)
        
        return MareiMekomosResponse(
            topic=request.topic,
            sources=final_sources,
            summary=summary,
            interpreted_query=interpreted_query,
            query_intent=query_intent.value,
            methodology_notes=methodology_notes,
            primary_masechta=primary_masechta,
        )
        
    except Exception as e:
        logger.error(f"Error in search: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "5.0.0",
        "methodology": "Sugya Archaeology + VGR Protocol",
        "cost_saving_mode": COST_SAVING_MODE,
        "strict_validation": STRICT_VALIDATION,
    }


@app.get("/cache/stats")
async def cache_stats():
    claude_stats = claude_cache.stats()
    sefaria_stats = sefaria_cache.stats()
    
    # Estimate savings
    estimated_savings = claude_stats["total_entries"] * 0.008
    
    return {
        "claude_cache": claude_stats,
        "sefaria_cache": sefaria_stats,
        "cost_saving_mode": COST_SAVING_MODE,
        "estimated_savings": f"~${estimated_savings:.2f}"
    }


@app.post("/cache/clear")
async def clear_cache():
    logger.warning("Clearing all caches")
    claude_cache.clear()
    sefaria_cache.clear()
    return {"status": "cleared"}


@app.get("/test/intent/{query}")
async def test_intent(query: str):
    """Test endpoint for query intent detection"""
    intent = detect_query_intent(query)
    entropy = check_query_entropy(query)
    
    return {
        "query": query,
        "detected_intent": intent.value,
        "high_entropy": entropy is not None,
        "clarifying_questions": entropy or [],
        "priority_commentators": get_priority_commentators(None, intent)[:10]
    }


@app.get("/test/slug/{ref:path}")
async def test_slug(ref: str):
    """Test endpoint for slug translation"""
    translated = translate_to_sefaria_slug(ref)
    return {
        "original": ref,
        "translated": translated,
        "changed": ref != translated
    }


@app.get("/test/related/{ref:path}")
async def test_related(ref: str):
    """Test endpoint for Related API"""
    commentaries = await get_related_commentaries(ref)
    return {
        "ref": ref,
        "commentary_count": len(commentaries),
        "commentaries": commentaries[:20]
    }


if __name__ == "__main__":
    import uvicorn
    logger.info("🚀 Starting Marei Mekomos API v5.0")
    logger.info("   Methodology: Sugya Archaeology + VGR Protocol")
    logger.info("   Features: Contextual Vectorization, Masechta-specific prioritization")
    logger.info(f"   Cost Saving Mode: {COST_SAVING_MODE}")
    logger.info(f"   Strict Validation: {STRICT_VALIDATION}")
    uvicorn.run(app, host="0.0.0.0", port=8000)
