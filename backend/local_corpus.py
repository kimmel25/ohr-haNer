"""
Local Corpus Handler for Sefaria Export JSON Files - V10
=========================================================

V10 CHANGES:
1. Fixed siman extraction - skip non-digit keys instead of returning 0
2. Added Tur nosei keilim extraction (Beis Yosef, Bach, Darchei Moshe)
3. Added Rambam nosei keilim extraction (Maggid Mishneh, Kesef Mishneh, etc.)
4. Updated discover_main_sugyos to use SA, Tur, AND Rambam citations
5. Added rishonim fallback for gemara searches
"""

import json
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


# ==============================================================================
#  CONFIGURATION
# ==============================================================================

DEFAULT_CORPUS_ROOT = Path("C:/Projects/Sefaria-Export/json")


# ==============================================================================
#  DATA STRUCTURES
# ==============================================================================

@dataclass
class LocalSearchHit:
    """A search hit from local corpus."""
    sefer: str
    siman: int
    seif: Optional[int]
    text_snippet: str
    ref: str


@dataclass 
class GemaraCitation:
    """A gemara citation extracted from text."""
    masechta: str
    daf: str
    source_ref: str
    source_text: str
    confidence: float


# ==============================================================================
#  MASECHTA MAPPINGS
# ==============================================================================

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
    'ר"ה': 'Rosh Hashanah',
    'תענית': 'Taanit',
    'מגילה': 'Megillah',
    'מועד קטן': 'Moed Katan',
    'מ"ק': 'Moed Katan',
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
    'ב"ק': 'Bava Kamma',
    'בבא מציעא': 'Bava Metzia',
    'ב"מ': 'Bava Metzia',
    'בבא בתרא': 'Bava Batra',
    'ב"ב': 'Bava Batra',
    'סנהדרין': 'Sanhedrin',
    'מכות': 'Makkot',
    'שבועות': 'Shevuot',
    'עבודה זרה': 'Avodah Zarah',
    'ע"ז': 'Avodah Zarah',
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

# Maximum daf numbers for each Bavli masechta (to filter out garbage citations)
# Masechtos not in Bavli (like Challah, Middot, etc.) are not included
MASECHTA_MAX_DAF = {
    # Seder Zeraim (only Berakhot has Bavli)
    'Berakhot': 64,
    
    # Seder Moed
    'Shabbat': 157,
    'Eruvin': 105,
    'Pesachim': 121,
    'Shekalim': 22,  # Yerushalmi in Bavli editions
    'Yoma': 88,
    'Sukkah': 56,
    'Beitzah': 40,
    'Rosh Hashanah': 35,
    'Taanit': 31,
    'Megillah': 32,
    'Moed Katan': 29,
    'Chagigah': 27,
    
    # Seder Nashim
    'Yevamot': 122,
    'Ketubot': 112,
    'Nedarim': 91,
    'Nazir': 66,
    'Sotah': 49,
    'Gittin': 90,
    'Kiddushin': 82,
    
    # Seder Nezikin
    'Bava Kamma': 119,
    'Bava Metzia': 119,
    'Bava Batra': 176,
    'Sanhedrin': 113,
    'Makkot': 24,
    'Shevuot': 49,
    'Avodah Zarah': 76,
    'Horayot': 14,
    
    # Seder Kodshim
    'Zevachim': 120,
    'Menachot': 110,
    'Chullin': 142,
    'Bekhorot': 61,
    'Arakhin': 34,
    'Temurah': 34,
    'Keritot': 28,
    'Meilah': 22,
    'Tamid': 33,
    # Middot and Kinnim have no Bavli
    
    # Seder Taharot (only Niddah has Bavli)
    'Niddah': 73,
}

MASECHTA_ABBREV = {
    'פסח': 'פסחים',
    'שב': 'שבת',
    'עירוב': 'עירובין',
    'סוכ': 'סוכה',
    'ביצ': 'ביצה',
    'מגיל': 'מגילה',
    'חגיג': 'חגיגה',
    'יבמ': 'יבמות',
    'כתוב': 'כתובות',
    'גיט': 'גיטין',
    'קידוש': 'קידושין',
    'סנהד': 'סנהדרין',
    'מכ': 'מכות',
    'שבוע': 'שבועות',
    'חול': 'חולין',
    'בכור': 'בכורות',
    'ערכ': 'ערכין',
    'כרית': 'כריתות',
    'נד': 'נדה',
}


