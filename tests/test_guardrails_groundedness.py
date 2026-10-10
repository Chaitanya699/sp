"""
Tests for Guardrails - Groundedness module
"""

import pytest
from nim_sentinel.guardrails.groundedness import (
    check_groundedness,
    check_citation_coverage,
    GroundednessResult,
)


class TestCheckGroundedness:
    """Tests for check_groundedness function."""

    def test_no_citations(self):
        """Test groundedness fails with no citations."""
        result = check_groundedness("The answer is 42", None)
        assert result.grounded is False
        assert result.score == 0.0
        assert result.reason == "No citations provided"
        assert result.citation_count == 0

    def test_empty_citations(self):
        """Test groundedness fails with empty citations."""
        result = check_groundedness("The answer is 42", [])
        assert result.grounded is False
        assert result.citation_count == 0

    def test_citations_no_specific_claims(self):
        """Test groundedness passes with citations but no specific claims."""
        citations = [{"content": "General information about the topic"}]
        result = check_groundedness("This is a general answer", citations)
        assert result.grounded is True
        assert result.score == 0.7
        assert result.has_specific_claims is False

    def test_citations_with_specific_claims_sufficient(self):
        """Test groundedness passes with specific claims and sufficient citations."""
        citations = [{"content": "The answer is 42 according to the documentation and verified sources"}]
        result = check_groundedness("The answer is 42", citations)
        assert result.grounded is True
        assert result.score == 0.8
        assert result.has_specific_claims is True
        assert result.total_citation_chars >= 50

    def test_citations_with_specific_claims_insufficient(self):
        """Test groundedness fails with specific claims but sparse citations."""
        citations = [{"content": "x"}]
        result = check_groundedness("The answer is 42 and the user is John", citations)
        assert result.grounded is False
        assert result.score == 0.3
        assert result.has_specific_claims is True
        assert result.total_citation_chars < 50

    def test_citations_with_numbers(self):
        """Test groundedness with numeric claims."""
        citations = [{"content": "The temperature is 25 degrees Celsius"}]
        result = check_groundedness("The temperature is 25 degrees", citations)
        assert result.grounded is True
        assert result.has_specific_claims is True

    def test_citations_with_entities(self):
        """Test groundedness with entity claims."""
        citations = [{"content": "John Smith works at Acme Corp"}]
        result = check_groundedness("John Smith works at Acme Corp", citations)
        assert result.grounded is True
        assert result.has_specific_claims is True


class TestCheckCitationCoverage:
    """Tests for check_citation_coverage function."""

    def test_full_coverage(self):
        """Test full coverage of key terms."""
        answer = "The temperature is 25 degrees in New York"
        citations = [{"content": "The temperature is 25 degrees in New York according to the weather service"}]
        result = check_citation_coverage(answer, citations)
        assert result["coverage"] == 1.0
        assert len(result["missing_from_citations"]) == 0

    def test_partial_coverage(self):
        """Test partial coverage."""
        answer = "The temperature is 25 degrees in New York"
        citations = [{"content": "The temperature is 25 degrees"}]
        result = check_citation_coverage(answer, citations)
        assert result["coverage"] < 1.0
        assert "New York" in result["missing_from_citations"]

    def test_no_key_terms(self):
        """Test with no key terms."""
        answer = "This is a general statement"
        citations = [{"content": "Some content"}]
        result = check_citation_coverage(answer, citations)
        assert result["coverage"] == 1.0

    def test_custom_key_terms(self):
        """Test with custom key terms."""
        answer = "The answer is 42"
        citations = [{"content": "The answer is 42"}]
        result = check_citation_coverage(answer, citations, key_terms=["42", "answer"])
        assert result["coverage"] == 1.0
        assert "42" in result["found_in_citations"]
        assert "answer" in result["found_in_citations"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])