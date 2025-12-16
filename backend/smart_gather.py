"""
Smart Sefaria Data Gathering V2 - Multi-Layer Meta-Term Detection
===================================================================

4-LAYER DEFENSE SYSTEM:
  Layer A: Expanded Dictionary (100+ Hebrew/Aramaic meta-terms)
  Layer C: Pattern Detection (construct forms, prefixes, morphology)
  Layer D: Statistical Heuristic (hit distribution analysis)
  Layer B: Claude Fallback (last resort for edge cases)

PHILOSOPHY:
  - Meta-terms describe HOW a topic is discussed (שיטה, סברא, מחלוקת)
  - Substantive terms are the ACTUAL TOPIC (ביטול חמץ, חזקת הגוף)
  - We want to find primary sugya based on SUBSTANTIVE terms, not meta

FIXES IN THIS VERSION:
  - Filter out Yerushalmi (Jerusalem Talmud) - prefer Bavli
  - Validate that constructed refs are for Bavli, not Yerushalmi
  - Better masechta extraction that handles Yerushalmi refs
"""

import logging
import re
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum

# Import from MASTER knowledge base
from tools.torah_authors_master import (
    is_author,
    get_author_matches,
    disambiguate_author,
    get_sefaria_ref,
    normalize_text,
)

logger = logging.getLogger(__name__)


# ==============================================================================
#  LAYER A: EXPANDED META-TERMS DICTIONARY
# ==============================================================================
# Comprehensive list from research document + common usage patterns
# This catches ~90% of meta-terms

META_TERMS_HEBREW: Set[str] = {
    # ==========================================
    # OPINION / APPROACH TERMS
    # ==========================================
    'שיטה', 'שיטות', 'שיטת',           # shittah - approach/method
    'דעה', 'דעות', 'דעת',              # de'ah - opinion
    'סברא', 'סברה', 'סברות',           # sevara - reasoning
    'לדעת', 'לשיטת',                   # "according to opinion/approach of"
    'כדעת', 'כשיטת',                   # "like the opinion/approach of"
    'אליבא', 'אליבה',                  # "according to" (Aramaic)
    
    # ==========================================
    # DISPUTE / DEBATE TERMS  
    # ==========================================
    'מחלוקת', 'מחלוקות',               # machloket - dispute
    'פלוגתא', 'פלוגתות',               # plugta - dispute (Aramaic)
    'חולקים', 'חולק', 'נחלקו',          # disagree
    'מחלוקתם',                         # their dispute
    
    # ==========================================
    # REASONING / RATIONALE TERMS
    # ==========================================
    'טעם', 'טעמא', 'טעמים', 'טעמי',     # ta'am - reason
    'נימוק', 'נימוקים',                 # nimuk - justification
    'סיבה', 'סיבות',                   # sibah - cause
    'הסבר', 'הסברים',                  # hesber - explanation
    'יסוד', 'יסודות', 'יסודי',          # yesod - foundation
    
    # ==========================================
    # LAW / HALACHA TERMS (generic)
    # ==========================================
    'דין', 'דינים', 'דיני', 'דינא',     # din - law/judgment
    'הלכה', 'הלכות', 'הלכתא',           # halacha - law
    'פסק', 'פסקים', 'פסיקה',            # psak - ruling
    'איסור', 'איסורים', 'איסורי',       # issur - prohibition (can be meta or substantive)
    'היתר', 'היתרים',                  # heter - permission
    
    # ==========================================
    # RULE / PRINCIPLE TERMS
    # ==========================================
    'כלל', 'כללים', 'כללי', 'כללא',     # klal - rule
    'עיקר', 'עיקרים', 'עיקרי',          # ikar - principle
    'יסוד', 'יסודות', 'יסודי',          # yesod - foundation
    'גדר', 'גדרים', 'גדרי',             # geder - parameter/scope
    
    # ==========================================
    # SOURCE / PROOF TERMS
    # ==========================================
    'מקור', 'מקורות', 'מקורו',          # makor - source
    'ראיה', 'ראיות', 'ראיית',           # ra'ayah - proof
    'הוכחה', 'הוכחות',                 # hokhakha - proof
    'אסמכתא',                          # asmakhta - supporting reference
    'סמך', 'סמיכה',                    # basis/support
    
    # ==========================================
    # EXPLANATION / INTERPRETATION TERMS
    # ==========================================
    'פירוש', 'פירושים', 'פירושו', 'פירושא',  # perush - interpretation
    'ביאור', 'ביאורים', 'ביאורו',            # bi'ur - explanation
    'פשט', 'פשטות', 'פשוטו',                 # pshat - plain meaning
    'משמעות', 'משמעותו',                    # meaning
    'הבנה', 'הבנת', 'הבנתו',                 # understanding
    
    # ==========================================
    # COMPARISON / DISTINCTION TERMS
    # ==========================================
    'חילוק', 'חילוקים', 'חילוקי',       # chiluk - distinction
    'הבדל', 'הבדלים', 'הבדלי',          # hevdel - difference
    'סתירה', 'סתירות', 'סתירת',         # stira - contradiction
    'דמיון',                           # similarity
    'השוואה',                          # comparison
    
    # ==========================================
    # DEFINITION / CHARACTERIZATION TERMS
    # ==========================================
    'הגדרה', 'הגדרות', 'הגדרת',         # hagdara - definition
    'גדר', 'גדרים', 'גדרי',             # geder - parameter
    'תוכן', 'תכנים',                   # content
    'מהות', 'מהותו',                   # essence
    
    # ==========================================
    # QUESTION / CHALLENGE TERMS
    # ==========================================
    'שאלה', 'שאלות', 'שאלת',            # she'elah - question
    'קושיא', 'קושיה', 'קושיות', 'קושיית',  # kushya - challenge
    'קשה', 'קשיא',                      # difficult/challenge
    'תמיהה', 'תמיהות',                  # wonder/puzzle
    'ספק', 'ספקות', 'ספיקא',            # safek - doubt
    'בעיה', 'בעיות', 'בעיא',            # problem/question
    
    # ==========================================
    # ANSWER / RESOLUTION TERMS
    # ==========================================
    'תרוץ', 'תירוץ', 'תירוצים', 'תרוצים',  # terutz - answer
    'תשובה', 'תשובות',                     # teshuvah - answer
    'יישוב', 'יישובים',                    # resolution
    'אוקימתא',                             # okimta - establishing interpretation
    'פירוקא',                              # piruka - resolution (Aramaic)
    
    # ==========================================
    # CONCLUSION / OUTCOME TERMS
    # ==========================================
    'מסקנה', 'מסקנות', 'מסקנא', 'מסקנת',   # maskana - conclusion
    'הלכתא',                               # hilkheta - the law is
    'תיובתא',                              # tiyuvta - refutation
    'נפקא מינה', 'נפקותא',                 # nafka mina - practical difference
    
    # ==========================================
    # REFERENCE / DISCOURSE TERMS
    # ==========================================
    'דברי', 'דבריו', 'דבריהם',          # divrei - words of
    'לשון', 'לשונו', 'לשונות',          # lashon - language/wording
    'עניין', 'ענין', 'ענייני', 'עניינים',  # inyan - matter/topic
    'נושא', 'נושאים',                   # noseh - subject
    'סוגיא', 'סוגיה', 'סוגיות',          # sugya - topic (but can be substantive)
    
    # ==========================================
    # STRUCTURAL / ORGANIZATIONAL TERMS
    # ==========================================
    'משנה', 'משניות',                   # Mishnah (structural reference)
    'גמרא', 'גמרות',                    # Gemara (structural reference)
    'ברייתא', 'ברייתות',                # Braita
    'תנא', 'תנאי', 'תנאים',             # Tanna
    'אמורא', 'אמוראי', 'אמוראים',        # Amora
    
    # ==========================================
    # COMMON TALMUDIC DISCOURSE MARKERS
    # ==========================================
    'למאי', 'למה',                      # for what purpose
    'מנא', 'מנין', 'מנלן',              # from where (source)
    'היכי', 'איך',                      # how
    'מאי', 'מה',                        # what
    'אמאי',                             # why
}

