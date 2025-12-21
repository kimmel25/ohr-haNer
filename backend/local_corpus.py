"""
Local Corpus Handler for Sefaria Export JSON Files
===================================================

This module provides local search and citation extraction from the
Sefaria JSON export, eliminating the need for excessive API calls.

Structure expected:
    CORPUS_ROOT/
    ├── Halakhah/
    │   ├── Shulchan Arukh/
    │   │   ├── Shulchan Arukh, Orach Chayim/Hebrew/merged.json
    │   │   ├── Commentary/
    │   │   │   ├── Magen Avraham/Magen Avraham/Hebrew/merged.json
    │   │   │   ├── Mishna Berura/...
    │   │   │   └── ...
    │   ├── Tur/...
    │   ├── Mishneh Torah/...
    ├── Talmud/
    │   ├── Bavli/
    │   │   ├── Pesachim/Hebrew/merged.json
    │   │   └── ...
"""

import json
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any, Any
from dataclasses import dataclass, field
from collections import defaultdict
import hashlib

logger = logging.getLogger(__name__)


# ==============================================================================
#  CONFIGURATION
# ==============================================================================

# Default path - user should set this to their actual export location
DEFAULT_CORPUS_ROOT = Path("C:/Projects/Sefaria-Export/json")

# Sefarim paths relative to corpus root
SEFARIM_PATHS = {
    # Shulchan Aruch
    "sa_oc": "Halakhah/Shulchan Arukh/Shulchan Arukh, Orach Chayim/Hebrew/merged.json",
    "sa_yd": "Halakhah/Shulchan Arukh/Shulchan Arukh, Yoreh De'ah/Hebrew/merged.json",
    "sa_eh": "Halakhah/Shulchan Arukh/Shulchan Arukh, Even HaEzer/Hebrew/merged.json",
    "sa_cm": "Halakhah/Shulchan Arukh/Shulchan Arukh, Choshen Mishpat/Hebrew/merged.json",
    
    # Tur
    "tur_oc": "Halakhah/Tur/Tur, Orach Chaim/Hebrew/merged.json",
    "tur_yd": "Halakhah/Tur/Tur, Yoreh Deah/Hebrew/merged.json",
    "tur_eh": "Halakhah/Tur/Tur, Even HaEzer/Hebrew/merged.json",
    "tur_cm": "Halakhah/Tur/Tur, Choshen Mishpat/Hebrew/merged.json",
    
    # Rambam - Mishneh Torah has many sefarim, we'll handle dynamically
    "rambam_base": "Halakhah/Mishneh Torah",
}

# SA Commentary paths (relative to Shulchan Arukh/Commentary/)
SA_COMMENTARIES = {
    # Orach Chaim
    "magen_avraham": "Magen Avraham/Magen Avraham/Hebrew/merged.json",
    "mishna_berura": "Mishnah Berurah/Mishnah Berurah/Hebrew/merged.json",
    "taz_oc": "Turei Zahav/Turei Zahav/Hebrew/merged.json",
    "beer_hetev_oc": "Ba'er Hetev/Ba'er Hetev/Hebrew/merged.json",
    "beer_hagolah": "Be'er HaGolah/Be'er HaGolah/Hebrew/merged.json",
    "chok_yaakov": "Chok Yaakov/Chok Yaakov/Hebrew/merged.json",
    "eliyah_rabbah": "Eliyah Rabbah/Eliyah Rabbah/Hebrew/merged.json",
    "machatzit_hashekel": "Machatzit HaShekel/Machatzit HaShekel/Hebrew/merged.json",
    
    # Even HaEzer
    "chelkat_mechokek": "Chelkat Mechokek/Chelkat Mechokek/Hebrew/merged.json",
    "beit_shmuel": "Beit Shmuel/Beit Shmuel/Hebrew/merged.json",
    
    # Yoreh Deah
    "shach": "Siftei Kohen/Siftei Kohen/Hebrew/merged.json",
    "taz_yd": "Turei Zahav/Turei Zahav/Hebrew/merged.json",
    
    # Choshen Mishpat
    "sma": "Sefer Meirat Einayim/Sefer Meirat Einayim/Hebrew/merged.json",
    "ketzos": "Ketzot HaChoshen/Ketzot HaChoshen/Hebrew/merged.json",
    "nesivos": "Netivot HaMishpat, Beurim/Netivot HaMishpat, Beurim/Hebrew/merged.json",
}


