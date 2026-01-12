"""
Unit tests for known_sugyos module.

These tests ensure the matching logic works correctly and prevents
false positives from substring matching bugs.

CRITICAL: The "bedikas chometz" → "mukas etz" bug (2026-01-11) was caused by
substring matching where "mukas" matched inside "bedikas". These tests
ensure this class of bugs never happens again.
"""

import pytest
from known_sugyos import (
    _normalize_text,
    _get_words,
    _phrase_in_text_word_bounded,
    _calculate_match_score,
    lookup_known_sugya,
)


class TestWordBoundaryMatching:
    """Tests for word-boundary matching helpers."""

    def test_get_words_simple(self):
        """Basic word splitting."""
        assert _get_words("hello world") == {"hello", "world"}
        assert _get_words("one") == {"one"}
        assert _get_words("") == set()

    def test_phrase_in_text_single_word_match(self):
        """Single word should match as whole word only."""
        assert _phrase_in_text_word_bounded("mukas", "mukas etz") is True
        assert _phrase_in_text_word_bounded("etz", "mukas etz") is True

    def test_phrase_in_text_single_word_no_substring(self):
        """Single word must NOT match as substring inside another word."""
        # THE CRITICAL BUG TEST: "mukas" must NOT match in "bedikas"
        assert _phrase_in_text_word_bounded("mukas", "bedikas chometz") is False
        assert _phrase_in_text_word_bounded("mukkas", "bedikas chometz") is False
        assert _phrase_in_text_word_bounded("mukat", "bedikas chometz") is False

    def test_phrase_in_text_multi_word_match(self):
        """Multi-word phrase matching."""
        assert _phrase_in_text_word_bounded("mukas etz", "tell me about mukas etz please") is True
        assert _phrase_in_text_word_bounded("bedikas chometz", "bedikas chometz laws") is True

    def test_phrase_in_text_multi_word_no_match(self):
        """Multi-word phrase must match as complete words."""
        # "mukas etz" should NOT match in "bedikas chometz"
        assert _phrase_in_text_word_bounded("mukas etz", "bedikas chometz") is False

    def test_phrase_in_text_partial_overlap(self):
        """Partial word overlaps must not match."""
        assert _phrase_in_text_word_bounded("kas", "mukas") is False
        assert _phrase_in_text_word_bounded("bed", "bedikas") is False


class TestCalculateMatchScore:
    """Tests for the match score calculation."""

    def test_bedikas_chometz_no_false_positive(self):
        """
        REGRESSION TEST: 'bedikas chometz' must NOT match 'mukas etz'.

        This was the bug from 2026-01-11 where substring matching caused
        'mukas' to match inside 'bedikas', giving a false 0.90 score.
        """
        mukas_etz_sugya = {
            "id": "mukas_etz",
            "names": {
                "hebrew": ["מוכת עץ"],
                "english": ["mukas etz"],
                "transliterations": ["mukas etz", "mukkas etz", "mukat etz"]
            },
            "key_terms": ["מוכת עץ", "דרוסת איש", "בתולה"]
        }

        score, reason = _calculate_match_score(
            query="bedikas chometz",
            hebrew_terms=["חמץ בדקת", "חמץ", "בדקת"],
            sugya=mukas_etz_sugya
        )

        # Score MUST be 0 - there is no legitimate match
        assert score == 0.0, f"False positive! Score was {score}, reason: {reason}"
        assert reason == "No match"

    def test_exact_transliteration_match(self):
        """Exact transliteration should match with high score."""
        sugya = {
            "id": "test_sugya",
            "names": {
                "transliterations": ["bedikas chometz"]
            }
        }

        score, reason = _calculate_match_score(
            query="bedikas chometz",
            hebrew_terms=[],
            sugya=sugya
        )

        assert score >= 0.45, f"Expected high score for exact match, got {score}"
        assert "Transliteration match" in reason

    def test_hebrew_term_exact_match(self):
        """Hebrew term in hebrew_terms list should match."""
        sugya = {
            "id": "test_sugya",
            "names": {
                "hebrew": ["בדיקת חמץ"]
            }
        }

        score, reason = _calculate_match_score(
            query="bedikas chometz",
            hebrew_terms=["בדיקת חמץ"],
            sugya=sugya
        )

        assert score >= 0.5, f"Expected match for Hebrew term, got {score}"
        assert "Hebrew term match" in reason

    def test_no_match_completely_different(self):
        """Completely unrelated terms should not match."""
        sugya = {
            "id": "ayin_hara",
            "names": {
                "hebrew": ["עין הרע"],
                "transliterations": ["ayin hara", "ayin hora"]
            }
        }

        score, reason = _calculate_match_score(
            query="bedikas chometz",
            hebrew_terms=["בדיקת חמץ"],
            sugya=sugya
        )

        assert score == 0.0, f"Expected no match, got score {score}"


class TestLookupKnownSugya:
    """Integration tests for the full lookup function."""

    def test_bedikas_chometz_no_ketubot(self):
        """
        REGRESSION TEST: 'bedikas chometz' must not return Ketubot refs.

        This ensures the full pipeline doesn't produce false positives.
        """
        result = lookup_known_sugya(
            query="bedikas chometz",
            hebrew_terms=["חמץ בדקת", "חמץ", "בדקת"]
        )

        # Either no match, or if there is a match, it should NOT be mukas_etz
        if result is not None:
            assert result.sugya_id != "mukas_etz", \
                f"False positive! Matched mukas_etz with confidence {result.match_confidence}"
            # Also ensure no Ketubot refs
            for ref in result.primary_refs:
                assert "Ketubot" not in ref and "Kesubos" not in ref, \
                    f"False positive! Got Ketubot ref: {ref}"


class TestNormalizeText:
    """Tests for text normalization."""

    def test_lowercase(self):
        assert _normalize_text("HELLO World") == "hello world"

    def test_remove_punctuation(self):
        assert _normalize_text("hello, world!") == "hello world"

    def test_collapse_whitespace(self):
        assert _normalize_text("hello   world") == "hello world"

    def test_preserve_hebrew(self):
        result = _normalize_text("בדיקת חמץ")
        assert "בדיקת" in result
        assert "חמץ" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