# Additional meta-term roots for pattern matching (Layer C)
META_TERM_ROOTS: Set[str] = {
    'שיט', 'דע', 'סבר', 'טעמ', 'נימוק', 'כלל', 'עיקר',
    'מקור', 'ראי', 'פירוש', 'ביאור', 'חילוק', 'הבדל',
    'הגדר', 'גדר', 'שאל', 'קושי', 'תרוץ', 'תירוץ', 'מסקנ',
}


# ==============================================================================
#  LAYER C: PATTERN DETECTION (Morphological Analysis)
# ==============================================================================

CONSTRUCT_PREFIXES = {'ל', 'ב', 'כ', 'מ', 'ש', 'ו', 'ה'}
CONSTRUCT_SUFFIXES = {'ת', 'י', 'ו', 'ם'}  # smichut, plural, possessive


def analyze_construct_form(term: str) -> Tuple[bool, str]:
    """
    Analyze if term is a construct form of a meta-term.
    
    Examples:
        "לדעת" → (True, "prefix 'ל' + meta root 'דעת'")
        "בשיטת" → (True, "prefix 'ב' + meta root 'שיטת'")
        "דיני" → (True, "meta root 'דין' + construct suffix 'י'")
    
    Returns:
        (is_meta_construct, reason)
    """
    if len(term) < 2:
        return False, ""
    
    # Check prefix + meta root
    if term[0] in CONSTRUCT_PREFIXES:
        remainder = term[1:]
        # Check if remainder is in META_TERMS_HEBREW
        if remainder in META_TERMS_HEBREW:
            return True, f"prefix '{term[0]}' + meta term '{remainder}'"
        # Check if remainder starts with a meta root
        for root in META_TERM_ROOTS:
            if remainder.startswith(root):
                return True, f"prefix '{term[0]}' + meta root '{root}'"
    
    # Check meta root + suffix
    for root in META_TERM_ROOTS:
        if term.startswith(root) and len(term) > len(root):
            suffix = term[len(root):]
            if suffix in CONSTRUCT_SUFFIXES or suffix in {'ות', 'ים', 'ות'}:
                return True, f"meta root '{root}' + suffix '{suffix}'"
    
    return False, ""


