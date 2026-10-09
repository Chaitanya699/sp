"""
NIM Sentinel Guardrails

Input and output guardrails for safety, PII protection, and groundedness.
"""

import asyncio
import logging
import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from langchain_nvidia_ai_endpoints import ChatNVIDIA
from nim_sentinel.core.config import get_model_config, get_settings
from nim_sentinel.llm.model_registry import get_model_registry

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
    GROUNDEDNESS = "groundedness"
    TOPIC_CONTROL = "topic_control"


@dataclass
class GuardResult:
    """Result of a guardrail check."""
    category: GuardCategory
    action: GuardAction
    triggered: bool
    details: dict[str, Any]
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category.value,
            "action": self.action.value,
            "triggered": self.triggered,
            "details": self.details,
            "confidence": self.confidence,
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


# PII Patterns for detection/redaction
PII_PATTERNS = {
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    "phone": re.compile(r"\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "credit_card": re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"),
    "ip_address": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    "api_key": re.compile(r"\b(?:sk-|api_|key_)[A-Za-z0-9_-]{20,}\b"),
    "jwt": re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"),
}

# Jailbreak/Injection patterns
JAILBREAK_PATTERNS = [
    re.compile(r"ignore\s+(?:previous|above|all)\s+(?:instructions|prompts|rules)", re.IGNORECASE),
    re.compile(r"forget\s+(?:everything|all|previous)", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+(?:a|an)\s+\w+", re.IGNORECASE),
    re.compile(r"pretend\s+(?:to\s+be|you\s+are)", re.IGNORECASE),
    re.compile(r"roleplay\s+as", re.IGNORECASE),
    re.compile(r"system\s+prompt", re.IGNORECASE),
    re.compile(r"developer\s+mode", re.IGNORECASE),
    re.compile(r"DAN\s+mode", re.IGNORECASE),
    re.compile(r"do\s+anything\s+now", re.IGNORECASE),
    re.compile(r"bypass\s+(?:safety|filter|guard)", re.IGNORECASE),
    re.compile(r"override\s+(?:instructions|safety)", re.IGNORECASE),
    re.compile(r"disregard\s+(?:previous|above)", re.IGNORECASE),
    re.compile(r"new\s+instructions?:", re.IGNORECASE),
    re.compile(r"act\s+as\s+(?:if|though)", re.IGNORECASE),
    re.compile(r"simulate\s+(?:being|a)", re.IGNORECASE),
]

INJECTION_PATTERNS = [
    re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL),
    re.compile(r"javascript:", re.IGNORECASE),
    re.compile(r"on\w+\s*=", re.IGNORECASE),
    re.compile(r"eval\s*\(", re.IGNORECASE),
    re.compile(r"exec\s*\(", re.IGNORECASE),
    re.compile(r"system\s*\(", re.IGNORECASE),
    re.compile(r"subprocess", re.IGNORECASE),
    re.compile(r"__import__", re.IGNORECASE),
    re.compile(r"getattr\s*\(", re.IGNORECASE),
    re.compile(r"globals\s*\(\)", re.IGNORECASE),
    re.compile(r"locals\s*\(\)", re.IGNORECASE),
]


