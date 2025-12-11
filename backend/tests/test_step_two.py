"""
Unit Tests for Step 2: UNDERSTAND
==================================

Tests the understanding/analysis phase of Marei Mekomos.
Uses pytest with async support.

Test Categories:
1. Data Structure Tests - Verify enums and dataclasses work correctly
2. Sefaria Gathering Tests - Test the data collection phase
3. Claude Analysis Tests - Test the interpretation phase (with mocking)
4. Integration Tests - Full Step 2 flow (requires API keys)

Running:
    pytest test_step_two_unit.py -v                    # Run all tests
    pytest test_step_two_unit.py -v -k "data_structure" # Run specific category
    pytest test_step_two_unit.py -v --integration      # Include integration tests

Note: Integration tests require ANTHROPIC_API_KEY environment variable
"""

import sys
import os
import pytest
import asyncio
import json
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

# Import Step 2 components
from step_two_understand import (
    QueryType,
    FetchStrategy,
    SearchStrategy,
    RelatedSugya,
    gather_sefaria_data,
    analyze_with_claude,
    understand,
    _parse_claude_response,
    _fallback_strategy,
    ANALYSIS_SYSTEM_PROMPT,
    ANALYSIS_USER_TEMPLATE,
)


# ==========================================
#  FIXTURES
# ==========================================

@pytest.fixture
def sample_sefaria_data() -> Dict[str, Any]:
    """Sample Sefaria search results for testing."""
    return {
        "query": "חזקת הגוף",
        "total_hits": 156,
        "hits_by_category": {
            "Talmud": 89,
            "Halakhah": 34,
            "Commentary": 33
        },
        "hits_by_masechta": {
            "Ketubot": 45,
            "Niddah": 23,
            "Yevamot": 12,
            "Gittin": 9
        },
        "top_refs": [
            "Ketubot 9a:1",
            "Ketubot 9a:5",
            "Ketubot 12b:3",
            "Niddah 2a:1",
            "Yevamot 93a:4"
        ],
        "sample_hits": [
            {
                "ref": "Ketubot 9a:1",
                "he_ref": "כתובות ט׳ א:א",
                "category": "Talmud",
                "snippet": "העמד אשה על חזקתה..."
            },
            {
                "ref": "Niddah 2a:1",
                "he_ref": "נדה ב׳ א:א",
                "category": "Talmud",
                "snippet": "כל הנשים בחזקת טהרה..."
            }
        ]
    }


@pytest.fixture
def sample_claude_response() -> str:
    """Sample Claude JSON response for testing."""
    return json.dumps({
        "query_type": "sugya_concept",
        "primary_source": "Ketubot 9a",
        "primary_source_he": "כתובות ט׳ א",
        "reasoning": "The term חזקת הגוף (chezkas haguf) is primarily discussed in the sugya of Kesubos 9a regarding a woman's physical status at the time of marriage.",
        "related_sugyos": [
            {
                "ref": "Niddah 2a",
                "he_ref": "נדה ב׳ א",
                "connection": "Also discusses העמדת אשה על חזקתה",
                "importance": "secondary"
            }
        ],
        "depth": "standard",
        "confidence": "high",
        "clarification_prompt": None
    })


@pytest.fixture
def mock_claude_client():
    """Mock Anthropic client for testing without API calls."""
    mock = Mock()
    mock.messages.create.return_value = Mock(
        content=[Mock(text=json.dumps({
            "query_type": "sugya_concept",
            "primary_source": "Ketubot 9a",
            "primary_source_he": "כתובות ט׳ א",
            "reasoning": "Test reasoning",
            "related_sugyos": [],
            "depth": "standard",
            "confidence": "high",
            "clarification_prompt": None
        }))]
    )
    return mock


# ==========================================
#  DATA STRUCTURE TESTS
# ==========================================

