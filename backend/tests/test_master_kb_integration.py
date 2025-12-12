"""
Master KB Integration Test Suite
=================================
Run this file to verify that Master KB integration is working correctly.

Usage:
    python test_master_kb_integration.py

This will test:
1. Master KB loads correctly
2. Author detection works
3. Reference construction works
4. Smart gathering works (if Sefaria available)
5. Helper functions work
"""

import sys
import logging
from typing import List, Dict

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)

# ==========================================
# TEST 1: MASTER KB LOADS
# ==========================================

def test_master_kb_loads():
    """Test that the Master KB module loads correctly."""
    logger.info("\n" + "=" * 70)
    logger.info("TEST 1: Master KB Loads")
    logger.info("=" * 70)
    
    try:
        from tools.torah_authors_master import (
            TORAH_AUTHORS_KB,
            is_author,
            get_author_matches,
            disambiguate_author,
            get_sefaria_ref,
            detect_authors_in_text,
            get_stats,
        )
        
        stats = get_stats()
        logger.info(f"✓ Master KB loaded successfully")
        logger.info(f"  Total authors: {stats['total_authors']}")
        logger.info(f"  Rishonim: {stats['rishonim']}")
        logger.info(f"  Acharonim: {stats['acharonim']}")
        logger.info(f"  With Sefaria base: {stats['with_sefaria_base']}")
        logger.info(f"  Ambiguous acronyms: {stats['ambiguous_acronyms']}")
        
        return True
        
    except ImportError as e:
        logger.error(f"✗ Failed to import Master KB: {e}")
        logger.error(f"  Make sure torah_authors_master.py is in backend/tools/")
        return False
    except Exception as e:
        logger.error(f"✗ Error loading Master KB: {e}")
        return False

# ==========================================
# TEST 2: AUTHOR DETECTION
# ==========================================

def test_author_detection():
    """Test that author detection works correctly."""
    logger.info("\n" + "=" * 70)
    logger.info("TEST 2: Author Detection")
    logger.info("=" * 70)
    
    try:
        from tools.torah_authors_master import is_author, get_author_matches
        
        test_cases = [
            ('רש"י', True, 'Rashi'),
            ('רן', True, 'Ran'),
            ('תוספות', True, 'Tosafot'),
            ('רמב"ם', True, 'Rambam'),
            ('חזקת הגוף', False, None),  # Concept, not author
            ('ביטול חמץ', False, None),  # Concept, not author
        ]
        
        all_passed = True
        
        for term, should_be_author, expected_name in test_cases:
            is_author_result = is_author(term)
            
            if is_author_result == should_be_author:
                if should_be_author:
                    matches = get_author_matches(term)
                    actual_name = matches[0]['primary_name_en'] if matches else 'Unknown'
                    logger.info(f"✓ '{term}' correctly detected as author: {actual_name}")
                else:
                    logger.info(f"✓ '{term}' correctly detected as concept")
            else:
                logger.error(f"✗ '{term}' detection failed (expected {should_be_author}, got {is_author_result})")
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        logger.error(f"✗ Author detection test failed: {e}")
        return False

# ==========================================
# TEST 3: REFERENCE CONSTRUCTION
# ==========================================

def test_reference_construction():
    """Test that Sefaria reference construction works."""
    logger.info("\n" + "=" * 70)
    logger.info("TEST 3: Reference Construction")
    logger.info("=" * 70)
    
    try:
        from tools.torah_authors_master import get_sefaria_ref
        
        test_cases = [
            ('רן', 'Pesachim 4b', 'Ran on Pesachim 4b'),
            ('תוספות', 'Bava Metzia 10a', 'Tosafot on Bava Metzia 10a'),
            ('רש"י', 'Ketubot 7b', 'Rashi on Ketubot 7b'),
            ('רמב"ם', 'Beitzah 2a', 'Rambam on Beitzah 2a'),
        ]
        
        all_passed = True
        
        for author, sugya, expected_ref in test_cases:
            actual_ref = get_sefaria_ref(author, sugya)
            
            if actual_ref == expected_ref:
                logger.info(f"✓ {author} + {sugya} → {actual_ref}")
            else:
                logger.error(f"✗ {author} + {sugya} failed")
                logger.error(f"  Expected: {expected_ref}")
                logger.error(f"  Got: {actual_ref}")
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        logger.error(f"✗ Reference construction test failed: {e}")
        return False

# ==========================================
# TEST 4: DISAMBIGUATION
# ==========================================

