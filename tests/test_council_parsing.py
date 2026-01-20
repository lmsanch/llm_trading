"""Test council ranking parsing logic.

This module tests the parse_ranking_from_text function which extracts
rankings from model responses in various formats.
"""

import pytest
from backend.council import parse_ranking_from_text


class TestParseRankingFromText:
    """Test suite for parse_ranking_from_text function."""

    def test_valid_final_ranking_format(self):
        """Test parsing of correctly formatted FINAL RANKING section."""
        ranking_text = """After evaluating all responses:

Response A provides comprehensive analysis.
Response B offers good technical perspective.
Response C gives balanced view.

FINAL RANKING:
1. Response C
2. Response A
3. Response B
"""
        result = parse_ranking_from_text(ranking_text)
        assert result == ["Response C", "Response A", "Response B"]

    def test_final_ranking_with_extra_spaces(self):
        """Test parsing with extra spaces in numbered list."""
        ranking_text = """Some analysis...

FINAL RANKING:
1.   Response A
2.  Response B
3.    Response C
"""
        result = parse_ranking_from_text(ranking_text)
        assert result == ["Response A", "Response B", "Response C"]

    def test_final_ranking_without_spaces(self):
        """Test parsing when numbered list has no spaces after period."""
        ranking_text = """Analysis here.

FINAL RANKING:
1.Response D
2.Response B
3.Response A
"""
        result = parse_ranking_from_text(ranking_text)
        assert result == ["Response D", "Response B", "Response A"]

    def test_final_ranking_four_responses(self):
        """Test parsing with four responses (all PM models)."""
        ranking_text = """Detailed evaluation of all responses.

FINAL RANKING:
1. Response D
2. Response A
3. Response C
4. Response B
"""
        result = parse_ranking_from_text(ranking_text)
        assert result == ["Response D", "Response A", "Response C", "Response B"]

    def test_missing_final_ranking_section(self):
        """Test fallback when FINAL RANKING section is missing."""
        ranking_text = """I think Response A is best, followed by Response C and then Response B.
Response D was the weakest overall.

My preference order: Response A, Response C, Response B, Response D.
"""
        result = parse_ranking_from_text(ranking_text)
        # Should fallback to finding all Response X patterns in order
        assert result == ["Response A", "Response C", "Response B", "Response D", "Response A", "Response C", "Response B", "Response D"]

    def test_final_ranking_with_extra_text(self):
        """Test parsing when FINAL RANKING has extra text after rankings."""
        ranking_text = """Evaluation complete.

FINAL RANKING:
1. Response B
2. Response C
3. Response A

These rankings reflect the overall quality and comprehensiveness of each response.
"""
        result = parse_ranking_from_text(ranking_text)
        # Should extract only the numbered list part
        assert result == ["Response B", "Response C", "Response A"]

    def test_malformed_ranking_without_numbers(self):
        """Test when response lists Response X but not in numbered format."""
        ranking_text = """FINAL RANKING:
Best: Response C
Second: Response A
Third: Response B
"""
        result = parse_ranking_from_text(ranking_text)
        # Falls back to extracting Response X patterns
        assert result == ["Response C", "Response A", "Response B"]

    def test_empty_ranking_text(self):
        """Test parsing empty string."""
        result = parse_ranking_from_text("")
        assert result == []

    def test_no_response_labels(self):
        """Test when text contains no Response X labels."""
        ranking_text = """FINAL RANKING:
1. The first one
2. The second one
3. The third one
"""
        result = parse_ranking_from_text(ranking_text)
        assert result == []

    def test_single_response_ranking(self):
        """Test parsing with only one response."""
        ranking_text = """FINAL RANKING:
1. Response A
"""
        result = parse_ranking_from_text(ranking_text)
        assert result == ["Response A"]

    def test_final_ranking_lowercase(self):
        """Test that lowercase 'final ranking:' is not matched (case-sensitive)."""
        ranking_text = """final ranking:
1. Response A
2. Response B
3. Response C
"""
        result = parse_ranking_from_text(ranking_text)
        # Should not match "final ranking:" (lowercase)
        # Falls back to finding Response X patterns
        assert result == ["Response A", "Response B", "Response C"]

    def test_final_ranking_mixed_case(self):
        """Test that mixed case 'Final Ranking:' is not matched."""
        ranking_text = """Final Ranking:
1. Response B
2. Response A
"""
        result = parse_ranking_from_text(ranking_text)
        # Should not match "Final Ranking:" (mixed case)
        # Falls back to finding Response X patterns
        assert result == ["Response B", "Response A"]

    def test_response_labels_beyond_D(self):
        """Test parsing with response labels beyond D (e.g., Response E)."""
        ranking_text = """FINAL RANKING:
1. Response E
2. Response C
3. Response A
4. Response D
5. Response B
"""
        result = parse_ranking_from_text(ranking_text)
        assert result == ["Response E", "Response C", "Response A", "Response D", "Response B"]

    def test_duplicate_response_labels(self):
        """Test when a Response label appears multiple times."""
        ranking_text = """FINAL RANKING:
1. Response A
2. Response A
3. Response B
"""
        result = parse_ranking_from_text(ranking_text)
        # Should capture both occurrences
        assert result == ["Response A", "Response A", "Response B"]

    def test_final_ranking_with_newlines(self):
        """Test parsing with extra newlines between rankings."""
        ranking_text = """FINAL RANKING:

1. Response C

2. Response A

3. Response B
"""
        result = parse_ranking_from_text(ranking_text)
        assert result == ["Response C", "Response A", "Response B"]

    def test_response_in_analysis_section(self):
        """Test that Response labels in analysis are not included when FINAL RANKING exists."""
        ranking_text = """Response A is excellent.
Response B is good but lacks depth.
Response C is comprehensive.

FINAL RANKING:
1. Response C
2. Response A
3. Response B
"""
        result = parse_ranking_from_text(ranking_text)
        # Should only extract from FINAL RANKING section
        assert result == ["Response C", "Response A", "Response B"]

    def test_numbered_list_with_periods_after_response(self):
        """Test parsing when response labels have periods or punctuation."""
        ranking_text = """FINAL RANKING:
1. Response A.
2. Response B.
3. Response C.
"""
        result = parse_ranking_from_text(ranking_text)
        # Regex should not capture the period after Response X
        assert result == ["Response A", "Response B", "Response C"]

    def test_multiple_final_ranking_sections(self):
        """Test when multiple FINAL RANKING sections appear (uses first)."""
        ranking_text = """First attempt:
FINAL RANKING:
1. Response A
2. Response B

Actually, let me reconsider...

FINAL RANKING:
1. Response B
2. Response A
"""
        result = parse_ranking_from_text(ranking_text)
        # When split() is called, it creates parts[0], parts[1], parts[2]
        # parts[1] is the text BETWEEN the two occurrences
        # So it only captures the first ranking
        assert result == ["Response A", "Response B"]

    def test_whitespace_only(self):
        """Test parsing with only whitespace."""
        result = parse_ranking_from_text("   \n\n  \t  ")
        assert result == []

    def test_final_ranking_no_colon(self):
        """Test when FINAL RANKING appears without colon."""
        ranking_text = """FINAL RANKING
1. Response A
2. Response B
"""
        result = parse_ranking_from_text(ranking_text)
        # Should not match without colon, falls back to Response X patterns
        assert result == ["Response A", "Response B"]

    def test_numbered_list_double_digit(self):
        """Test parsing with double-digit numbering (edge case)."""
        ranking_text = """FINAL RANKING:
10. Response A
11. Response B
12. Response C
"""
        result = parse_ranking_from_text(ranking_text)
        assert result == ["Response A", "Response B", "Response C"]

    def test_response_with_lowercase_letter(self):
        """Test that lowercase response labels are not matched."""
        ranking_text = """FINAL RANKING:
1. Response a
2. Response b
3. Response c
"""
        result = parse_ranking_from_text(ranking_text)
        # Regex looks for [A-Z] (uppercase only)
        assert result == []

    def test_partial_response_label(self):
        """Test when text has partial matches like 'Resp' or 'Response' without letter."""
        ranking_text = """FINAL RANKING:
1. Resp A
2. Response
3. Response C
"""
        result = parse_ranking_from_text(ranking_text)
        # Only "Response C" should match the pattern
        assert result == ["Response C"]

    def test_response_with_multiple_spaces(self):
        """Test Response label with multiple spaces between word and letter."""
        ranking_text = """FINAL RANKING:
1. Response   A
2. Response  B
"""
        result = parse_ranking_from_text(ranking_text)
        # Regex pattern is "Response [A-Z]" (single space)
        assert result == []

    def test_realistic_model_response_with_analysis(self):
        """Test with realistic model response including detailed analysis."""
        ranking_text = """After evaluating all responses:

Response A provides comprehensive analysis with strong reasoning and clear actionable insights.
Response B offers good technical perspective but lacks depth on fundamentals.
Response C gives balanced view but misses some key risk factors.
Response D has interesting points but overall less comprehensive.

FINAL RANKING:
1. Response A
2. Response C
3. Response B
4. Response D
"""
        result = parse_ranking_from_text(ranking_text)
        assert result == ["Response A", "Response C", "Response B", "Response D"]
        assert len(result) == 4

    def test_empty_final_ranking_section(self):
        """Test when FINAL RANKING section exists but is empty."""
        ranking_text = """Great analysis above.

FINAL RANKING:

"""
        result = parse_ranking_from_text(ranking_text)
        assert result == []

    def test_response_in_quoted_text(self):
        """Test Response labels with quotes after them."""
        ranking_text = """FINAL RANKING:
1. Response A
2. Response B
3. Response C
"""
        result = parse_ranking_from_text(ranking_text)
        # Should match Response A, B, C
        assert result == ["Response A", "Response B", "Response C"]