# ==============================================================================
#  DATA STRUCTURES
# ==============================================================================

@dataclass
class LocalSearchHit:
    """A search hit from local corpus."""
    sefer: str           # e.g., "Shulchan Arukh, Orach Chayim"
    siman: int           # Siman number (1-indexed for display)
    seif: Optional[int]  # Se'if number if applicable
    text_snippet: str    # Matched text snippet
    ref: str             # Full reference string


@dataclass 
class GemaraCitation:
    """A gemara citation extracted from text."""
    masechta: str        # e.g., "Pesachim"
    daf: str             # e.g., "4b"
    source_ref: str      # Where this citation was found
    source_text: str     # The text containing the citation
    confidence: float    # How confident we are in this extraction


@dataclass
class SimanData:
    """Data about a siman including its nosei keilim."""
    sefer: str
    siman: int
    main_text: str
    nosei_keilim: Dict[str, str] = field(default_factory=dict)  # {author: text}
    gemara_citations: List[GemaraCitation] = field(default_factory=list)


# ==============================================================================
#  CITATION EXTRACTION PATTERNS
# ==============================================================================

# Hebrew masechta names and their English equivalents
MASECHTA_MAP = {
    # Seder Zeraim
    'ברכות': 'Berakhot',
    'פאה': 'Peah',
    'דמאי': 'Demai',
    'כלאים': 'Kilayim',
    'שביעית': 'Sheviit',
    'תרומות': 'Terumot',
    'מעשרות': 'Maasrot',
    'מעשר שני': 'Maaser Sheni',
    'חלה': 'Challah',
    'ערלה': 'Orlah',
    'ביכורים': 'Bikkurim',
    
    # Seder Moed
    'שבת': 'Shabbat',
    'עירובין': 'Eruvin',
    'פסחים': 'Pesachim',
    'שקלים': 'Shekalim',
    'יומא': 'Yoma',
    'סוכה': 'Sukkah',
    'ביצה': 'Beitzah',
    'ראש השנה': 'Rosh Hashanah',
    'תענית': 'Taanit',
    'מגילה': 'Megillah',
    'מועד קטן': 'Moed Katan',
    'חגיגה': 'Chagigah',
    
    # Seder Nashim
    'יבמות': 'Yevamot',
    'כתובות': 'Ketubot',
    'נדרים': 'Nedarim',
    'נזיר': 'Nazir',
    'סוטה': 'Sotah',
    'גיטין': 'Gittin',
    'קידושין': 'Kiddushin',
    
    # Seder Nezikin
    'בבא קמא': 'Bava Kamma',
    'בבא מציעא': 'Bava Metzia',
    'בבא בתרא': 'Bava Batra',
    'סנהדרין': 'Sanhedrin',
    'מכות': 'Makkot',
    'שבועות': 'Shevuot',
    'עבודה זרה': 'Avodah Zarah',
    'הוריות': 'Horayot',
    
    # Seder Kodshim
    'זבחים': 'Zevachim',
    'מנחות': 'Menachot',
    'חולין': 'Chullin',
    'בכורות': 'Bekhorot',
    'ערכין': 'Arakhin',
    'תמורה': 'Temurah',
    'כריתות': 'Keritot',
    'מעילה': 'Meilah',
    'תמיד': 'Tamid',
    'מדות': 'Middot',
    'קינים': 'Kinnim',
    
    # Seder Taharot
    'נדה': 'Niddah',
}

# Reverse map for English to Hebrew
MASECHTA_MAP_REVERSE = {v: k for k, v in MASECHTA_MAP.items()}

# Build regex pattern for masechta names
MASECHTA_PATTERN = '|'.join(re.escape(m) for m in MASECHTA_MAP.keys())

