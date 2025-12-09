"""
Clean and regenerate word_dictionary.json

Options:
1. Remove low-confidence auto-generated entries
2. Regenerate transliterations from Hebrew using better rules
3. Keep only curated/high-usage entries
"""

import json
import re
from pathlib import Path
from datetime import datetime

DICT_PATH = Path(__file__).parent.parent / "data" / "word_dictionary.json"
BACKUP_PATH = Path(__file__).parent.parent / "data" / "backups" / f"dict_before_clean_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"


def load_dictionary():
    """Load the current dictionary"""
    with open(DICT_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def backup_dictionary(data):
    """Create a backup before cleaning"""
    BACKUP_PATH.parent.mkdir(exist_ok=True)
    with open(BACKUP_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✓ Backed up to: {BACKUP_PATH.name}")


def save_dictionary(data):
    """Save cleaned dictionary"""
    with open(DICT_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def clean_strategy_1_remove_low_quality(data):
    """
    Strategy 1: Remove low-quality auto-generated entries
    
    Keeps:
    - High confidence entries from any source
    - Medium confidence with usage_count > 0
    - All manual/curated sources (notes, yeshivish_consolidated, user_confirmed)
    
    Removes:
    - Low confidence sefaria entries with no usage
    - Medium confidence sefaria entries with no usage
    """
    good_sources = {"notes", "yeshivish_consolidated", "user_confirmed", "manual"}
    
    cleaned = {}
    removed_count = 0
    
    for key, entry in data.items():
        source = entry.get("source", "")
        confidence = entry.get("confidence", "low")
        usage = entry.get("usage_count", 0)
        
        # Keep if from good source
        if source in good_sources:
            cleaned[key] = entry
            continue
        
        # Keep if high confidence
        if confidence == "high":
            cleaned[key] = entry
            continue
        
        # Keep if actually used
        if usage > 0:
            cleaned[key] = entry
            continue
        
        # Otherwise, remove
        removed_count += 1
        print(f"Removing: '{key}' → {entry['hebrew']} (confidence={confidence}, usage={usage}, source={source})")
    
    print(f"\n✓ Removed {removed_count} low-quality entries")
    print(f"✓ Kept {len(cleaned)} entries")
    
    return cleaned


def clean_strategy_2_remove_all_sefaria(data):
    """
    Strategy 2: Remove ALL auto-generated sefaria entries
    
    Only keeps manually curated entries (notes, yeshivish_consolidated, user_confirmed)
    """
    good_sources = {"notes", "yeshivish_consolidated", "user_confirmed", "manual"}
    
    cleaned = {}
    removed_count = 0
    
    for key, entry in data.items():
        source = entry.get("source", "")
        
        if source in good_sources:
            cleaned[key] = entry
        else:
            removed_count += 1
    
    print(f"\n✓ Removed {removed_count} auto-generated entries")
    print(f"✓ Kept {len(cleaned)} curated entries")
    
    return cleaned


def clean_strategy_3_keep_used_only(data):
    """
    Strategy 3: Keep only entries that have been used
    
    Removes anything with usage_count = 0
    """
    cleaned = {}
    removed_count = 0
    
    for key, entry in data.items():
        usage = entry.get("usage_count", 0)
        
        if usage > 0:
            cleaned[key] = entry
        else:
            removed_count += 1
    
    print(f"\n✓ Removed {removed_count} unused entries")
    print(f"✓ Kept {len(cleaned)} used entries")
    
    return cleaned


def show_stats(data):
    """Show statistics about the dictionary"""
    total = len(data)
    by_source = {}
    by_confidence = {}
    by_usage = {"unused": 0, "used_1-5": 0, "used_6+": 0}
    
    for entry in data.values():
        source = entry.get("source", "unknown")
        confidence = entry.get("confidence", "unknown")
        usage = entry.get("usage_count", 0)
        
        by_source[source] = by_source.get(source, 0) + 1
        by_confidence[confidence] = by_confidence.get(confidence, 0) + 1
        
        if usage == 0:
            by_usage["unused"] += 1
        elif usage <= 5:
            by_usage["used_1-5"] += 1
        else:
            by_usage["used_6+"] += 1
    
    print("\n" + "=" * 60)
    print(f"DICTIONARY STATS: {total} entries")
    print("=" * 60)
    
    print("\nBy Source:")
    for source, count in sorted(by_source.items(), key=lambda x: -x[1]):
        print(f"  {source:30} {count:4} entries")
    
    print("\nBy Confidence:")
    for conf, count in sorted(by_confidence.items(), key=lambda x: -x[1]):
        print(f"  {conf:30} {count:4} entries")
    
    print("\nBy Usage:")
    for usage_cat, count in sorted(by_usage.items(), key=lambda x: -x[1]):
        print(f"  {usage_cat:30} {count:4} entries")
    
    print("=" * 60)


if __name__ == "__main__":
    print("WORD DICTIONARY CLEANER")
    print("=" * 60)
    
    # Load current dictionary
    data = load_dictionary()
    print(f"Loaded {len(data)} entries")
    
    # Show stats
    show_stats(data)
    
    # Choose strategy
    print("\nCleaning Strategies:")
    print("1. Remove low-quality entries (low confidence + no usage)")
    print("2. Remove ALL auto-generated (sefaria) entries")
    print("3. Keep only used entries (usage_count > 0)")
    print("4. Just show stats (no changes)")
    
    choice = input("\nSelect strategy (1-4): ").strip()
    
    if choice == "1":
        backup_dictionary(data)
        cleaned = clean_strategy_1_remove_low_quality(data)
        save_dictionary(cleaned)
        print("\n✓ Dictionary cleaned!")
        show_stats(cleaned)
        
    elif choice == "2":
        backup_dictionary(data)
        cleaned = clean_strategy_2_remove_all_sefaria(data)
        save_dictionary(cleaned)
        print("\n✓ Dictionary cleaned!")
        show_stats(cleaned)
        
    elif choice == "3":
        backup_dictionary(data)
        cleaned = clean_strategy_3_keep_used_only(data)
        save_dictionary(cleaned)
        print("\n✓ Dictionary cleaned!")
        show_stats(cleaned)
        
    elif choice == "4":
        print("\n✓ No changes made")
    
    else:
        print("Invalid choice")
