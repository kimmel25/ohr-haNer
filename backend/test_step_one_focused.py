"""
Test Suite for Step 1: DECIPHER - FOCUSED ON STEPS 2 & 3
==========================================================

This test suite focuses on testing:
- Step 2: Transliteration (smart variant generation)
- Step 3: Vector search + Claude verification

Only 10 dictionary tests for quick validation.
"""

import asyncio
import sys
import logging
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from step_one_decipher import decipher
from tools.word_dictionary import get_dictionary


# ==========================================
#  TEST-SPECIFIC LOGGING SETUP
# ==========================================

def setup_test_logging():
    """Set up dedicated logging for test runs"""
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"test_step_one_focused_{timestamp}.log"

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%H:%M:%S'
    )

    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    root_logger.handlers.clear()
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    print(f"\n{'='*80}")
    print(f"FOCUSED TEST SUITE - STEPS 2 & 3")
    print(f"{'='*80}")
    print(f"Log file: {log_file}")
    print(f"Testing: Transliteration + Vector Search (not dictionary)")
    print(f"{'='*80}\n")

    return log_file


# ==========================================
#  TEST CASES - FOCUSED ON STEPS 2 & 3
# ==========================================

TEST_CASES = [
    # ========================================
    # GROUP 1: DICTIONARY VALIDATION (10 tests)
    # ========================================
    # Quick check that consolidated dictionary works
    {
        "query": "kesubos",
        "expected_hebrew": "כתובות",
        "expected_method": "dictionary",
        "description": "Masechta (in dict after consolidation)"
    },
    {
        "query": "gittin",
        "expected_hebrew": "גיטין",
        "expected_method": "dictionary",
        "description": "Masechta (in dict)"
    },
    {
        "query": "eruvin",
        "expected_hebrew": "עירובין",
        "expected_method": "dictionary",
        "description": "Masechta (in dict)"
    },
    {
        "query": "bava kama",
        "expected_hebrew": "בבא קמא",
        "expected_method": "dictionary",
        "description": "Masechta (in dict)"
    },
    {
        "query": "bereirah",
        "expected_hebrew": "ברירה",
        "expected_method": "dictionary",
        "description": "Common concept (in dict)"
    },
    {
        "query": "sfek sfeika",
        "expected_hebrew": "ספק ספיקא",
        "expected_method": "dictionary",
        "description": "Double doubt (in dict)"
    },
    {
        "query": "safek safeika",
        "expected_hebrew": "ספק ספיקא",
        "expected_method": "dictionary",
        "description": "Alt spelling (in dict)"
    },
    {
        "query": "bitul chametz",
        "expected_hebrew": "ביטול חמץ",
        "expected_method": "dictionary",
        "description": "Pesach concept (in dict)"
    },
    {
        "query": "chezkas haguf",
        "expected_hebrew": "חזקת הגוף",
        "expected_method": "dictionary",
        "description": "Kesubos concept (in dict)"
    },
    {
        "query": "chatzi shiur",
        "expected_hebrew": "חצי שיעור",
        "expected_method": "dictionary",
        "description": "Half measure (in dict)"
    },

    # ========================================
    # GROUP 2: TRANSLITERATION TESTS (15 tests)
    # ========================================
    # These are NOT in dictionary - test smart variant generation
    {
        "query": "migu",
        "expected_hebrew": "מיגו",
        "expected_method": "any",
        "description": "Since he could have said - simple transliteration"
    },
    {
        "query": "umdena",
        "expected_hebrew": "אומדנא",
        "expected_method": "any",
        "description": "Assessment - word-initial vowel test"
    },
    {
        "query": "kdai shiur",
        "expected_hebrew": "כדי שיעור",
        "expected_method": "any",
        "description": "K vs K' - multi-word transliteration"
    },
    {
        "query": "trei vetrei",
        "expected_hebrew": "תרי ותרי",
        "expected_method": "any",
        "description": "Aramaic - two and two"
    },
    {
        "query": "lo plug",
        "expected_hebrew": "לא פלוג",
        "expected_method": "any",
        "description": "Don't distinguish - simple phrase"
    },
    {
        "query": "chozer vniur",
        "expected_hebrew": "חוזר ונעור",
        "expected_method": "any",
        "description": "Awakens again - ch, v, n sounds"
    },
    {
        "query": "kdai achila",
        "expected_hebrew": "כדי אכילה",
        "expected_method": "any",
        "description": "Measure of eating - k, ch sounds"
    },
    {
        "query": "ribui umiut",
        "expected_hebrew": "ריבוי ומיעוט",
        "expected_method": "any",
        "description": "Inclusion and exclusion - vowel test"
    },
    {
        "query": "klal uprat",
        "expected_hebrew": "כלל ופרט",
        "expected_method": "any",
        "description": "General and specific - standard phrase"
    },
    {
        "query": "kal vchomer",
        "expected_hebrew": "קל וחומר",
        "expected_method": "any",
        "description": "A fortiori - standard logic term"
    },
    {
        "query": "gezeira shava",
        "expected_hebrew": "גזירה שווה",
        "expected_method": "any",
        "description": "Textual analogy - g, z, sh sounds"
    },
    {
        "query": "binyan av",
        "expected_hebrew": "בנין אב",
        "expected_method": "any",
        "description": "Paradigm - word-initial vowel"
    },
    {
        "query": "davar halamd meinyano",
        "expected_hebrew": "דבר הלמד מעניינו",
        "expected_method": "any",
        "description": "Learned from context - complex phrase"
    },
    {
        "query": "tzad hashaveh",
        "expected_hebrew": "צד השווה",
        "expected_method": "any",
        "description": "Common side - tz sound"
    },
    {
        "query": "shnei kesuvim",
        "expected_hebrew": "שני כתובים",
        "expected_method": "any",
        "description": "Two verses - sh, s sounds"
    },

    # ========================================
    # GROUP 3: VECTOR SEARCH TESTS (15 tests)
    # ========================================
    # Complex phrases that need vector matching
    {
        "query": "chaticha deisura",
        "expected_hebrew": "חתיכה דאיסורא",
        "expected_method": "any",
        "description": "Piece of forbidden - Aramaic"
    },
    {
        "query": "kol davar sheyesh lo matirin",
        "expected_hebrew": "כל דבר שיש לו מתירין",
        "expected_method": "any",
        "description": "Anything that will become permitted"
    },
    {
        "query": "zeh neheneh vzeh lo chaser",
        "expected_hebrew": "זה נהנה וזה לא חסר",
        "expected_method": "any",
        "description": "One benefits, other loses nothing"
    },
    {
        "query": "ain shliach lidvar aveirah",
        "expected_hebrew": "אין שליח לדבר עבירה",
        "expected_method": "any",
        "description": "No agency for sin"
    },
    {
        "query": "kol deparish mrubo parish",
        "expected_hebrew": "כל דפריש מרובא פריש",
        "expected_method": "any",
        "description": "What separates comes from majority"
    },
    {
        "query": "rov deparish",
        "expected_hebrew": "רוב דפריש",
        "expected_method": "any",
        "description": "Majority of what separates"
    },
    {
        "query": "davar shelo ba lolam",
        "expected_hebrew": "דבר שלא בא לעולם",
        "expected_method": "any",
        "description": "Something not yet in existence"
    },
    {
        "query": "kim lei dirabanan",
        "expected_hebrew": "קים ליה דרבנן",
        "expected_method": "any",
        "description": "Principle in rabbinic law"
    },
    {
        "query": "eid echad neeman bissurim",
        "expected_hebrew": "עד אחד נאמן באיסורים",
        "expected_method": "any",
        "description": "One witness believed for prohibitions"
    },
    {
        "query": "ain adam oser davar shelo ba lolam",
        "expected_hebrew": "אין אדם אוסר דבר שלא בא לעולם",
        "expected_method": "any",
        "description": "Cannot prohibit what doesn't exist - long phrase"
    },
    {
        "query": "mvazeh es chaveiro",
        "expected_hebrew": "מבזה את חברו",
        "expected_method": "any",
        "description": "Embarrasses his friend - 'es' particle"
    },
    {
        "query": "hasam es piv",
        "expected_hebrew": "חסם את פיו",
        "expected_method": "any",
        "description": "Muzzle its mouth - 'es' particle"
    },
    {
        "query": "hafkaas kiddushin",
        "expected_hebrew": "הפקעת קידושין",
        "expected_method": "any",
        "description": "Annulling marriage - apostrophe variant"
    },
    {
        "query": "chalipin kinyan",
        "expected_hebrew": "חליפין קנין",
        "expected_method": "any",
        "description": "Exchange acquisition"
    },
    {
        "query": "meshicha kinyan",
        "expected_hebrew": "משיכה קנין",
        "expected_method": "any",
        "description": "Pulling acquisition"
    },

    # ========================================
    # GROUP 4: AMBIGUOUS (5 tests - should request clarification)
    # ========================================
    {
        "query": "chezka",
        "expected_hebrew": None,
        "expected_method": "clarification",
        "description": "Ambiguous - could be many things"
    },
    {
        "query": "niddah",
        "expected_hebrew": "נדה",
        "expected_method": "any",
        "description": "Could mean masechta or state - single word"
    },
    {
        "query": "taref",
        "expected_hebrew": None,
        "expected_method": "clarification",
        "description": "Torn animal or non-kosher"
    },
    {
        "query": "klal",
        "expected_hebrew": None,
        "expected_method": "clarification",
        "description": "General rule or community"
    },
    {
        "query": "din",
        "expected_hebrew": None,
        "expected_method": "clarification",
        "description": "Too general - law, judgment, etc."
    },

    # ========================================
    # GROUP 5: DIFFICULT/STRESS TEST (5 tests)
    # ========================================
    {
        "query": "kol hameshaneh mimatas chachamim yadov al hatachtonah",
        "expected_hebrew": "כל המשנה ממטבע חכמים ידו על התחתונה",
        "expected_method": "any",
        "description": "Very long phrase about formulas"
    },
    {
        "query": "ain adam makneh davar shelo ba lolam",
        "expected_hebrew": "אין אדם מקנה דבר שלא בא לעולם",
        "expected_method": "any",
        "description": "Cannot transfer what doesn't exist"
    },
    {
        "query": "yachol shema michlal hen ata shomea lav",
        "expected_hebrew": "יכול שמע מכלל הן אתה שומע לאו",
        "expected_method": "any",
        "description": "Complex logical phrase"
    },
    {
        "query": "adam muad leolam",
        "expected_hebrew": "אדם מועד לעולם",
        "expected_method": "any",
        "description": "Person always liable - standard phrase"
    },
    {
        "query": "shor hamuad shenagach",
        "expected_hebrew": "שור המועד שנגח",
        "expected_method": "any",
        "description": "Warned ox that gored - damages"
    },
]