# Citation patterns
GEMARA_CITATION_PATTERNS = [
    # "בגמרא דף ד" or "בגמ' דף ד ע"א"
    rf'בגמ(?:רא|\')\s+(?:דף\s+)?(\d+)\s*(?:ע["\']?([אב]))?',
    
    # "בפסחים דף ד ע"א" - masechta + daf
    rf'ב({MASECHTA_PATTERN})\s+(?:דף\s+)?(\d+)\s*(?:ע["\']?([אב]))?',
    
    # "פסחים ד:" or "פסחים ד ע"א"
    rf'({MASECHTA_PATTERN})\s+(\d+)\s*(?::|ע["\']?([אב]))',
    
    # "כדאיתא בפסחים" or "עיין פסחים"
    rf'(?:כד(?:איתא|אמרינן)|עיין|ע\')\s+(?:ב)?({MASECHTA_PATTERN})\s+(?:דף\s+)?(\d+)?',
    
    # "בסוגיא דפסחים"
    rf'בסוגי[אה]\s+(?:ד)?({MASECHTA_PATTERN})\s+(?:דף\s+)?(\d+)?',
    
    # Abbreviated forms: "בפסח'" "בשב'"
    rf'ב(פסח|שב|עירוב|יומ|סוכ|ביצ|מגיל|חגיג|יבמו|כתובו|גיט|קידוש|ב"ק|ב"מ|ב"ב|סנהד|מכו|שבועו|ע"ז|חול|נד)[\'"]?\s+(?:דף\s+)?(\d+)',
]


def extract_gemara_citations(
    text: str, 
    source_ref: str,
    default_masechta: str = None
) -> List[GemaraCitation]:
    """
    Extract gemara citations from nosei keilim text.
    
    Args:
        text: The Hebrew text to scan
        source_ref: Reference string for where this text is from
        default_masechta: If only a daf is found, assume this masechta
    
    Returns:
        List of GemaraCitation objects
    """
    citations = []
    seen = set()  # Avoid duplicates
    
    # Clean HTML tags but preserve text
    clean_text = re.sub(r'<[^>]+>', ' ', text)
    
    for pattern in GEMARA_CITATION_PATTERNS:
        for match in re.finditer(pattern, clean_text):
            groups = match.groups()
            
            masechta_he = None
            daf_num = None
            amud = None
            
            # Parse based on pattern structure
            if len(groups) >= 2:
                # Try to identify masechta vs daf in the groups
                for g in groups:
                    if g is None:
                        continue
                    if g in MASECHTA_MAP:
                        masechta_he = g
                    elif g.isdigit():
                        daf_num = g
                    elif g in ('א', 'ב', 'a', 'b'):
                        amud = 'a' if g in ('א', 'a') else 'b'
            
            # Handle abbreviated masechta names
            if not masechta_he and groups[0]:
                abbrev = groups[0]
                abbrev_map = {
                    'פסח': 'פסחים',
                    'שב': 'שבת',
                    'עירוב': 'עירובין',
                    'יומ': 'יומא',
                    'סוכ': 'סוכה',
                    'ביצ': 'ביצה',
                    'מגיל': 'מגילה',
                    'חגיג': 'חגיגה',
                    'יבמו': 'יבמות',
                    'כתובו': 'כתובות',
                    'גיט': 'גיטין',
                    'קידוש': 'קידושין',
                    'ב"ק': 'בבא קמא',
                    'ב"מ': 'בבא מציעא',
                    'ב"ב': 'בבא בתרא',
                    'סנהד': 'סנהדרין',
                    'מכו': 'מכות',
                    'שבועו': 'שבועות',
                    'ע"ז': 'עבודה זרה',
                    'חול': 'חולין',
                    'נד': 'נדה',
                }
                masechta_he = abbrev_map.get(abbrev)
            
            # Use default masechta if we only found a daf
            if not masechta_he and daf_num and default_masechta:
                masechta_he = default_masechta
            
            if not masechta_he or not daf_num:
                continue
            
            # Convert to English masechta name
            masechta_en = MASECHTA_MAP.get(masechta_he, masechta_he)
            
            # Default amud to 'a' if not specified
            if not amud:
                amud = 'a'
            
            daf = f"{daf_num}{amud}"
            
            # Create unique key to avoid duplicates
            key = f"{masechta_en}_{daf}"
            if key in seen:
                continue
            seen.add(key)
            
            # Calculate confidence based on match quality
            confidence = 0.8
            if masechta_he in clean_text:  # Full masechta name appears
                confidence = 0.95
            if amud != 'a':  # Explicit amud mentioned
                confidence = min(confidence + 0.05, 1.0)
            
            citations.append(GemaraCitation(
                masechta=masechta_en,
                daf=daf,
                source_ref=source_ref,
                source_text=match.group(0),
                confidence=confidence
            ))
    
    return citations