class TestDataStructures:
    """Tests for enums and dataclasses."""
    
    def test_query_type_values(self):
        """Verify all QueryType enum values exist."""
        expected_types = [
            "sugya_concept", "halacha_term", "daf_reference",
            "masechta", "person", "pasuk", "klal", 
            "ambiguous", "unknown"
        ]
        actual_types = [qt.value for qt in QueryType]
        
        for expected in expected_types:
            assert expected in actual_types, f"Missing QueryType: {expected}"
    
    def test_fetch_strategy_values(self):
        """Verify all FetchStrategy enum values exist."""
        expected = ["trickle_up", "trickle_down", "direct", "survey"]
        actual = [fs.value for fs in FetchStrategy]
        
        for exp in expected:
            assert exp in actual, f"Missing FetchStrategy: {exp}"
    
    def test_search_strategy_creation(self):
        """Test creating a SearchStrategy with all fields."""
        strategy = SearchStrategy(
            query_type=QueryType.SUGYA_CONCEPT,
            primary_source="Ketubot 9a",
            primary_source_he="כתובות ט׳ א",
            reasoning="Test reasoning",
            fetch_strategy=FetchStrategy.TRICKLE_UP,
            depth="standard",
            confidence="high"
        )
        
        assert strategy.query_type == QueryType.SUGYA_CONCEPT
        assert strategy.primary_source == "Ketubot 9a"
        assert strategy.depth == "standard"
        assert strategy.confidence == "high"
    
    def test_search_strategy_defaults(self):
        """Test SearchStrategy default values."""
        strategy = SearchStrategy(query_type=QueryType.UNKNOWN)
        
        assert strategy.primary_source is None
        assert strategy.fetch_strategy == FetchStrategy.TRICKLE_UP
        assert strategy.depth == "standard"
        assert strategy.confidence == "high"
        assert strategy.related_sugyos == []
    
    def test_search_strategy_to_dict(self):
        """Test SearchStrategy serialization."""
        strategy = SearchStrategy(
            query_type=QueryType.SUGYA_CONCEPT,
            primary_source="Ketubot 9a",
            confidence="medium"
        )
        
        d = strategy.to_dict()
        
        assert d["query_type"] == "sugya_concept"
        assert d["primary_source"] == "Ketubot 9a"
        assert d["confidence"] == "medium"
        assert isinstance(d, dict)
    
    def test_related_sugya_creation(self):
        """Test creating RelatedSugya."""
        sugya = RelatedSugya(
            ref="Niddah 2a",
            he_ref="נדה ב׳ א",
            connection="Also discusses chazaka",
            importance="secondary"
        )
        
        assert sugya.ref == "Niddah 2a"
        assert sugya.importance == "secondary"


# ==========================================
#  RESPONSE PARSING TESTS
# ==========================================

class TestResponseParsing:
    """Tests for Claude response parsing."""
    
    def test_parse_clean_json(self, sample_claude_response):
        """Test parsing clean JSON response."""
        result = _parse_claude_response(sample_claude_response)
        
        assert result["query_type"] == "sugya_concept"
        assert result["primary_source"] == "Ketubot 9a"
    
    def test_parse_json_with_markdown(self):
        """Test parsing JSON wrapped in markdown code fence."""
        response = """Here's my analysis:

```json
{
    "query_type": "halacha_term",
    "primary_source": null,
    "reasoning": "Migu appears in multiple sugyos",
    "depth": "standard",
    "confidence": "medium"
}
```

Hope this helps!"""
        
        result = _parse_claude_response(response)
        
        assert result["query_type"] == "halacha_term"
        assert result["confidence"] == "medium"
    
    def test_parse_json_with_preamble(self):
        """Test parsing JSON with text before it."""
        response = """Based on my analysis, I believe:

{
    "query_type": "daf_reference",
    "primary_source": "Ketubot 9a",
    "confidence": "high"
}"""
        
        result = _parse_claude_response(response)
        
        assert result["query_type"] == "daf_reference"
    
    def test_parse_invalid_json(self):
        """Test handling invalid JSON gracefully."""
        response = "This is not valid JSON at all"
        
        result = _parse_claude_response(response)
        
        assert result == {}
    
    def test_parse_empty_response(self):
        """Test handling empty response."""
        result = _parse_claude_response("")
        assert result == {}


# ==========================================
#  FALLBACK STRATEGY TESTS
# ==========================================