# ==========================================
#  TEST RUNNER
# ==========================================

async def run_test(test_case: dict) -> dict:
    """Run a single test case"""
    query = test_case["query"]
    expected_hebrew = test_case.get("expected_hebrew")
    expected_method = test_case.get("expected_method")
    description = test_case.get("description", "")

    print(f"\n🔍 {query}")
    print(f"   {description}")

    result = await decipher(query)

    # Check if test passed
    test_passed = False

    if expected_method == "clarification":
        # Should need clarification
        test_passed = result.get("needs_clarification", False) or not result.get("success", True)
    elif expected_method == "any":
        # Just check if it succeeded (any method OK)
        test_passed = result.get("success", False)
    else:
        # Check specific method and hebrew match
        if result.get("success"):
            method_match = result.get("method") == expected_method
            hebrew_match = expected_hebrew is None or result.get("hebrew_term") == expected_hebrew
            test_passed = method_match and hebrew_match

    # Print result
    if test_passed:
        method = result.get("method", "unknown")
        hebrew = result.get("hebrew_term", "N/A")
        print(f"   ✓ PASS via {method}: {hebrew}")
    else:
        print(f"   ✗ FAIL")
        print(f"     Got: {result}")

    return {
        "test": description,
        "query": query,
        "passed": test_passed,
        "result": result
    }


