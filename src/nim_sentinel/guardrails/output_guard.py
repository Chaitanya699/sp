"""
NIM Sentinel Guardrails - Output Guard

Checks generated responses for safety, groundedness, and PII leaks.
"""

import logging
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from nim_sentinel.guardrails.groundedness import check_groundedness, GroundednessResult
from nim_sentinel.guardrails.nemoguard import (
    NemoGuardClient,
    NemoGuardResult,
    get_nemo_guard_client,
)
from nim_sentinel.guardrails.pii import detect_pii

logger = logging.getLogger(__name__)


class GuardAction(StrEnum):
    """Action to take when guardrail triggers."""
    ALLOW = "allow"
    BLOCK = "block"
    FLAG = "flag"


class GuardCategory(StrEnum):
    """Categories of guardrail checks."""
    CONTENT_SAFETY = "content_safety"
    GROUNDEDNESS = "groundedness"
    PII = "pii"


@dataclass
class GuardResult:
    """Result of a guardrail check."""
    category: GuardCategory
    action: GuardAction
    triggered: bool
    details: dict[str, Any]
    confidence: float = 0.0
    source: str = "heuristic"  # "heuristic" or "nemoguard"

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category.value,
            "action": self.action.value,
            "triggered": self.triggered,
            "details": self.details,
            "confidence": self.confidence,
            "source": self.source,
        }


@dataclass
class GuardrailResponse:
    """Combined response from multiple guardrails."""
    allowed: bool
    results: list[GuardResult]
    modified_content: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "results": [r.to_dict() for r in self.results],
            "modified_content": self.modified_content,
        }


class OutputGuardrails:
    """
    Output guardrails for generated responses.

    Checks:
    - Content safety (NemoGuard)
    - Groundedness (answer supported by citations)
    - PII leak detection
    """

    def __init__(self, use_nemoguard: bool = True) -> None:
        self.use_nemoguard = use_nemoguard
        self._nemoguard: NemoGuardClient | None = None

    @property
    def nemoguard(self) -> NemoGuardClient:
        """Get NemoGuard client."""
        if self._nemoguard is None:
            self._nemoguard = get_nemo_guard_client()
        return self._nemoguard

    def check_groundedness(self, answer: str, citations: list[dict[str, Any]] | None) -> GuardResult:
        """Check if answer is grounded in citations."""
        result: GroundednessResult = check_groundedness(answer, citations)

        return GuardResult(
            category=GuardCategory.GROUNDEDNESS,
            action=GuardAction.FLAG if not result.grounded else GuardAction.ALLOW,
            triggered=not result.grounded,
            details={
                "reason": result.reason,
                "citation_count": result.citation_count,
                "total_citation_chars": result.total_citation_chars,
                "has_specific_claims": result.has_specific_claims,
            },
            confidence=result.score,
            source="heuristic",
        )

    def check_pii_leak(self, answer: str) -> GuardResult:
        """Check if answer leaks PII."""
        pii_results = detect_pii(answer)

        if pii_results:
            pii_details = {r.pii_type: r.count for r in pii_results}
            return GuardResult(
                category=GuardCategory.PII,
                action=GuardAction.BLOCK,
                triggered=True,
                details={"findings": pii_details},
                confidence=0.95,
                source="heuristic",
            )

        return GuardResult(
            category=GuardCategory.PII,
            action=GuardAction.ALLOW,
            triggered=False,
            details={},
            confidence=0.0,
            source="heuristic",
        )

    async def check_nemoguard_content_safety(self, text: str) -> GuardResult:
        """Check content safety using NemoGuard."""
        if not self.use_nemoguard:
            return GuardResult(
                category=GuardCategory.CONTENT_SAFETY,
                action=GuardAction.ALLOW,
                triggered=False,
                details={"available": False},
                confidence=0.0,
                source="nemoguard",
            )

        cs = await self.nemoguard.check_content_safety(text)

        if cs.triggered:
            return GuardResult(
                category=GuardCategory.CONTENT_SAFETY,
                action=GuardAction.BLOCK,
                triggered=True,
                details={"nemo_category": cs.category},
                confidence=cs.confidence,
                source="nemoguard",
            )
        elif not cs.available:
            return GuardResult(
                category=GuardCategory.CONTENT_SAFETY,
                action=GuardAction.ALLOW,
                triggered=False,
                details={"error": cs.error, "available": False},
                confidence=0.0,
                source="nemoguard",
            )
        else:
            return GuardResult(
                category=GuardCategory.CONTENT_SAFETY,
                action=GuardAction.ALLOW,
                triggered=False,
                details={},
                confidence=cs.confidence,
                source="nemoguard",
            )

    async def check_all(
        self,
        answer: str,
        citations: list[dict[str, Any]] | None = None,
    ) -> GuardrailResponse:
        """
        Run all output guardrails.

        Args:
            answer: Generated answer to check
            citations: Citations used in answer

        Returns:
            GuardrailResponse with combined results
        """
        results = []

        # Groundedness check
        results.append(self.check_groundedness(answer, citations))

        # PII leak check
        results.append(self.check_pii_leak(answer))

        # NemoGuard content safety (only if enabled)
        if self.use_nemoguard:
            nemo_result = await self.check_nemoguard_content_safety(answer)
            results.append(nemo_result)

        # Determine overall action
        blocked = any(r.action == GuardAction.BLOCK and r.triggered for r in results)
        allowed = not blocked

        return GuardrailResponse(
            allowed=allowed,
            results=results,
            modified_content=None,  # Output guardrails don't modify
        )


# Global instance
_output_guardrails: OutputGuardrails | None = None


def get_output_guardrails(use_nemoguard: bool = True) -> OutputGuardrails:
    """Get global OutputGuardrails instance."""
    global _output_guardrails
    if _output_guardrails is None:
        _output_guardrails = OutputGuardrails(use_nemoguard=use_nemoguard)
    return _output_guardrails


def reset_output_guardrails() -> None:
    """Reset global OutputGuardrails (for testing)."""
    global _output_guardrails
    _output_guardrails = None