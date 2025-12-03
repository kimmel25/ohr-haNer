"""
Test Suite for Step 1: DECIPHER
================================

Test the three-tool cascade with real yeshivish queries.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from step_one_decipher import decipher
from tools.word_dictionary import get_dictionary


# ==========================================
#  TEST CASES
# ==========================================

TEST_CASES = [
    # ========================================
    # GROUP 1: DICTIONARY HITS (should be instant)
    # ========================================
    {
        "query": "bari vishma",
        "expected_hebrew": "ברי ושמא",
        "expected_method": "dictionary",
        "description": "Common Talmudic phrase"
    },
    {
        "query": "chezkas haguf",
        "expected_hebrew": "חזקת הגוף",
        "expected_method": "dictionary",
        "description": "Kesubos concept"
    },
    {
        "query": "shaviya anafshe",
        "expected_hebrew": "שוייא אנפשיה",
        "expected_method": "dictionary",
        "description": "Key concept from Kesubos 12b"
    },
    
    # ========================================
    # GROUP 2: YESHIVISH SPELLINGS (transliteration map)
    # ========================================
    {
        "query": "kesubos",
        "expected_hebrew": "כתובות",
        "expected_method": "transliteration",
        "description": "Yeshivish masechta name (sav not tav)"
    },
    {
        "query": "shabbos",
        "expected_hebrew": "שבת",
        "expected_method": "transliteration",
        "description": "Yeshivish spelling"
    },
    {
        "query": "pesachim",
        "expected_hebrew": "פסחים",
        "expected_method": "transliteration",
        "description": "Masechta name"
    },
    
    # ========================================
    # GROUP 3: SPELLING VARIANTS (should handle)
    # ========================================
    {
        "query": "safek safeika",
        "expected_hebrew": "ספק ספיקא",
        "expected_method": "dictionary",
        "description": "Alternative spelling of sfek sfeika"
    },
    {
        "query": "chezka rav huna",
        "expected_hebrew": "חזקת רב הונא",
        "expected_method": "dictionary",
        "description": "Without final 's' on chezkas"
    },
    {
        "query": "ed echad",
        "expected_hebrew": "עד אחד",
        "expected_method": "dictionary",
        "description": "Without yud"
    },
    
    # ========================================
    # GROUP 4: COMPLEX PHRASES (may need vector search)
    # ========================================
    {
        "query": "chaticha deisura",
        "expected_hebrew": "חתיכה דאיסורא",
        "expected_method": "any",  # dictionary or transliteration
        "description": "Aramaic phrase"
    },
    {
        "query": "bitul chametz",
        "expected_hebrew": "ביטול חמץ",
        "expected_method": "dictionary",
        "description": "Pesach concept"
    },
    
    # ========================================
    # GROUP 5: AMBIGUOUS (should ask for clarification)
    # ========================================
    {
        "query": "chezka",
        "expected_hebrew": None,  # Ambiguous - many possible meanings
        "expected_method": "clarification",
        "description": "Ambiguous - need more context"
    },
    {
        "query": "niddah",
        "expected_hebrew": None,
        "expected_method": "clarification",
        "description": "Could mean laws, tum'ah, or mikvah"
    },
    
    # ========================================
    # GROUP 6: DIFFICULT CASES (stress test)
    # ========================================
    {
        "query": "mvazeh es chaveiro",
        "expected_hebrew": "מבזה את חברו",
        "expected_method": "any",
        "description": "Multi-word phrase with 'es'"
    },
]


# ==========================================
#  TEST RUNNER
# ==========================================

async def run_test(test_case: dict) -> dict:
    """Run a single test case"""
    query = test_case["query"]
    
    print(f"\n{'='*70}")
    print(f"TEST: {test_case['description']}")
    print(f"Query: '{query}'")
    print(f"Expected: {test_case['expected_hebrew']} via {test_case['expected_method']}")
    print(f"{'='*70}")
    
    result = await decipher(query)
    
    # Check result
    test_passed = False
    
    if test_case["expected_method"] == "clarification":
        # Expect needs_clarification = True
        test_passed = result.get("needs_clarification", False)
        status = "✓ PASS" if test_passed else "✗ FAIL"
        
        print(f"\n{status}: Expected clarification request")
        if result.get("needs_clarification"):
            print(f"  Message: {result.get('message', '')}")
        else:
            print(f"  Got: {result.get('hebrew_term', '')} instead")
    
    else:
        # Expect successful resolution
        if result["success"]:
            # Check if Hebrew matches (approximately)
            got_hebrew = result["hebrew_term"]
            expected_hebrew = test_case["expected_hebrew"]
            
            # Normalize spaces and compare
            got_clean = got_hebrew.replace(" ", "").strip()
            expected_clean = expected_hebrew.replace(" ", "").strip() if expected_hebrew else ""
            
            hebrew_match = got_clean == expected_clean or got_clean in expected_clean or expected_clean in got_clean
            
            # Check method if specified
            method_match = (
                test_case["expected_method"] == "any" or 
                result["method"] == test_case["expected_method"]
            )
            
            test_passed = hebrew_match and method_match
            
            status = "✓ PASS" if test_passed else "✗ FAIL"
            print(f"\n{status}")
            print(f"  Got: {got_hebrew} via {result['method']}")
            print(f"  Confidence: {result['confidence']}")
            
            if not hebrew_match:
                print(f"  ⚠️  Hebrew mismatch! Expected: {expected_hebrew}")
            if not method_match:
                print(f"  ⚠️  Method mismatch! Expected: {test_case['expected_method']}")
        
        else:
            status = "✗ FAIL"
            print(f"\n{status}: Failed to resolve")
            print(f"  Message: {result.get('message', '')}")
    
    return {
        "test": test_case["description"],
        "query": query,
        "passed": test_passed,
        "result": result
    }


async def run_all_tests():
    """Run all test cases"""
    
    print("=" * 80)
    print("STEP 1 TEST SUITE - DECIPHER")
    print("=" * 80)
    print(f"Total tests: {len(TEST_CASES)}")
    print()
    
    # Get dictionary stats
    dictionary = get_dictionary()
    stats = dictionary.get_stats()
    print(f"Dictionary: {stats['total_entries']} entries")
    print(f"  By source: {stats['by_source']}")
    print(f"  By confidence: {stats['by_confidence']}")
    
    # Run tests
    results = []
    for test_case in TEST_CASES:
        result = await run_test(test_case)
        results.append(result)
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    
    print(f"\nPassed: {passed}/{total} ({passed/total*100:.1f}%)")
    
    # Group by result
    print("\n📊 Results by group:")
    
    groups = {
        "Dictionary Hits": list(range(0, 3)),
        "Yeshivish Spellings": list(range(3, 6)),
        "Spelling Variants": list(range(6, 9)),
        "Complex Phrases": list(range(9, 11)),
        "Ambiguous (clarification)": list(range(11, 13)),
        "Difficult Cases": list(range(13, len(TEST_CASES))),
    }
    
    for group_name, indices in groups.items():
        group_results = [results[i] for i in indices if i < len(results)]
        group_passed = sum(1 for r in group_results if r["passed"])
        group_total = len(group_results)
        
        print(f"  {group_name}: {group_passed}/{group_total}")
    
    # Failed tests
    failed = [r for r in results if not r["passed"]]
    if failed:
        print("\n❌ Failed tests:")
        for r in failed:
            print(f"  - {r['test']}: '{r['query']}'")
    
    # Dictionary stats after tests
    print("\n📚 Dictionary stats after tests:")
    stats = dictionary.get_stats()
    print(f"  Total entries: {stats['total_entries']}")
    print(f"  Runtime learned: {stats['by_source'].get('runtime', 0)}")
    
    return results


# ==========================================
#  INDIVIDUAL TEST FUNCTIONS
# ==========================================

async def test_dictionary_only():
    """Test just the dictionary lookup"""
    print("\n=== DICTIONARY TEST ===\n")
    
    dictionary = get_dictionary()
    
    test_queries = [
        "bari vishma",
        "chezkas haguf",
        "shaviya anafshe",
        "unknown query xyz",
    ]
    
    for query in test_queries:
        result = dictionary.lookup(query)
        if result:
            print(f"✓ '{query}' → {result['hebrew']} (confidence: {result['confidence']})")
        else:
            print(f"✗ '{query}' not found")


async def test_transliteration_only():
    """Test just the transliteration map"""
    print("\n=== TRANSLITERATION TEST ===\n")
    
    from tools.transliteration_map import generate_hebrew_variants
    
    test_queries = [
        "chezkas haguf",
        "bari vishma",
        "kesubos",
    ]
    
    for query in test_queries:
        variants = generate_hebrew_variants(query, max_variants=5)
        print(f"\nQuery: '{query}'")
        print(f"Variants: {variants}")


# ==========================================
#  MAIN
# ==========================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Step 1: DECIPHER")
    parser.add_argument("--full", action="store_true", help="Run full test suite")
    parser.add_argument("--dict", action="store_true", help="Test dictionary only")
    parser.add_argument("--trans", action="store_true", help="Test transliteration only")
    
    args = parser.parse_args()
    
    if args.dict:
        asyncio.run(test_dictionary_only())
    elif args.trans:
        asyncio.run(test_transliteration_only())
    else:
        # Run full suite by default
        asyncio.run(run_all_tests())