def detect_plural_abstract(term: str) -> Tuple[bool, str]:
    """
    Detect plural forms of abstract nouns (often meta-terms).
    
    Examples:
        "שיטות" → True (plural of שיטה)
        "דעות" → True (plural of דעה)
        "הלכות" → True (plural of הלכה)
    """
    # Common abstract plural endings
    abstract_plural_endings = ['ות', 'יות', 'אות']
    
    for ending in abstract_plural_endings:
        if term.endswith(ending):
            # Check if singular might be a meta-term
            singular_guess = term[:-len(ending)] + 'ה'
            if singular_guess in META_TERMS_HEBREW:
                return True, f"plural of meta-term '{singular_guess}'"
            singular_guess2 = term[:-len(ending)] + 'א'
            if singular_guess2 in META_TERMS_HEBREW:
                return True, f"plural of meta-term '{singular_guess2}'"
    
    return False, ""


# ==============================================================================
#  LAYER D: STATISTICAL HEURISTIC (Hit Distribution Analysis)
# ==============================================================================

@dataclass
class HitDistribution:
    """Statistics about how a term's hits are distributed."""
    term: str
    total_hits: int
    masechta_count: int
    max_concentration: float  # Highest % in any single masechta
    top_masechta: str
    distribution_score: float  # 0=concentrated, 1=spread


def analyze_hit_distribution(term: str, sefaria_data: Dict) -> HitDistribution:
    """
    Analyze how a term's Sefaria hits are distributed across masechtot.
    
    Generic meta-terms spread evenly; substantive terms cluster.
    
    Example:
        "שיטה" → 10k hits, spread across 15 masechtot (~5% each) → GENERIC
        "ביטול חמץ" → 1.7k hits, 70% in Pesachim → SUBSTANTIVE
    """
    total_hits = sefaria_data.get('total_hits', 0)
    masechtot = sefaria_data.get('masechtot', {})
    
    if not masechtot or total_hits == 0:
        return HitDistribution(
            term=term,
            total_hits=total_hits,
            masechta_count=0,
            max_concentration=0.0,
            top_masechta="",
            distribution_score=0.5
        )
    
    # Calculate concentration
    total_in_masechtot = sum(masechtot.values())
    if total_in_masechtot == 0:
        total_in_masechtot = 1  # Avoid division by zero
    
    # Find max concentration
    max_count = max(masechtot.values())
    max_masechta = max(masechtot.items(), key=lambda x: x[1])[0]
    max_concentration = max_count / total_in_masechtot
    
    # Distribution score: 1 - max_concentration
    # High score = spread out (generic)
    # Low score = concentrated (substantive)
    distribution_score = 1.0 - max_concentration
    
    return HitDistribution(
        term=term,
        total_hits=total_hits,
        masechta_count=len(masechtot),
        max_concentration=max_concentration,
        top_masechta=max_masechta,
        distribution_score=distribution_score
    )


def is_statistically_generic(stats: HitDistribution) -> Tuple[bool, float, str]:
    """
    Determine if hit distribution suggests a generic/meta term.
    
    Thresholds:
        - High hit count (5000+)
        - Many masechtot (10+)
        - Low concentration (<35% in top masechta)
    
    Returns:
        (is_generic, confidence, reason)
    """
    # Not enough data
    if stats.total_hits < 100:
        return False, 0.3, "Insufficient hits for statistical analysis"
    
    # Very high hits + spread out = likely generic
    if stats.total_hits >= 5000 and stats.masechta_count >= 10 and stats.max_concentration < 0.35:
        return True, 0.85, f"High hits ({stats.total_hits}), spread across {stats.masechta_count} masechtot"
    
    # Moderate hits but very spread out
    if stats.total_hits >= 1000 and stats.distribution_score > 0.7:
        return True, 0.70, f"Hits spread evenly (distribution score: {stats.distribution_score:.2f})"
    
    # Concentrated = NOT generic
    if stats.max_concentration > 0.50:
        return False, 0.80, f"Concentrated in {stats.top_masechta} ({stats.max_concentration:.0%})"
    
    # Ambiguous
    return False, 0.50, "Ambiguous distribution"


# ==============================================================================
#  TERM CLASSIFICATION
# ==============================================================================

class TermType(Enum):
    AUTHOR = "author"
    META = "meta"
    SUBSTANTIVE = "substantive"
    UNKNOWN = "unknown"


@dataclass
class TermClassification:
    term: str
    term_type: TermType
    confidence: float
    detection_layer: str  # 'dictionary', 'pattern', 'statistical', 'author_kb', 'default'
    reason: str
    needs_claude_verification: bool = False


