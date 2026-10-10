"""
Tests for Guardrails - PII module
"""

import pytest
from nim_sentinel.guardrails.pii import (
    PII_PATTERNS,
    detect_pii,
    redact_pii,
    redact_pii_dict,
)


class TestPIIPatterns:
    """Tests for PII detection patterns."""

    def test_email_pattern(self):
        """Test email detection."""
        pattern = PII_PATTERNS["email"]
        assert pattern.search("test@example.com")
        assert pattern.search("user.name@domain.org")
        assert not pattern.search("not-an-email")

    def test_phone_pattern(self):
        """Test phone number detection."""
        pattern = PII_PATTERNS["phone"]
        assert pattern.search("555-123-4567")
        assert pattern.search("(555) 123-4567")
        assert pattern.search("+1 555 123 4567")
        assert not pattern.search("123-456")

    def test_ssn_pattern(self):
        """Test SSN detection."""
        pattern = PII_PATTERNS["ssn"]
        assert pattern.search("123-45-6789")
        assert not pattern.search("123456789")

    def test_credit_card_pattern(self):
        """Test credit card detection."""
        pattern = PII_PATTERNS["credit_card"]
        assert pattern.search("1234-5678-9012-3456")
        assert pattern.search("1234 5678 9012 3456")
        assert pattern.search("1234567890123456")
        assert not pattern.search("1234-5678")

    def test_ip_address_pattern(self):
        """Test IP address detection."""
        pattern = PII_PATTERNS["ip_address"]
        assert pattern.search("192.168.1.1")
        assert pattern.search("10.0.0.1")
        # Pattern matches any 1-3 digit groups
        assert pattern.search("999.999.999.999")

    def test_api_key_pattern(self):
        """Test API key detection."""
        pattern = PII_PATTERNS["api_key"]
        assert pattern.search("sk-abcdefghijklmnopqrstuvwxyz")
        assert pattern.search("api_abcdefghijklmnopqrstuvwxyz")
        assert not pattern.search("sk-short")

    def test_jwt_pattern(self):
        """Test JWT detection."""
        pattern = PII_PATTERNS["jwt"]
        assert pattern.search(
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        )
        assert not pattern.search("not-a-jwt")

    def test_aadhaar_pattern(self):
        """Test Aadhaar detection (Indian 12-digit)."""
        pattern = PII_PATTERNS["aadhaar"]
        assert pattern.search("1234 5678 9012")
        assert pattern.search("123456789012")
        assert pattern.search("1234 5678 9012")
        assert not pattern.search("12345678901")

    def test_pan_pattern(self):
        """Test PAN detection (Indian)."""
        pattern = PII_PATTERNS["pan"]
        assert pattern.search("ABCDE1234F")
        assert pattern.search("AAAAA0000A")
        assert not pattern.search("abcde1234f")  # lowercase
        assert not pattern.search("ABCDE1234")  # missing last char

    def test_phone_in_pattern(self):
        """Test Indian phone detection."""
        pattern = PII_PATTERNS["phone_in"]
        assert pattern.search("+91 9876543210")
        assert pattern.search("919876543210")
        assert pattern.search("9876543210")
        assert pattern.search("+91-9876543210")
        assert not pattern.search("1234567890")  # doesn't start with 6-9


class TestDetectPII:
    """Tests for detect_pii function."""

    def test_detect_email(self):
        """Test email detection."""
        results = detect_pii("Contact me at test@example.com")
        assert len(results) == 1
        assert results[0].pii_type == "email"
        assert results[0].count == 1

    def test_detect_multiple(self):
        """Test multiple PII types."""
        text = "Email: test@example.com, Phone: 555-123-4567, SSN: 123-45-6789"
        results = detect_pii(text)
        assert len(results) == 3
        types = {r.pii_type for r in results}
        assert types == {"email", "phone", "ssn"}

    def test_detect_indian_formats(self):
        """Test Indian PII formats."""
        text = "Aadhaar: 1234 5678 9012, PAN: ABCDE1234F, Phone: +91 9876543210"
        results = detect_pii(text)
        assert len(results) == 4
        types = {r.pii_type for r in results}
        assert types == {"aadhaar", "pan", "phone_in", "phone"}

    def test_detect_no_pii(self):
        """Test no PII found."""
        results = detect_pii("Hello world")
        assert len(results) == 0

    def test_detect_empty(self):
        """Test empty string."""
        results = detect_pii("")
        assert len(results) == 0


class TestRedactPII:
    """Tests for redact_pii function."""

    def test_redact_email(self):
        """Test email redaction."""
        text = "Contact me at test@example.com"
        result = redact_pii(text)
        assert "[REDACTED_EMAIL]" in result
        assert "test@example.com" not in result

    def test_redact_multiple(self):
        """Test multiple PII redaction."""
        text = "Email: test@example.com, Phone: 555-123-4567"
        result = redact_pii(text)
        assert "[REDACTED_EMAIL]" in result
        assert "[REDACTED_PHONE]" in result

    def test_redact_indian_formats(self):
        """Test Indian PII redaction."""
        text = "Aadhaar: 1234 5678 9012, PAN: ABCDE1234F"
        result = redact_pii(text)
        assert "[REDACTED_AADHAAR]" in result
        assert "[REDACTED_PAN]" in result

    def test_redact_custom_replacement(self):
        """Test custom replacement string."""
        text = "Email: test@example.com"
        result = redact_pii(text, replacement="***")
        assert "***_EMAIL" in result

    def test_redact_no_pii(self):
        """Test no PII to redact."""
        text = "Hello world"
        result = redact_pii(text)
        assert result == "Hello world"

    def test_redact_empty(self):
        """Test empty string."""
        result = redact_pii("")
        assert result == ""


class TestRedactPIIDict:
    """Tests for redact_pii_dict function."""

    def test_redact_dict_string_values(self):
        """Test dict redaction with string values."""
        data = {"email": "test@example.com", "name": "John"}
        result = redact_pii_dict(data)
        assert "[REDACTED_EMAIL]" in result["email"]
        assert result["name"] == "John"

    def test_redact_dict_nested(self):
        """Test dict redaction with nested dict."""
        data = {"user": {"email": "test@example.com", "age": 30}}
        result = redact_pii_dict(data)
        assert "[REDACTED_EMAIL]" in result["user"]["email"]
        assert result["user"]["age"] == 30

    def test_redact_dict_list(self):
        """Test dict redaction with list of strings."""
        data = {"emails": ["test@example.com", "admin@example.com"]}
        result = redact_pii_dict(data)
        assert "[REDACTED_EMAIL]" in result["emails"][0]
        assert "[REDACTED_EMAIL]" in result["emails"][1]

    def test_redact_dict_list_of_dicts(self):
        """Test dict redaction with list of dicts."""
        data = {"users": [{"email": "test@example.com"}, {"email": "admin@example.com"}]}
        result = redact_pii_dict(data)
        assert "[REDACTED_EMAIL]" in result["users"][0]["email"]
        assert "[REDACTED_EMAIL]" in result["users"][1]["email"]

    def test_redact_non_dict(self):
        """Test non-dict input returns as-is."""
        assert redact_pii_dict("string") == "string"
        assert redact_pii_dict(123) == 123
        assert redact_pii_dict(["list"]) == ["list"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