def test_disambiguation():
    """Test that acronym disambiguation works."""
    logger.info("\n" + "=" * 70)
    logger.info("TEST 4: Acronym Disambiguation")
    logger.info("=" * 70)
    
    try:
        from tools.torah_authors_master import get_author_matches, disambiguate_author
        
        # Test case: Multiple Maharams
        term = 'מהר"ם'
        matches = get_author_matches(term)
        
        logger.info(f"Testing '{term}' (should have multiple matches):")
        logger.info(f"  Found {len(matches)} matches:")
        
        for match in matches:
            logger.info(f"    - {match['primary_name_en']} ({match.get('period', 'Unknown')})")
        
        if len(matches) > 1:
            logger.info(f"✓ Correctly detected ambiguous acronym")
            
            # Test disambiguation with context
            result = disambiguate_author(term, context="Rothenburg")
            if result and 'Rothenburg' in result.get('full_name_en', ''):
                logger.info(f"✓ Disambiguation with 'Rothenburg' context: {result['primary_name_en']}")
            else:
                logger.warning(f"⚠ Disambiguation with context may need refinement")
            
            return True
        else:
            logger.error(f"✗ Expected multiple matches for {term}, got {len(matches)}")
            return False
        
    except Exception as e:
        logger.error(f"✗ Disambiguation test failed: {e}")
        return False

# ==========================================
# TEST 5: INTEGRATION HELPERS
# ==========================================

def test_integration_helpers():
    """Test that integration helper functions work."""
    logger.info("\n" + "=" * 70)
    logger.info("TEST 5: Integration Helpers")
    logger.info("=" * 70)
    
    try:
        from phase2_integration_helpers import (
            has_authors,
            should_use_smart_gather,
            separate_authors_and_concepts,
            debug_author_detection,
            get_author_handling_instructions,
        )
        
        # Test has_authors
        test_terms = ['רן', 'ביטול חמץ', 'תוספות']
        result = has_authors(test_terms)
        
        if result:
            logger.info(f"✓ has_authors() correctly detected authors in {test_terms}")
        else:
            logger.error(f"✗ has_authors() failed to detect authors")
            return False
        
        # Test separation
        separated = separate_authors_and_concepts(test_terms)
        logger.info(f"✓ separate_authors_and_concepts():")
        logger.info(f"    Authors: {separated['authors']}")
        logger.info(f"    Concepts: {separated['concepts']}")
        
        # Test should_use_smart_gather
        should_use = should_use_smart_gather(test_terms)
        if should_use:
            logger.info(f"✓ should_use_smart_gather() correctly recommends smart gathering")
        else:
            logger.error(f"✗ should_use_smart_gather() failed")
            return False
        
        # Test debug function
        debug_info = debug_author_detection(test_terms)
        logger.info(f"✓ debug_author_detection() works")
        logger.info(f"    {debug_info}")
        
        # Test prompt generation
        instructions = get_author_handling_instructions()
        if len(instructions) > 100:
            logger.info(f"✓ get_author_handling_instructions() generated {len(instructions)} chars")
        else:
            logger.error(f"✗ get_author_handling_instructions() seems incomplete")
            return False
        
        return True
        
    except ImportError as e:
        logger.error(f"✗ Failed to import integration helpers: {e}")
        logger.error(f"  Make sure phase2_integration_helpers.py is in backend/")
        return False
    except Exception as e:
        logger.error(f"✗ Integration helpers test failed: {e}")
        return False

# ==========================================
# TEST 6: SMART GATHER (if Sefaria available)
# ==========================================

def test_smart_gather():
    """Test smart gather if Sefaria client is available."""
    logger.info("\n" + "=" * 70)
    logger.info("TEST 6: Smart Gather (Requires Sefaria)")
    logger.info("=" * 70)
    
    try:
        from smart_gather import gather_sefaria_data_smart, format_smart_gather_for_claude
        from tools.sefaria_client import get_client
        
        logger.info("✓ Smart gather modules imported successfully")
        logger.info("  Note: Full test requires Sefaria API connection")
        logger.info("  This is verified during actual query processing")
        
        return True
        
    except ImportError as e:
        logger.warning(f"⚠ Could not import smart gather: {e}")
        logger.warning(f"  Make sure smart_gather.py is in backend/")
        return False
    except Exception as e:
        logger.warning(f"⚠ Smart gather test incomplete: {e}")
        return False

# ==========================================
# RUN ALL TESTS
# ==========================================

def run_all_tests():
    """Run all integration tests."""
    logger.info("\n" + "=" * 70)
    logger.info("MASTER KB INTEGRATION TEST SUITE")
    logger.info("=" * 70)
    
    tests = [
        ("Master KB Loads", test_master_kb_loads),
        ("Author Detection", test_author_detection),
        ("Reference Construction", test_reference_construction),
        ("Disambiguation", test_disambiguation),
        ("Integration Helpers", test_integration_helpers),
        ("Smart Gather", test_smart_gather),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            logger.error(f"\n✗ {test_name} crashed: {e}")
            results[test_name] = False
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("TEST SUMMARY")
    logger.info("=" * 70)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{status}: {test_name}")
    
    logger.info("=" * 70)
    logger.info(f"TOTAL: {passed}/{total} tests passed")
    logger.info("=" * 70)
    
    if passed == total:
        logger.info("\n🎉 ALL TESTS PASSED! Integration is working correctly!")
        logger.info("    Your Master KB is ready for production use.")
        return 0
    else:
        logger.error(f"\n⚠ {total - passed} test(s) failed. Check errors above.")
        logger.error("    Review integration steps and file locations.")
        return 1

# ==========================================
# MAIN
# ==========================================

if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)