# ==============================================================================
#  LOCAL CORPUS CLASS
# ==============================================================================

class LocalCorpus:
    """
    Handler for local Sefaria JSON export files.
    
    Provides:
    - Text search across SA/Tur/Rambam
    - Nosei keilim text retrieval
    - Gemara citation extraction
    """
    
    def __init__(self, corpus_root: Path = None):
        self.corpus_root = Path(corpus_root) if corpus_root else DEFAULT_CORPUS_ROOT
        self._cache: Dict[str, Any] = {}
        self._index_cache: Dict[str, List[Tuple[int, str]]] = {}  # topic -> [(siman, sefer)]
        
        logger.info(f"[LocalCorpus] Initialized with root: {self.corpus_root}")
    
    def _load_json(self, relative_path: str) -> Optional[Dict]:
        """Load and cache a JSON file."""
        if relative_path in self._cache:
            return self._cache[relative_path]
        
        full_path = self.corpus_root / relative_path
        
        if not full_path.exists():
            logger.warning(f"[LocalCorpus] File not found: {full_path}")
            return None
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self._cache[relative_path] = data
            logger.debug(f"[LocalCorpus] Loaded: {relative_path}")
            return data
        except Exception as e:
            logger.error(f"[LocalCorpus] Failed to load {full_path}: {e}")
            return None
    
    def _get_text_array(self, json_data: Dict) -> List:
        """Extract the text array from JSON data."""
        if not json_data:
            return []
        return json_data.get('text', [])
    
    def _flatten_text(self, text_item) -> str:
        """Flatten nested text arrays into a single string."""
        if text_item is None:
            return ''
        if isinstance(text_item, str):
            return text_item
        if isinstance(text_item, list):
            return ' '.join(self._flatten_text(t) for t in text_item if t)
        if isinstance(text_item, dict):
            # Some structures use dicts - flatten all values
            return ' '.join(self._flatten_text(v) for v in text_item.values() if v)
        return str(text_item)
    
    def search_sefer(
        self, 
        sefer_path: str, 
        query: str,
        sefer_name: str = None
    ) -> List[LocalSearchHit]:
        """
        Search for a query in a sefer.
        
        Args:
            sefer_path: Path to the JSON file
            query: Hebrew text to search for
            sefer_name: Display name for the sefer
        
        Returns:
            List of LocalSearchHit objects
        """
        data = self._load_json(sefer_path)
        if not data:
            return []
        
        text_array = self._get_text_array(data)
        sefer_name = sefer_name or data.get('title', sefer_path)
        hits = []
        
        try:
            # Handle both list and dict structures
            if isinstance(text_array, list):
                for siman_idx, siman_text in enumerate(text_array):
                    siman_num = siman_idx + 1  # 1-indexed
                    
                    flat_text = self._flatten_text(siman_text)
                    if query in flat_text:
                        # Extract snippet around the match
                        match_pos = flat_text.find(query)
                        start = max(0, match_pos - 50)
                        end = min(len(flat_text), match_pos + len(query) + 50)
                        snippet = flat_text[start:end]
                        
                        hits.append(LocalSearchHit(
                            sefer=sefer_name,
                            siman=siman_num,
                            seif=None,
                            text_snippet=snippet,
                            ref=f"{sefer_name} {siman_num}"
                        ))
            elif isinstance(text_array, dict):
                # Some sefarim use dict structure (e.g., by perek)
                for key, siman_text in text_array.items():
                    try:
                        siman_num = int(key) if str(key).isdigit() else 0
                    except (ValueError, TypeError):
                        siman_num = 0
                    
                    flat_text = self._flatten_text(siman_text)
                    if query in flat_text:
                        match_pos = flat_text.find(query)
                        start = max(0, match_pos - 50)
                        end = min(len(flat_text), match_pos + len(query) + 50)
                        snippet = flat_text[start:end]
                        
                        hits.append(LocalSearchHit(
                            sefer=sefer_name,
                            siman=siman_num,
                            seif=None,
                            text_snippet=snippet,
                            ref=f"{sefer_name} {key}"
                        ))
        except Exception as e:
            logger.warning(f"[LocalCorpus] Error searching {sefer_name}: {e}")
        
        return hits
    
    def search_shulchan_aruch(self, query: str) -> List[LocalSearchHit]:
        """Search all four chelkei Shulchan Aruch."""
        all_hits = []
        
        sa_paths = [
            (SEFARIM_PATHS["sa_oc"], "Shulchan Arukh, Orach Chayim"),
            (SEFARIM_PATHS["sa_yd"], "Shulchan Arukh, Yoreh De'ah"),
            (SEFARIM_PATHS["sa_eh"], "Shulchan Arukh, Even HaEzer"),
            (SEFARIM_PATHS["sa_cm"], "Shulchan Arukh, Choshen Mishpat"),
        ]
        
        for path, name in sa_paths:
            hits = self.search_sefer(path, query, name)
            all_hits.extend(hits)
            if hits:
                logger.info(f"[LocalCorpus] Found {len(hits)} hits in {name}")
        
        return all_hits
    
    def search_tur(self, query: str) -> List[LocalSearchHit]:
        """Search all four chelkei Tur."""
        all_hits = []
        
        tur_paths = [
            (SEFARIM_PATHS["tur_oc"], "Tur, Orach Chaim"),
            (SEFARIM_PATHS["tur_yd"], "Tur, Yoreh Deah"),
            (SEFARIM_PATHS["tur_eh"], "Tur, Even HaEzer"),
            (SEFARIM_PATHS["tur_cm"], "Tur, Choshen Mishpat"),
        ]
        
        for path, name in tur_paths:
            hits = self.search_sefer(path, query, name)
            all_hits.extend(hits)
            if hits:
                logger.info(f"[LocalCorpus] Found {len(hits)} hits in {name}")
        
        return all_hits
    
    def search_rambam(self, query: str) -> List[LocalSearchHit]:
        """Search Mishneh Torah (all hilchos)."""
        all_hits = []
        rambam_base = self.corpus_root / SEFARIM_PATHS["rambam_base"]
        
        if not rambam_base.exists():
            logger.warning(f"[LocalCorpus] Rambam directory not found: {rambam_base}")
            return []
        
        try:
            # Find all merged.json files under Mishneh Torah
            # Only search Hebrew files to avoid duplicates
            for json_file in rambam_base.rglob("merged.json"):
                try:
                    # Skip English versions to avoid duplicates
                    if "English" in str(json_file):
                        continue
                    
                    # Skip Commentary folder - we want the main Rambam text
                    if "Commentary" in str(json_file):
                        continue
                    
                    relative_path = str(json_file.relative_to(self.corpus_root))
                    
                    # Get sefer name from path - look for "Mishneh Torah, X" pattern
                    sefer_name = None
                    for part in json_file.parts:
                        if part.startswith("Mishneh Torah,"):
                            sefer_name = part.replace("Mishneh Torah, ", "")
                            break
                    
                    if not sefer_name:
                        # Fallback: use grandparent directory name
                        sefer_name = json_file.parent.parent.name
                    
                    hits = self.search_sefer(relative_path, query, sefer_name)
                    all_hits.extend(hits)
                    
                except Exception as e:
                    logger.debug(f"[LocalCorpus] Error searching Rambam file {json_file}: {e}")
                    continue
        
        except Exception as e:
            logger.warning(f"[LocalCorpus] Error iterating Rambam directory: {e}")
        
        if all_hits:
            logger.info(f"[LocalCorpus] Found {len(all_hits)} total Rambam hits")
        
        return all_hits
    
    def get_nosei_keilim_for_siman(
        self,
        chelek: str,  # "oc", "yd", "eh", "cm"
        siman: int
    ) -> Dict[str, str]:
        """
        Get all nosei keilim text for a specific SA siman.
        
        Returns: {author_name: text}
        """
        result = {}
        
        # Map chelek to commentary base path
        chelek_map = {
            "oc": "Halakhah/Shulchan Arukh/Commentary",
            "yd": "Halakhah/Shulchan Arukh/Commentary", 
            "eh": "Halakhah/Shulchan Arukh/Commentary",
            "cm": "Halakhah/Shulchan Arukh/Commentary",
        }
        
        base_path = chelek_map.get(chelek)
        if not base_path:
            logger.debug(f"[LocalCorpus] Unknown chelek: {chelek}")
            return result
        
        commentary_base = self.corpus_root / base_path
        
        if not commentary_base.exists():
            logger.warning(f"[LocalCorpus] Commentary directory not found: {commentary_base}")
            return result
        
        # Find all commentary merged.json files
        try:
            for author_dir in commentary_base.iterdir():
                if not author_dir.is_dir():
                    continue
                
                author_name = author_dir.name
                
                # Look for merged.json
                for json_file in author_dir.rglob("merged.json"):
                    try:
                        data = self._load_json(str(json_file.relative_to(self.corpus_root)))
                        if not data:
                            continue
                        
                        text_array = self._get_text_array(data)
                        
                        # Handle list structure
                        if isinstance(text_array, list):
                            if 0 < siman <= len(text_array):
                                siman_text = self._flatten_text(text_array[siman - 1])
                                if siman_text and siman_text.strip():
                                    result[author_name] = siman_text
                        
                        # Handle dict structure
                        elif isinstance(text_array, dict):
                            siman_key = str(siman)
                            if siman_key in text_array:
                                siman_text = self._flatten_text(text_array[siman_key])
                                if siman_text and siman_text.strip():
                                    result[author_name] = siman_text
                            # Also try 0-indexed key
                            elif str(siman - 1) in text_array:
                                siman_text = self._flatten_text(text_array[str(siman - 1)])
                                if siman_text and siman_text.strip():
                                    result[author_name] = siman_text
                    
                    except Exception as e:
                        logger.debug(f"[LocalCorpus] Error reading {json_file}: {e}")
                        continue
                    
                    break  # Only need one merged.json per author
        
        except Exception as e:
            logger.warning(f"[LocalCorpus] Error iterating commentary directory: {e}")
        
        logger.debug(f"[LocalCorpus] Found {len(result)} nosei keilim for {chelek.upper()} {siman}")
        return result
    
    def extract_citations_from_siman(
        self,
        chelek: str,
        siman: int,
        default_masechta: str = None
    ) -> List[GemaraCitation]:
        """
        Extract all gemara citations from a siman's nosei keilim.
        
        Only works for SA simanim - Rambam/Tur have different nosei keilim structures.
        """
        all_citations = []
        
        try:
            nosei_keilim = self.get_nosei_keilim_for_siman(chelek, siman)
            
            for author, text in nosei_keilim.items():
                try:
                    source_ref = f"{author} on SA {chelek.upper()} {siman}"
                    citations = extract_gemara_citations(text, source_ref, default_masechta)
                    all_citations.extend(citations)
                    
                    if citations:
                        logger.debug(f"  {author}: {len(citations)} citations")
                except Exception as e:
                    logger.debug(f"[LocalCorpus] Error extracting from {author}: {e}")
                    continue
        
        except Exception as e:
            logger.warning(f"[LocalCorpus] Error in extract_citations_from_siman({chelek}, {siman}): {e}")
        
        return all_citations
    
    def locate_topic(self, topic_hebrew: str) -> Dict[str, Any]:
        """
        Find where a topic appears in SA/Tur/Rambam.
        
        Returns a structured dict separating the different sefarim:
        {
            "sa": {"oc": [431, 432], "yd": [], "eh": [], "cm": []},
            "tur": {"oc": [431], "yd": [], "eh": [], "cm": []},
            "rambam": [{"sefer": "Leavened and Unleavened Bread", "perek": 2, "ref": "..."}],
            "raw_hits": [...]  # All original hits for reference
        }
        """
        result = {
            "sa": {"oc": [], "yd": [], "eh": [], "cm": []},
            "tur": {"oc": [], "yd": [], "eh": [], "cm": []},
            "rambam": [],
            "raw_hits": []
        }
        
        try:
            # Search SA
            sa_hits = self.search_shulchan_aruch(topic_hebrew)
            for hit in sa_hits:
                result["raw_hits"].append(hit)
                chelek = self._extract_chelek(hit.sefer)
                if chelek and hit.siman not in result["sa"][chelek]:
                    result["sa"][chelek].append(hit.siman)
        except Exception as e:
            logger.warning(f"[LocalCorpus] Error searching SA: {e}")
        
        try:
            # Search Tur
            tur_hits = self.search_tur(topic_hebrew)
            for hit in tur_hits:
                result["raw_hits"].append(hit)
                chelek = self._extract_chelek(hit.sefer)
                if chelek and hit.siman not in result["tur"][chelek]:
                    result["tur"][chelek].append(hit.siman)
        except Exception as e:
            logger.warning(f"[LocalCorpus] Error searching Tur: {e}")
        
        try:
            # Search Rambam - different structure (sefer/perek, not chelek/siman)
            rambam_hits = self.search_rambam(topic_hebrew)
            for hit in rambam_hits:
                result["raw_hits"].append(hit)
                result["rambam"].append({
                    "sefer": hit.sefer,
                    "perek": hit.siman,  # In Rambam this is perek
                    "ref": hit.ref,
                    "snippet": hit.text_snippet
                })
        except Exception as e:
            logger.warning(f"[LocalCorpus] Error searching Rambam: {e}")
        
        return result
    
    def _extract_chelek(self, sefer_name: str) -> Optional[str]:
        """Extract chelek (oc/yd/eh/cm) from sefer name."""
        if not sefer_name:
            return None
        
        name_lower = sefer_name.lower()
        
        if "orach" in name_lower or "chayim" in name_lower:
            return "oc"
        elif "yoreh" in name_lower or "de'ah" in name_lower or "deah" in name_lower:
            return "yd"
        elif "even" in name_lower or "ezer" in name_lower:
            return "eh"
        elif "choshen" in name_lower or "mishpat" in name_lower:
            return "cm"
        
        return None
    
    def _sefer_to_key(self, sefer_name: str) -> str:
        """Convert sefer name to a short key. (Legacy helper)"""
        name_lower = sefer_name.lower() if sefer_name else ""
        
        if "orach" in name_lower:
            return "sa_oc" if "shulchan" in name_lower else "tur_oc"
        elif "yoreh" in name_lower:
            return "sa_yd" if "shulchan" in name_lower else "tur_yd"
        elif "even" in name_lower:
            return "sa_eh" if "shulchan" in name_lower else "tur_eh"
        elif "choshen" in name_lower:
            return "sa_cm" if "shulchan" in name_lower else "tur_cm"
        
        return sefer_name.replace(' ', '_').lower() if sefer_name else "unknown"