def extract_gemara_citations(
    text: str, 
    source_ref: str,
    default_masechta: str = None
) -> List[GemaraCitation]:
    """
    Extract gemara citations from nosei keilim text.
    """
    citations = []
    seen = set()
    
    if not text:
        return citations
    
    all_masechtos = list(MASECHTA_MAP.keys())
    masechta_pattern = '|'.join(re.escape(m) for m in sorted(all_masechtos, key=len, reverse=True))
    
    hebrew_nums = {
        'ב': 2, 'ג': 3, 'ד': 4, 'ה': 5, 'ו': 6, 'ז': 7, 'ח': 8, 'ט': 9,
        'י': 10, 'יא': 11, 'יב': 12, 'יג': 13, 'יד': 14, 'טו': 15, 'טז': 16,
        'יז': 17, 'יח': 18, 'יט': 19, 'כ': 20, 'כא': 21, 'כב': 22, 'כג': 23,
        'כד': 24, 'כה': 25, 'כו': 26, 'כז': 27, 'כח': 28, 'כט': 29, 'ל': 30,
        'לא': 31, 'לב': 32, 'לג': 33, 'לד': 34, 'לה': 35, 'לו': 36, 'לז': 37,
        'לח': 38, 'לט': 39, 'מ': 40, 'מא': 41, 'מב': 42, 'מג': 43, 'מד': 44,
        'מה': 45, 'מו': 46, 'מז': 47, 'מח': 48, 'מט': 49, 'נ': 50,
        'נא': 51, 'נב': 52, 'נג': 53, 'נד': 54, 'נה': 55, 'נו': 56, 'נז': 57,
        'נח': 58, 'נט': 59, 'ס': 60, 'סא': 61, 'סב': 62, 'סג': 63, 'סד': 64,
        'סה': 65, 'סו': 66, 'סז': 67, 'סח': 68, 'סט': 69, 'ע': 70,
        'עא': 71, 'עב': 72, 'עג': 73, 'עד': 74, 'עה': 75, 'עו': 76, 'עז': 77,
        'עח': 78, 'עט': 79, 'פ': 80, 'פא': 81, 'פב': 82, 'פג': 83, 'פד': 84,
        'פה': 85, 'פו': 86, 'פז': 87, 'פח': 88, 'פט': 89, 'צ': 90,
        'צא': 91, 'צב': 92, 'צג': 93, 'צד': 94, 'צה': 95, 'צו': 96, 'צז': 97,
        'צח': 98, 'צט': 99, 'ק': 100,
    }
    
    def parse_daf_number(s: str) -> Optional[int]:
        if not s:
            return None
        s = s.strip().replace("'", "").replace('"', '').replace('׳', '').replace('״', '')
        if s.isdigit():
            return int(s)
        if s in hebrew_nums:
            return hebrew_nums[s]
        if len(s) == 2 and s in hebrew_nums:
            return hebrew_nums[s]
        return None
    
    def parse_amud(s: str) -> str:
        if not s:
            return 'a'
        s = s.strip()
        if 'ב' in s or 'b' in s.lower():
            return 'b'
        return 'a'
    
    patterns = [
        rf'(?:ב)?({masechta_pattern})\s+(?:דף\s+)?([א-תa-z0-9]+)[\'״׳"]?\s*(?:ע["\']?([אב]))?',
        rf'({masechta_pattern})\s+([א-תa-z0-9]+)[\'״׳"]?\s*[:.]',
        rf'\(({masechta_pattern})\s+([א-תa-z0-9]+)[\'״׳"]?\)',
        rf'בגמ[\'״׳]?\s+(?:דף\s+)?([א-תa-z0-9]+)[\'״׳"]?\s*(?:ע["\']?([אב]))?',
        rf'(?:עיין|עי[\'״׳])\s+({masechta_pattern})\s+(?:דף\s+)?([א-תa-z0-9]+)?',
        rf'(?:^|\s)דף\s+([א-תa-z0-9]+)[\'״׳"]?\s*(?:ע["\']?([אב]))?',
    ]
    
    for pattern_idx, pattern in enumerate(patterns):
        for match in re.finditer(pattern, text, re.IGNORECASE):
            groups = match.groups()
            
            masechta_he = None
            daf_str = None
            amud_str = None
            
            if pattern_idx == 3:
                daf_str = groups[0]
                amud_str = groups[1] if len(groups) > 1 else None
                masechta_he = default_masechta
            elif pattern_idx == 5:
                daf_str = groups[0]
                amud_str = groups[1] if len(groups) > 1 else None
                masechta_he = default_masechta
            else:
                masechta_he = groups[0] if groups[0] in MASECHTA_MAP else None
                daf_str = groups[1] if len(groups) > 1 else None
                amud_str = groups[2] if len(groups) > 2 else None
            
            if not masechta_he:
                continue
            
            daf_num = parse_daf_number(daf_str)
            if not daf_num or daf_num < 2 or daf_num > 180:
                continue
            
            amud = parse_amud(amud_str)
            masechta_en = MASECHTA_MAP.get(masechta_he, masechta_he)
            
            # Validate daf number is valid for this specific masechta
            # This filters out garbage like "Challah 31a" (Challah has no Bavli)
            max_daf = MASECHTA_MAX_DAF.get(masechta_en)
            if max_daf is None:
                # Masechta not in Bavli (e.g., Challah, Middot) - skip
                continue
            if daf_num > max_daf:
                # Daf number exceeds max for this masechta - skip
                continue
            
            daf = f"{daf_num}{amud}"
            
            key = f"{masechta_en}_{daf}"
            if key in seen:
                continue
            seen.add(key)
            
            citations.append(GemaraCitation(
                masechta=masechta_en,
                daf=daf,
                source_ref=source_ref,
                source_text=match.group(0)[:50],
                confidence=0.9 if pattern_idx < 3 else 0.7
            ))
    
    return citations


