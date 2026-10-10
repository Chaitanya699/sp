"""
NIM Sentinel Guardrails - Groundedness Checking

Checks if generated answers are grounded in retrieved citations.
"""

import re
from dataclasses import dataclass
from typing import Any


@dataclass
class GroundednessResult:
    """Result of groundedness check."""
    grounded: bool
    score: float
    reason: str
    citation_count: int
    total_citation_chars: int
    has_specific_claims: bool


def check_groundedness(
    answer: str,
    citations: list[dict[str, Any]] | None,
    min_citation_chars: int = 20,
) -> GroundednessResult:
    """
    Check if answer is grounded in citations.

    Simple heuristic: if answer has citations and makes factual claims
    (numbers, proper nouns), check that citations have sufficient content.

    Args:
        answer: Generated answer to check
        citations: List of citation dicts with 'content' key
        min_citation_chars: Minimum total citation characters for specific claims

    Returns:
        GroundednessResult with details
    """
    if not citations:
        return GroundednessResult(
            grounded=False,
            score=0.0,
            reason="No citations provided",
            citation_count=0,
            total_citation_chars=0,
            has_specific_claims=False,
        )

    # Check if answer contains specific claims that should be cited
    has_numbers = bool(re.search(r"\b\d+(?:\.\d+)?\b", answer))
    # Entities: capitalized words not at start of string, or multi-word proper nouns
    has_entities = bool(re.search(r"(?<!\A\s)\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b", answer)) or \
                   bool(re.search(r"(?<=\s)\b[A-Z][a-z]{2,}\b(?!\s+[a-z])", answer))
    has_specific_claims = has_numbers or has_entities

    # Verify citations have content
    total_citation_chars = sum(len(c.get("content", "")) for c in citations)
    citation_count = len(citations)

    if has_specific_claims:
        if total_citation_chars < min_citation_chars:
            return GroundednessResult(
                grounded=False,
                score=0.3,
                reason=f"Citations too sparse for specific claims ({total_citation_chars} chars < {min_citation_chars})",
                citation_count=citation_count,
                total_citation_chars=total_citation_chars,
                has_specific_claims=True,
            )
        else:
            return GroundednessResult(
                grounded=True,
                score=0.8,
                reason="Specific claims supported by citations",
                citation_count=citation_count,
                total_citation_chars=total_citation_chars,
                has_specific_claims=True,
            )
    else:
        # No specific claims, just general answer
        if total_citation_chars > 0:
            return GroundednessResult(
                grounded=True,
                score=0.7,
                reason="General answer with citations",
                citation_count=citation_count,
                total_citation_chars=total_citation_chars,
                has_specific_claims=False,
            )
        else:
            return GroundednessResult(
                grounded=False,
                score=0.2,
                reason="No citation content",
                citation_count=citation_count,
                total_citation_chars=0,
                has_specific_claims=False,
            )


def check_citation_coverage(
    answer: str,
    citations: list[dict[str, Any]],
    key_terms: list[str] | None = None,
) -> dict[str, Any]:
    """
    Check if key terms from answer appear in citations.

    Args:
        answer: Generated answer
        citations: List of citation dicts
        key_terms: Optional list of key terms to check (extracted from answer if not provided)

    Returns:
        Dictionary with coverage details
    """
    if key_terms is None:
        # Extract potential key terms (proper nouns - multi-word capitalized, numbers)
        # Exclude first word of sentence
        key_terms = re.findall(r"(?<=\s)\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b|\b\d+(?:\.\d+)?\b", answer)

    citation_text = " ".join(c.get("content", "") for c in citations)

    found = []
    missing = []
    for term in key_terms:
        if term.lower() in citation_text.lower():
            found.append(term)
        else:
            missing.append(term)

    coverage = len(found) / len(key_terms) if key_terms else 1.0

    return {
        "coverage": coverage,
        "key_terms": key_terms,
        "found_in_citations": found,
        "missing_from_citations": missing,
    }