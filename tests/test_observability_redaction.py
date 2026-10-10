"""
Tests for Observability - Redaction module
"""

import pytest
from nim_sentinel.observability.redaction import (
    redact_for_logging,
    redact_messages_for_logging,
    redact_state_for_logging,
)


class TestRedactForLogging:
    """Tests for redact_for_logging function."""

    def test_redact_string(self):
        """Test string redaction."""
        text = "Email: test@example.com"
        result = redact_for_logging(text)
        assert "[REDACTED_EMAIL]" in result

    def test_redact_dict(self):
        """Test dict redaction."""
        data = {"email": "test@example.com", "name": "John"}
        result = redact_for_logging(data)
        assert "[REDACTED_EMAIL]" in result["email"]
        assert result["name"] == "John"

    def test_redact_list(self):
        """Test list redaction."""
        data = ["test@example.com", "admin@example.com"]
        result = redact_for_logging(data)
        assert "[REDACTED_EMAIL]" in result[0]
        assert "[REDACTED_EMAIL]" in result[1]

    def test_redact_tuple(self):
        """Test tuple redaction."""
        data = ("test@example.com", "admin@example.com")
        result = redact_for_logging(data)
        assert "[REDACTED_EMAIL]" in result[0]
        assert "[REDACTED_EMAIL]" in result[1]

    def test_redact_non_string(self):
        """Test non-string types pass through."""
        assert redact_for_logging(123) == 123
        assert redact_for_logging(True) is True
        assert redact_for_logging(None) is None


class TestRedactStateForLogging:
    """Tests for redact_state_for_logging function."""

    def test_redact_state(self):
        """Test state dict redaction."""
        state = {
            "query": "Find test@example.com",
            "tenant_id": "tenant_123",
            "answer": "The email is test@example.com",
            "metadata": {"user_email": "user@example.com"},
        }
        result = redact_state_for_logging(state)
        assert "[REDACTED_EMAIL]" in result["query"]
        assert "[REDACTED_EMAIL]" in result["answer"]
        assert "[REDACTED_EMAIL]" in result["metadata"]["user_email"]
        assert result["tenant_id"] == "tenant_123"


class TestRedactMessagesForLogging:
    """Tests for redact_messages_for_logging function."""

    def test_redact_base_message(self):
        """Test redaction of BaseMessage-like objects."""

        class MockMessage:
            def __init__(self, content):
                self.content = content

        messages = [MockMessage("Email: test@example.com"), MockMessage("Hello")]
        result = redact_messages_for_logging(messages)
        assert "[REDACTED_EMAIL]" in result[0].content
        assert result[1].content == "Hello"

    def test_redact_dict_message(self):
        """Test redaction of dict messages."""
        messages = [
            {"content": "Email: test@example.com", "role": "user"},
            {"content": "Hello", "role": "assistant"},
        ]
        result = redact_messages_for_logging(messages)
        assert "[REDACTED_EMAIL]" in result[0]["content"]
        assert result[1]["content"] == "Hello"

    def test_redact_non_content(self):
        """Test messages without content pass through."""
        messages = [{"role": "system", "other": "data"}]
        result = redact_messages_for_logging(messages)
        assert result == messages


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
