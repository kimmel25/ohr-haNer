"""
Local Corpus Handler for Sefaria Export JSON Files - FINAL VERSION
===================================================================

This module provides local search and citation extraction from the
Sefaria JSON export, eliminating the need for excessive API calls.

V7 FINAL - Key improvements:
- AND-based word matching for multi-word queries
- Comprehensive gemara citation extraction patterns
- Handles HTML-embedded text
- Path auto-discovery for SA, Tur, Rambam
- Nosei keilim extraction with duplicate folder handling
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

# Default path - user should set this to their actual export location
DEFAULT_CORPUS_ROOT = Path("C:/Projects/Sefaria-Export/json")


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

# Abbreviated masechta names commonly used in nosei keilim
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
    
    Handles various citation formats found in SA commentaries:
    - "בפסחים דף ד'" / "בפסחים דף ד' ע"א"
    - "פסחים ד:" / "פסחים ד."
    - "בגמ' דף ד'" (with default masechta)
    - "(פסחים ד')" in parentheses
    - "עיין פסחים ד"
    """
    citations = []
    seen = set()
    
    if not text:
        return citations
    
    # Build masechta pattern from all known names
    all_masechtos = list(MASECHTA_MAP.keys())
    masechta_pattern = '|'.join(re.escape(m) for m in sorted(all_masechtos, key=len, reverse=True))
    
    # Hebrew number words
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
        """Parse a daf number from Hebrew or Arabic numerals."""
        if not s:
            return None
        s = s.strip().replace("'", "").replace('"', '').replace('׳', '').replace('״', '')
        
        # Try Arabic numeral
        if s.isdigit():
            return int(s)
        
        # Try Hebrew numeral
        if s in hebrew_nums:
            return hebrew_nums[s]
        
        # Try two-letter Hebrew
        if len(s) == 2 and s in hebrew_nums:
            return hebrew_nums[s]
        
        return None
    
    def parse_amud(s: str) -> str:
        """Parse amud indicator."""
        if not s:
            return 'a'
        s = s.strip()
        if 'ב' in s or 'b' in s.lower():
            return 'b'
        return 'a'
    
    # CITATION PATTERNS - ordered by specificity
    patterns = [
        # Pattern 1: Full reference "בפסחים דף ד' ע"א" or "פסחים דף ד ע"ב"
        rf'(?:ב)?({masechta_pattern})\s+(?:דף\s+)?([א-תa-z0-9]+)[\'״׳"]?\s*(?:ע["\']?([אב]))?',
        
        # Pattern 2: "פסחים ד:" or "פסחים ד."
        rf'({masechta_pattern})\s+([א-תa-z0-9]+)[\'״׳"]?\s*[:.]',
        
        # Pattern 3: In parentheses "(פסחים ד')"
        rf'\(({masechta_pattern})\s+([א-תa-z0-9]+)[\'״׳"]?\)',
        
        # Pattern 4: "בגמ' דף X" or "בגמרא דף X" (needs default masechta)
        rf'בגמ[\'״׳]?\s+(?:דף\s+)?([א-תa-z0-9]+)[\'״׳"]?\s*(?:ע["\']?([אב]))?',
        
        # Pattern 5: "עיין פסחים" or "עי' פסחים"
        rf'(?:עיין|עי[\'״׳])\s+({masechta_pattern})\s+(?:דף\s+)?([א-תa-z0-9]+)?',
        
        # Pattern 6: Just "דף X" with context (needs default)
        rf'(?:^|\s)דף\s+([א-תa-z0-9]+)[\'״׳"]?\s*(?:ע["\']?([אב]))?',
    ]
    
    for pattern_idx, pattern in enumerate(patterns):
        for match in re.finditer(pattern, text, re.IGNORECASE):
            groups = match.groups()
            
            masechta_he = None
            daf_str = None
            amud_str = None
            
            # Parse based on pattern
            if pattern_idx == 3:  # "בגמ' דף X" pattern - no masechta in match
                daf_str = groups[0]
                amud_str = groups[1] if len(groups) > 1 else None
                masechta_he = default_masechta
            elif pattern_idx == 5:  # "דף X" pattern - no masechta
                daf_str = groups[0]
                amud_str = groups[1] if len(groups) > 1 else None
                masechta_he = default_masechta
            else:
                masechta_he = groups[0] if groups[0] in MASECHTA_MAP else None
                daf_str = groups[1] if len(groups) > 1 else None
                amud_str = groups[2] if len(groups) > 2 else None
            
            # Skip if no masechta
            if not masechta_he:
                continue
            
            # Parse daf number
            daf_num = parse_daf_number(daf_str)
            if not daf_num or daf_num < 2 or daf_num > 180:  # Valid gemara daf range
                continue
            
            # Parse amud
            amud = parse_amud(amud_str)
            
            # Convert to English
            masechta_en = MASECHTA_MAP.get(masechta_he, masechta_he)
            daf = f"{daf_num}{amud}"
            
            # Deduplicate
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
    """
    Handler for local Sefaria JSON export files.
    """
    
    def __init__(self, corpus_root: Path = None):
        self.corpus_root = Path(corpus_root) if corpus_root else DEFAULT_CORPUS_ROOT
        self._cache: Dict[str, Any] = {}
        
        logger.info(f"[LocalCorpus] Initialized with root: {self.corpus_root}")
    
    def _load_json(self, relative_path: str) -> Optional[Dict]:
        """Load and cache a JSON file."""
        # Normalize path separators
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
                # Try without final letters (ם ן ף ך ץ -> מ נ פ כ צ)
                word_base = word.replace('ם', 'מ').replace('ן', 'נ').replace('ף', 'פ').replace('ך', 'כ').replace('ץ', 'צ')
                if word_base not in text and word not in text:
                    return False
        return True
    
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
                        # Get snippet
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
                    siman_num = int(key) if str(key).isdigit() else 0
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
    
    def search_shulchan_aruch(self, query: str) -> List[LocalSearchHit]:
        """Search all four chelkei Shulchan Aruch."""
        all_hits = []
        sa_base = self.corpus_root / "Halakhah" / "Shulchan Arukh"
        
        if not sa_base.exists():
            return all_hits
        
        try:
            for subdir in sa_base.iterdir():
                if subdir.is_dir() and subdir.name.startswith("Shulchan Arukh,"):
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
    
    def search_tur(self, query: str) -> List[LocalSearchHit]:
        """Search all four chelkei Tur."""
        all_hits = []
        tur_base = self.corpus_root / "Halakhah" / "Tur"
        
        if not tur_base.exists():
            return all_hits
        
        try:
            for subdir in tur_base.iterdir():
                if subdir.is_dir() and subdir.name.startswith("Tur"):
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
            """
            Get all nosei keilim text for a specific SA siman.
            
            V8 FIX: Properly matches chelek names in folder paths.
            """
            result = {}
            commentary_base = self.corpus_root / "Halakhah" / "Shulchan Arukh" / "Commentary"
            
            if not commentary_base.exists():
                return result
            
            # Map chelek codes to possible folder name patterns
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
                    
                    # V8: Find merged.json that matches our chelek
                    found_json = None
                    
                    for json_file in author_dir.rglob("merged.json"):
                        json_path_lower = str(json_file).lower()
                        
                        # Check if this file is for the right chelek
                        chelek_match = False
                        for pattern in patterns:
                            if pattern in json_path_lower:
                                chelek_match = True
                                break
                        
                        if chelek_match:
                            # Prefer Hebrew version
                            if "hebrew" in json_path_lower:
                                found_json = json_file
                                break
                            elif found_json is None:
                                found_json = json_file
                    
                    # If no chelek-specific file, fall back to author-level file
                    if found_json is None:
                        for json_file in author_dir.rglob("merged.json"):
                            json_path_str = str(json_file).lower()
                            # Only use if NOT chelek-specific
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
    
    def extract_citations_from_siman(self, chelek: str, siman: int, default_masechta: str = None) -> List[GemaraCitation]:
        """Extract all gemara citations from a siman's nosei keilim."""
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
            logger.warning(f"[LocalCorpus] Error extracting citations: {e}")
        
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
                if chelek and hit.siman not in result["sa"][chelek]:
                    result["sa"][chelek].append(hit.siman)
        except Exception as e:
            logger.warning(f"Error searching SA: {e}")
        
        # Search Tur
        try:
            for hit in self.search_tur(topic_hebrew):
                result["raw_hits"].append(hit)
                chelek = extract_chelek(hit.sefer)
                if chelek and hit.siman not in result["tur"][chelek]:
                    result["tur"][chelek].append(hit.siman)
        except Exception as e:
            logger.warning(f"Error searching Tur: {e}")
        
        # Search Rambam
        try:
            for hit in self.search_rambam(topic_hebrew):
                result["raw_hits"].append(hit)
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
#  MAIN DISCOVERY FUNCTION
# ==============================================================================

