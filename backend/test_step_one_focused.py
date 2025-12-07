"""
Test Suite for Step 1: DECIPHER - CLAUDE-FREE TESTING
=======================================================

This test suite focuses on testing the Claude-free Step 1 system:
- 5 dictionary tests (quick validation)
- 35 transliteration + vector tests (NOT in dictionary)

All tests run with TEST_MODE=true to prevent dictionary pollution.
"""

import asyncio
import sys
import logging
import os
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# CRITICAL: Enable TEST_MODE before importing
os.environ["TEST_MODE"] = "true"

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
    print(f"CLAUDE-FREE TEST SUITE - Step 1: DECIPHER")
    print(f"{'='*80}")
    print(f"TEST_MODE: {os.environ.get('TEST_MODE', 'false')}")
    print(f"Log file: {log_file}")
    print(f"Testing: Dictionary → Transliteration → Vector (NO Claude)")
    print(f"{'='*80}\n")

    return log_file


# ==========================================
#  TEST CASES
# ==========================================

TEST_CASES = [
    # ========================================
    # GROUP 1: DICTIONARY VALIDATION (5 tests)
    # ========================================
    # Quick check that dictionary works
    {
        "query": "kesubos",
        "expected_hebrew": "כתובות",
        "expected_method": "dictionary",
        "description": "Masechta - dictionary hit"
    },
    {
        "query": "bava kama",
        "expected_hebrew": "בבא קמא",
        "expected_method": "dictionary",
        "description": "Masechta - two words"
    },
    {
        "query": "bereirah",
        "expected_hebrew": "ברירה",
        "expected_method": "dictionary",
        "description": "Common concept"
    },
    {
        "query": "sfek sfeika",
        "expected_hebrew": "ספק ספיקא",
        "expected_method": "dictionary",
        "description": "Double doubt"
    },
    {
        "query": "chatzi shiur",
        "expected_hebrew": "חצי שיעור",
        "expected_method": "dictionary",
        "description": "Half measure"
    },

    # ========================================
    # GROUP 2: TRANSLITERATION TESTS (20 tests)
    # ========================================
    # Terms NOT in dictionary - test smart variant generation
    {
        "query": "migu",
        "expected_hebrew": "מיגו",
        "expected_method": "any",
        "description": "Since he could have said"
    },
    {
        "query": "umdena",
        "expected_hebrew": "אומדנא",
        "expected_method": "any",
        "description": "Assessment - word-initial vowel"
    },
    {
        "query": "kdai shiur",
        "expected_hebrew": "כדי שיעור", #didt work cuz the ayin
        "expected_method": "any",
        "description": "K vs K' - sufficient measure"
    },
    {
        "query": "trei vetrei",
        "expected_hebrew": "תרי ותרי",  #
        "expected_method": "any",
        "description": "Aramaic - two and two"
    },
    {
        "query": "lo plug",
        "expected_hebrew": "לא פלוג",
        "expected_method": "any",
        "description": "Don't distinguish"
    },
    {
        "query": "chozer vniur",
        "expected_hebrew": "חוזר ונעור",
        "expected_method": "any",
        "description": "Awakens again"
    },
    {
        "query": "kdai achila",
        "expected_hebrew": "כדי אכילה",
        "expected_method": "any",
        "description": "Measure of eating"
    },
    {
        "query": "ribui umiut",
        "expected_hebrew": "ריבוי ומיעוט",
        "expected_method": "any",
        "description": "Inclusion and exclusion"
    },
    {
        "query": "klal uprat",
        "expected_hebrew": "כלל ופרט",
        "expected_method": "any",
        "description": "General and specific"
    },
    {
        "query": "kal vchomer",
        "expected_hebrew": "קל וחומר",
        "expected_method": "any",
        "description": "A fortiori"
    },
    {
        "query": "gezeira shava",
        "expected_hebrew": "גזירה שווה",
        "expected_method": "any",
        "description": "Textual analogy"
    },
    {
        "query": "binyan av",
        "expected_hebrew": "בנין אב",
        "expected_method": "any",
        "description": "Paradigm - building father"
    },
    {
        "query": "davar halamd meinyano",
        "expected_hebrew": "דבר הלמד מעניינו",
        "expected_method": "any",
        "description": "Learned from context"
    },
    {
        "query": "tzad hashaveh",
        "expected_hebrew": "צד השווה",
        "expected_method": "any",
        "description": "Common side"
    },
    {
        "query": "shnei kesuvim",
        "expected_hebrew": "שני כתובים",
        "expected_method": "any",
        "description": "Two verses"
    },
    {
        "query": "miktzas hayom kchulo",
        "expected_hebrew": "מקצת היום ככולו",
        "expected_method": "any",
        "description": "Part of day like whole"
    },
    {
        "query": "yad soledet bo",
        "expected_hebrew": "יד סולדת בו",
        "expected_method": "any",
        "description": "Hand recoils from heat"
    },
    {
        "query": "shiur kzayis",
        "expected_hebrew": "שיעור כזית",
        "expected_method": "any",
        "description": "Olive-sized measure"
    },
    {
        "query": "shiur kbeitza",
        "expected_hebrew": "שיעור כביצה",
        "expected_method": "any",
        "description": "Egg-sized measure"
    },
    {
        "query": "lavud",
        "expected_hebrew": "לבוד",
        "expected_method": "any",
        "description": "Principle of attachment"
    },

    # ========================================
    # GROUP 3: VECTOR SEARCH TESTS (15 tests)
    # ========================================
    # Complex phrases needing vector matching
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
        "description": "Rabbinic principle - greater liability"
    },
    {
        "query": "eid echad neeman bissurim",
        "expected_hebrew": "עד אחד נאמן באיסורים",
        "expected_method": "any",
        "description": "One witness believed for prohibitions"
    },
    {
        "query": "hafkaas kiddushin",
        "expected_hebrew": "הפקעת קידושין",
        "expected_method": "any",
        "description": "Annulling marriage"
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
    {
        "query": "adam muad leolam",
        "expected_hebrew": "אדם מועד לעולם",
        "expected_method": "any",
        "description": "Person always liable"
    },
    {
        "query": "shor hamuad shenagach",
        "expected_hebrew": "שור המועד שנגח",
        "expected_method": "any",
        "description": "Warned ox that gored"
    },
    {
        "query": "ain adam oser davar shelo ba lolam",
        "expected_hebrew": "אין אדם אוסר דבר שלא בא לעולם",
        "expected_method": "any",
        "description": "Cannot prohibit what doesn't exist"
    },
]


