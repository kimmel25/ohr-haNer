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
    # ========================================
    # GROUP 4: NEW TERMS - SOFIT LETTERS (5 tests)
    # ========================================
    {
        "query": "motzin umachnisim",
        "expected_hebrew": "מוציאין ומכניסין",
        "expected_method": "any",
        "description": "Taking out and bringing in - double nun sofit"
    },
    {
        "query": "nishbaim",
        "expected_hebrew": "נשבעים",
        "expected_method": "any",
        "description": "Those who swear - mem sofit plural"
    },
    {
        "query": "chotzetz",
        "expected_hebrew": "חוצץ",
        "expected_method": "any",
        "description": "Interposes - tzadi sofit"
    },
    {
        "query": "maarich",
        "expected_hebrew": "מאריך",
        "expected_method": "any",
        "description": "Prolongs - khaf sofit"
    },
    {
        "query": "masof",
        "expected_hebrew": "מסוף",
        "expected_method": "any",
        "description": "From the end - peh sofit"
    },

    # ========================================
    # GROUP 5: NEW TERMS - AYIN DETECTION (4 tests)
    # ========================================
    {
        "query": "baal mum",
        "expected_hebrew": "בעל מום",
        "expected_method": "any",
        "description": "Owner of blemish - ayin in baal"
    },
    {
        "query": "kviius seudah",
        "expected_hebrew": "קביעות סעודה",
        "expected_method": "any",
        "description": "Established meal - ayin in seudah"
    },
    {
        "query": "taanas baal din",
        "expected_hebrew": "טענת בעל דין",
        "expected_method": "any",
        "description": "Claim of litigant - multiple ayins"
    },
    {
        "query": "maaser sheni",
        "expected_hebrew": "מעשר שני",
        "expected_method": "any",
        "description": "Second tithe - ayin in maaser"
    },

    # ========================================
    # GROUP 6: NEW TERMS - PREFIX DETECTION (4 tests)
    # ========================================
    {
        "query": "shenishtanu",
        "expected_hebrew": "שנשתנו",
        "expected_method": "any",
        "description": "That changed - she prefix"
    },
    {
        "query": "hamotzi meichaveiro",
        "expected_hebrew": "המוציא מחבירו",
        "expected_method": "any",
        "description": "One who extracts from another"
    },
    {
        "query": "vehevi",
        "expected_hebrew": "והביא",
        "expected_method": "any",
        "description": "And he brought"
    },
    {
        "query": "lechatchila",
        "expected_hebrew": "לכתחילה",
        "expected_method": "any",
        "description": "From the outset"
    },

    # ========================================
    # GROUP 7: NEW TERMS - DOUBLE LETTERS (3 tests)
    # ========================================
    {
        "query": "shoor",
        "expected_hebrew": "שור",
        "expected_method": "any",
        "description": "Ox - user typed double o"
    },
    {
        "query": "kibbud av vaeim",
        "expected_hebrew": "כיבוד אב ואם",
        "expected_method": "any",
        "description": "Honoring parents - double bet"
    },
    {
        "query": "tikkun",
        "expected_hebrew": "תיקון",
        "expected_method": "any",
        "description": "Repair - double kuf"
    },

    # ========================================
    # GROUP 8: NEW TERMS - ARAMAIC/YESHIVISH (4 tests)
    # ========================================
    {
        "query": "gemara",
        "expected_hebrew": "גמרא",
        "expected_method": "any",
        "description": "Talmud - Aramaic ending"
    },
    {
        "query": "stam",
        "expected_hebrew": "סתם",
        "expected_method": "any",
        "description": "Anonymous/plain"
    },
    {
        "query": "sugya",
        "expected_hebrew": "סוגיא",
        "expected_method": "any",
        "description": "Topic/passage - Aramaic ending"
    },
    {
        "query": "shakla vetarya",
        "expected_hebrew": "שקלא וטריא",
        "expected_method": "any",
        "description": "Give and take discussion"
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