class TestParseRankingEdgeCases:
    """Test edge cases and error conditions for parse_ranking_from_text."""

    def test_none_input_should_raise(self):
        """Test that None input raises an error."""
        with pytest.raises(TypeError):
            parse_ranking_from_text(None)

    def test_non_string_input_should_raise(self):
        """Test that non-string input raises an error."""
        with pytest.raises(TypeError):
            parse_ranking_from_text(123)

    def test_very_long_text(self):
        """Test parsing with very long text (performance check)."""
        long_text = "Some filler text. " * 10000 + """
FINAL RANKING:
1. Response A
2. Response B
"""
        result = parse_ranking_from_text(long_text)
        assert result == ["Response A", "Response B"]

    def test_unicode_characters(self):
        """Test parsing with unicode characters in text."""
        ranking_text = """Analysé des réponses 🎯

FINAL RANKING:
1. Response A 👍
2. Response B ⭐
3. Response C
"""
        result = parse_ranking_from_text(ranking_text)
        assert result == ["Response A", "Response B", "Response C"]

    def test_special_characters_in_analysis(self):
        """Test parsing when analysis contains special regex characters."""
        ranking_text = r"""Response A: $100 [profit] (best) {top}
Response B: *good* but needs work
Response C: okay \d+ regex test

FINAL RANKING:
1. Response A
2. Response B
3. Response C
"""
        result = parse_ranking_from_text(ranking_text)
        assert result == ["Response A", "Response B", "Response C"]