def discover_main_sugyos(
    corpus: LocalCorpus,
    topic_hebrew: str,
    default_masechta: str = None
) -> Tuple[Dict[str, int], List[GemaraCitation]]:
    """
    Find where a topic lives and extract gemara citations from nosei keilim.
    
    Returns:
        - daf_counts: {daf_ref: citation_count} sorted by count
        - all_citations: List of all citations found
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
    
    # Extract citations from SA nosei keilim
    all_citations: List[GemaraCitation] = []
    daf_counts: Dict[str, int] = defaultdict(int)
    
    for chelek in ["oc", "yd", "eh", "cm"]:
        for siman in locations["sa"].get(chelek, []):
            if siman == 0:  # Skip invalid simanim
                continue
            try:
                citations = corpus.extract_citations_from_siman(chelek, siman, default_masechta)
                all_citations.extend(citations)
                
                for cite in citations:
                    daf_ref = f"{cite.masechta} {cite.daf}"
                    daf_counts[daf_ref] += 1
            except Exception as e:
                logger.warning(f"Error extracting from {chelek} {siman}: {e}")
    
    # Sort by citation count
    sorted_counts = dict(sorted(daf_counts.items(), key=lambda x: -x[1]))
    
    logger.info(f"[DISCOVER] Found {len(all_citations)} citations across {len(sorted_counts)} dapim")
    
    # Log top sugyos
    if sorted_counts:
        logger.info("[DISCOVER] Top sugyos by citation count:")
        for ref, count in list(sorted_counts.items())[:10]:
            logger.info(f"  {ref}: {count} citations")
    
    # Log Rambam info
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
    
    # Structure check
    print("\n" + "="*60)
    print("CORPUS STRUCTURE CHECK")
    print("="*60)
    
    sa_base = corpus.corpus_root / "Halakhah" / "Shulchan Arukh"
    tur_base = corpus.corpus_root / "Halakhah" / "Tur"
    
    print(f"SA exists: {sa_base.exists()}")
    print(f"Tur exists: {tur_base.exists()}")
    
    # Test the search
    topic = "ביטול חמץ"
    print(f"\n{'='*60}")
    print(f"SEARCHING FOR: {topic}")
    print(f"{'='*60}\n")
    
    daf_counts, citations = discover_main_sugyos(corpus, topic, default_masechta="פסחים")
    
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
            print(f"    Text: \"{cite.source_text}\"")
    else:
        print("\n⚠️  No gemara citations extracted.")
        print("\nDEBUG - Let's see what's in a nosei keilim:")
        
        # Get one nosei keilim and show raw text
        nk = corpus.get_nosei_keilim_for_siman("oc", 434)
        if nk:
            author = list(nk.keys())[0]
            text = nk[author][:500]
            print(f"\nSample from {author} on OC 434:")
            print(f"  \"{text}...\"")
            
            # Try to find any daf references manually
            print(f"\n  Contains 'דף': {'דף' in text}")
            print(f"  Contains 'פסחים': {'פסחים' in text}")
            print(f"  Contains 'בגמ': {'בגמ' in text}")