class InputGuardrails:
    """
    Input guardrails for user queries.

    Checks:
    - Jailbreak detection (heuristic patterns)
    - Prompt injection detection (heuristic patterns)
    - NemoGuard content safety (via NVIDIA model)
    - PII detection and redaction
    """

    def __init__(self) -> None:
        self._nemo_content_safety: ChatNVIDIA | None = None
        self._nemo_jailbreak: ChatNVIDIA | None = None
        self._nemo_topic: ChatNVIDIA | None = None

    @staticmethod
    def _extract_content(content: str | list[str | dict[str, Any]]) -> str:
        """Extract string content from LLM response."""
        if isinstance(content, str):
            return content
        # Handle list of content blocks (e.g., [{"type": "text", "text": "..."}])
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_val = block.get("text", "")
                    return text_val if isinstance(text_val, str) else str(text_val)
                if isinstance(block, str):
                    return block
        return str(content)

    async def _get_nemo_content_safety(self) -> ChatNVIDIA | None:
        """Get NemoGuard content safety model."""
        if self._nemo_content_safety is None:
            try:
                registry = get_model_registry()
                self._nemo_content_safety = registry.get_chat_model("safety_content")
            except Exception as e:
                logger.warning(f"Failed to load NemoGuard content safety: {e}")
        return self._nemo_content_safety

    async def _get_nemo_jailbreak(self) -> ChatNVIDIA | None:
        """Get NemoGuard jailbreak detection model."""
        if self._nemo_jailbreak is None:
            try:
                registry = get_model_registry()
                self._nemo_jailbreak = registry.get_chat_model("safety_jailbreak")
            except Exception as e:
                logger.warning(f"Failed to load NemoGuard jailbreak: {e}")
        return self._nemo_jailbreak

    async def _get_nemo_topic(self) -> ChatNVIDIA | None:
        """Get NemoGuard topic control model."""
        if self._nemo_topic is None:
            try:
                registry = get_model_registry()
                self._nemo_topic = registry.get_chat_model("safety_topic")
            except Exception as e:
                logger.warning(f"Failed to load NemoGuard topic: {e}")
        return self._nemo_topic

    def check_jailbreak_heuristic(self, text: str) -> GuardResult:
        """Check for jailbreak patterns using heuristics."""
        matches = []
        for pattern in JAILBREAK_PATTERNS:
            if pattern.search(text):
                matches.append(pattern.pattern)

        triggered = len(matches) > 0
        return GuardResult(
            category=GuardCategory.JAILBREAK,
            action=GuardAction.BLOCK if triggered else GuardAction.ALLOW,
            triggered=triggered,
            details={"matched_patterns": matches, "method": "heuristic"},
            confidence=0.9 if triggered else 0.0,
        )

    def check_injection_heuristic(self, text: str) -> GuardResult:
        """Check for prompt injection patterns using heuristics."""
        matches = []
        for pattern in INJECTION_PATTERNS:
            if pattern.search(text):
                matches.append(pattern.pattern)

        triggered = len(matches) > 0
        return GuardResult(
            category=GuardCategory.INJECTION,
            action=GuardAction.BLOCK if triggered else GuardAction.ALLOW,
            triggered=triggered,
            details={"matched_patterns": matches, "method": "heuristic"},
            confidence=0.85 if triggered else 0.0,
        )

    def check_pii(self, text: str, redact: bool = True) -> tuple[GuardResult, str]:
        """Check for PII and optionally redact."""
        findings = {}
        redacted_text = text

        for pii_type, pattern in PII_PATTERNS.items():
            matches = pattern.findall(text)
            if matches:
                findings[pii_type] = len(matches)
                if redact:
                    redacted_text = pattern.sub(f"[REDACTED_{pii_type.upper()}]", redacted_text)

        triggered = len(findings) > 0
        return GuardResult(
            category=GuardCategory.PII,
            action=GuardAction.REDACT if triggered else GuardAction.ALLOW,
            triggered=triggered,
            details={"findings": findings, "method": "regex"},
            confidence=0.95 if triggered else 0.0,
        ), redacted_text

    async def check_nemo_content_safety(self, text: str) -> GuardResult:
        """Check content safety using NemoGuard model."""
        model = await self._get_nemo_content_safety()
        if model is None:
            return GuardResult(
                category=GuardCategory.CONTENT_SAFETY,
                action=GuardAction.ALLOW,
                triggered=False,
                details={"error": "Model not available", "method": "nemo_guard"},
                confidence=0.0,
            )

        try:
            prompt = f"""Analyze the following text for safety violations.
Categories: hate speech, harassment, violence, illegal activities, sexual content, self-harm.
Respond with ONLY "SAFE" or "UNSAFE: <category>".

Text: {text}"""
            response = await model.ainvoke(prompt)
            content = self._extract_content(response.content).strip().upper()

            if content.startswith("UNSAFE"):
                category = content.replace("UNSAFE:", "").strip()
                return GuardResult(
                    category=GuardCategory.CONTENT_SAFETY,
                    action=GuardAction.BLOCK,
                    triggered=True,
                    details={"nemo_category": category, "method": "nemo_guard"},
                    confidence=0.9,
                )
            else:
                return GuardResult(
                    category=GuardCategory.CONTENT_SAFETY,
                    action=GuardAction.ALLOW,
                    triggered=False,
                    details={"method": "nemo_guard"},
                    confidence=0.9,
                )
        except Exception as e:
            logger.warning(f"NemoGuard content safety check failed: {e}")
            return GuardResult(
                category=GuardCategory.CONTENT_SAFETY,
                action=GuardAction.ALLOW,
                triggered=False,
                details={"error": str(e), "method": "nemo_guard"},
                confidence=0.0,
            )

    async def check_nemo_jailbreak(self, text: str) -> GuardResult:
        """Check jailbreak using NemoGuard model."""
        model = await self._get_nemo_jailbreak()
        if model is None:
            return GuardResult(
                category=GuardCategory.JAILBREAK,
                action=GuardAction.ALLOW,
                triggered=False,
                details={"error": "Model not available", "method": "nemo_guard"},
                confidence=0.0,
            )

        try:
            prompt = f"""Analyze the following text for jailbreak attempts.
Respond with ONLY "SAFE" or "JAILBREAK: <type>".

Text: {text}"""
            response = await model.ainvoke(prompt)
            content = self._extract_content(response.content).strip().upper()

            if content.startswith("JAILBREAK"):
                jailbreak_type = content.replace("JAILBREAK:", "").strip()
                return GuardResult(
                    category=GuardCategory.JAILBREAK,
                    action=GuardAction.BLOCK,
                    triggered=True,
                    details={"nemo_type": jailbreak_type, "method": "nemo_guard"},
                    confidence=0.95,
                )
            else:
                return GuardResult(
                    category=GuardCategory.JAILBREAK,
                    action=GuardAction.ALLOW,
                    triggered=False,
                    details={"method": "nemo_guard"},
                    confidence=0.9,
                )
        except Exception as e:
            logger.warning(f"NemoGuard jailbreak check failed: {e}")
            return GuardResult(
                category=GuardCategory.JAILBREAK,
                action=GuardAction.ALLOW,
                triggered=False,
                details={"error": str(e), "method": "nemo_guard"},
                confidence=0.0,
            )

    async def check_nemo_topic(self, text: str) -> GuardResult:
        """Check topic control using NemoGuard model."""
        model = await self._get_nemo_topic()
        if model is None:
            return GuardResult(
                category=GuardCategory.TOPIC_CONTROL,
                action=GuardAction.ALLOW,
                triggered=False,
                details={"error": "Model not available", "method": "nemo_guard"},
                confidence=0.0,
            )

        try:
            prompt = f"""Analyze if the following text is on-topic for enterprise RAG assistance.
Allowed topics: document queries, system features, technical questions, troubleshooting.
Respond with ONLY "ON_TOPIC" or "OFF_TOPIC: <reason>".

Text: {text}"""
            response = await model.ainvoke(prompt)
            content = self._extract_content(response.content).strip().upper()

            if content.startswith("OFF_TOPIC"):
                reason = content.replace("OFF_TOPIC:", "").strip()
                return GuardResult(
                    category=GuardCategory.TOPIC_CONTROL,
                    action=GuardAction.FLAG,
                    triggered=True,
                    details={"reason": reason, "method": "nemo_guard"},
                    confidence=0.8,
                )
            else:
                return GuardResult(
                    category=GuardCategory.TOPIC_CONTROL,
                    action=GuardAction.ALLOW,
                    triggered=False,
                    details={"method": "nemo_guard"},
                    confidence=0.8,
                )
        except Exception as e:
            logger.warning(f"NemoGuard topic check failed: {e}")
            return GuardResult(
                category=GuardCategory.TOPIC_CONTROL,
                action=GuardAction.ALLOW,
                triggered=False,
                details={"error": str(e), "method": "nemo_guard"},
                confidence=0.0,
            )

    async def check_all(self, text: str, use_nemo: bool = True, redact_pii: bool = True) -> GuardrailResponse:
        """
        Run all input guardrails.

        Args:
            text: Input text to check
            use_nemo: Whether to use NemoGuard models (requires API)
            redact_pii: Whether to redact PII from text

        Returns:
            GuardrailResponse with combined results
        """
        results = []
        current_text = text

        # Heuristic checks (fast, no API)
        results.append(self.check_jailbreak_heuristic(current_text))
        results.append(self.check_injection_heuristic(current_text))

        pii_result, redacted = self.check_pii(current_text, redact=redact_pii)
        results.append(pii_result)
        if redact_pii:
            current_text = redacted

        # NemoGuard checks (require API)
        if use_nemo:
            nemo_results = await asyncio.gather(
                self.check_nemo_content_safety(current_text),
                self.check_nemo_jailbreak(current_text),
                self.check_nemo_topic(current_text),
                return_exceptions=True,
            )
            for r in nemo_results:
                if isinstance(r, GuardResult):
                    results.append(r)
                else:
                    logger.warning(f"NemoGuard check failed: {r}")

        # Determine overall action
        blocked = any(r.action == GuardAction.BLOCK and r.triggered for r in results)
        allowed = not blocked

        return GuardrailResponse(
            allowed=allowed,
            results=results,
            modified_content=current_text if redact_pii and current_text != text else None,
        )


