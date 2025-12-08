"""
Console Tester for Transliteration System (V2)
==============================================

Interactive tool for manually testing transliteration WITH USER VALIDATION.

Usage:
    python console_tester.py

Commands:
    - Type any transliteration to see Hebrew variants
    - Type 'q' or 'quit' to exit
    - Type 'debug <word>' to see detailed pattern detection
    - Type 'rules <word>' to see which rules fired
    - Type 'strict <query>' to force validation even on medium confidence
    - Type 'json <query>' to see JSON output (for frontend testing)
    - Type 'wbw <query>' for word-by-word validation
"""

import sys
import json
from pathlib import Path

# Import validation module
try:
    from user_validation import (
        analyze_query,
        get_validation_prompt,
        apply_user_selection,
        validate_word_by_word,
        reconstruct_phrase,
        ValidationResult,
        ValidationType,
    )
    from tools.transliteration_map import (
        generate_smart_variants,
        normalize_input,
        detect_ayin_patterns,
        detect_aramaic_ending,
        detect_smichut_ending,
        detect_feminine_ending,
        detect_final_bet,
        detect_double_consonants,
        split_all_prefixes,
        MINIMAL_EXCEPTIONS,
    )
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent))
    from user_validation import (
        analyze_query,
        get_validation_prompt,
        apply_user_selection,
        validate_word_by_word,
        reconstruct_phrase,
        ValidationResult,
        ValidationType,
    )
    from tools.transliteration_map import (
        generate_smart_variants,
        normalize_input,
        detect_ayin_patterns,
        detect_aramaic_ending,
        detect_smichut_ending,
        detect_feminine_ending,
        detect_final_bet,
        detect_double_consonants,
        split_all_prefixes,
        MINIMAL_EXCEPTIONS,
    )


def print_header():
    """Print welcome header."""
    print("\n" + "=" * 60)
    print("  TRANSLITERATION CONSOLE TESTER (with Validation)")
    print("  Rules-Based Hebrew Transliteration Engine")
    print("=" * 60)
    print("\nCommands:")
    print("  <query>        - Transliterate with validation")
    print("  debug <word>   - Show pattern detection details")
    print("  rules <word>   - Show which rules fired")
    print("  strict <query> - Force validation prompt")
    print("  json <query>   - Show JSON output (for frontend)")
    print("  wbw <query>    - Word-by-word validation")
    print("  q / quit       - Exit")
    print("=" * 60 + "\n")


def debug_word(word: str):
    """Show detailed pattern detection for a word."""
    print(f"\n--- Debug: '{word}' ---")
    
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


def transliterate_with_validation(query: str, strict: bool = False) -> str:
    """
    Main transliteration function WITH user validation.
    Returns the final Hebrew result after any validation.
    """
    result = analyze_query(query, strict=strict)
    
    # Display initial info
    print(f"\n📝 Input: '{query}'")
    if result.normalized != query.lower():
        print(f"   Normalized: '{result.normalized}'")
    
    # Show confidence
    confidence_emoji = {"high": "🟢", "medium": "🟡", "low": "🔴"}
    emoji = confidence_emoji.get(result.confidence, "⚪")
    print(f"   Confidence: {emoji} {result.confidence} ({result.confidence_score:.2f})")
    
    # Show word breakdown if multi-word
    if len(result.word_validations) > 1:
        print(f"\n   Word breakdown:")
        for i, wv in enumerate(result.word_validations):
            marker = "⚠️ " if wv.needs_validation else "✓ "
            exc = " (exception)" if wv.is_exception else ""
            print(f"      {marker}'{wv.original}' → {wv.best_match}{exc}")
    
    # If no validation needed, show result and return
    if not result.needs_validation:
        print(f"\n🔤 Result: {result.best_match}")
        if len(result.all_variants) > 1:
            print(f"   Alternatives: {', '.join(result.all_variants[1:5])}")
        return result.best_match
    
    # Validation needed - prompt user
    print(f"\n⚠️  Validation needed ({result.validation_type.value})")
    print("-" * 40)
    
    prompt = get_validation_prompt(result, "console")
    print(prompt)
    
    # Get user selection
    while True:
        try:
            selection_input = input("\n🔹 Your choice (or 'skip' to use best guess): ").strip()
            
            if selection_input.lower() == 'skip':
                print(f"\n🔤 Using best guess: {result.best_match}")
                return result.best_match
            
            selection = int(selection_input)
            
            if selection == 0:
                # User said "none of these"
                print("\n❌ None selected. Please try a different spelling.")
                return ""
            
            selected = apply_user_selection(result, selection)
            if selected:
                print(f"\n🔤 Selected: {selected}")
                return selected
            else:
                print("Invalid selection. Please try again.")
                
        except ValueError:
            print("Please enter a number (1-5) or 'skip'.")
        except (EOFError, KeyboardInterrupt):
            print("\n\nSkipping validation.")
            return result.best_match


def show_json_output(query: str):
    """Show JSON output for frontend testing."""
    result = analyze_query(query)
    output = result.to_dict()
    print(f"\n--- JSON Output for '{query}' ---")
    print(json.dumps(output, indent=2, ensure_ascii=False))


def word_by_word_validation(query: str) -> str:
    """
    Validate a multi-word query word by word.
    Useful for complex phrases where one word is uncertain.
    """
    print(f"\n--- Word-by-Word Validation: '{query}' ---")
    
    word_results = validate_word_by_word(query)
    final_words = []
    
    for i, result in enumerate(word_results):
        print(f"\nWord {i+1}: '{result.query}'")
        
        if not result.needs_validation:
            print(f"  ✓ {result.best_match} (high confidence)")
            final_words.append(result.best_match)
        else:
            print(f"  ⚠️ Needs validation")
            prompt = get_validation_prompt(result, "console")
            print("  " + prompt.replace("\n", "\n  "))
            
            while True:
                try:
                    selection_input = input("  Your choice (or 'skip'): ").strip()
                    
                    if selection_input.lower() == 'skip':
                        final_words.append(result.best_match)
                        break
                    
                    selection = int(selection_input)
                    if selection == 0:
                        alt = input("  Enter correct Hebrew: ").strip()
                        if alt:
                            final_words.append(alt)
                        break
                    
                    selected = apply_user_selection(result, selection)
                    if selected:
                        final_words.append(selected)
                        break
                    else:
                        print("  Invalid selection.")
                except ValueError:
                    print("  Please enter a number or 'skip'.")
                except (EOFError, KeyboardInterrupt):
                    final_words.append(result.best_match)
                    break
    
    final_phrase = " ".join(final_words)
    print(f"\n🔤 Final result: {final_phrase}")
    return final_phrase


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
        
        if lower_input.startswith('rules '):
            word = user_input[6:].strip()
            if word:
                show_rules(word)
            else:
                print("Usage: rules <word>")
            continue
        
        if lower_input.startswith('strict '):
            query = user_input[7:].strip()
            if query:
                transliterate_with_validation(query, strict=True)
            else:
                print("Usage: strict <query>")
            continue
        
        if lower_input.startswith('json '):
            query = user_input[5:].strip()
            if query:
                show_json_output(query)
            else:
                print("Usage: json <query>")
            continue
        
        if lower_input.startswith('wbw '):
            query = user_input[4:].strip()
            if query:
                word_by_word_validation(query)
            else:
                print("Usage: wbw <multi-word query>")
            continue
        
        # Regular transliteration with validation
        transliterate_with_validation(user_input)


if __name__ == "__main__":
    main()