# ==============================================================================
#  MAIN SEARCH FUNCTIONS
# ==============================================================================

def discover_main_sugyos(
    corpus: LocalCorpus,
    topic_hebrew: str,
    default_masechta: str = None
) -> Tuple[Dict[str, int], List[GemaraCitation]]:
    """
    Main entry point: Find where a topic lives and extract gemara citations.
    
    This function:
    1. Locates the topic in SA/Tur/Rambam
    2. Extracts gemara citations from SA nosei keilim (primary source)
    3. Returns citation counts to identify main sugyos
    
    Returns:
        - daf_counts: {daf_ref: citation_count} - sorted by count
        - all_citations: List of all citations found
    """
    logger.info(f"[DISCOVER] Finding main sugyos for: {topic_hebrew}")
    
    # Phase A: Locate topic in SA/Tur/Rambam
    try:
        locations = corpus.locate_topic(topic_hebrew)
    except Exception as e:
        logger.error(f"[DISCOVER] Failed to locate topic: {e}")
        return {}, []
    
    # Check if we found anything
    sa_found = any(locations["sa"][chelek] for chelek in ["oc", "yd", "eh", "cm"])
    tur_found = any(locations["tur"][chelek] for chelek in ["oc", "yd", "eh", "cm"])
    rambam_found = bool(locations["rambam"])
    
    if not (sa_found or tur_found or rambam_found):
        logger.warning(f"[DISCOVER] Topic not found in local corpus: {topic_hebrew}")
        return {}, []
    
    # Log what we found
    found_in = []
    if sa_found:
        sa_cheleks = [f"{c.upper()}:{locations['sa'][c]}" for c in ["oc", "yd", "eh", "cm"] if locations['sa'][c]]
        found_in.append(f"SA ({', '.join(sa_cheleks)})")
    if tur_found:
        tur_cheleks = [f"{c.upper()}:{locations['tur'][c]}" for c in ["oc", "yd", "eh", "cm"] if locations['tur'][c]]
        found_in.append(f"Tur ({', '.join(tur_cheleks)})")
    if rambam_found:
        found_in.append(f"Rambam ({len(locations['rambam'])} hits)")
    
    logger.info(f"[DISCOVER] Found topic in: {', '.join(found_in)}")
    
    # Phase B: Extract citations from SA nosei keilim (PRIMARY SOURCE)
    all_citations: List[GemaraCitation] = []
    daf_counts: Dict[str, int] = defaultdict(int)
    
    # Process SA hits - this is our main source of gemara citations
    for chelek in ["oc", "yd", "eh", "cm"]:
        simanim = locations["sa"].get(chelek, [])
        for siman in simanim:
            try:
                logger.debug(f"[DISCOVER] Extracting citations from SA {chelek.upper()} {siman}")
                citations = corpus.extract_citations_from_siman(chelek, siman, default_masechta)
                all_citations.extend(citations)
                
                # Count daf references
                for cite in citations:
                    daf_ref = f"{cite.masechta} {cite.daf}"
                    daf_counts[daf_ref] += 1
                    
                if citations:
                    logger.debug(f"    Found {len(citations)} citations")
                    
            except Exception as e:
                logger.warning(f"[DISCOVER] Error extracting from SA {chelek.upper()} {siman}: {e}")
                continue
    
    # TODO: Could also process Tur nosei keilim (Bach, Beis Yosef, etc.)
    # TODO: Could also process Rambam nosei keilim (Maggid Mishneh, Kesef Mishneh, etc.)
    # For now, SA nosei keilim is our primary source
    
    # Phase C: Sort by citation count (most cited = main sugyos)
    sorted_counts = dict(sorted(daf_counts.items(), key=lambda x: -x[1]))
    
    logger.info(f"[DISCOVER] Found {len(all_citations)} citations across {len(sorted_counts)} dapim")
    
    # Log top 10
    top_10 = list(sorted_counts.items())[:10]
    if top_10:
        logger.info("[DISCOVER] Top sugyos by citation count:")
        for ref, count in top_10:
            logger.info(f"  {ref}: {count} citations")
    
    # Also log Rambam info for reference (even though we don't extract citations from it yet)
    if rambam_found:
        logger.info(f"[DISCOVER] Also found in Rambam:")
        for hit in locations["rambam"][:5]:  # Show first 5
            logger.info(f"  {hit['sefer']} perek {hit['perek']}")
    
    return sorted_counts, all_citations


