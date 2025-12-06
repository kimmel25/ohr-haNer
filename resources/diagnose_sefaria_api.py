"""
Sefaria API Diagnostic Tool
============================

This script makes direct API calls to Sefaria and shows EXACTLY what comes back.
Run this to diagnose why validation is returning 0 hits.

Usage:
    python diagnose_sefaria_api.py
"""

import httpx
import json
import asyncio
from urllib.parse import quote


async def test_sefaria_api():
    """Test the Sefaria API with known terms"""
    
    print("\n" + "="*80)
    print("SEFARIA API DIAGNOSTIC TEST")
    print("="*80)
    
    # Test terms that DEFINITELY exist in Sefaria
    test_terms = [
        ("מיגו", "migu - extremely common Talmudic concept"),
        ("קל וחומר", "kal vchomer - one of the 13 hermeneutic principles"),
        ("בנין אב", "binyan av - another hermeneutic principle"),
        ("ספק ספיקא", "safek safeika - common halachic principle"),
        ("כתובות", "kesubos - name of a masechta"),
    ]
    
    async with httpx.AsyncClient(verify=False, timeout=15.0) as client:
        for hebrew_term, description in test_terms:
            print(f"\n{'='*80}")
            print(f"Testing: {hebrew_term}")
            print(f"Description: {description}")
            print(f"{'='*80}")
            
            # Try the current endpoint (search-wrapper)
            print("\n[Test 1] Current endpoint: /api/search-wrapper")
            url1 = "https://www.sefaria.org/api/search-wrapper"
            params1 = {
                "query": hebrew_term,
                "type": "text",
                "size": 5
            }
            
            try:
                response1 = await client.get(url1, params=params1)
                print(f"  Status: {response1.status_code}")
                print(f"  URL: {response1.url}")
                
                if response1.status_code == 200:
                    data1 = response1.json()
                    print(f"\n  Raw JSON keys: {list(data1.keys())}")
                    
                    # Show the full response (truncated)
                    json_str = json.dumps(data1, ensure_ascii=False, indent=2)
                    if len(json_str) > 2000:
                        json_str = json_str[:2000] + "\n... (truncated)"
                    print(f"\n  Full Response:")
                    print(json_str)
                    
                    # Try to extract hits
                    hits = data1.get("hits", {})
                    print(f"\n  'hits' field type: {type(hits)}")
                    print(f"  'hits' field value: {hits}")
                    
                    if isinstance(hits, dict):
                        total = hits.get("total", "NOT FOUND")
                        print(f"  hits['total']: {total}")
                        
                        if isinstance(total, dict):
                            value = total.get("value", "NOT FOUND")
                            print(f"  hits['total']['value']: {value}")
                    
                else:
                    print(f"  ERROR: HTTP {response1.status_code}")
                    print(f"  Response: {response1.text[:500]}")
                    
            except Exception as e:
                print(f"  EXCEPTION: {e}")
            
            # Try alternative endpoint (regular search)
            print("\n[Test 2] Alternative endpoint: /api/search")
            url2 = "https://www.sefaria.org/api/search"
            params2 = {
                "q": hebrew_term,  # Note: 'q' instead of 'query'
                "size": 5
            }
            
            try:
                response2 = await client.get(url2, params=params2)
                print(f"  Status: {response2.status_code}")
                print(f"  URL: {response2.url}")
                
                if response2.status_code == 200:
                    data2 = response2.json()
                    print(f"\n  Raw JSON keys: {list(data2.keys())}")
                    
                    # Show the full response (truncated)
                    json_str = json.dumps(data2, ensure_ascii=False, indent=2)
                    if len(json_str) > 2000:
                        json_str = json_str[:2000] + "\n... (truncated)"
                    print(f"\n  Full Response:")
                    print(json_str)
                    
                else:
                    print(f"  ERROR: HTTP {response2.status_code}")
                    print(f"  Response: {response2.text[:500]}")
                    
            except Exception as e:
                print(f"  EXCEPTION: {e}")
            
            # Give the API a brief rest between requests
            await asyncio.sleep(0.5)
    
    print("\n" + "="*80)
    print("DIAGNOSTIC TEST COMPLETE")
    print("="*80)
    print("\nWhat to look for:")
    print("  1. Does the API return any hits?")
    print("  2. What is the structure of the 'hits' field?")
    print("  3. Are there any error messages?")
    print("  4. Does one endpoint work better than the other?")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(test_sefaria_api())