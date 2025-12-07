"""
Console Tester for Transliteration System
==========================================

Interactive tool for manually testing transliteration.
Run this file directly to enter test mode.

Usage:
    python console_tester.py

Commands:
    - Type any transliteration to see Hebrew variants
    - Type 'q' or 'quit' to exit
    - Type 'debug <word>' to see detailed pattern detection
    - Type 'prefix <word>' to test prefix detection
    - Type 'rules <word>' to see which rules fired
"""

import sys
from pathlib import Path

# Import the transliteration engine
try:
    from tools.transliteration_map import (
        generate_smart_variants,
        normalize_input,
        detect_ayin_patterns,
        detect_aramaic_ending,
        detect_smichut_ending,
        detect_feminine_ending,
        detect_final_bet,
        detect_double_consonants,
        detect_prefix,
        split_all_prefixes,
        MINIMAL_EXCEPTIONS,
        transliteration_confidence,
    )
except ImportError:
    # Try relative import
    sys.path.insert(0, str(Path(__file__).parent))
    from tools.transliteration_map import (
        generate_smart_variants,
        normalize_input,
        detect_ayin_patterns,
        detect_aramaic_ending,
        detect_smichut_ending,
        detect_feminine_ending,
        detect_final_bet,
        detect_double_consonants,
        detect_prefix,
        split_all_prefixes,
        MINIMAL_EXCEPTIONS,
        transliteration_confidence,
    )


def print_header():
    """Print welcome header."""
    print("\n" + "=" * 60)
    print("  TRANSLITERATION CONSOLE TESTER")
    print("  Rules-Based Hebrew Transliteration Engine")
    print("=" * 60)
    print("\nCommands:")
    print("  <word>        - Transliterate a word/phrase")
    print("  debug <word>  - Show pattern detection details")
    print("  prefix <word> - Test prefix detection")
    print("  rules <word>  - Show which rules fired")
    print("  q / quit      - Exit")
    print("=" * 60 + "\n")


def debug_word(word: str):
    """Show detailed pattern detection for a word."""
    print(f"\n--- Debug: '{word}' ---")
    
    # Normalize
    normalized = normalize_input(word)
    print(f"Normalized: '{normalized}'")
    
    # Check exceptions
    if normalized in MINIMAL_EXCEPTIONS:
        print(f"⚡ EXCEPTION HIT: {MINIMAL_EXCEPTIONS[normalized]}")
        return
    
    # Ayin patterns
    ayin = detect_ayin_patterns(normalized)
    if ayin:
        print(f"\n🔍 Ayin Patterns Detected:")
        for p in ayin:
            print(f"   - {p.pattern_type} at pos {p.position}: '{normalized[p.position:p.position+p.length]}' → {p.likely_hebrew} (conf: {p.confidence:.2f})")
    else:
        print(f"\n🔍 Ayin Patterns: None detected")
    
    # Aramaic ending
    aramaic = detect_aramaic_ending(normalized)
    if aramaic:
        print(f"\n🔍 Aramaic Ending Detected:")
        print(f"   - {aramaic.pattern_type}: '{normalized[aramaic.position:]}' → {aramaic.likely_hebrew} (conf: {aramaic.confidence:.2f})")
    else:
        print(f"\n🔍 Aramaic Ending: None detected")
    
    # Smichut ending (saf)
    smichut = detect_smichut_ending(normalized)
    if smichut:
        print(f"\n🔍 Smichut Ending (Saf) Detected:")
        print(f"   - {smichut.pattern_type}: final 's' → {smichut.likely_hebrew} (conf: {smichut.confidence:.2f})")
    else:
        print(f"\n🔍 Smichut Ending: None detected")
    
    # Feminine ending
    feminine = detect_feminine_ending(normalized)
    if feminine:
        print(f"\n🔍 Feminine Ending Detected:")
        print(f"   - {feminine.pattern_type}: final 'a' → {feminine.likely_hebrew} (conf: {feminine.confidence:.2f})")
    else:
        print(f"\n🔍 Feminine Ending: None detected")
    
    # Final bet
    final_b = detect_final_bet(normalized)
    if final_b:
        print(f"\n🔍 Final Bet Detected:")
        print(f"   - {final_b.pattern_type}: final 'v' → {final_b.likely_hebrew} (conf: {final_b.confidence:.2f})")
    else:
        print(f"\n🔍 Final Bet: None detected")
    
    # Double consonants
    doubles = detect_double_consonants(normalized)
    if doubles:
        print(f"\n🔍 Double Consonants Detected:")
        for p in doubles:
            print(f"   - {p.pattern_type}: '{normalized[p.position:p.position+p.length]}' → {p.likely_hebrew} (conf: {p.confidence:.2f})")
    else:
        print(f"\n🔍 Double Consonants: None detected")
    
    # Prefix detection
    prefix_heb, root = split_all_prefixes(normalized)
    if prefix_heb:
        print(f"\n🔍 Prefix Detection:")
        print(f"   - Hebrew prefix: '{prefix_heb}'")
        print(f"   - Remaining root: '{root}'")
    else:
        print(f"\n🔍 Prefix Detection: No prefix found")
    
    # Final variants
    variants = generate_smart_variants(normalized)
    print(f"\n📝 Generated Variants ({len(variants)}):")
    for i, v in enumerate(variants[:10], 1):
        print(f"   {i}. {v}")