def classify_term(
    term: str,
    sefaria_data: Optional[Dict] = None,
    skip_statistical: bool = False
) -> TermClassification:
    """
    Classify a Hebrew term using 4-layer detection.
    
    Order:
        1. Author KB check
        2. Layer A: Dictionary lookup
        3. Layer C: Pattern detection
        4. Layer D: Statistical heuristic (if sefaria_data provided)
        5. Default: Assume substantive
    
    Args:
        term: Hebrew term to classify
        sefaria_data: Optional Sefaria search results for statistical analysis
        skip_statistical: Skip Layer D (for initial classification)
    
    Returns:
        TermClassification with type, confidence, and reason
    """
    # ==========================================
    # Check Author KB first
    # ==========================================
    if is_author(term):
        return TermClassification(
            term=term,
            term_type=TermType.AUTHOR,
            confidence=0.95,
            detection_layer='author_kb',
            reason=f"Found in Torah Authors KB"
        )
    
    # ==========================================
    # Layer A: Dictionary lookup
    # ==========================================
    if term in META_TERMS_HEBREW:
        return TermClassification(
            term=term,
            term_type=TermType.META,
            confidence=0.95,
            detection_layer='dictionary',
            reason=f"Found in meta-terms dictionary"
        )
    
    # ==========================================
    # Layer C: Pattern detection
    # ==========================================
    is_construct, construct_reason = analyze_construct_form(term)
    if is_construct:
        return TermClassification(
            term=term,
            term_type=TermType.META,
            confidence=0.80,
            detection_layer='pattern',
            reason=f"Construct form: {construct_reason}"
        )
    
    is_plural, plural_reason = detect_plural_abstract(term)
    if is_plural:
        return TermClassification(
            term=term,
            term_type=TermType.META,
            confidence=0.75,
            detection_layer='pattern',
            reason=f"Abstract plural: {plural_reason}"
        )
    
    # ==========================================
    # Layer D: Statistical heuristic
    # ==========================================
    if not skip_statistical and sefaria_data:
        stats = analyze_hit_distribution(term, sefaria_data)
        is_generic, confidence, reason = is_statistically_generic(stats)
        
        if is_generic:
            return TermClassification(
                term=term,
                term_type=TermType.META,
                confidence=confidence,
                detection_layer='statistical',
                reason=reason,
                needs_claude_verification=True  # Flag for verification
            )
    
    # ==========================================
    # No meta indicators found - assume substantive
    # ==========================================
    return TermClassification(
        term=term,
        term_type=TermType.SUBSTANTIVE,
        confidence=0.70,  # Not 100% sure
        detection_layer='default',
        reason='No meta indicators detected - treating as substantive'
    )


def classify_terms(
    hebrew_terms: List[str],
    sefaria_results: Optional[Dict[str, Dict]] = None
) -> Tuple[List[str], List[str], List[str], List[TermClassification]]:
    """
    Classify multiple Hebrew terms.
    
    Args:
        hebrew_terms: List of Hebrew terms
        sefaria_results: Optional dict of {term: sefaria_data}
    
    Returns:
        (authors, substantive_concepts, meta_terms, all_classifications)
    """
    authors = []
    substantive = []
    meta = []
    all_classifications = []
    
    for term in hebrew_terms:
        sefaria_data = sefaria_results.get(term) if sefaria_results else None
        classification = classify_term(term, sefaria_data)
        all_classifications.append(classification)
        
        if classification.term_type == TermType.AUTHOR:
            authors.append(term)
        elif classification.term_type == TermType.META:
            meta.append(term)
        else:
            substantive.append(term)
    
    return authors, substantive, meta, all_classifications


# ==============================================================================
#  MASECHTA MAPPING (for reference construction)
# ==============================================================================

MASECHTA_NAMES = {
    # Seder Zeraim
    'ברכות': 'Berakhot',
    # Seder Moed
    'שבת': 'Shabbat', 'עירובין': 'Eruvin', 'פסחים': 'Pesachim',
    'יומא': 'Yoma', 'סוכה': 'Sukkah', 'ביצה': 'Beitzah',
    'ראש השנה': 'Rosh Hashanah', 'תענית': 'Taanit', 'מגילה': 'Megillah',
    'מועד קטן': 'Moed Katan', 'חגיגה': 'Chagigah',
    # Seder Nashim
    'יבמות': 'Yevamot', 'כתובות': 'Ketubot', 'נדרים': 'Nedarim',
    'נזיר': 'Nazir', 'סוטה': 'Sotah', 'גיטין': 'Gittin', 'קידושין': 'Kiddushin',
    # Seder Nezikin
    'בבא קמא': 'Bava Kamma', 'בבא מציעא': 'Bava Metzia', 
    'בבא בתרא': 'Bava Batra', 'סנהדרין': 'Sanhedrin', 'מכות': 'Makkot',
    'שבועות': 'Shevuot', 'עבודה זרה': 'Avodah Zarah', 'הוריות': 'Horayot',
    # Seder Kodashim
    'זבחים': 'Zevachim', 'מנחות': 'Menachot', 'חולין': 'Chullin',
    'בכורות': 'Bekhorot', 'ערכין': 'Arakhin', 'תמורה': 'Temurah',
    'כריתות': 'Keritot', 'מעילה': 'Meilah',
    # Seder Taharot
    'נידה': 'Niddah',
}

MASECHTA_NAMES_EN = set(MASECHTA_NAMES.values())

