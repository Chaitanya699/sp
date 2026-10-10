"""
NIM Sentinel Guardrails - Jailbreak Detection

Heuristic-based jailbreak and prompt injection detection.
"""

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class JailbreakType(StrEnum):
    """Types of jailbreak attempts."""
    IGNORE_INSTRUCTIONS = "ignore_instructions"
    ROLEPLAY = "roleplay"
    DAN_MODE = "dan_mode"
    DEVELOPER_MODE = "developer_mode"
    BYPASS_SAFETY = "bypass_safety"
    OVERRIDE_INSTRUCTIONS = "override_instructions"
    FORGET_EVERYTHING = "forget_everything"
    SYSTEM_PROMPT = "system_prompt"
    NEW_INSTRUCTIONS = "new_instructions"
    ACT_AS = "act_as"
    SIMULATE = "simulate"
    DISREGARD = "disregard"


class InjectionType(StrEnum):
    """Types of prompt injection attempts."""
    SCRIPT_TAG = "script_tag"
    JAVASCRIPT_PROTOCOL = "javascript_protocol"
    EVENT_HANDLER = "event_handler"
    EVAL_EXEC = "eval_exec"
    SYSTEM_CALL = "system_call"
    SUBPROCESS = "subprocess"
    IMPORT = "import"
    GETATTR = "getattr"
    GLOBALS_LOCALS = "globals_locals"


# Jailbreak patterns - order matters! More specific patterns first
JAILBREAK_PATTERNS = [
    (JailbreakType.NEW_INSTRUCTIONS, re.compile(r"new\s+instructions?:", re.IGNORECASE)),
    (JailbreakType.IGNORE_INSTRUCTIONS, re.compile(r"ignore\s+(?:previous|above|all)\s+(?:instructions|prompts|rules)", re.IGNORECASE)),
    (JailbreakType.IGNORE_INSTRUCTIONS, re.compile(r"ignore\s+instructions", re.IGNORECASE)),
    (JailbreakType.FORGET_EVERYTHING, re.compile(r"forget\s+(?:everything|all|previous)", re.IGNORECASE)),
    (JailbreakType.ROLEPLAY, re.compile(r"you\s+are\s+now\s+(?:a|an)\s+\w+", re.IGNORECASE)),
    (JailbreakType.ROLEPLAY, re.compile(r"pretend\s+(?:to\s+be|you\s+are)", re.IGNORECASE)),
    (JailbreakType.ROLEPLAY, re.compile(r"roleplay\s+as", re.IGNORECASE)),
    (JailbreakType.SYSTEM_PROMPT, re.compile(r"system\s+prompt", re.IGNORECASE)),
    (JailbreakType.DEVELOPER_MODE, re.compile(r"developer\s+mode", re.IGNORECASE)),
    (JailbreakType.DAN_MODE, re.compile(r"DAN\s+mode", re.IGNORECASE)),
    (JailbreakType.DAN_MODE, re.compile(r"do\s+anything\s+now", re.IGNORECASE)),
    (JailbreakType.BYPASS_SAFETY, re.compile(r"bypass\s+(?:safety|filter|guard)", re.IGNORECASE)),
    (JailbreakType.OVERRIDE_INSTRUCTIONS, re.compile(r"override\s+(?:instructions|safety)", re.IGNORECASE)),
    (JailbreakType.DISREGARD, re.compile(r"disregard\s+(?:previous|above)", re.IGNORECASE)),
    (JailbreakType.ACT_AS, re.compile(r"act\s+as\s+(?:if|though)", re.IGNORECASE)),
    (JailbreakType.SIMULATE, re.compile(r"simulate\s+(?:being|a)", re.IGNORECASE)),
]

# Injection patterns - order matters! More specific patterns first
INJECTION_PATTERNS = [
    (InjectionType.SCRIPT_TAG, re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL)),
    (InjectionType.JAVASCRIPT_PROTOCOL, re.compile(r"javascript:", re.IGNORECASE)),
    (InjectionType.EVENT_HANDLER, re.compile(r"on\w+\s*=", re.IGNORECASE)),
    (InjectionType.IMPORT, re.compile(r"__import__", re.IGNORECASE)),
    (InjectionType.GETATTR, re.compile(r"getattr\s*\(", re.IGNORECASE)),
    (InjectionType.GLOBALS_LOCALS, re.compile(r"globals\s*\(\)", re.IGNORECASE)),
    (InjectionType.GLOBALS_LOCALS, re.compile(r"locals\s*\(\)", re.IGNORECASE)),
    (InjectionType.EVAL_EXEC, re.compile(r"eval\s*\(", re.IGNORECASE)),
    (InjectionType.EVAL_EXEC, re.compile(r"exec\s*\(", re.IGNORECASE)),
    (InjectionType.SYSTEM_CALL, re.compile(r"system\s*\(", re.IGNORECASE)),
    (InjectionType.SUBPROCESS, re.compile(r"subprocess", re.IGNORECASE)),
]


@dataclass
class JailbreakResult:
    """Result of jailbreak detection."""
    triggered: bool
    jailbreak_type: JailbreakType | None = None
    matched_pattern: str | None = None
    confidence: float = 0.0


@dataclass
class InjectionResult:
    """Result of injection detection."""
    triggered: bool
    injection_type: InjectionType | None = None
    matched_pattern: str | None = None
    confidence: float = 0.0


def detect_jailbreak(text: str) -> JailbreakResult:
    """
    Detect jailbreak attempts in text using heuristic patterns.

    Args:
        text: Text to scan

    Returns:
        JailbreakResult with detection details
    """
    for jb_type, pattern in JAILBREAK_PATTERNS:
        match = pattern.search(text)
        if match:
            return JailbreakResult(
                triggered=True,
                jailbreak_type=jb_type,
                matched_pattern=match.group(0),
                confidence=0.9,
            )
    return JailbreakResult(triggered=False, confidence=0.0)


def detect_injection(text: str) -> InjectionResult:
    """
    Detect prompt injection attempts in text using heuristic patterns.

    Args:
        text: Text to scan

    Returns:
        InjectionResult with detection details
    """
    for inj_type, pattern in INJECTION_PATTERNS:
        match = pattern.search(text)
        if match:
            return InjectionResult(
                triggered=True,
                injection_type=inj_type,
                matched_pattern=match.group(0),
                confidence=0.85,
            )
    return InjectionResult(triggered=False, confidence=0.0)


def detect_all_heuristic(text: str) -> dict[str, Any]:
    """
    Run all heuristic detections.

    Args:
        text: Text to scan

    Returns:
        Dictionary with jailbreak and injection results
    """
    jailbreak = detect_jailbreak(text)
    injection = detect_injection(text)

    return {
        "jailbreak": {
            "triggered": jailbreak.triggered,
            "type": jailbreak.jailbreak_type.value if jailbreak.jailbreak_type else None,
            "matched": jailbreak.matched_pattern,
            "confidence": jailbreak.confidence,
        },
        "injection": {
            "triggered": injection.triggered,
            "type": injection.injection_type.value if injection.injection_type else None,
            "matched": injection.matched_pattern,
            "confidence": injection.confidence,
        },
        "blocked": jailbreak.triggered or injection.triggered,
    }