def test_prefix(word: str):
    """Test prefix detection on a word."""
    print(f"\n--- Prefix Test: '{word}' ---")
    
    normalized = normalize_input(word)
    
    # Single prefix detection
    eng, heb, remaining = detect_prefix(normalized)
    if eng:
        print(f"Single prefix: '{eng}' ({heb}) + '{remaining}'")
    else:
        print(f"Single prefix: None detected")
    
    # Full split
    all_heb, root = split_all_prefixes(normalized)
    print(f"Full split: '{all_heb}' + '{root}'")


def show_rules(word: str):
    """Show which rules fired for a word."""
    print(f"\n--- Rules Analysis: '{word}' ---")
    
    normalized = normalize_input(word)
    words = normalized.split()
    
    for w in words:
        print(f"\nWord: '{w}'")
        
        # Check exception
        if w in MINIMAL_EXCEPTIONS:
            print(f"  ⚡ Exception: {MINIMAL_EXCEPTIONS[w]}")
            continue
        
        rules_fired = []
        
        # Ayin rules
        ayin = detect_ayin_patterns(w)
        for p in ayin:
            rules_fired.append(f"AYIN_{p.pattern_type.upper()}: pos {p.position}")
        
        # Aramaic
        aramaic = detect_aramaic_ending(w)
        if aramaic:
            rules_fired.append(f"ARAMAIC_ENDING: {aramaic.pattern_type}")
        
        # Smichut
        smichut = detect_smichut_ending(w)
        if smichut:
            rules_fired.append(f"SMICHUT_SAF: final 's' → ת")
        
        # Feminine
        feminine = detect_feminine_ending(w)
        if feminine:
            rules_fired.append(f"FEMININE_HEY: final 'a' → ה")
        
        # Final bet
        final_b = detect_final_bet(w)
        if final_b:
            rules_fired.append(f"FINAL_BET: final 'v' → ב")
        
        # Doubles
        doubles = detect_double_consonants(w)
        for p in doubles:
            rules_fired.append(f"DOUBLE: {w[p.position:p.position+2]} → {p.likely_hebrew}")
        
        # Prefix
        prefix_heb, root = split_all_prefixes(w)
        if prefix_heb:
            rules_fired.append(f"PREFIX: {prefix_heb}")
        
        if rules_fired:
            print(f"  Rules fired:")
            for rule in rules_fired:
                print(f"    → {rule}")
        else:
            print(f"  No special rules fired (basic transliteration)")


def transliterate(query: str):
    """Main transliteration function with nice output."""
    normalized = normalize_input(query)
    confidence = transliteration_confidence(normalized)
    variants = generate_smart_variants(normalized)
    
    print(f"\n📝 Input: '{query}'")
    if normalized != query.lower():
        print(f"   Normalized: '{normalized}'")
    print(f"   Confidence: {confidence}")
    print(f"\n🔤 Hebrew Variants ({len(variants)}):")
    
    for i, variant in enumerate(variants[:10], 1):
        marker = "→" if i == 1 else " "
        print(f"   {marker} {i}. {variant}")
    
    if len(variants) > 10:
        print(f"   ... and {len(variants) - 10} more")


def main():
    """Main interactive loop."""
    print_header()
    
    while True:
        try:
            user_input = input("\n🔹 Enter transliteration: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nGoodbye!")
            break
        
        if not user_input:
            continue
        
        # Check for commands
        lower_input = user_input.lower()
        
        if lower_input in ('q', 'quit', 'exit'):
            print("\nGoodbye!")
            break
        
        if lower_input.startswith('debug '):
            word = user_input[6:].strip()
            if word:
                debug_word(word)
            else:
                print("Usage: debug <word>")
            continue
        
        if lower_input.startswith('prefix '):
            word = user_input[7:].strip()
            if word:
                test_prefix(word)
            else:
                print("Usage: prefix <word>")
            continue
        
        if lower_input.startswith('rules '):
            word = user_input[6:].strip()
            if word:
                show_rules(word)
            else:
                print("Usage: rules <word>")
            continue
        
        # Regular transliteration
        transliterate(user_input)


if __name__ == "__main__":
    main()