class TestParseRankingIntegration:
    """Integration tests for parse_ranking_from_text with real fixtures."""

    def test_parse_mock_ranking_response(self):
        """Test parsing mock ranking response from fixtures."""
        from tests.fixtures.mock_council_responses import get_mock_ranking_response

        ranking_text = get_mock_ranking_response(
            "test-model",
            ["Response C", "Response A", "Response B", "Response D"]
        )
        result = parse_ranking_from_text(ranking_text)
        assert result == ["Response C", "Response A", "Response B", "Response D"]

    def test_parse_malformed_mock_ranking(self):
        """Test parsing malformed mock ranking response."""
        from tests.fixtures.mock_council_responses import get_mock_ranking_response_malformed

        ranking_text = get_mock_ranking_response_malformed("test-model")
        result = parse_ranking_from_text(ranking_text)
        # Should still extract Response labels even without FINAL RANKING
        assert "Response A" in result
        assert "Response C" in result
        assert "Response B" in result
        assert "Response D" in result

    def test_parse_all_stage2_mock_responses(self):
        """Test parsing all Stage 2 mock responses."""
        from tests.fixtures.mock_council_responses import get_mock_stage2_responses

        stage2_responses = get_mock_stage2_responses()
        for response in stage2_responses:
            result = parse_ranking_from_text(response["ranking_text"])
            # Each should return a non-empty list
            assert len(result) > 0
            # Each should contain Response labels
            assert all("Response" in item for item in result)