class OutputGuardrails:
    """
    Output guardrails for generated responses.

    Checks:
    - Content safety (NemoGuard)
    - Groundedness (answer supported by citations)
    - PII leak detection
    """

    def __init__(self) -> None:
        self._nemo_content_safety: ChatNVIDIA | None = None

    @staticmethod
    def _extract_content(content: str | list[str | dict[str, Any]]) -> str:
        """Extract string content from LLM response."""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_val = block.get("text", "")
                    return text_val if isinstance(text_val, str) else str(text_val)
                if isinstance(block, str):
                    return block
        return str(content)

    async def _get_nemo_content_safety(self) -> ChatNVIDIA | None:
        """Get NemoGuard content safety model."""
        if self._nemo_content_safety is None:
            try:
                registry = get_model_registry()
                self._nemo_content_safety = registry.get_chat_model("safety_content")
            except Exception as e:
                logger.warning(f"Failed to load NemoGuard content safety: {e}")
        return self._nemo_content_safety

    def check_groundedness(self, answer: str, citations: list[dict[str, Any]] | None) -> GuardResult:
        """
        Check if answer is grounded in citations.

        Simple heuristic: if answer has citations and makes factual claims,
        check that key entities/numbers appear in cited sources.
        """
        if not citations:
            return GuardResult(
                category=GuardCategory.GROUNDEDNESS,
                action=GuardAction.FLAG,
                triggered=True,
                details={"reason": "No citations provided", "method": "heuristic"},
                confidence=0.7,
            )

        # Check if answer contains specific claims that should be cited
        # This is a simplified check - in production, use an LLM judge
        has_specific_claims = bool(re.search(r"\b\d+(?:\.\d+)?\b", answer))  # Numbers
        has_entities = bool(re.search(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", answer))  # Proper nouns

        if has_specific_claims or has_entities:
            # Verify citations have content
            total_citation_chars = sum(len(c.get("content", "")) for c in citations)
            if total_citation_chars < 50:
                return GuardResult(
                    category=GuardCategory.GROUNDEDNESS,
                    action=GuardAction.FLAG,
                    triggered=True,
                    details={
                        "reason": "Citations too sparse for specific claims",
                        "citation_count": len(citations),
                        "total_citation_chars": total_citation_chars,
                        "method": "heuristic",
                    },
                    confidence=0.6,
                )

        return GuardResult(
            category=GuardCategory.GROUNDEDNESS,
            action=GuardAction.ALLOW,
            triggered=False,
            details={"citation_count": len(citations), "method": "heuristic"},
            confidence=0.8,
        )

    def check_pii_leak(self, answer: str) -> GuardResult:
        """Check if answer leaks PII."""
        findings = {}
        for pii_type, pattern in PII_PATTERNS.items():
            matches = pattern.findall(answer)
            if matches:
                findings[pii_type] = len(matches)

        triggered = len(findings) > 0
        return GuardResult(
            category=GuardCategory.PII,
            action=GuardAction.BLOCK if triggered else GuardAction.ALLOW,
            triggered=triggered,
            details={"findings": findings, "method": "regex"},
            confidence=0.95 if triggered else 0.0,
        )

    async def check_nemo_content_safety(self, text: str) -> GuardResult:
        """Check content safety using NemoGuard model."""
        model = await self._get_nemo_content_safety()
        if model is None:
            return GuardResult(
                category=GuardCategory.CONTENT_SAFETY,
                action=GuardAction.ALLOW,
                triggered=False,
                details={"error": "Model not available", "method": "nemo_guard"},
                confidence=0.0,
            )

        try:
            prompt = f"""Analyze the following generated response for safety violations.
Categories: hate speech, harassment, violence, illegal activities, sexual content, self-harm, PII.
Respond with ONLY "SAFE" or "UNSAFE: <category>".

Response: {text}"""
            response = await model.ainvoke(prompt)
            content = self._extract_content(response.content).strip().upper()

            if content.startswith("UNSAFE"):
                category = content.replace("UNSAFE:", "").strip()
                return GuardResult(
                    category=GuardCategory.CONTENT_SAFETY,
                    action=GuardAction.BLOCK,
                    triggered=True,
                    details={"nemo_category": category, "method": "nemo_guard"},
                    confidence=0.9,
                )
            else:
                return GuardResult(
                    category=GuardCategory.CONTENT_SAFETY,
                    action=GuardAction.ALLOW,
                    triggered=False,
                    details={"method": "nemo_guard"},
                    confidence=0.9,
                )
        except Exception as e:
            logger.warning(f"NemoGuard output content safety check failed: {e}")
            return GuardResult(
                category=GuardCategory.CONTENT_SAFETY,
                action=GuardAction.ALLOW,
                triggered=False,
                details={"error": str(e), "method": "nemo_guard"},
                confidence=0.0,
            )

    async def check_all(
        self,
        answer: str,
        citations: list[dict[str, Any]] | None = None,
        use_nemo: bool = True,
    ) -> GuardrailResponse:
        """
        Run all output guardrails.

        Args:
            answer: Generated answer to check
            citations: Citations used in answer
            use_nemo: Whether to use NemoGuard models

        Returns:
            GuardrailResponse with combined results
        """
        results = []

        # Groundedness check
        results.append(self.check_groundedness(answer, citations))

        # PII leak check
        results.append(self.check_pii_leak(answer))

        # NemoGuard content safety
        if use_nemo:
            nemo_result = await self.check_nemo_content_safety(answer)
            results.append(nemo_result)

        # Determine overall action
        blocked = any(r.action == GuardAction.BLOCK and r.triggered for r in results)
        allowed = not blocked

        return GuardrailResponse(
            allowed=allowed,
            results=results,
            modified_content=None,  # Output guardrails don't modify
        )


# Global instances
_input_guardrails: InputGuardrails | None = None
_output_guardrails: OutputGuardrails | None = None


def get_input_guardrails() -> InputGuardrails:
    """Get global InputGuardrails instance."""
    global _input_guardrails
    if _input_guardrails is None:
        _input_guardrails = InputGuardrails()
    return _input_guardrails


def get_output_guardrails() -> OutputGuardrails:
    """Get global OutputGuardrails instance."""
    global _output_guardrails
    if _output_guardrails is None:
        _output_guardrails = OutputGuardrails()
    return _output_guardrails


def reset_guardrails() -> None:
    """Reset global guardrails (for testing)."""
    global _input_guardrails, _output_guardrails
    _input_guardrails = None
    _output_guardrails = None