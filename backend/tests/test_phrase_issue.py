"""
Test to verify the "chezkas mara kama" phrase issue is fixed.
"""
import requests
import json

API_BASE = "http://localhost:8000"

def test_chezkas_mara_kama():
    """Test that multi-word phrases are correctly translated."""
    
    # Step 1: Send the query
    print("\n=== Testing: chezkas mara kama ===\n")
    
    response = requests.post(
        f"{API_BASE}/decipher",
        json={"query": "chezkas mara kama", "strict": False}
    )
    
    print(f"Status: {response.status_code}")
    data = response.json()
    
    print(f"\nOriginal Query: {data['original_query']}")
    print(f"Hebrew Term: {data.get('hebrew_term', 'N/A')}")
    print(f"Confidence: {data['confidence']}")
    print(f"Needs Validation: {data['needs_validation']}")
    
    if data.get('word_validations'):
        print(f"\nWord Breakdown:")
        for wv in data['word_validations']:
            print(f"  - {wv['original']} → {wv['best_match']} (confidence: {wv['confidence']})")
    
    # Check if all words are translated
    if data.get('word_validations'):
        all_translated = all(
            wv['best_match'] and any('\u0590' <= c <= '\u05FF' for c in wv['best_match'])
            for wv in data['word_validations']
        )
        
        if all_translated:
            print("\n✓ SUCCESS: All words were translated to Hebrew!")
            hebrew_phrase = ' '.join(wv['best_match'] for wv in data['word_validations'])
            print(f"Complete Hebrew phrase: {hebrew_phrase}")
        else:
            print("\n✗ FAILURE: Some words were not translated!")
            return False
    
    return True

if __name__ == "__main__":
    try:
        success = test_chezkas_mara_kama()
        if success:
            print("\n=== Test passed! ===")
        else:
            print("\n=== Test failed! ===")
    except Exception as e:
        print(f"\n✗ Error: {e}")