# Yerushalmi indicators to SKIP
YERUSHALMI_INDICATORS = [
    'Jerusalem Talmud',
    'Yerushalmi',
    'Palestinian Talmud',
    'Talmud Yerushalmi',
    'JT ',  # Sometimes abbreviated
]


def is_yerushalmi_ref(ref: str) -> bool:
    """Check if a reference is to Yerushalmi (Jerusalem Talmud)."""
    ref_lower = ref.lower()
    for indicator in YERUSHALMI_INDICATORS:
        if indicator.lower() in ref_lower:
            return True
    return False


def extract_masechta_from_ref(ref: str) -> Optional[str]:
    """Extract masechta name from a Sefaria reference."""
    # First, strip Yerushalmi indicator if present
    ref = re.sub(r'^Jerusalem Talmud ', '', ref)
    ref = re.sub(r'^Yerushalmi ', '', ref)
    
    # Strip commentary prefixes
    ref = re.sub(r'^(Rashi|Tosafot|Ran|Rashba|Ritva|Meiri) on ', '', ref)
    
    sorted_masechtot = sorted(MASECHTA_NAMES_EN, key=len, reverse=True)
    for masechta_en in sorted_masechtot:
        if masechta_en in ref:
            return masechta_en
    return None


def extract_daf_from_ref(ref: str) -> Optional[str]:
    """Extract daf from reference."""
    match = re.search(r'(\d+[ab])', ref)
    return match.group(1) if match else None


def clean_sugya_ref(ref: str) -> str:
    """Clean a sugya reference to just masechta + daf."""
    # Remove Yerushalmi prefix first
    ref = re.sub(r'^Jerusalem Talmud ', '', ref)
    ref = re.sub(r'^Yerushalmi ', '', ref)
    
    ref = ref.split(' on ')[-1]
    masechta = extract_masechta_from_ref(ref)
    daf = extract_daf_from_ref(ref)
    if masechta and daf:
        return f"{masechta} {daf}"
    return ref


# ==============================================================================
#  SMART GATHERING - MAIN FUNCTION
# ==============================================================================

MODERN_WORKS_TO_SKIP = [
    'Peninei Halakhah', 'Mishnat Eretz Yisrael', 'Kovetz',
    'Encyclopedia', 'Contemporary', 'Modern',
]


def extract_primary_sugya_from_results(
    concept: str,
    sefaria_results: Dict,
    prefer_gemara: bool = True,
    prefer_bavli: bool = True  # NEW: Prefer Bavli over Yerushalmi
) -> Optional[str]:
    """
    Extract primary sugya reference from Sefaria search results.
    
    FIXED: Now filters out Yerushalmi (Jerusalem Talmud) references.
    The Rishonim primarily commented on Bavli, so we want Bavli refs.
    
    Args:
        concept: The concept being searched
        sefaria_results: Sefaria search results
        prefer_gemara: Prefer Gemara over commentaries
        prefer_bavli: Prefer Bavli over Yerushalmi (NEW)
    """
    top_refs = sefaria_results.get('top_refs', [])
    masechtot = sefaria_results.get('masechtot', {})
    
    if not top_refs:
        return None
    
    primary_masechta = None
    if masechtot:
        primary_masechta = max(masechtot.items(), key=lambda x: x[1])[0]
    
    bavli_gemara_refs = []
    yerushalmi_refs = []
    commentary_refs = []
    
    for ref in top_refs[:30]:  # Check more refs to find Bavli
        # Skip modern works
        if any(modern in ref for modern in MODERN_WORKS_TO_SKIP):
            continue
        
        # Check if Yerushalmi
        if is_yerushalmi_ref(ref):
            yerushalmi_refs.append(ref)
            logger.debug(f"[EXTRACT-SUGYA] Skipping Yerushalmi: {ref}")
            continue
        
        # Check if commentary
        is_commentary = any(comm in ref for comm in [
            'Rashi on', 'Tosafot on', 'Ran on', 'Rashba on',
            'Meiri on', 'Ritva on', 'Nimukei Yosef on'
        ])
        
        masechta = extract_masechta_from_ref(ref)
        
        if not is_commentary and masechta:
            # It's a Gemara ref (Bavli since we filtered Yerushalmi)
            if primary_masechta and masechta == primary_masechta:
                bavli_gemara_refs.insert(0, ref)
            else:
                bavli_gemara_refs.append(ref)
        elif masechta:
            commentary_refs.append(ref)
    
    # Prefer Bavli Gemara
    if prefer_bavli and bavli_gemara_refs:
        selected = bavli_gemara_refs[0]
        logger.info(f"[EXTRACT-SUGYA] Selected Bavli: {selected}")
        return selected
    
    # Fall back to commentary refs (which should also be on Bavli)
    if commentary_refs:
        # Extract the base sugya from commentary
        for comm_ref in commentary_refs:
            if not is_yerushalmi_ref(comm_ref):
                base_ref = comm_ref.split(' on ')[-1] if ' on ' in comm_ref else comm_ref
                logger.info(f"[EXTRACT-SUGYA] Extracted from commentary: {base_ref}")
                return base_ref
    
    # Last resort: Yerushalmi (if nothing else)
    if yerushalmi_refs and not prefer_bavli:
        logger.warning(f"[EXTRACT-SUGYA] Only Yerushalmi found: {yerushalmi_refs[0]}")
        return yerushalmi_refs[0]
    
    logger.warning(f"[EXTRACT-SUGYA] No valid Bavli sugya found for '{concept}'")
    return None