class TestFallbackStrategy:
    """Tests for fallback strategy when Claude fails."""
    
    def test_fallback_with_sefaria_data(self, sample_sefaria_data):
        """Test fallback uses Sefaria data intelligently."""
        strategy = _fallback_strategy("חזקת הגוף", sample_sefaria_data)
        
        assert strategy.query_type == QueryType.SUGYA_CONCEPT
        assert strategy.primary_source == "Ketubot 9a:1"  # Top ref
        assert strategy.confidence == "low"
        assert strategy.clarification_prompt is not None
    
    def test_fallback_with_empty_data(self):
        """Test fallback with no Sefaria data."""
        empty_data = {
            "query": "unknown term",
            "total_hits": 0,
            "hits_by_category": {},
            "hits_by_masechta": {},
            "top_refs": [],
            "sample_hits": []
        }
        
        strategy = _fallback_strategy("unknown term", empty_data)
        
        assert strategy.primary_source is None
        assert strategy.confidence == "low"


# ==========================================
#  PROMPT TESTS
# ==========================================

class TestPrompts:
    """Tests for system and user prompts."""
    
    def test_system_prompt_contains_query_types(self):
        """Verify system prompt includes all query types."""
        for qt in QueryType:
            assert qt.value in ANALYSIS_SYSTEM_PROMPT, \
                f"Query type {qt.value} missing from system prompt"
    
    def test_system_prompt_uses_yeshivish(self):
        """Verify prompt uses sav not tav (yeshivish style)."""
        # Should say "Kesubos" not "Ketubot"
        assert "sav" in ANALYSIS_SYSTEM_PROMPT.lower() or \
               "Kesubos" in ANALYSIS_SYSTEM_PROMPT or \
               "Tosfos" in ANALYSIS_SYSTEM_PROMPT
    
    def test_user_template_formatting(self, sample_sefaria_data):
        """Test user message template can be formatted."""
        message = ANALYSIS_USER_TEMPLATE.format(
            hebrew_term="חזקת הגוף",
            total_hits=sample_sefaria_data["total_hits"],
            hits_by_category=json.dumps(sample_sefaria_data["hits_by_category"]),
            hits_by_masechta=json.dumps(sample_sefaria_data["hits_by_masechta"]),
            top_refs=sample_sefaria_data["top_refs"],
            sample_snippets="1. Ketubot 9a:1: העמד אשה על חזקתה..."
        )
        
        assert "חזקת הגוף" in message
        assert "156" in message  # total_hits


# ==========================================
#  MOCKED INTEGRATION TESTS
# ==========================================

class TestMockedAnalysis:
    """Tests with mocked external services."""
    
    @pytest.mark.asyncio
    async def test_analyze_with_mocked_claude(self, sample_sefaria_data, mock_claude_client):
        """Test analyze_with_claude with mocked client."""
        with patch('step_two_understand.get_claude_client', return_value=mock_claude_client):
            strategy = await analyze_with_claude("חזקת הגוף", sample_sefaria_data)
        
        assert strategy.query_type == QueryType.SUGYA_CONCEPT
        assert strategy.primary_source == "Ketubot 9a"
    
    @pytest.mark.asyncio
    async def test_strategy_adjustment_for_daf_reference(self, mock_claude_client):
        """Test that DAF_REFERENCE gets DIRECT fetch strategy."""
        # Mock Claude to return daf_reference type
        mock_claude_client.messages.create.return_value = Mock(
            content=[Mock(text=json.dumps({
                "query_type": "daf_reference",
                "primary_source": "Ketubot 9a",
                "primary_source_he": "כתובות ט׳ א",
                "reasoning": "Direct daf reference",
                "related_sugyos": [],
                "depth": "standard",
                "confidence": "high",
                "clarification_prompt": None
            }))]
        )
        
        sefaria_data = {"total_hits": 50, "hits_by_masechta": {}, "sample_hits": []}
        
        with patch('step_two_understand.get_claude_client', return_value=mock_claude_client):
            strategy = await analyze_with_claude("כתובות ט", sefaria_data)
        
        assert strategy.fetch_strategy == FetchStrategy.DIRECT
    
    @pytest.mark.asyncio
    async def test_strategy_adjustment_for_halacha_term(self, mock_claude_client):
        """Test that HALACHA_TERM gets SURVEY fetch strategy."""
        mock_claude_client.messages.create.return_value = Mock(
            content=[Mock(text=json.dumps({
                "query_type": "halacha_term",
                "primary_source": None,
                "primary_source_he": None,
                "reasoning": "Appears in multiple sugyos",
                "related_sugyos": [],
                "depth": "standard",
                "confidence": "medium",
                "clarification_prompt": None
            }))]
        )
        
        sefaria_data = {"total_hits": 200, "hits_by_masechta": {}, "sample_hits": []}
        
        with patch('step_two_understand.get_claude_client', return_value=mock_claude_client):
            strategy = await analyze_with_claude("מיגו", sefaria_data)
        
        assert strategy.fetch_strategy == FetchStrategy.SURVEY
    
    @pytest.mark.asyncio
    async def test_strategy_adjustment_for_klal(self, mock_claude_client):
        """Test that KLAL gets expanded depth."""
        mock_claude_client.messages.create.return_value = Mock(
            content=[Mock(text=json.dumps({
                "query_type": "klal",
                "primary_source": "Yevamot 93a",
                "primary_source_he": "יבמות צג׳ א",
                "reasoning": "Broad principle",
                "related_sugyos": [],
                "depth": "standard",
                "confidence": "high",
                "clarification_prompt": None
            }))]
        )
        
        sefaria_data = {"total_hits": 50, "hits_by_masechta": {}, "sample_hits": []}
        
        with patch('step_two_understand.get_claude_client', return_value=mock_claude_client):
            strategy = await analyze_with_claude("אין אדם מקנה", sefaria_data)
        
        assert strategy.depth == "expanded"