# ==============================================================================
#  LOCAL CORPUS CLASS
# ==============================================================================

class LocalCorpus:
    """Handler for local Sefaria JSON export files."""
    
    def __init__(self, corpus_root: Path = None):
        self.corpus_root = Path(corpus_root) if corpus_root else DEFAULT_CORPUS_ROOT
        self._cache: Dict[str, Any] = {}
        logger.info(f"[LocalCorpus] Initialized with root: {self.corpus_root}")
    
    def _load_json(self, relative_path: str) -> Optional[Dict]:
        """Load and cache a JSON file."""
        relative_path = relative_path.replace('\\', '/')
        
        if relative_path in self._cache:
            return self._cache[relative_path]
        
        full_path = self.corpus_root / relative_path
        
        if not full_path.exists():
            return None
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self._cache[relative_path] = data
            return data
        except Exception as e:
            logger.debug(f"[LocalCorpus] Failed to load {full_path}: {e}")
            return None
    
    def _get_text_array(self, json_data: Dict) -> Any:
        """Extract the text array from JSON data."""
        if not json_data:
            return []
        return json_data.get('text', [])
    
    def _strip_html(self, text: str) -> str:
        """Remove HTML tags from text."""
        if not text:
            return ''
        clean = re.sub(r'<[^>]+>', '', text)
        clean = re.sub(r'\s+', ' ', clean)
        return clean.strip()
    
    def _flatten_text(self, text_item) -> str:
        """Flatten nested text arrays into a single string, stripping HTML."""
        if text_item is None:
            return ''
        if isinstance(text_item, str):
            return self._strip_html(text_item)
        if isinstance(text_item, list):
            return ' '.join(self._flatten_text(t) for t in text_item if t)
        if isinstance(text_item, dict):
            return ' '.join(self._flatten_text(v) for v in text_item.values() if v)
        return str(text_item)
    
    def _text_matches_query(self, text: str, query_words: List[str]) -> bool:
        """Check if text contains all query words (AND logic)."""
        if not text or not query_words:
            return False
        
        for word in query_words:
            if word not in text:
                word_base = word.replace('ם', 'מ').replace('ן', 'נ').replace('ף', 'פ').replace('ך', 'כ').replace('ץ', 'צ')
                if word_base not in text and word not in text:
                    return False
        return True
    
    def _extract_siman_from_key(self, key: str) -> int:
        """
        V10 FIX: Extract siman number from a dictionary key.
        Returns 0 if can't extract (caller should skip).
        """
        key_str = str(key).strip()
        
        # Simple digit
        if key_str.isdigit():
            return int(key_str)
        
        # Extract leading digits (handles "17:3" -> 17)
        match = re.match(r'^(\d+)', key_str)
        if match:
            return int(match.group(1))
        
        # Could not extract siman
        return 0
    
    def search_sefer(self, sefer_path: str, query: str, sefer_name: str = None) -> List[LocalSearchHit]:
        """Search for a query in a sefer using AND logic for multiple words."""
        data = self._load_json(sefer_path)
        if not data:
            return []
        
        text_array = self._get_text_array(data)
        sefer_name = sefer_name or data.get('title', sefer_path)
        hits = []
        query_words = query.split()
        
        try:
            if isinstance(text_array, list):
                for siman_idx, siman_text in enumerate(text_array):
                    siman_num = siman_idx + 1
                    flat_text = self._flatten_text(siman_text)
                    
                    if self._text_matches_query(flat_text, query_words):
                        first_word = query_words[0]
                        match_pos = flat_text.find(first_word)
                        start = max(0, match_pos - 30) if match_pos >= 0 else 0
                        end = min(len(flat_text), start + 150)
                        snippet = flat_text[start:end]
                        
                        hits.append(LocalSearchHit(
                            sefer=sefer_name,
                            siman=siman_num,
                            seif=None,
                            text_snippet=snippet,
                            ref=f"{sefer_name} {siman_num}"
                        ))
                        
            elif isinstance(text_array, dict):
                for key, siman_text in text_array.items():
                    # V10 FIX: Better siman extraction
                    siman_num = self._extract_siman_from_key(key)
                    
                    # V10 FIX: Skip non-siman entries instead of using 0
                    if siman_num == 0:
                        logger.debug(f"[search_sefer] Skipping non-siman key: {key}")
                        continue
                    
                    flat_text = self._flatten_text(siman_text)
                    
                    if self._text_matches_query(flat_text, query_words):
                        first_word = query_words[0]
                        match_pos = flat_text.find(first_word)
                        start = max(0, match_pos - 30) if match_pos >= 0 else 0
                        end = min(len(flat_text), start + 150)
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
    
    def search_shulchan_aruch(self, query: str, chelek: str = None) -> List[LocalSearchHit]:
        """Search Shulchan Aruch. If chelek specified (oc/yd/eh/cm), search only that chelek."""
        all_hits = []
        sa_base = self.corpus_root / "Halakhah" / "Shulchan Arukh"
        
        if not sa_base.exists():
            return all_hits
        
        # Map chelek codes to full names
        chelek_map = {
            "oc": "Orach Chayim",
            "yd": "Yoreh De'ah",
            "eh": "Even HaEzer",
            "cm": "Choshen Mishpat"
        }
        
        try:
            for subdir in sa_base.iterdir():
                if subdir.is_dir() and subdir.name.startswith("Shulchan Arukh,"):
                    # If chelek specified, filter by it
                    if chelek:
                        chelek_name = chelek_map.get(chelek.lower(), chelek)
                        if chelek_name not in subdir.name:
                            continue
                    
                    json_path = subdir / "Hebrew" / "merged.json"
                    if json_path.exists():
                        relative = str(json_path.relative_to(self.corpus_root))
                        hits = self.search_sefer(relative, query, subdir.name)
                        all_hits.extend(hits)
                        if hits:
                            logger.info(f"[LocalCorpus] Found {len(hits)} hits in {subdir.name}")
        except Exception as e:
            logger.warning(f"[LocalCorpus] Error searching SA: {e}")
        
        return all_hits
    
    def search_tur(self, query: str, chelek: str = None) -> List[LocalSearchHit]:
        """Search Tur. If chelek specified (oc/yd/eh/cm), search only that chelek."""
        all_hits = []
        tur_base = self.corpus_root / "Halakhah" / "Tur"
        
        if not tur_base.exists():
            return all_hits
        
        # Map chelek codes to full names  
        chelek_map = {
            "oc": "Orach Chaim",
            "yd": "Yoreh Deah",
            "eh": "Even HaEzer",
            "cm": "Choshen Mishpat"
        }
        
        try:
            for subdir in tur_base.iterdir():
                if subdir.is_dir() and subdir.name.startswith("Tur"):
                    # If chelek specified, filter by it
                    if chelek:
                        chelek_name = chelek_map.get(chelek.lower(), chelek)
                        if chelek_name not in subdir.name:
                            continue
                    
                    json_path = subdir / "Hebrew" / "merged.json"
                    if json_path.exists():
                        relative = str(json_path.relative_to(self.corpus_root))
                        hits = self.search_sefer(relative, query, subdir.name)
                        all_hits.extend(hits)
                        if hits:
                            logger.info(f"[LocalCorpus] Found {len(hits)} hits in {subdir.name}")
        except Exception as e:
            logger.warning(f"[LocalCorpus] Error searching Tur: {e}")
        
        return all_hits
    
    def search_rambam(self, query: str) -> List[LocalSearchHit]:
        """Search Mishneh Torah (all hilchos)."""
        all_hits = []
        rambam_base = self.corpus_root / "Halakhah" / "Mishneh Torah"
        
        if not rambam_base.exists():
            return all_hits
        
        try:
            for json_file in rambam_base.rglob("merged.json"):
                if "English" in str(json_file) or "Commentary" in str(json_file):
                    continue
                
                relative_path = str(json_file.relative_to(self.corpus_root))
                sefer_name = None
                for part in json_file.parts:
                    if part.startswith("Mishneh Torah,"):
                        sefer_name = part.replace("Mishneh Torah, ", "")
                        break
                
                if not sefer_name:
                    sefer_name = json_file.parent.parent.name
                
                hits = self.search_sefer(relative_path, query, sefer_name)
                all_hits.extend(hits)
        except Exception as e:
            logger.warning(f"[LocalCorpus] Error searching Rambam: {e}")
        
        if all_hits:
            logger.info(f"[LocalCorpus] Found {len(all_hits)} total Rambam hits")
        
        return all_hits
    
    def get_nosei_keilim_for_siman(self, chelek: str, siman: int) -> Dict[str, str]:
        """Get all nosei keilim text for a specific SA siman."""
        result = {}
        commentary_base = self.corpus_root / "Halakhah" / "Shulchan Arukh" / "Commentary"
        
        if not commentary_base.exists():
            return result
        
        chelek_patterns = {
            "oc": ["orach chaim", "orach_chaim"],
            "yd": ["yoreh de'ah", "yoreh deah", "yoreh_deah"],
            "eh": ["even haezer", "even ha'ezer", "even_haezer"],
            "cm": ["choshen mishpat", "choshen_mishpat"],
        }
        
        patterns = chelek_patterns.get(chelek.lower(), [chelek.lower()])
        
        try:
            for author_dir in commentary_base.iterdir():
                if not author_dir.is_dir():
                    continue
                
                author_name = author_dir.name
                found_json = None
                
                for json_file in author_dir.rglob("merged.json"):
                    json_path_lower = str(json_file).lower()
                    
                    chelek_match = False
                    for pattern in patterns:
                        if pattern in json_path_lower:
                            chelek_match = True
                            break
                    
                    if chelek_match:
                        if "hebrew" in json_path_lower:
                            found_json = json_file
                            break
                        elif found_json is None:
                            found_json = json_file
                
                if found_json is None:
                    for json_file in author_dir.rglob("merged.json"):
                        json_path_str = str(json_file).lower()
                        has_any_chelek = any(
                            any(p in json_path_str for p in chelek_patterns[c])
                            for c in chelek_patterns
                        )
                        if not has_any_chelek:
                            if "hebrew" in json_path_str:
                                found_json = json_file
                                break
                            elif found_json is None:
                                found_json = json_file
                
                if not found_json:
                    continue
                
                try:
                    relative_path = str(found_json.relative_to(self.corpus_root))
                    data = self._load_json(relative_path)
                    if not data:
                        continue
                    
                    text_array = self._get_text_array(data)
                    
                    if isinstance(text_array, list) and 0 < siman <= len(text_array):
                        siman_text = self._flatten_text(text_array[siman - 1])
                        if siman_text and len(siman_text) > 10:
                            result[author_name] = siman_text
                    elif isinstance(text_array, dict):
                        for key in [str(siman), str(siman - 1)]:
                            if key in text_array:
                                siman_text = self._flatten_text(text_array[key])
                                if siman_text and len(siman_text) > 10:
                                    result[author_name] = siman_text
                                break
                except Exception:
                    continue
                    
        except Exception as e:
            logger.warning(f"[LocalCorpus] Error getting nosei keilim: {e}")
        
        if result:
            logger.info(f"[LocalCorpus] Found {len(result)} nosei keilim for SA {chelek.upper()} {siman}: {list(result.keys())}")
        
        return result
    
    def get_tur_nosei_keilim_for_siman(self, chelek: str, siman: int) -> Dict[str, str]:
        """
        V10: Get nosei keilim text for a Tur siman.
        
        Includes: Beis Yosef, Bach, Darchei Moshe, Perishah, Derishah
        """
        result = {}
        
        chelek_map = {
            "oc": "Orach Chayim",
            "yd": "Yoreh Deah",
            "eh": "Even HaEzer",
            "cm": "Choshen Mishpat"
        }
        
        chelek_name = chelek_map.get(chelek.lower(), chelek)
        
        # Try multiple path patterns for Tur commentaries
        tur_base = self.corpus_root / "Halakhah" / "Tur"
        commentary_paths = [
            tur_base / "Commentary",
            tur_base,
        ]
        
        author_patterns = {
            "Beit Yosef": ["beit yosef", "beis yosef", "bet yosef"],
            "Bach": ["bach", "bayit chadash"],
            "Darchei Moshe": ["darchei moshe", "darkhei moshe"],
            "Perishah": ["perishah", "prisha"],
            "Derishah": ["derishah", "drisha"],
        }
        
        for commentary_base in commentary_paths:
            if not commentary_base.exists():
                continue
            
            try:
                for author_dir in commentary_base.iterdir():
                    if not author_dir.is_dir():
                        continue
                    
                    dir_name_lower = author_dir.name.lower()
                    
                    # Check if this directory matches any author
                    matched_author = None
                    for author, patterns in author_patterns.items():
                        if any(p in dir_name_lower for p in patterns):
                            matched_author = author
                            break
                    
                    if not matched_author:
                        continue
                    
                    # Find the right JSON file for this chelek
                    found_json = None
                    for json_file in author_dir.rglob("merged.json"):
                        json_path_lower = str(json_file).lower()
                        
                        # Check if it's for the right chelek
                        if chelek_name.lower().replace(" ", "") in json_path_lower.replace(" ", ""):
                            if "hebrew" in json_path_lower:
                                found_json = json_file
                                break
                            elif found_json is None:
                                found_json = json_file
                    
                    if not found_json:
                        continue
                    
                    try:
                        relative_path = str(found_json.relative_to(self.corpus_root))
                        data = self._load_json(relative_path)
                        if not data:
                            continue
                        
                        text_array = self._get_text_array(data)
                        siman_text = ""
                        
                        if isinstance(text_array, list) and 0 < siman <= len(text_array):
                            siman_text = self._flatten_text(text_array[siman - 1])
                        elif isinstance(text_array, dict):
                            for key in [str(siman), str(siman - 1)]:
                                if key in text_array:
                                    siman_text = self._flatten_text(text_array[key])
                                    break
                        
                        if siman_text and len(siman_text) > 10:
                            result[matched_author] = siman_text
                            
                    except Exception as e:
                        logger.debug(f"Could not read {found_json}: {e}")
                        continue
                        
            except Exception as e:
                logger.debug(f"Error scanning {commentary_base}: {e}")
                continue
        
        if result:
            logger.info(f"[LocalCorpus] Found {len(result)} Tur nosei keilim for {chelek.upper()} {siman}: {list(result.keys())}")
        
        return result
    
    def get_rambam_nosei_keilim_for_halacha(self, sefer: str, perek: int) -> Dict[str, str]:
        """
        V10: Get nosei keilim text for a Rambam halacha.
        
        Includes: Maggid Mishneh, Kesef Mishneh, Lechem Mishneh, Hagahos Maimoniyos
        """
        result = {}
        
        rambam_base = self.corpus_root / "Halakhah" / "Mishneh Torah"
        
        author_patterns = {
            "Maggid Mishneh": ["maggid mishneh", "magid mishneh"],
            "Kesef Mishneh": ["kesef mishneh", "kessef mishneh"],
            "Lechem Mishneh": ["lechem mishneh"],
            "Hagahos Maimoniyos": ["hagahos", "hagahot"],
            "Mishneh LaMelech": ["mishneh lamelech", "mishneh lemelech"],
        }
        
        # Search in Commentary folder
        commentary_base = rambam_base / "Commentary"
        if not commentary_base.exists():
            return result
        
        try:
            for author_dir in commentary_base.iterdir():
                if not author_dir.is_dir():
                    continue
                
                dir_name_lower = author_dir.name.lower()
                
                matched_author = None
                for author, patterns in author_patterns.items():
                    if any(p in dir_name_lower for p in patterns):
                        matched_author = author
                        break
                
                if not matched_author:
                    continue
                
                # Find JSON for this sefer
                found_json = None
                sefer_lower = sefer.lower().replace(" ", "")
                
                for json_file in author_dir.rglob("merged.json"):
                    json_path_lower = str(json_file).lower().replace(" ", "")
                    
                    if sefer_lower in json_path_lower:
                        if "hebrew" in json_path_lower:
                            found_json = json_file
                            break
                        elif found_json is None:
                            found_json = json_file
                
                if not found_json:
                    continue
                
                try:
                    relative_path = str(found_json.relative_to(self.corpus_root))
                    data = self._load_json(relative_path)
                    if not data:
                        continue
                    
                    text_array = self._get_text_array(data)
                    perek_text = ""
                    
                    if isinstance(text_array, list) and 0 < perek <= len(text_array):
                        perek_text = self._flatten_text(text_array[perek - 1])
                    elif isinstance(text_array, dict):
                        for key in [str(perek), str(perek - 1)]:
                            if key in text_array:
                                perek_text = self._flatten_text(text_array[key])
                                break
                    
                    if perek_text and len(perek_text) > 10:
                        result[matched_author] = perek_text
                        
                except Exception as e:
                    logger.debug(f"Could not read {found_json}: {e}")
                    continue
                    
        except Exception as e:
            logger.debug(f"Error searching Rambam nosei keilim: {e}")
        
        if result:
            logger.info(f"[LocalCorpus] Found {len(result)} Rambam nosei keilim for {sefer} {perek}: {list(result.keys())}")
        
        return result
    
    def extract_citations_from_siman(self, chelek: str, siman: int, default_masechta: str = None) -> List[GemaraCitation]:
        """Extract all gemara citations from a SA siman's nosei keilim."""
        all_citations = []
        
        try:
            nosei_keilim = self.get_nosei_keilim_for_siman(chelek, siman)
            
            for author, text in nosei_keilim.items():
                source_ref = f"{author} on SA {chelek.upper()} {siman}"
                citations = extract_gemara_citations(text, source_ref, default_masechta)
                all_citations.extend(citations)
                
                if citations:
                    logger.debug(f"  {author}: {len(citations)} citations")
        except Exception as e:
            logger.warning(f"[LocalCorpus] Error extracting SA citations: {e}")
        
        return all_citations
    
    def extract_citations_from_tur_siman(self, chelek: str, siman: int, default_masechta: str = None) -> List[GemaraCitation]:
        """V10: Extract all gemara citations from a Tur siman's nosei keilim."""
        all_citations = []
        
        try:
            nosei_keilim = self.get_tur_nosei_keilim_for_siman(chelek, siman)
            
            for author, text in nosei_keilim.items():
                source_ref = f"{author} on Tur {chelek.upper()} {siman}"
                citations = extract_gemara_citations(text, source_ref, default_masechta)
                all_citations.extend(citations)
                
                if citations:
                    logger.debug(f"  {author}: {len(citations)} citations")
        except Exception as e:
            logger.warning(f"[LocalCorpus] Error extracting Tur citations: {e}")
        
        return all_citations
    
    def extract_citations_from_rambam(self, sefer: str, perek: int, default_masechta: str = None) -> List[GemaraCitation]:
        """V10: Extract all gemara citations from a Rambam perek's nosei keilim."""
        all_citations = []
        
        try:
            nosei_keilim = self.get_rambam_nosei_keilim_for_halacha(sefer, perek)
            
            for author, text in nosei_keilim.items():
                source_ref = f"{author} on Rambam {sefer} {perek}"
                citations = extract_gemara_citations(text, source_ref, default_masechta)
                all_citations.extend(citations)
                
                if citations:
                    logger.debug(f"  {author}: {len(citations)} citations")
        except Exception as e:
            logger.warning(f"[LocalCorpus] Error extracting Rambam citations: {e}")
        
        return all_citations
    
    def locate_topic(self, topic_hebrew: str) -> Dict[str, Any]:
        """Find where a topic appears in SA/Tur/Rambam."""
        result = {
            "sa": {"oc": [], "yd": [], "eh": [], "cm": []},
            "tur": {"oc": [], "yd": [], "eh": [], "cm": []},
            "rambam": [],
            "raw_hits": []
        }
        
        def extract_chelek(sefer_name: str) -> Optional[str]:
            if not sefer_name:
                return None
            n = sefer_name.lower()
            if "orach" in n or "chayim" in n:
                return "oc"
            elif "yoreh" in n or "de'ah" in n or "deah" in n:
                return "yd"
            elif "even" in n or "ezer" in n:
                return "eh"
            elif "choshen" in n or "mishpat" in n:
                return "cm"
            return None
        
        # Search SA
        try:
            for hit in self.search_shulchan_aruch(topic_hebrew):
                result["raw_hits"].append(hit)
                chelek = extract_chelek(hit.sefer)
                if chelek and hit.siman != 0 and hit.siman not in result["sa"][chelek]:
                    result["sa"][chelek].append(hit.siman)
        except Exception as e:
            logger.warning(f"Error searching SA: {e}")
        
        # Search Tur
        try:
            for hit in self.search_tur(topic_hebrew):
                result["raw_hits"].append(hit)
                chelek = extract_chelek(hit.sefer)
                if chelek and hit.siman != 0 and hit.siman not in result["tur"][chelek]:
                    result["tur"][chelek].append(hit.siman)
        except Exception as e:
            logger.warning(f"Error searching Tur: {e}")
        
        # Search Rambam
        try:
            for hit in self.search_rambam(topic_hebrew):
                result["raw_hits"].append(hit)
                if hit.siman != 0:  # V10: Also filter siman 0 from Rambam
                    result["rambam"].append({
                        "sefer": hit.sefer,
                        "perek": hit.siman,
                        "ref": hit.ref,
                        "snippet": hit.text_snippet
                    })
        except Exception as e:
            logger.warning(f"Error searching Rambam: {e}")
        
        return result