# ==========================================
#  TEST RUNNER
# ==========================================

async def run_test(test_case: dict, test_num: int) -> dict:
    """Run a single test case with detailed logging"""
    query = test_case["query"]
    expected_hebrew = test_case.get("expected_hebrew")
    expected_method = test_case.get("expected_method")
    description = test_case.get("description", "")

    print(f"\n[{test_num:2d}] {query}")
    print(f"     {description}")

    result = await decipher(query)

    # Determine test outcome
    test_passed = False
    actual_hebrew = result.get("hebrew_term", "N/A")
    actual_method = result.get("method", "unknown")
    actual_confidence = result.get("confidence", "N/A")

    if expected_method == "clarification":
        # Should need clarification
        test_passed = result.get("needs_clarification", False) or not result.get("success", True)
    elif expected_method == "any":
        # Just check if it succeeded (any method OK)
        test_passed = result.get("success", False)
        # Optionally check if Hebrew matches (if provided)
        if test_passed and expected_hebrew:
            # Allow partial match for complex phrases
            test_passed = expected_hebrew in actual_hebrew or actual_hebrew in expected_hebrew
    else:
        # Check specific method and hebrew match
        if result.get("success"):
            method_match = actual_method == expected_method
            hebrew_match = expected_hebrew is None or actual_hebrew == expected_hebrew
            test_passed = method_match and hebrew_match

    # Print result with evaluation details
    if test_passed:
        print(f"     ✓ PASS via {actual_method.upper()}: {actual_hebrew}")
        print(f"       Confidence: {actual_confidence}")
    else:
        print(f"     ✗ FAIL")
        print(f"       Expected: {expected_hebrew} via {expected_method}")
        print(f"       Got: {actual_hebrew} via {actual_method}")

    return {
        "test_num": test_num,
        "test": description,
        "query": query,
        "expected_hebrew": expected_hebrew,
        "actual_hebrew": actual_hebrew,
        "expected_method": expected_method,
        "actual_method": actual_method,
        "confidence": actual_confidence,
        "passed": test_passed,
        "result": result
    }


async def run_all_tests():
    """Run all test cases with summary reporting"""
    log_file = setup_test_logging()

    print("=" * 80)
    print("CLAUDE-FREE TEST SUITE - Step 1: DECIPHER")
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
    for i, test_case in enumerate(TEST_CASES, start=1):
        result = await run_test(test_case, i)
        results.append(result)

    # ==========================================
    # SUMMARY REPORT
    # ==========================================

    passed = sum(1 for r in results if r["passed"])
    total = len(results)

    print(f"\n{'='*80}")
    print(f"RESULTS: {passed}/{total} ({passed/total*100:.1f}%)")
    print(f"{'='*80}")

    # Group results
    groups = {
        "Dictionary Validation": list(range(0, 5)),
        "Transliteration (Step 2)": list(range(5, 25)),
        "Vector Search (Step 3)": list(range(25, 40)),
    }

    print("\n📊 Results by group:")
    for group_name, indices in groups.items():
        group_results = [results[i] for i in indices if i < len(results)]
        group_passed = sum(1 for r in group_results if r["passed"])
        group_total = len(group_results)
        pct = (group_passed/group_total*100) if group_total > 0 else 0
        print(f"  {group_name:30s}: {group_passed:2d}/{group_total:2d} ({pct:5.1f}%)")

    # Method breakdown
    print("\n📈 Evaluation method breakdown:")
    method_counts = {}
    for r in results:
        method = r["actual_method"]
        method_counts[method] = method_counts.get(method, 0) + 1

    for method, count in sorted(method_counts.items()):
        pct = (count/total*100) if total > 0 else 0
        print(f"  {method:20s}: {count:2d} ({pct:5.1f}%)")

    # Failed tests detail
    failed = [r for r in results if not r["passed"]]
    if failed:
        print(f"\n❌ Failed tests ({len(failed)}):")
        for r in failed:
            print(f"  [{r['test_num']:2d}] {r['test']}")
            print(f"      Query: '{r['query']}'")
            print(f"      Expected: {r['expected_hebrew']} via {r['expected_method']}")
            print(f"      Got: {r['actual_hebrew']} via {r['actual_method']}")
    else:
        print(f"\n🎉 ALL TESTS PASSED!")

    # Evaluation summary table
    print(f"\n📋 Detailed Evaluation Summary:")
    print(f"{'#':>3} | {'Query':20s} | {'Method':15s} | {'Confidence':10s} | {'Result':6s}")
    print("-" * 80)
    for r in results:
        status = "✓ PASS" if r["passed"] else "✗ FAIL"
        print(f"{r['test_num']:3d} | {r['query']:20s} | {r['actual_method']:15s} | {r['confidence']:10s} | {status}")

    print(f"\n{'='*80}")
    print(f"Detailed logs: {log_file}")
    print(f"{'='*80}\n")

    return results


if __name__ == "__main__":
    asyncio.run(run_all_tests())