async def run_all_tests():
    """Run all test cases"""
    log_file = setup_test_logging()

    print("=" * 80)
    print("FOCUSED TEST SUITE - TRANSLITERATION + VECTOR SEARCH")
    print("=" * 80)
    print(f"Total tests: {len(TEST_CASES)}")
    print()

    # Get dictionary stats
    dictionary = get_dictionary()
    stats = dictionary.get_stats()
    print(f"Dictionary: {stats['total_entries']} entries")
    print(f"  By source: {stats['by_source']}")
    print()

    # Run tests
    results = []
    for test_case in TEST_CASES:
        result = await run_test(test_case)
        results.append(result)

    # Summary
    passed = sum(1 for r in results if r["passed"])
    total = len(results)

    print(f"\n{'='*80}")
    print(f"RESULTS: {passed}/{total} ({passed/total*100:.1f}%)")
    print(f"{'='*80}")

    # Group results
    groups = {
        "Dictionary Validation": list(range(0, 10)),
        "Transliteration (Step 2)": list(range(10, 25)),
        "Vector Search (Step 3)": list(range(25, 40)),
        "Ambiguous": list(range(40, 45)),
        "Difficult/Stress": list(range(45, 50)),
    }

    print("\n📊 Results by group:")
    for group_name, indices in groups.items():
        group_results = [results[i] for i in indices if i < len(results)]
        group_passed = sum(1 for r in group_results if r["passed"])
        group_total = len(group_results)
        print(f"  {group_name}: {group_passed}/{group_total}")

    # Failed tests
    failed = [r for r in results if not r["passed"]]
    if failed:
        print(f"\n❌ Failed tests ({len(failed)}):")
        for r in failed:
            print(f"  - {r['test']}: '{r['query']}'")

    print(f"\n{'='*80}")
    print(f"Detailed logs: {log_file}")
    print(f"{'='*80}\n")

    return results


if __name__ == "__main__":
    asyncio.run(run_all_tests())
