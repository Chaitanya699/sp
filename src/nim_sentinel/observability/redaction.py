"""
NIM Sentinel Observability - Redaction

PII redaction utilities for logging and tracing.
"""

import logging
from typing import Any

from nim_sentinel.guardrails.pii import redact_pii, redact_pii_dict

logger = logging.getLogger(__name__)


def redact_for_logging(data: Any) -> Any:
    """
    Redact PII from data for logging/tracing.

    Handles strings, dicts, lists, and other types.

    Args:
        data: Data to redact

    Returns:
        Redacted data
    """
    if isinstance(data, str):
        return redact_pii(data)
    elif isinstance(data, dict):
        return redact_pii_dict(data)
    elif isinstance(data, list):
        return [redact_for_logging(item) for item in data]
    elif isinstance(data, tuple):
        return tuple(redact_for_logging(item) for item in data)
    else:
        return data


def redact_state_for_logging(state: dict[str, Any]) -> dict[str, Any]:
    """
    Redact PII from LangGraph state for logging.

    Args:
        state: AgentState dict

    Returns:
        Redacted state dict
    """
    return redact_pii_dict(state)


def redact_messages_for_logging(messages: list[Any]) -> list[Any]:
    """
    Redact PII from message list for logging.

    Args:
        messages: List of messages (BaseMessage or dict)

    Returns:
        Redacted messages
    """
    redacted = []
    for msg in messages:
        if hasattr(msg, "content"):
            # BaseMessage-like object
            content = msg.content
            if isinstance(content, str):
                redacted_content = redact_pii(content)
                # Create a copy with redacted content
                redacted_msg = type(msg)(content=redacted_content)
                redacted.append(redacted_msg)
            else:
                redacted.append(msg)
        elif isinstance(msg, dict) and "content" in msg:
            # Dict message
            redacted_msg = msg.copy()
            redacted_msg["content"] = redact_pii(msg["content"])
            redacted.append(redacted_msg)
        else:
            redacted.append(msg)
    return redacted
