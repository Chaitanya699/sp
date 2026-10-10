"""
NIM Sentinel Guardrails - PII Detection and Redaction

Handles detection and redaction of personally identifiable information.
"""

import re
from dataclasses import dataclass
from typing import Any

# PII Patterns for detection/redaction
PII_PATTERNS = {
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    "phone": re.compile(r"\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "credit_card": re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"),
    "ip_address": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    "api_key": re.compile(r"\b(?:sk-|api_|key_)[A-Za-z0-9_-]{20,}\b"),
    "jwt": re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"),
    # Indian formats - more specific to avoid overlap with generic phone
    "aadhaar": re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"),
    "pan": re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"),
    "phone_in": re.compile(r"\b(?:\+91[-.\s]?|91[-.\s]?)?[6-9]\d{9}\b"),
}


@dataclass
class PIIResult:
    """Result of PII detection."""
    pii_type: str
    count: int
    matches: list[str]


def detect_pii(text: str) -> list[PIIResult]:
    """
    Detect PII in text.

    Args:
        text: Text to scan

    Returns:
        List of PIIResult for each type found
    """
    results = []
    for pii_type, pattern in PII_PATTERNS.items():
        matches = pattern.findall(text)
        if matches:
            # Handle tuple matches from groups
            flat_matches = []
            for m in matches:
                if isinstance(m, tuple):
                    flat_matches.append("".join(m))
                else:
                    flat_matches.append(m)
            results.append(PIIResult(pii_type=pii_type, count=len(flat_matches), matches=flat_matches))
    return results


def redact_pii(text: str, replacement: str = "[REDACTED]") -> str:
    """
    Redact PII from text.

    Args:
        text: Text to redact
        replacement: Replacement string (will append _TYPE)

    Returns:
        Redacted text
    """
    redacted = text
    for pii_type, pattern in PII_PATTERNS.items():
        redacted = pattern.sub(f"{replacement}_{pii_type.upper()}", redacted)
    # Fix format: [REDACTED]_EMAIL -> [REDACTED_EMAIL]
    redacted = re.sub(r"\[REDACTED\]_([A-Z_]+)", r"[REDACTED_\1]", redacted)
    return redacted


def redact_pii_dict(data: dict[str, Any], replacement: str = "[REDACTED]") -> dict[str, Any]:
    """
    Recursively redact PII from dictionary values.

    Args:
        data: Dictionary to redact
        replacement: Replacement string

    Returns:
        Redacted dictionary
    """
    if not isinstance(data, dict):
        return data

    redacted: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, str):
            redacted[key] = redact_pii(value, replacement)
        elif isinstance(value, dict):
            redacted[key] = redact_pii_dict(value, replacement)
        elif isinstance(value, list):
            redacted[key] = [
                redact_pii(item, replacement) if isinstance(item, str) else
                redact_pii_dict(item, replacement) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            redacted[key] = value
    return redacted