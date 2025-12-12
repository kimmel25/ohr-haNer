"""
Quick verification script - Check if you have the correct fixed files
======================================================================
Run this to verify your deployed files are the latest versions.
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

def check_files():
    """Check if the deployed files have the fixes."""
    print("\n" + "=" * 70)
    print("CHECKING DEPLOYED FILES")
    print("=" * 70)
    
    errors = []
    warnings = []
    
    # Check 1: phase2_integration_helpers.py
    print("\n1. Checking phase2_integration_helpers.py...")
    try:
        with open('phase2_integration_helpers.py', 'r', encoding='utf-8') as f:
            content = f.read()
            if 'get_client as get_sefaria_client' in content:
                errors.append("❌ phase2_integration_helpers.py has OLD import (get_client)")
                print("   ❌ WRONG: Still has 'get_client as get_sefaria_client'")
            elif 'from tools.sefaria_client import get_sefaria_client' in content:
                print("   ✅ CORRECT: Has 'get_sefaria_client' import")
            else:
                warnings.append("⚠️ phase2_integration_helpers.py - Can't find sefaria import")
                print("   ⚠️ WARNING: Can't verify import")
    except FileNotFoundError:
        errors.append("❌ phase2_integration_helpers.py NOT FOUND")
        print("   ❌ FILE NOT FOUND")
    
    # Check 2: step_two_understand.py
    print("\n2. Checking step_two_understand.py...")
    try:
        with open('step_two_understand.py', 'r', encoding='utf-8') as f:
            content = f.read()
            
            # Check import
            if 'get_client as get_sefaria_client' in content:
                errors.append("❌ step_two_understand.py has OLD import")
                print("   ❌ WRONG: Still has old import")
            elif 'from tools.sefaria_client import get_sefaria_client' in content:
                print("   ✅ Import: Correct")
            
            # Check backward compatibility
            if "decipher_result and 'all_terms' in decipher_result" in content:
                errors.append("❌ step_two_understand.py has OLD extraction code (all_terms)")
                print("   ❌ WRONG: Still looking for 'all_terms' field")
            elif 'hasattr(decipher_result, \'hebrew_terms\')' in content:
                print("   ✅ Extraction: Correct (uses hebrew_terms)")
            
            # Check for invalid enum
            if 'FetchStrategy.CLARIFICATION_NEEDED' in content:
                errors.append("❌ step_two_understand.py has invalid enum")
                print("   ❌ WRONG: Still using CLARIFICATION_NEEDED enum")
            else:
                print("   ✅ Enums: No invalid enums found")
                
    except FileNotFoundError:
        errors.append("❌ step_two_understand.py NOT FOUND")
        print("   ❌ FILE NOT FOUND")
    
    # Check 3: torah_authors_master.py
    print("\n3. Checking torah_authors_master.py...")
    try:
        with open('tools/torah_authors_master.py', 'r', encoding='utf-8') as f:
            content = f.read()
            if 'TORAH_AUTHORS_KB' in content and len(content) > 50000:
                print("   ✅ FOUND: Master KB file (large, looks good)")
            else:
                warnings.append("⚠️ torah_authors_master.py might be incomplete")
                print("   ⚠️ WARNING: File seems small")
    except FileNotFoundError:
        errors.append("❌ torah_authors_master.py NOT FOUND in tools/")
        print("   ❌ FILE NOT FOUND")
    
    # Check 4: smart_gather.py
    print("\n4. Checking smart_gather.py...")
    try:
        with open('smart_gather.py', 'r', encoding='utf-8') as f:
            content = f.read()
            if 'gather_sefaria_data_smart' in content:
                print("   ✅ FOUND: Enhanced smart gather")
            else:
                warnings.append("⚠️ smart_gather.py might be old version")
                print("   ⚠️ WARNING: Doesn't have smart gather function")
    except FileNotFoundError:
        errors.append("❌ smart_gather.py NOT FOUND")
        print("   ❌ FILE NOT FOUND")
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    if not errors and not warnings:
        print("✅ ALL CHECKS PASSED!")
        print("   Your files are correct and ready to use!")
        return 0
    
    if warnings:
        print(f"\n⚠️ {len(warnings)} WARNING(S):")
        for w in warnings:
            print(f"   {w}")
    
    if errors:
        print(f"\n❌ {len(errors)} ERROR(S):")
        for e in errors:
            print(f"   {e}")
        print("\n💡 SOLUTION: Re-download the fixed files from outputs!")
        print("   The files in /mnt/user-data/outputs/ are correct.")
        print("   You need to copy them again to your backend directory.")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = check_files()
    print("\n" + "=" * 70 + "\n")
    sys.exit(exit_code)