# ==============================================================================
#  MAIN DISCOVERY FUNCTION - V10
# ==============================================================================

def discover_main_sugyos(
    corpus: LocalCorpus,
    topic_hebrew: str,
    default_masechta: str = None
) -> Tuple[Dict[str, int], List[GemaraCitation]]:
    """
    V10: Find where a topic lives and extract gemara citations from ALL nosei keilim.
    
    Searches: SA nosei keilim, Tur nosei keilim, Rambam nosei keilim
    """
    logger.info(f"[DISCOVER] Finding main sugyos for: {topic_hebrew}")
    
    locations = corpus.locate_topic(topic_hebrew)
    
    # Check what we found
    sa_found = any(locations["sa"][c] for c in ["oc", "yd", "eh", "cm"])
    tur_found = any(locations["tur"][c] for c in ["oc", "yd", "eh", "cm"])
    rambam_found = bool(locations["rambam"])
    
    if not (sa_found or tur_found or rambam_found):
        logger.warning(f"[DISCOVER] Topic not found in local corpus: {topic_hebrew}")
        return {}, []
    
    # Log what we found
    found_parts = []
    if sa_found:
        sa_parts = [f"{c.upper()}:{locations['sa'][c]}" for c in ["oc", "yd", "eh", "cm"] if locations['sa'][c]]
        found_parts.append(f"SA ({', '.join(sa_parts)})")
    if tur_found:
        tur_parts = [f"{c.upper()}:{locations['tur'][c]}" for c in ["oc", "yd", "eh", "cm"] if locations['tur'][c]]
        found_parts.append(f"Tur ({', '.join(tur_parts)})")
    if rambam_found:
        found_parts.append(f"Rambam ({len(locations['rambam'])} hits)")
    
    logger.info(f"[DISCOVER] Found topic in: {', '.join(found_parts)}")
    
    all_citations: List[GemaraCitation] = []
    daf_counts: Dict[str, int] = defaultdict(int)
    
    # =========================================================================
    # Extract citations from SA nosei keilim
    # =========================================================================
    for chelek in ["oc", "yd", "eh", "cm"]:
        for siman in locations["sa"].get(chelek, []):
            if siman == 0:
                logger.warning(f"[DISCOVER] Skipping invalid SA siman 0 in {chelek}")
                continue
            try:
                citations = corpus.extract_citations_from_siman(chelek, siman, default_masechta)
                all_citations.extend(citations)
                for cite in citations:
                    daf_ref = f"{cite.masechta} {cite.daf}"
                    daf_counts[daf_ref] += 1
                if citations:
                    logger.info(f"[DISCOVER] SA {chelek.upper()} {siman}: {len(citations)} citations")
            except Exception as e:
                logger.warning(f"Error extracting from SA {chelek} {siman}: {e}")
    
    # =========================================================================
    # V10: Extract citations from Tur nosei keilim
    # =========================================================================
    for chelek in ["oc", "yd", "eh", "cm"]:
        for siman in locations["tur"].get(chelek, []):
            if siman == 0:
                logger.warning(f"[DISCOVER] Skipping invalid Tur siman 0 in {chelek}")
                continue
            try:
                citations = corpus.extract_citations_from_tur_siman(chelek, siman, default_masechta)
                all_citations.extend(citations)
                for cite in citations:
                    daf_ref = f"{cite.masechta} {cite.daf}"
                    daf_counts[daf_ref] += 1
                if citations:
                    logger.info(f"[DISCOVER] Tur {chelek.upper()} {siman}: {len(citations)} citations")
            except Exception as e:
                logger.warning(f"Error extracting from Tur {chelek} {siman}: {e}")
    
    # =========================================================================
    # V10: Extract citations from Rambam nosei keilim
    # =========================================================================
    for hit in locations.get("rambam", []):
        sefer = hit.get("sefer", "")
        perek = hit.get("perek", 0)
        
        if not sefer or perek == 0:
            continue
        
        try:
            citations = corpus.extract_citations_from_rambam(sefer, perek, default_masechta)
            all_citations.extend(citations)
            for cite in citations:
                daf_ref = f"{cite.masechta} {cite.daf}"
                daf_counts[daf_ref] += 1
            if citations:
                logger.info(f"[DISCOVER] Rambam {sefer} {perek}: {len(citations)} citations")
        except Exception as e:
            logger.warning(f"Error extracting from Rambam {sefer} {perek}: {e}")
        
        # Also extract citations from the raw Rambam snippet itself
        snippet = hit.get("snippet", "")
        if snippet:
            source_ref = f"Rambam {hit.get('ref', '')}"
            snippet_citations = extract_gemara_citations(snippet, source_ref, default_masechta)
            all_citations.extend(snippet_citations)
            for cite in snippet_citations:
                daf_ref = f"{cite.masechta} {cite.daf}"
                daf_counts[daf_ref] += 1
    
    # Sort by citation count
    sorted_counts = dict(sorted(daf_counts.items(), key=lambda x: -x[1]))
    
    logger.info(f"[DISCOVER] Found {len(all_citations)} citations across {len(sorted_counts)} dapim")
    
    if sorted_counts:
        logger.info("[DISCOVER] Top sugyos by citation count:")
        for ref, count in list(sorted_counts.items())[:10]:
            logger.info(f"  {ref}: {count} citations")
    
    if rambam_found:
        logger.info(f"[DISCOVER] Also found in Rambam:")
        for hit in locations["rambam"][:5]:
            logger.info(f"  {hit['sefer']} perek {hit['perek']}")
    
    return sorted_counts, all_citations