# ==============================================================================
#  SINGLETON / FACTORY
# ==============================================================================

_corpus_instance: Optional[LocalCorpus] = None


def get_local_corpus(corpus_root: Path = None) -> LocalCorpus:
    """Get or create the singleton LocalCorpus instance."""
    global _corpus_instance
    
    if _corpus_instance is None or corpus_root is not None:
        _corpus_instance = LocalCorpus(corpus_root)
    
    return _corpus_instance


# ==============================================================================
#  CLI FOR TESTING
# ==============================================================================

if __name__ == "__main__":
    import sys
    
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(levelname)s | %(message)s'
    )
    
    # Test with bittul chometz
    corpus = get_local_corpus()
    
    topic = "ביטול חמץ"
    print(f"\n{'='*60}")
    print(f"Testing topic: {topic}")
    print(f"{'='*60}\n")
    
    daf_counts, citations = discover_main_sugyos(corpus, topic, default_masechta="פסחים")
    
    print(f"\n{'='*60}")
    print("RESULTS")
    print(f"{'='*60}")
    print(f"Total citations found: {len(citations)}")
    print(f"Unique dapim: {len(daf_counts)}")
    print(f"\nMain sugyos (by citation count):")
    for ref, count in list(daf_counts.items())[:15]:
        print(f"  {ref}: {count}")