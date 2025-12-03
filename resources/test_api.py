#!/usr/bin/env python3
"""
Test script for Marei Mekomos V5 Backend

Run this to verify the API is working correctly.
Usage: python test_api.py
"""

import asyncio
import httpx
import json
import sys

BASE_URL = "http://localhost:8000"


async def test_health():
    """Test the health endpoint"""
    print("\n=== Testing /health ===")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200


async def test_root():
    """Test the root endpoint"""
    print("\n=== Testing / ===")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200


async def test_related_api():
    """Test the Sefaria related API wrapper"""
    print("\n=== Testing /test/related/Ketubot 4a ===")
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{BASE_URL}/test/related/Ketubot%204a")
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Commentary count: {data.get('commentary_count', 0)}")
        if data.get('commentaries'):
            print("Sample commentaries:")
            for comm in data['commentaries'][:5]:
                print(f"  - {comm.get('ref', '')}")
        return response.status_code == 200


async def test_search_simple():
    """Test a simple search query"""
    print("\n=== Testing /search with 'chuppas niddah' ===")
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{BASE_URL}/search",
            json={"topic": "chuppas niddah"}
        )
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Interpreted as: {data.get('interpreted_query', '')}")
            print(f"Needs clarification: {data.get('needs_clarification', False)}")
            print(f"Sources found: {len(data.get('sources', []))}")
            print(f"Summary: {data.get('summary', '')[:100]}...")
            
            if data.get('sources'):
                print("\nTop sources:")
                for src in data['sources'][:3]:
                    print(f"  - {src.get('ref', '')} ({src.get('category', '')})")
        else:
            print(f"Error: {response.text}")
        
        return response.status_code == 200


async def test_search_with_spelling_variation():
    """Test search with yeshivish spelling"""
    print("\n=== Testing /search with 'bitul chometz' (yeshivish spelling) ===")
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{BASE_URL}/search",
            json={"topic": "bitul chometz"}
        )
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Interpreted as: {data.get('interpreted_query', '')}")
            print(f"Sources found: {len(data.get('sources', []))}")
        
        return response.status_code == 200


async def test_cache_stats():
    """Test cache statistics"""
    print("\n=== Testing /cache/stats ===")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/cache/stats")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200


async def main():
    print("=" * 60)
    print("Marei Mekomos V5 API Test Suite")
    print("=" * 60)
    
    tests = [
        ("Health Check", test_health),
        ("Root Endpoint", test_root),
        ("Related API", test_related_api),
        ("Cache Stats", test_cache_stats),
    ]
    
    # Quick tests first
    results = []
    for name, test_func in tests:
        try:
            result = await test_func()
            results.append((name, result))
        except Exception as e:
            print(f"ERROR: {e}")
            results.append((name, False))
    
    # Longer search tests (optional, comment out if just testing connectivity)
    if "--full" in sys.argv:
        search_tests = [
            ("Search: chuppas niddah", test_search_simple),
            ("Search: bitul chometz", test_search_with_spelling_variation),
        ]
        for name, test_func in search_tests:
            try:
                result = await test_func()
                results.append((name, result))
            except Exception as e:
                print(f"ERROR: {e}")
                results.append((name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST RESULTS")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if "--full" not in sys.argv:
        print("\nNote: Run with --full to include search tests (slower, uses API)")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
