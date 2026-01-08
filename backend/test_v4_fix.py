"""
Quick test for V4.4 Pure English Query Fix
==========================================

Tests that "sources for women covering hair" is correctly identified
as a pure English query and NOT transliterated into Hebrew gibberish.
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from step_one_decipher import decipher, is_pure_english_query, is_mixed_query, ENGLISH_MARKERS


def test_english_markers():
    """Test that critical English words are in ENGLISH_MARKERS."""
    print("\n=== Testing ENGLISH_MARKERS ===")

    critical_words = ['sources', 'women', 'covering', 'hair', 'for']

    for word in critical_words:
        in_markers = word in ENGLISH_MARKERS
        status = "[OK]" if in_markers else "[MISSING!]"
        print(f"  '{word}': {status}")

    # Count how many critical words are markers
    count = sum(1 for w in critical_words if w in ENGLISH_MARKERS)
    print(f"\n  {count}/{len(critical_words)} critical words are in ENGLISH_MARKERS")

    return count >= 3  # At least 3 should be markers


def test_pure_english_detection():
    """Test is_pure_english_query() function."""
    print("\n=== Testing is_pure_english_query() ===")

    test_cases = [
        # Pure English queries - should return True
        ("sources for women covering hair", True),
        ("what is the law about eating on Yom Kippur", True),
        ("why do we light candles on Shabbat", True),
        ("obligation for married women to cover hair", True),

        # Mixed queries - should return False
        ("what is chezkas haguf", False),
        ("explain bari vishema", False),
        ("sources for kisui rosh", False),
        ("tosfos shittah on chometz", False),

        # Pure transliteration - should return False
        ("chezkas haguf", False),
        ("bari vishema", False),
        ("migu", False),
    ]

    all_passed = True
    for query, expected in test_cases:
        result = is_pure_english_query(query)
        status = "[OK]" if result == expected else "[WRONG!]"
        print(f"  '{query}': {result} (expected {expected}) {status}")
        if result != expected:
            all_passed = False

    return all_passed


def test_mixed_query_detection():
    """Test is_mixed_query() function."""
    print("\n=== Testing is_mixed_query() ===")

    test_cases = [
        ("sources for women covering hair", True),   # Now has 5 English markers
        ("what is chezkas haguf", True),             # Has 2+ English markers
        ("chezkas haguf", False),                    # Pure transliteration
        ("migu", False),                             # Single term
    ]

    for query, expected in test_cases:
        result = is_mixed_query(query)
        status = "[OK]" if result == expected else "[WRONG]"
        print(f"  '{query}': {result} (expected {expected}) {status}")


async def test_decipher():
    """Test the full decipher function."""
    print("\n=== Testing decipher() ===")

    test_queries = [
        "sources for women covering hair",  # Should be pure English
        "what is chezkas haguf",            # Mixed - should extract Hebrew
        "chezkas haguf",                    # Pure transliteration
    ]

    for query in test_queries:
        print(f"\n  Query: '{query}'")
        result = await decipher(query)

        print(f"    Success: {result.success}")
        print(f"    Method: {result.method}")
        # Handle Hebrew output encoding safely
        hebrew_term = result.hebrew_term or "None"
        hebrew_terms = result.hebrew_terms or []
        try:
            print(f"    Hebrew term: {hebrew_term}")
            print(f"    Hebrew terms: {hebrew_terms}")
        except UnicodeEncodeError:
            print(f"    Hebrew term: [Hebrew text - {len(str(hebrew_term))} chars]")
            print(f"    Hebrew terms: [{len(hebrew_terms)} terms]")
        print(f"    Is pure English: {getattr(result, 'is_pure_english', False)}")
        print(f"    Message: {result.message}")

        # Validate "sources for women covering hair"
        if query == "sources for women covering hair":
            is_pure_english = getattr(result, 'is_pure_english', False)
            if is_pure_english:
                print("    [OK] Correctly identified as pure English!")
            else:
                print("    [ERROR] Should be pure English, but wasn't detected!")


async def main():
    print("=" * 60)
    print("V4.4 Pure English Query Fix - Test Suite")
    print("=" * 60)

    # Run tests
    markers_ok = test_english_markers()
    pure_english_ok = test_pure_english_detection()
    test_mixed_query_detection()
    await test_decipher()

    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  ENGLISH_MARKERS: {'[PASS]' if markers_ok else '[FAIL]'}")
    print(f"  Pure English Detection: {'[PASS]' if pure_english_ok else '[FAIL]'}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
