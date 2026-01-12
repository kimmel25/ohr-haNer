"""
Test script for the V7 Clarification System
============================================

Tests the clarification flow:
1. Query that should trigger clarification
2. Verify clarification options are returned
3. Resume search with selected option
"""

import asyncio
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


async def test_clarification_flow():
    """Test the full clarification flow."""
    print("\n" + "=" * 70)
    print("TESTING V7 CLARIFICATION SYSTEM")
    print("=" * 70)

    # Test query that should trigger clarification
    # (machlokes query without specific qualifier)
    test_query = "machlokes abaya rava on tashbisu"

    print(f"\n1. Testing query: '{test_query}'")
    print("-" * 50)

    # Step 1: Run initial search
    from main_pipeline import search_sources
    result = await search_sources(test_query)

    print(f"\n   Success: {result.success}")
    print(f"   Needs clarification: {result.needs_clarification}")
    print(f"   Clarification prompt: {result.clarification_prompt}")
    print(f"   Clarification options: {result.clarification_options}")
    print(f"   Message: {result.message}")
    print(f"   Total sources: {result.total_sources}")

    if result.needs_clarification:
        print("\n2. Clarification was triggered!")
        print("-" * 50)

        # Extract query_id from message
        query_id = ""
        if result.message and "query_id:" in result.message:
            query_id = result.message.split("query_id:")[1].strip()
        print(f"   Query ID: {query_id}")

        if result.clarification_options:
            # Pick the first option
            selected_option = result.clarification_options[0]
            print(f"   Selected option: {selected_option}")

            print("\n3. Resuming search with clarification...")
            print("-" * 50)

            from main_pipeline import search_with_clarification
            clarified_result = await search_with_clarification(
                original_query=test_query,
                query_id=query_id,
                selected_option_id=selected_option,
            )

            print(f"\n   Success: {clarified_result.success}")
            print(f"   Total sources: {clarified_result.total_sources}")
            print(f"   Levels: {clarified_result.levels_included}")
            print(f"   Message: {clarified_result.message}")

            if clarified_result.sources:
                print(f"\n   First 3 sources:")
                for src in clarified_result.sources[:3]:
                    ref = src.get('ref', src) if isinstance(src, dict) else getattr(src, 'ref', str(src))
                    print(f"     - {ref}")
        else:
            print("   No clarification options provided!")
    else:
        print("\n   No clarification needed - search completed directly")
        if result.sources:
            print(f"\n   First 3 sources:")
            for src in result.sources[:3]:
                ref = src.get('ref', src) if isinstance(src, dict) else getattr(src, 'ref', str(src))
                print(f"     - {ref}")

    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)


async def test_high_confidence_no_clarification():
    """Test that high confidence queries don't trigger clarification."""
    print("\n" + "=" * 70)
    print("TESTING HIGH CONFIDENCE (NO CLARIFICATION)")
    print("=" * 70)

    # This should NOT trigger clarification (known sugya with high confidence)
    test_query = "chezkas haguf"

    print(f"\n1. Testing query: '{test_query}'")
    print("-" * 50)

    from main_pipeline import search_sources
    result = await search_sources(test_query)

    print(f"\n   Success: {result.success}")
    print(f"   Needs clarification: {result.needs_clarification}")
    print(f"   Total sources: {result.total_sources}")

    if not result.needs_clarification:
        print("\n   Correct! High confidence query did not trigger clarification.")
    else:
        print("\n   Unexpected: High confidence query triggered clarification")
        print(f"   Options: {result.clarification_options}")

    print("\n" + "=" * 70)


async def main():
    """Run all tests."""
    await test_clarification_flow()
    await test_high_confidence_no_clarification()


if __name__ == "__main__":
    asyncio.run(main())
