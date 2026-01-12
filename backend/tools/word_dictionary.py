"""
Word Dictionary - Self-Maintaining Cache V2
============================================

V2 IMPROVEMENTS:
- lookup_all() method to find ALL non-overlapping sub-phrases
- Better handling of multi-term queries like "chezkas haguf chezkas mammon"

Auto-populated from:
1. Your learning notes (Hebrew terms)
2. Runtime resolutions (learns as you use it)

NO manual maintenance required.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import Counter
from datetime import datetime


# ==========================================
#  DICTIONARY STRUCTURE
# ==========================================

DICTIONARY_FILE = Path(__file__).parent.parent / "data" / "word_dictionary.json"

# Format:
# {
#   "transliteration": {
#     "hebrew": "הברית",
#     "confidence": "high",
#     "usage_count": 12,
#     "source": "runtime" | "notes",
#     "last_used": "2025-01-15"
#   }
# }


# ==========================================
#  HEBREW EXTRACTION FROM NOTES
# ==========================================

def extract_hebrew_terms_from_notes(notes_path: Path) -> Dict[str, str]:
    """
    Extract Hebrew terms from Doyv's learning notes.
    
    Looks for:
    - Multi-word phrases (2-6 words)
    - Terms that appear multiple times (important concepts)
    - Filters out abbreviations and noise
    
    Returns:
        {hebrew_term: frequency_count}
    """
    if not notes_path.exists():
        return {}
    
    with open(notes_path, 'r', encoding='utf-8') as f:
        text = f.read()
    
    # Common abbreviations to skip
    abbreviations = {
        'י', 'ב', 'ד', 'א', 'ע', 'ש', 'נ', 'מ', 'ר', 'ה',  # Single letters
        'תוס', 'רש', 'רמב', 'רשב', 'ריטב', 'מהרש',  # Common abbreviations
        'עיי', 'דף', 'גמ', 'משנה', 'הל', 'פ', 'הגמ', 'הרא',
    }
    
    # Extract Hebrew phrases (2-6 words)
    # Match sequences of Hebrew words separated by spaces
    # Hebrew word: 2+ consecutive Hebrew letters
    hebrew_word = r'[\u0590-\u05FF]{2,}'
    phrase_pattern = rf'({hebrew_word}(?:\s+{hebrew_word}){{1,5}})'
    
    matches = re.findall(phrase_pattern, text)
    
    # Clean and filter
    hebrew_terms = []
    for match in matches:
        match = match.strip()
        
        # Skip if too short or too long
        if len(match) < 4 or len(match) > 60:
            continue
        
        # Split into words
        words = match.split()
        
        # Must have at least 2 words
        if len(words) < 2:
            continue
        
        # Skip if all words are abbreviations
        if all(word in abbreviations for word in words):
            continue
        
        # Skip if starts with common abbreviation
        if words[0] in abbreviations:
            continue
        
        hebrew_terms.append(match)
    
    # Count frequency
    term_counts = Counter(hebrew_terms)
    
    # Keep terms that appear at least 3 times (highly significant)
    significant_terms = {
        term: count 
        for term, count in term_counts.items() 
        if count >= 3
    }
    
    return significant_terms


def auto_generate_transliterations(hebrew_terms: Dict[str, int]) -> Dict[str, str]:
    """
    Auto-generate likely transliterations for Hebrew terms.
    
    This is a GUESS - but for common terms it's often good enough.
    Runtime learning will correct mistakes.
    """
    translit_dict = {}
    
    # Simple Hebrew → English mapping
    heb_to_eng = {
        'א': 'a',
        'ב': 'b',
        'ג': 'g',
        'ד': 'd',
        'ה': 'h',
        'ו': 'v',
        'ז': 'z',
        'ח': 'ch',
        'ט': 't',
        'י': 'i',
        'כ': 'k',
        'ך': 'k',
        'ל': 'l',
        'מ': 'm',
        'ם': 'm',
        'נ': 'n',
        'ן': 'n',
        'ס': 's',
        'ע': 'a',
        'פ': 'p',
        'ף': 'f',
        'צ': 'tz',
        'ץ': 'tz',
        'ק': 'k',
        'ר': 'r',
        'ש': 'sh',
        'ת': 's',  # yeshivish: tav → sav
        ' ': ' ',
    }
    
    for hebrew_term, count in hebrew_terms.items():
        # Generate transliteration
        translit = ''
        for char in hebrew_term:
            translit += heb_to_eng.get(char, '')
        
        translit = translit.strip().lower()
        
        # Skip empty or very short
        if len(translit) < 3:
            continue
        
        translit_dict[translit] = hebrew_term
    
    return translit_dict


def initialize_dictionary_from_notes() -> Dict:
    """
    Initialize dictionary from Doyv's notes.
    
    Called once on first run (or when rebuilding).
    """
    # Try multiple possible locations for notes
    possible_paths = [
        Path(__file__).parent.parent.parent / "my_notes.md",  # backend/../my_notes.md
        Path(__file__).parent.parent / "my_notes.md",  # backend/my_notes.md
        Path("/mnt/user-data/uploads/my_notes.md"),  # Gemini environment
        Path("my_notes.md"),  # Current directory
    ]
    
    notes_path = None
    for path in possible_paths:
        if path.exists():
            notes_path = path
            break
    
    if not notes_path:
        print(f"⚠️  Notes not found. Tried:")
        for p in possible_paths:
            print(f"    - {p}")
        print(f"\n  Dictionary will start empty and learn at runtime.")
        return {}
    
    print(f"📚 Extracting terms from notes: {notes_path}")
    
    # Extract Hebrew terms
    hebrew_terms = extract_hebrew_terms_from_notes(notes_path)
    print(f"   Found {len(hebrew_terms)} significant Hebrew terms")
    
    # Generate transliterations
    translit_dict = auto_generate_transliterations(hebrew_terms)
    print(f"   Generated {len(translit_dict)} transliteration mappings")
    
    # Format for dictionary
    dictionary = {}
    for translit, hebrew in translit_dict.items():
        dictionary[translit] = {
            "hebrew": hebrew,
            "confidence": "medium",  # Auto-generated, so medium confidence
            "usage_count": 0,
            "source": "notes",
            "last_used": None
        }
    
    # Add manual high-confidence entries (from your architecture notes)
    manual_entries = {
        "shaviya anafshe": "שוייא אנפשיה",
        "shavya anafshe": "שוייא אנפשיה",
        "chaticha deisura": "חתיכה דאיסורא",
        "chaticha daisura": "חתיכה דאיסורא",
        
        "bari vishma": "ברי ושמא",
        "bari vshma": "ברי ושמא",
        
        "sfek sfeika": "ספק ספיקא",
        "safek safeika": "ספק ספיקא",
        
        # FIXED: All variations of chezkas haguf/mammon
        "chezkas haguf": "חזקת הגוף",
        "chezka haguf": "חזקת הגוף",
        "chezkas mammon": "חזקת ממון",
        "chezkas mamon": "חזקת ממון",
        "chekas haguf": "חזקת הגוף",
        "chekas mammon": "חזקת ממון",
        "chekas mamon": "חזקת ממון",
        
        "chezkas rav huna": "חזקת רב הונא",
        "chezka rav huna": "חזקת רב הונא",
        
        "eid echad": "עד אחד",
        "ed echad": "עד אחד",
        
        "bitul chametz": "ביטול חמץ",
        "bitul chometz": "ביטול חמץ",
        
        "besulah niseis": "בתולה נשאת",
        "besulah nisais": "בתולה נשאת",
    }
    
    for translit, hebrew in manual_entries.items():
        dictionary[translit] = {
            "hebrew": hebrew,
            "confidence": "high",
            "usage_count": 0,
            "source": "manual",
            "last_used": None
        }
    
    return dictionary


# ==========================================
#  DICTIONARY OPERATIONS
# ==========================================

class WordDictionary:
    """
    Self-maintaining word dictionary with runtime learning.
    
    V2: Added lookup_all() for finding multiple non-overlapping sub-phrases.
    """
    
    def __init__(self):
        self.dict_path = DICTIONARY_FILE
        self.dict_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.dictionary = self._load_or_initialize()
    
    def _load_or_initialize(self) -> Dict:
        """Load existing dictionary or initialize from notes"""
        if self.dict_path.exists():
            with open(self.dict_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            print("📖 Initializing dictionary from notes...")
            dictionary = initialize_dictionary_from_notes()
            self._save(dictionary)
            print(f"✓ Dictionary initialized with {len(dictionary)} entries")
            return dictionary
    
    def _save(self, dictionary: Dict = None):
        """Save dictionary to disk"""
        if dictionary is None:
            dictionary = self.dictionary
        
        with open(self.dict_path, 'w', encoding='utf-8') as f:
            json.dump(dictionary, f, ensure_ascii=False, indent=2)
    
    def lookup(self, query: str) -> Optional[Dict]:
        """
        Look up a transliteration in the dictionary.
        
        V8: Tries sub-phrases if full query not found.
        NOTE: Returns FIRST match only. Use lookup_all() for multiple terms.
        
        Returns entry dict or None if not found.
        """
        query = query.lower().strip()
        
        # Try exact match first
        if query in self.dictionary:
            return self._update_and_return(query)
        
        # Try sub-phrases (longest first)
        words = query.split()
        for phrase_len in range(len(words), 1, -1):
            for start in range(len(words) - phrase_len + 1):
                phrase = ' '.join(words[start:start + phrase_len])
                if phrase in self.dictionary:
                    return self._update_and_return(phrase)
        
        # Try individual words
        for word in words:
            if word in self.dictionary:
                return self._update_and_return(word)
        
        return None
    
    def lookup_all(self, query: str) -> List[Tuple[str, str, Dict]]:
        """
        Find ALL non-overlapping dictionary matches in the query.
        
        V2 NEW METHOD: Returns multiple Hebrew terms for queries like
        "chezkas haguf chezkas mammon" → [חזקת הגוף, חזקת ממון]
        
        Uses greedy longest-first matching to avoid overlaps.
        
        Returns:
            List of (transliteration, hebrew, entry_dict) tuples
        """
        query = query.lower().strip()
        words = query.split()
        n = len(words)
        
        # Track which word positions are already matched
        used = [False] * n
        matches = []
        
        # Greedy: try longest phrases first
        for phrase_len in range(n, 0, -1):
            for start in range(n - phrase_len + 1):
                # Skip if any word in this range is already used
                if any(used[start:start + phrase_len]):
                    continue
                
                phrase = ' '.join(words[start:start + phrase_len])
                
                if phrase in self.dictionary:
                    entry = self.dictionary[phrase]
                    matches.append((phrase, entry['hebrew'], entry))
                    
                    # Mark these positions as used
                    for i in range(start, start + phrase_len):
                        used[i] = True
                    
                    # Update usage stats
                    self._update_entry_stats(phrase)
        
        # Sort matches by position in original query
        # (optional: currently returns in order found)
        return matches
    
    def _update_entry_stats(self, key: str):
        """Update usage stats for an entry (without returning it)."""
        if key in self.dictionary:
            self.dictionary[key]["usage_count"] += 1
            self.dictionary[key]["last_used"] = self._get_timestamp()
            self._save()
    
    def _update_and_return(self, key: str) -> Dict:
        """Update usage stats and return entry."""
        entry = self.dictionary[key]
        entry["usage_count"] += 1
        entry["last_used"] = self._get_timestamp()
        self._save()
        return entry
    
    def _confidence_from_hits(self, hits: Optional[int]) -> str:
        """Map Sefaria hit counts to a confidence string."""
        if hits is None:
            return "high"
        if hits >= 100:
            return "high"
        if hits >= 10:
            return "medium"
        if hits >= 1:
            return "low"
        return "low"
    
    def add_entry(
        self, 
        transliteration: str, 
        hebrew: str, 
        confidence: str = "high",
        source: str = "runtime",
        hits: Optional[int] = None
    ):
        """
        Add or update dictionary entry.
        
        Called when:
        1. User confirms a resolution (runtime learning)
        2. Vector search finds a new term
        """
        transliteration = transliteration.lower().strip()
        
        if transliteration in self.dictionary:
            # Update existing entry
            entry = self.dictionary[transliteration]
            entry["hebrew"] = hebrew
            entry["confidence"] = confidence
            entry["usage_count"] += 1
            entry["last_used"] = self._get_timestamp()
            if hits is not None:
                entry["hits"] = hits
        else:
            # Add new entry
            entry = {
                "hebrew": hebrew,
                "confidence": confidence,
                "usage_count": 1,
                "source": source,
                "last_used": self._get_timestamp()
            }
            if hits is not None:
                entry["hits"] = hits
            self.dictionary[transliteration] = entry
        
        self._save()
        print(f"✓ Dictionary learned: '{transliteration}' → '{hebrew}'")
    
    def add(
        self,
        transliteration: str,
        hebrew: str,
        hits: Optional[int] = None,
        confidence: Optional[str] = None,
        source: str = "runtime",
    ):
        """
        Backwards-compatible helper used by Step 1 and console tools.
        
        Args:
            transliteration: English/transliterated term
            hebrew: Resolved Hebrew term
            hits: Optional Sefaria hit count for context
            confidence: Optional confidence string; derived from hits if missing
            source: Where the learning came from (runtime/user/sefaria/etc.)
        """
        resolved_confidence = confidence or self._confidence_from_hits(hits)
        self.add_entry(
            transliteration=transliteration,
            hebrew=hebrew,
            confidence=resolved_confidence,
            source=source,
            hits=hits,
        )
    
    def get_stats(self) -> Dict:
        """Get dictionary statistics"""
        return {
            "total_entries": len(self.dictionary),
            "by_source": {
                source: sum(1 for e in self.dictionary.values() if e.get("source") == source)
                for source in ["notes", "manual", "runtime", "sefaria", "manual_fix", "user_confirmed"]
            },
            "by_confidence": {
                conf: sum(1 for e in self.dictionary.values() if e.get("confidence") == conf)
                for conf in ["high", "medium", "low"]
            }
        }
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        return datetime.now().isoformat()


# ==========================================
#  GLOBAL INSTANCE
# ==========================================

_dictionary = None


def get_dictionary() -> WordDictionary:
    """Get global dictionary instance"""
    global _dictionary
    if _dictionary is None:
        _dictionary = WordDictionary()
    return _dictionary


# ==========================================
#  TESTING
# ==========================================

if __name__ == "__main__":
    # Test dictionary
    dict_obj = get_dictionary()
    
    print("\n=== Dictionary Stats ===")
    stats = dict_obj.get_stats()
    print(f"Total entries: {stats['total_entries']}")
    print(f"By source: {stats['by_source']}")
    print(f"By confidence: {stats['by_confidence']}")
    
    print("\n=== Test Single Lookups ===")
    test_queries = [
        "bari vishma",
        "chezkas haguf",
        "shaviya anafshe",
    ]
    
    for query in test_queries:
        result = dict_obj.lookup(query)
        if result:
            print(f"✓ '{query}' → {result['hebrew']} (confidence: {result['confidence']})")
        else:
            print(f"✗ '{query}' not found")
    
    print("\n=== Test Multi-Term Lookups (V2 lookup_all) ===")
    multi_queries = [
        "chezkas haguf chezkas mammon",
        "bari vishma sfek sfeika",
        "what is chezkas haguf",  # Should find "chezkas haguf"
    ]
    
    for query in multi_queries:
        results = dict_obj.lookup_all(query)
        if results:
            print(f"✓ '{query}':")
            for translit, hebrew, _ in results:
                print(f"    → '{translit}' = '{hebrew}'")
        else:
            print(f"✗ '{query}' - no matches")