# ==========================================
#  LIVE INTEGRATION TESTS (require API keys)
# ==========================================

@pytest.mark.integration
class TestLiveIntegration:
    """
    Integration tests that hit real APIs.
    
    Run with: pytest test_step_two_unit.py -v --integration
    Requires: ANTHROPIC_API_KEY environment variable
    """
    
    @pytest.fixture(autouse=True)
    def skip_without_api_key(self):
        """Skip integration tests if API key not available."""
        if not os.environ.get("ANTHROPIC_API_KEY"):
            pytest.skip("ANTHROPIC_API_KEY not set")
    
    @pytest.mark.asyncio
    async def test_gather_sefaria_data_live(self):
        """Test gathering Sefaria data with real API."""
        data = await gather_sefaria_data("חזקת הגוף")
        
        assert data["query"] == "חזקת הגוף"
        assert data["total_hits"] > 0
        assert "Ketubot" in data["hits_by_masechta"] or "Kesubos" in str(data)
    
    @pytest.mark.asyncio
    async def test_understand_chezkas_haguf(self):
        """Test full understand for חזקת הגוף."""
        strategy = await understand("חזקת הגוף", "chezkas haguf")
        
        assert strategy.query_type in [QueryType.SUGYA_CONCEPT, QueryType.HALACHA_TERM]
        assert strategy.primary_source is not None
        assert "9" in strategy.primary_source or "Ketubot" in strategy.primary_source
    
    @pytest.mark.asyncio
    async def test_understand_migu(self):
        """Test full understand for מיגו."""
        strategy = await understand("מיגו", "migu")
        
        # Migu could be sugya_concept or halacha_term depending on interpretation
        assert strategy.query_type in [QueryType.SUGYA_CONCEPT, QueryType.HALACHA_TERM]
        assert strategy.confidence in ["high", "medium", "low"]
    
    @pytest.mark.asyncio
    async def test_understand_daf_reference(self):
        """Test full understand for direct daf reference."""
        strategy = await understand("כתובות ט", "kesubos 9")
        
        assert strategy.query_type == QueryType.DAF_REFERENCE
        assert strategy.fetch_strategy == FetchStrategy.DIRECT
        assert "Ketubot" in strategy.primary_source or "כתובות" in str(strategy.primary_source_he)


# ==========================================
#  PYTEST CONFIGURATION
# ==========================================

def pytest_addoption(parser):
    """Add custom pytest options."""
    parser.addoption(
        "--integration",
        action="store_true",
        default=False,
        help="Run integration tests that require API keys"
    )


def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires API keys)"
    )


def pytest_collection_modifyitems(config, items):
    """Skip integration tests unless --integration flag is passed."""
    if config.getoption("--integration"):
        return
    
    skip_integration = pytest.mark.skip(reason="need --integration option to run")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)


# ==========================================
#  RUN DIRECTLY
# ==========================================

if __name__ == "__main__":
    # Run with pytest
    pytest.main([__file__, "-v"])