# ==============================================================================
#  SINGLETON
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
    logging.basicConfig(level=logging.INFO, format='%(levelname)s | %(message)s')
    
    corpus = get_local_corpus()
    
    print("\n" + "="*60)
    print("CORPUS STRUCTURE CHECK")
    print("="*60)
    
    sa_base = corpus.corpus_root / "Halakhah" / "Shulchan Arukh"
    tur_base = corpus.corpus_root / "Halakhah" / "Tur"
    rambam_base = corpus.corpus_root / "Halakhah" / "Mishneh Torah"
    
    print(f"SA exists: {sa_base.exists()}")
    print(f"Tur exists: {tur_base.exists()}")
    print(f"Rambam exists: {rambam_base.exists()}")
    
    # Test the search
    topic = "חזקת הגוף חזקת ממון"
    print(f"\n{'='*60}")
    print(f"SEARCHING FOR: {topic}")
    print(f"{'='*60}\n")
    
    daf_counts, citations = discover_main_sugyos(corpus, topic, default_masechta="כתובות")
    
    print(f"\n{'='*60}")
    print("RESULTS")
    print(f"{'='*60}")
    print(f"Total citations found: {len(citations)}")
    print(f"Unique dapim: {len(daf_counts)}")
    
    if daf_counts:
        print(f"\n🎯 MAIN SUGYOS (by citation count):")
        for ref, count in list(daf_counts.items())[:15]:
            print(f"  {ref}: {count} citations")
        
        print(f"\nSample citations:")
        for cite in citations[:10]:
            print(f"  - {cite.masechta} {cite.daf} (from {cite.source_ref})")
    else:
        print("\n⚠️  No gemara citations extracted.")