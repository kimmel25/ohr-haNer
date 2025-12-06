"""
Clean Bad Dictionary Entries
============================

This script removes "garbage" entries that were added by the buggy TEST_MODE.

BAD entries are identified by:
1. source="claude" or source="vector"  (auto-added, not manual)
2. Hebrew text > 30 characters  (document content, not terms)
3. Low Hebrew character ratio  (< 50% Hebrew)

GOOD entries that WON'T be removed:
- source="manual" (manually added)
- source="transliteration" (single high-confidence variants)
- source="runtime" (learned from actual use)
- Short Hebrew text (< 30 chars, actual terms)

Usage:
    python clean_bad_dictionary_entries.py
    
This will:
1. Load word_dictionary.json
2. Identify bad entries
3. Show you what will be removed
4. Ask for confirmation
5. Create backup
6. Save cleaned dictionary
"""

import json
from pathlib import Path
from datetime import datetime

# Paths
DATA_DIR = Path(__file__).parent.parent / "data"
DICT_FILE = DATA_DIR / "word_dictionary.json"
BACKUP_DIR = DATA_DIR / "backups"

def is_bad_entry(key: str, entry: dict) -> tuple[bool, str]:
    """
    Check if an entry is bad (should be removed).
    
    Returns: (is_bad, reason)
    """
    source = entry.get('source', '')
    hebrew = entry.get('hebrew', '')
    
    # Good sources (never remove)
    if source in ['manual', 'transliteration', 'runtime']:
        return False, "Good source"
    
    # Check if Hebrew is too long (content text, not term)
    if len(hebrew) > 30:
        return True, f"Hebrew too long ({len(hebrew)} chars) - looks like document content"
    
    # Check Hebrew character ratio
    if hebrew:
        hebrew_chars = sum(1 for c in hebrew if '\u0590' <= c <= '\u05FF')
        ratio = hebrew_chars / len(hebrew) if len(hebrew) > 0 else 0
        
        if ratio < 0.5:
            return True, f"Not mostly Hebrew ({ratio:.0%}) - suspicious"
    
    return False, "OK"


def clean_dictionary():
    """Clean bad entries from dictionary"""
    
    print("="*80)
    print("DICTIONARY CLEANER")
    print("="*80)
    print()
    
    # Check if file exists
    if not DICT_FILE.exists():
        print(f"❌ Dictionary not found: {DICT_FILE}")
        return
    
    # Load dictionary
    print(f"Loading dictionary from: {DICT_FILE}")
    with open(DICT_FILE, 'r', encoding='utf-8') as f:
        dict_data = json.load(f)
    
    print(f"  ✓ Loaded {len(dict_data)} total entries")
    print()
    
    # Analyze entries
    print("Analyzing entries...")
    print()
    
    bad_entries = []
    source_counts = {}
    
    for key, entry in dict_data.items():
        source = entry.get('source', 'unknown')
        source_counts[source] = source_counts.get(source, 0) + 1
        
        is_bad, reason = is_bad_entry(key, entry)
        if is_bad:
            bad_entries.append((key, entry, reason))
    
    # Show statistics
    print("Current dictionary breakdown by source:")
    print("-"*60)
    for source, count in sorted(source_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  {source:20s}: {count:4d} entries")
    print()
    
    # Show bad entries
    if not bad_entries:
        print("✅ No bad entries found! Dictionary is clean.")
        return
    
    print(f"Found {len(bad_entries)} bad entries:")
    print("="*80)
    print()
    
    for i, (key, entry, reason) in enumerate(bad_entries[:20], 1):
        hebrew = entry['hebrew']
        source = entry['source']
        
        print(f"[{i}] '{key}'")
        print(f"    Source: {source}")
        print(f"    Hebrew: {hebrew[:60]}{'...' if len(hebrew) > 60 else ''}")
        print(f"    Reason: {reason}")
        print()
    
    if len(bad_entries) > 20:
        print(f"... and {len(bad_entries) - 20} more")
        print()
    
    # Confirm
    print("="*80)
    print(f"This will REMOVE {len(bad_entries)} entries")
    print(f"Keeping {len(dict_data) - len(bad_entries)} good entries")
    print()
    
    response = input("Continue? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("Cancelled.")
        return
    
    # Backup
    print()
    print("Creating backup...")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = BACKUP_DIR / f"dict_before_clean_{timestamp}.json"
    
    with open(backup_file, 'w', encoding='utf-8') as f:
        json.dump(dict_data, f, ensure_ascii=False, indent=2)
    
    print(f"  ✓ Backup saved: {backup_file}")
    
    # Remove bad entries
    print()
    print("Removing bad entries...")
    for key, entry, reason in bad_entries:
        del dict_data[key]
    
    # Save cleaned dictionary
    with open(DICT_FILE, 'w', encoding='utf-8') as f:
        json.dump(dict_data, f, ensure_ascii=False, indent=2)
    
    print(f"  ✓ Cleaned dictionary saved: {DICT_FILE}")
    print()
    
    # Summary
    print("="*80)
    print("CLEANING COMPLETE")
    print("="*80)
    print()
    print(f"Entries before: {len(dict_data) + len(bad_entries)}")
    print(f"Entries removed: {len(bad_entries)}")
    print(f"Entries after: {len(dict_data)}")
    print()
    print("✅ Dictionary is now clean!")
    print()
    print("Backup location:", backup_file)


if __name__ == "__main__":
    clean_dictionary()