async def gather_sefaria_data_smart(
    hebrew_terms: List[str],
    original_query: str,
    sefaria_client
) -> Dict:
    """
    Intelligently gather Sefaria data with 4-layer meta-term detection.
    
    Process:
    1. Initial classification (Layer A + C)
    2. Search substantive terms FIRST
    3. Search meta-terms for context
    4. Apply Layer D statistical analysis
    5. Construct author references
    
    FIXED: Now filters out Yerushalmi and validates refs.
    
    Args:
        hebrew_terms: List of Hebrew terms from Step 1
        original_query: Original English/transliterated query
        sefaria_client: Instance of SefariaClient
    
    Returns:
        Dict with data for each term
    """
    logger.info("=" * 70)
    logger.info("[SMART-GATHER-V2] Starting with 4-layer meta-term detection")
    logger.info("=" * 70)
    
    # ==========================================
    # PHASE 0: Initial Classification (Layer A + C only)
    # ==========================================
    authors, substantive, meta, classifications = classify_terms(hebrew_terms)
    
    logger.info(f"[SMART-GATHER-V2] Initial classification:")
    logger.info(f"  Authors: {authors}")
    logger.info(f"  Substantive: {substantive}")  
    logger.info(f"  Meta: {meta}")
    
    for c in classifications:
        logger.debug(f"  {c.term}: {c.term_type.value} ({c.detection_layer}, {c.confidence:.0%})")
    
    # Process author metadata
    author_metadata = {}
    for term in authors:
        matches = get_author_matches(term)
        if len(matches) == 1:
            author_metadata[term] = matches[0]
        elif len(matches) > 1:
            best = disambiguate_author(term, context=original_query)
            if best:
                author_metadata[term] = best
            else:
                author_metadata[term] = {'ambiguous': True, 'matches': matches}
    
    sefaria_data = {}
    primary_sugya = None
    primary_masechta = None
    
    # ==========================================
    # PHASE 1: Search SUBSTANTIVE concepts first
    # ==========================================
    logger.info(f"[SMART-GATHER-V2] Phase 1: Searching {len(substantive)} substantive concepts")
    
    for concept in substantive:
        logger.info(f"[SMART-GATHER-V2] Searching substantive: '{concept}'")
        
        try:
            result = await sefaria_client.search(concept, size=100)
            
            total_hits = result.total_hits
            top_refs = [hit.ref for hit in result.hits][:30]  # Get more refs
            
            categories = {}
            masechtot = {}
            
            for hit in result.hits[:100]:
                cat = hit.category
                categories[cat] = categories.get(cat, 0) + 1
                
                # Only count Bavli masechtot for primary sugya selection
                if not is_yerushalmi_ref(hit.ref):
                    masechta = extract_masechta_from_ref(hit.ref)
                    if masechta:
                        masechtot[masechta] = masechtot.get(masechta, 0) + 1
            
            # Run Layer D statistical check
            stat_analysis = analyze_hit_distribution(concept, {
                'total_hits': total_hits,
                'masechtot': masechtot
            })
            is_generic, gen_conf, gen_reason = is_statistically_generic(stat_analysis)
            
            if is_generic:
                logger.warning(f"[SMART-GATHER-V2] Layer D flagged '{concept}' as potentially generic")
                logger.warning(f"  Reason: {gen_reason}")
                # Move to meta, but with lower confidence
                meta.append(concept)
                substantive.remove(concept)
                sefaria_data[concept] = {
                    'type': 'meta_term',
                    'flagged_by': 'statistical',
                    'total_hits': total_hits,
                    'masechtot': masechtot,
                    'statistical_reason': gen_reason,
                }
                continue
            
            # Extract primary sugya (FIXED: now filters Yerushalmi)
            sugya = extract_primary_sugya_from_results(
                concept,
                {'top_refs': top_refs, 'masechtot': masechtot},
                prefer_bavli=True  # IMPORTANT: Prefer Bavli
            )
            
            if sugya and not primary_sugya:
                primary_sugya = clean_sugya_ref(sugya)
                primary_masechta = extract_masechta_from_ref(primary_sugya)
                logger.info(f"[SMART-GATHER-V2] ⭐ PRIMARY SUGYA (Bavli): {primary_sugya}")
            
            sefaria_data[concept] = {
                'type': 'concept',
                'is_substantive': True,
                'total_hits': total_hits,
                'top_refs': [r for r in top_refs[:10] if not is_yerushalmi_ref(r)],  # Filter Yerushalmi
                'primary_sugya': sugya,
                'masechtot': masechtot,
            }
            
        except Exception as e:
            logger.error(f"[SMART-GATHER-V2] Search failed for '{concept}': {e}")
            sefaria_data[concept] = {'type': 'concept', 'error': str(e)}
    
    # ==========================================
    # PHASE 2: Search meta-terms (for context only)
    # ==========================================
    if meta:
        logger.info(f"[SMART-GATHER-V2] Phase 2: Searching {len(meta)} meta-terms (context only)")
        
        for term in meta:
            if term in sefaria_data:  # Already searched if flagged by Layer D
                continue
                
            try:
                result = await sefaria_client.search(term, size=50)
                
                sefaria_data[term] = {
                    'type': 'meta_term',
                    'is_substantive': False,
                    'total_hits': result.total_hits,
                    'top_refs': [h.ref for h in result.hits][:5],
                    'note': 'Meta-term - not used for primary sugya'
                }
                
            except Exception as e:
                sefaria_data[term] = {'type': 'meta_term', 'error': str(e)}
    
    # ==========================================
    # PHASE 3: Construct author references
    # ==========================================
    if authors and primary_sugya:
        logger.info(f"[SMART-GATHER-V2] Phase 3: Constructing author refs for {primary_sugya}")
        
        # VALIDATION: Ensure primary_sugya is Bavli, not Yerushalmi
        if is_yerushalmi_ref(primary_sugya):
            logger.error(f"[SMART-GATHER-V2] Primary sugya is Yerushalmi! Cannot construct Rishon refs.")
            for author_term in authors:
                sefaria_data[author_term] = {
                    'type': 'author',
                    'construction_failed': True,
                    'reason': 'Primary sugya is Yerushalmi - Rishonim commented on Bavli',
                    'based_on_sugya': primary_sugya,
                }
        else:
            for author_term in authors:
                author_data = author_metadata.get(author_term)
                
                if author_data and author_data.get('ambiguous'):
                    sefaria_data[author_term] = {
                        'type': 'author',
                        'needs_clarification': True,
                        'matches': [{'name_en': m['primary_name_en']} for m in author_data['matches']]
                    }
                    continue
                
                if not author_data:
                    sefaria_data[author_term] = {'type': 'author', 'error': 'No metadata'}
                    continue
                
                # Check coverage
                coverage = author_data.get('masechta_coverage')
                primary_masechtot = author_data.get('primary_masechtot', [])
                
                covers = True
                if coverage in ('select', 'minimal'):
                    if primary_masechta and primary_masechta not in primary_masechtot:
                        covers = False
                
                if not covers:
                    sefaria_data[author_term] = {
                        'type': 'author',
                        'coverage_issue': True,
                        'coverage_note': f"{author_data['primary_name_en']} may not cover {primary_masechta}",
                        'attempted_sugya': primary_sugya,
                        'author_info': {
                            'name_en': author_data['primary_name_en'],
                            'primary_masechtot': primary_masechtot,
                        }
                    }
                    continue
                
                # Construct reference (will be for Bavli since we validated)
                constructed_ref = get_sefaria_ref(author_term, primary_sugya)
                
                if constructed_ref:
                    sefaria_data[author_term] = {
                        'type': 'author',
                        'constructed_ref': constructed_ref,
                        'based_on_sugya': primary_sugya,
                        'author_info': {
                            'name_en': author_data['primary_name_en'],
                            'name_he': author_data['primary_name_he'],
                        }
                    }
                else:
                    sefaria_data[author_term] = {
                        'type': 'author',
                        'construction_failed': True,
                        'based_on_sugya': primary_sugya,
                    }
    
    elif authors and not primary_sugya:
        logger.warning("[SMART-GATHER-V2] Authors found but no sugya!")
        for author_term in authors:
            sefaria_data[author_term] = {
                'type': 'author',
                'needs_clarification': True,
                'reason': 'No sugya found'
            }
    
    logger.info("=" * 70)
    logger.info(f"[SMART-GATHER-V2] Complete. Primary sugya: {primary_sugya}")
    logger.info("=" * 70)
    
    return sefaria_data


