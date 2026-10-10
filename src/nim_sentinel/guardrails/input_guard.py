"""
NIM Sentinel Guardrails - Input Guard

Combines heuristic and NemoGuard checks for input validation.
"""

import logging
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from nim_sentinel.guardrails.groundedness import GroundednessResult
from nim_sentinel.guardrails.jailbreak import detect_all_heuristic
from nim_sentinel.guardrails.nemoguard import (
    NemoGuardClient,
    NemoGuardResult,
    get_nemo_guard_client,
)
from nim_sentinel.guardrails.pii import detect_pii, redact_pii, PIIResult

logger = logging.getLogger(__name__)


class GuardAction(StrEnum):
    """Action to take when guardrail triggers."""
    ALLOW = "allow"
    BLOCK = "block"
    REDACT = "redact"
    FLAG = "flag"


class GuardCategory(StrEnum):
    """Categories of guardrail checks."""
    JAILBREAK = "jailbreak"
    INJECTION = "injection"
    CONTENT_SAFETY = "content_safety"
    PII = "pii"
    TOPIC_CONTROL = "topic_control"


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
    pii_redacted: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "results": [r.to_dict() for r in self.results],
            "modified_content": self.modified_content,
            "pii_redacted": self.pii_redacted,
        }


class InputGuardrails:
    """
    Input guardrails for user queries.

    Checks:
    - Jailbreak detection (heuristic + NemoGuard)
    - Prompt injection detection (heuristic + NemoGuard)
    - Content safety (NemoGuard)
    - Topic control (NemoGuard)
    - PII detection and redaction
    """

    def __init__(self, use_nemoguard: bool = True, redact_pii: bool = True) -> None:
        self.use_nemoguard = use_nemoguard
        self.redact_pii = redact_pii
        self._nemoguard: NemoGuardClient | None = None

    @property
    def nemoguard(self) -> NemoGuardClient:
        """Get NemoGuard client."""
        if self._nemoguard is None:
            self._nemoguard = get_nemo_guard_client()
        return self._nemoguard

    def check_heuristic(self, text: str) -> list[GuardResult]:
        """Run heuristic checks (jailbreak, injection, PII)."""
        results = []

        # Jailbreak + Injection
        heuristic_result = detect_all_heuristic(text)

        if heuristic_result["jailbreak"]["triggered"]:
            results.append(GuardResult(
                category=GuardCategory.JAILBREAK,
                action=GuardAction.BLOCK,
                triggered=True,
                details={
                    "type": heuristic_result["jailbreak"]["type"],
                    "matched": heuristic_result["jailbreak"]["matched"],
                },
                confidence=heuristic_result["jailbreak"]["confidence"],
                source="heuristic",
            ))

        if heuristic_result["injection"]["triggered"]:
            results.append(GuardResult(
                category=GuardCategory.INJECTION,
                action=GuardAction.BLOCK,
                triggered=True,
                details={
                    "type": heuristic_result["injection"]["type"],
                    "matched": heuristic_result["injection"]["matched"],
                },
                confidence=heuristic_result["injection"]["confidence"],
                source="heuristic",
            ))

        # PII
        pii_results = detect_pii(text)
        if pii_results:
            pii_details = {r.pii_type: r.count for r in pii_results}
            results.append(GuardResult(
                category=GuardCategory.PII,
                action=GuardAction.REDACT,
                triggered=True,
                details={"findings": pii_details},
                confidence=0.95,
                source="heuristic",
            ))

        return results

    async def check_nemoguard(self, text: str) -> list[GuardResult]:
        """Run NemoGuard checks."""
        if not self.use_nemoguard:
            return []

        results = []
        nemo_results = await self.nemoguard.check_all(text)

        # Content safety
        cs = nemo_results["content_safety"]
        if cs.triggered:
            results.append(GuardResult(
                category=GuardCategory.CONTENT_SAFETY,
                action=GuardAction.BLOCK,
                triggered=True,
                details={"nemo_category": cs.category},
                confidence=cs.confidence,
                source="nemoguard",
            ))
        elif not cs.available:
            results.append(GuardResult(
                category=GuardCategory.CONTENT_SAFETY,
                action=GuardAction.ALLOW,
                triggered=False,
                details={"error": cs.error, "available": False},
                confidence=0.0,
                source="nemoguard",
            ))

        # Jailbreak
        jb = nemo_results["jailbreak"]
        if jb.triggered:
            results.append(GuardResult(
                category=GuardCategory.JAILBREAK,
                action=GuardAction.BLOCK,
                triggered=True,
                details={"nemo_type": jb.category},
                confidence=jb.confidence,
                source="nemoguard",
            ))
        elif not jb.available:
            results.append(GuardResult(
                category=GuardCategory.JAILBREAK,
                action=GuardAction.ALLOW,
                triggered=False,
                details={"error": jb.error, "available": False},
                confidence=0.0,
                source="nemoguard",
            ))

        # Topic
        topic = nemo_results["topic"]
        if topic.triggered:
            results.append(GuardResult(
                category=GuardCategory.TOPIC_CONTROL,
                action=GuardAction.FLAG,
                triggered=True,
                details={"reason": topic.category},
                confidence=topic.confidence,
                source="nemoguard",
            ))
        elif not topic.available:
            results.append(GuardResult(
                category=GuardCategory.TOPIC_CONTROL,
                action=GuardAction.ALLOW,
                triggered=False,
                details={"error": topic.error, "available": False},
                confidence=0.0,
                source="nemoguard",
            ))

        return results

    async def check_all(self, text: str) -> GuardrailResponse:
        """
        Run all input guardrails.

        Args:
            text: Input text to check

        Returns:
            GuardrailResponse with combined results
        """
        results = []
        current_text = text

        # Heuristic checks (fast, no API)
        heuristic_results = self.check_heuristic(current_text)
        results.extend(heuristic_results)

        # PII redaction
        pii_redacted = False
        if self.redact_pii:
            pii_results = detect_pii(current_text)
            if pii_results:
                current_text = redact_pii(current_text)
                pii_redacted = True

        # NemoGuard checks (require API)
        nemo_results = await self.check_nemoguard(current_text)
        results.extend(nemo_results)

        # Determine overall action
        blocked = any(r.action == GuardAction.BLOCK and r.triggered for r in results)
        allowed = not blocked

        return GuardrailResponse(
            allowed=allowed,
            results=results,
            modified_content=current_text if pii_redacted and current_text != text else None,
            pii_redacted=pii_redacted,
        )


# Global instance
_input_guardrails: InputGuardrails | None = None


def get_input_guardrails(use_nemoguard: bool = True, redact_pii: bool = True) -> InputGuardrails:
    """Get global InputGuardrails instance."""
    global _input_guardrails
    if _input_guardrails is None:
        _input_guardrails = InputGuardrails(use_nemoguard=use_nemoguard, redact_pii=redact_pii)
    return _input_guardrails


def reset_input_guardrails() -> None:
    """Reset global InputGuardrails (for testing)."""
    global _input_guardrails
    _input_guardrails = None