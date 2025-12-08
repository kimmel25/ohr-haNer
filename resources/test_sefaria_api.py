"""
Comprehensive Sefaria API Test
===============================

Tests MULTIPLE different ways of searching Sefaria to find which one works.
"""

import httpx
import json
import asyncio


async def test_all_approaches():
    """Try every possible way to search Sefaria"""
    
    test_term = "מיגו"  # "migu" - extremely common term
    
    print("\n" + "="*100)
    print(f"TESTING ALL SEFARIA API APPROACHES")
    print(f"Search term: {test_term} (migu)")
    print("="*100)
    
    async with httpx.AsyncClient(verify=False, timeout=15.0) as client:
        
        # ========================================
        # APPROACH 1: search-wrapper (current)
        # ========================================
        print("\n" + "="*100)
        print("APPROACH 1: /api/search-wrapper (current approach)")
        print("="*100)
        
        try:
            url = "https://www.sefaria.org/api/search-wrapper"
            params = {
                "query": test_term,
                "type": "text",
                "size": 5
            }
            
            print(f"URL: {url}")
            print(f"Params: {params}")
            
            response = await client.get(url, params=params)
            print(f"Status: {response.status_code}")
            print(f"Full URL: {response.url}\n")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Response keys: {list(data.keys())}")
                
                # Pretty print relevant parts
                if "hits" in data:
                    hits_data = data["hits"]
                    if isinstance(hits_data, dict):
                        total = hits_data.get("total", "NOT FOUND")
                        print(f"Total hits: {total}")
                        
                        results = hits_data.get("hits", [])
                        print(f"Number of results: {len(results)}")
                        
                        if results:
                            print(f"\nFirst result:")
                            print(json.dumps(results[0], ensure_ascii=False, indent=2)[:500])
                    else:
                        print(f"'hits' is type: {type(hits_data)}")
                        print(f"'hits' value: {hits_data}")
                else:
                    print("❌ NO 'hits' FIELD IN RESPONSE")
                    print(f"\nFull response:\n{json.dumps(data, ensure_ascii=False, indent=2)[:1000]}")
            else:
                print(f"❌ ERROR: {response.status_code}")
                print(response.text[:500])
                
        except Exception as e:
            print(f"❌ EXCEPTION: {e}")
        
        await asyncio.sleep(0.5)
        
        # ========================================
        # APPROACH 2: /api/search
        # ========================================
        print("\n" + "="*100)
        print("APPROACH 2: /api/search (alternative endpoint)")
        print("="*100)
        
        try:
            url = "https://www.sefaria.org/api/search"
            params = {
                "q": test_term,  # Note: 'q' not 'query'
                "size": 5
            }
            
            print(f"URL: {url}")
            print(f"Params: {params}")
            
            response = await client.get(url, params=params)
            print(f"Status: {response.status_code}")
            print(f"Full URL: {response.url}\n")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Response keys: {list(data.keys())}")
                print(f"\nFull response:\n{json.dumps(data, ensure_ascii=False, indent=2)[:1000]}")
            else:
                print(f"❌ ERROR: {response.status_code}")
                print(response.text[:500])
                
        except Exception as e:
            print(f"❌ EXCEPTION: {e}")
        
        await asyncio.sleep(0.5)
        
        # ========================================
        # APPROACH 3: search with filters
        # ========================================
        print("\n" + "="*100)
        print("APPROACH 3: /api/search-wrapper with filters")
        print("="*100)
        
        try:
            url = "https://www.sefaria.org/api/search-wrapper"
            params = {
                "query": test_term,
                "type": "text",
                "size": 5,
                "filters": json.dumps(["Talmud"])  # Try filtering to Talmud only
            }
            
            print(f"URL: {url}")
            print(f"Params: {params}")
            
            response = await client.get(url, params=params)
            print(f"Status: {response.status_code}")
            print(f"Full URL: {response.url}\n")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Response keys: {list(data.keys())}")
                
                if "hits" in data:
                    hits_data = data["hits"]
                    if isinstance(hits_data, dict):
                        total = hits_data.get("total", "NOT FOUND")
                        print(f"Total hits: {total}")
                else:
                    print("❌ NO 'hits' FIELD")
                    print(f"\nFull response:\n{json.dumps(data, ensure_ascii=False, indent=2)[:1000]}")
            else:
                print(f"❌ ERROR: {response.status_code}")
                
        except Exception as e:
            print(f"❌ EXCEPTION: {e}")
        
        await asyncio.sleep(0.5)
        
        # ========================================
        # APPROACH 4: Try finding a specific text
        # ========================================
        print("\n" + "="*100)
        print("APPROACH 4: /api/texts (sanity check - fetch a known text)")
        print("="*100)
        
        try:
            # Try fetching a known text that definitely exists
            url = "https://www.sefaria.org/api/texts/Shabbat.2a"
            
            print(f"URL: {url}")
            
            response = await client.get(url)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Successfully fetched text")
                print(f"Response keys: {list(data.keys())}")
                
                # Check if we got Hebrew text
                if "he" in data:
                    he_text = str(data["he"])[:200]
                    print(f"Hebrew text (first 200 chars): {he_text}")
                    print("\n✅ API is working! Text fetch successful.")
                else:
                    print("Text structure:", data.keys())
            else:
                print(f"❌ ERROR: {response.status_code}")
                print("This would indicate a general API problem")
                
        except Exception as e:
            print(f"❌ EXCEPTION: {e}")
        
        # ========================================
        # APPROACH 5: Try the name API
        # ========================================
        print("\n" + "="*100)
        print("APPROACH 5: /api/name (check if API responds)")
        print("="*100)
        
        try:
            url = "https://www.sefaria.org/api/name/Shabbat"
            
            print(f"URL: {url}")
            
            response = await client.get(url)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Name API works")
                print(f"Response keys: {list(data.keys())}")
            else:
                print(f"Status: {response.status_code}")
                
        except Exception as e:
            print(f"❌ EXCEPTION: {e}")
    
    print("\n" + "="*100)
    print("TEST COMPLETE - SUMMARY")
    print("="*100)
    print("\nWhat to check:")
    print("  1. Did Approach 4 (text fetch) work? If YES → API is responding")
    print("  2. Did Approach 5 (name API) work? If YES → API connection is good")
    print("  3. Which search approach returned actual hits?")
    print("  4. If NONE worked, there may be an API key or auth requirement")
    print("="*100 + "\n")


if __name__ == "__main__":
    asyncio.run(test_all_approaches())