# ==============================================================================
#  HELPER: Format Sefaria data for Claude
# ==============================================================================

def _format_matches(matches: List[Dict]) -> str:
    """Format author matches for Claude prompt."""
    if not matches:
        return "[]"
    return ", ".join(m.get('name_en', '?') for m in matches)


def format_for_claude(sefaria_data: Dict) -> str:
    """
    Format gathered Sefaria data into a readable string for Claude.
    
    Claude needs to see:
    1. Which concepts have clear primary sugyot
    2. Which authors can be looked up
    3. Which terms are meta/context vs substantive
    """
    if not sefaria_data:
        return "No Sefaria data available."
    
    lines = []
    lines.append("=== SEFARIA DATA ===")
    lines.append("")
    
    for term, data in sefaria_data.items():
        if not isinstance(data, dict):
            continue
        
        entry_type = data.get('type', 'unknown')
        
        # -----------------------
        # Author handling
        # -----------------------
        if entry_type == 'author':
            name_en = (
                data.get('author_info', {}).get('name_en')
                or data.get('author_name')
                or "Unknown"
            )
            lines.append(f"--- {term} (AUTHOR: {name_en}) ---")
            
            if data.get('constructed_ref'):
                lines.append(f"  Commentary reference: {data['constructed_ref']}")
            if data.get('based_on_sugya'):
                lines.append(f"  Based on sugya: {data['based_on_sugya']}")
            if data.get('coverage_issue'):
                note = data.get('coverage_note', 'Coverage issue detected')
                lines.append(f"  Coverage issue: {note}")
                if data.get('attempted_sugya'):
                    lines.append(f"  Attempted sugya: {data['attempted_sugya']}")
            if data.get('needs_clarification'):
                lines.append("  Needs clarification: multiple authors match")
                matches = data.get('matches', [])
                if matches:
                    lines.append(f"  Matches: {_format_matches(matches)}")
            if data.get('construction_failed'):
                reason = data.get('reason', 'Unknown reason')
                lines.append(f"  Construction failed: {reason}")
            if data.get('error'):
                lines.append(f"  Error: {data['error']}")
            
            lines.append("")
            continue
        
        # -----------------------
        # Concept handling
        # -----------------------
        if entry_type == 'concept':
            lines.append(f"--- {term} (CONCEPT) ---")
            if 'total_hits' in data:
                lines.append(f"  Total hits: {data.get('total_hits')}")
            primary = data.get('primary_sugya')
            if primary:
                lines.append(f"  Primary sugya: {clean_sugya_ref(primary)}")
            top_refs = data.get('top_refs') or data.get('categories')
            if top_refs:
                if isinstance(top_refs, list):
                    preview = ", ".join(top_refs[:5])
                    lines.append(f"  Top refs: {preview}")
                elif isinstance(top_refs, dict) and data.get('masechtot'):
                    top_masechtot = sorted(
                        data['masechtot'].items(),
                        key=lambda item: item[1],
                        reverse=True
                    )[:3]
                    preview = ", ".join(f"{m}({c})" for m, c in top_masechtot)
                    lines.append(f"  Top masechtot: {preview}")
            if data.get('note'):
                lines.append(f"  Note: {data['note']}")
            if data.get('error'):
                lines.append(f"  Error: {data['error']}")
            
            lines.append("")
            continue
        
        # -----------------------
        # Meta-term / context handling
        # -----------------------
        if entry_type == 'meta_term':
            lines.append(f"--- {term} (META TERM) ---")
            if 'total_hits' in data:
                lines.append(f"  Total hits: {data.get('total_hits')}")
            if data.get('note'):
                lines.append(f"  Note: {data['note']}")
            top_refs = data.get('top_refs')
            if top_refs:
                preview = ", ".join(top_refs[:3])
                lines.append(f"  Example refs: {preview}")
            if data.get('error'):
                lines.append(f"  Error: {data['error']}")
            
            lines.append("")
            continue
        
        # -----------------------
        # Fallback
        # -----------------------
        lines.append(f"--- {term} ---")
        for key, value in data.items():
            lines.append(f"  {key}: {value}")
        lines.append("")
    
    return "\n".join(lines).strip()


# Backwards compatibility: older callers expect this name.
# Keep it as a thin wrapper to the current formatter.
def format_smart_gather_for_claude(sefaria_data: Dict) -> str:
    return format_for_claude(sefaria_data)


# ==============================================================================
#  TESTING
# ==============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("SMART GATHER V2 - 4-LAYER META-TERM DETECTION TEST")
    print("=" * 70)
    
    # Test Layer A: Dictionary
    print("\n📚 LAYER A: Dictionary Lookup")
    print("-" * 50)
    layer_a_tests = [
        ('שיטה', True),
        ('סברא', True),
        ('מחלוקת', True),
        ('ביטול חמץ', False),
        ('חזקת הגוף', False),
        ('פסחים', False),
    ]
    
    for term, expected_meta in layer_a_tests:
        result = classify_term(term, skip_statistical=True)
        is_meta = result.term_type == TermType.META
        status = "✓" if is_meta == expected_meta else "✗"
        print(f"  {status} '{term}': {result.term_type.value} ({result.detection_layer})")
    
    # Test Yerushalmi filtering
    print("\n🏛️ YERUSHALMI FILTERING")
    print("-" * 50)
    test_refs = [
        ("Jerusalem Talmud Pesachim 2:2:6:2", True),
        ("Pesachim 4b", False),
        ("Yerushalmi Berakhot 1:1", True),
        ("Rashi on Pesachim 4b", False),
        ("Ran on Jerusalem Talmud Pesachim", True),
    ]
    
    for ref, expected_yerushalmi in test_refs:
        is_yer = is_yerushalmi_ref(ref)
        status = "✓" if is_yer == expected_yerushalmi else "✗"
        print(f"  {status} '{ref}': {'Yerushalmi' if is_yer else 'Bavli'}")
    
    print("\n" + "=" * 70)
    print("Full term classification:")
    print("=" * 70)
    
    test_terms = ['רן', 'שיטה', 'ביטול חמץ', 'תוספות', 'רשי', 'דעת', 'חזקה']
    authors, subst, meta, all_class = classify_terms(test_terms)
    
    print(f"\nInput: {test_terms}")
    print(f"Authors: {authors}")
    print(f"Substantive: {subst}")
    print(f"Meta: {meta}")
