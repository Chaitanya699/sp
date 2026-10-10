"""
Tests for Guardrails - Output Guard module
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from nim_sentinel.guardrails.output_guard import (
    OutputGuardrails,
    GuardrailResponse,
    GuardResult,
    GuardAction,
    GuardCategory,
    get_output_guardrails,
    reset_output_guardrails,
)
from nim_sentinel.guardrails.nemoguard import NemoGuardResult, NemoGuardModel, NemoGuardAction


class TestOutputGuardrails:
    """Tests for OutputGuardrails class."""

    @pytest.fixture
    def guardrails(self):
        """Create OutputGuardrails instance."""
        reset_output_guardrails()
        return OutputGuardrails(use_nemoguard=False)

    def test_check_groundedness_no_citations(self, guardrails):
        """Test groundedness flags when no citations."""
        result = guardrails.check_groundedness("The answer is 42", None)
        assert result.triggered is True
        assert result.action == GuardAction.FLAG
        assert result.category == GuardCategory.GROUNDEDNESS

    def test_check_groundedness_with_citations(self, guardrails):
        """Test groundedness passes with citations."""
        citations = [{"content": "The answer is 42 according to the documentation and verified sources"}]
        result = guardrails.check_groundedness("The answer is 42", citations)
        assert result.triggered is False
        assert result.action == GuardAction.ALLOW

    def test_check_groundedness_sparse_citations(self, guardrails):
        """Test groundedness flags sparse citations with specific claims."""
        citations = [{"content": "x"}]
        result = guardrails.check_groundedness("The answer is 42 and the user is John", citations)
        assert result.triggered is True
        assert result.action == GuardAction.FLAG

    def test_check_pii_leak_clean(self, guardrails):
        """Test PII leak check on clean answer."""
        result = guardrails.check_pii_leak("The answer is based on the document.")
        assert result.triggered is False
        assert result.action == GuardAction.ALLOW

    def test_check_pii_leak_detected(self, guardrails):
        """Test PII leak check detects PII in answer."""
        result = guardrails.check_pii_leak("The user's email is test@example.com")
        assert result.triggered is True
        assert result.action == GuardAction.BLOCK
        assert "email" in result.details["findings"]

    @pytest.mark.asyncio
    async def test_check_nemoguard_content_safety_no_model(self, guardrails):
        """Test NemoGuard output content safety when model unavailable."""
        guardrails.use_nemoguard = True
        nemo_result = NemoGuardResult(
            model=NemoGuardModel.CONTENT_SAFETY,
            action=NemoGuardAction.ALLOW,
            triggered=False,
            available=False,
            error="Model not available",
        )
        with patch.object(guardrails.nemoguard, "check_content_safety", return_value=nemo_result):
            result = await guardrails.check_nemoguard_content_safety("Hello world")
            assert result.triggered is False
            assert result.action == GuardAction.ALLOW
            assert result.details.get("available") is False

    @pytest.mark.asyncio
    async def test_check_nemoguard_content_safety_block(self, guardrails):
        """Test NemoGuard content safety blocks."""
        guardrails.use_nemoguard = True
        nemo_result = NemoGuardResult(
            model=NemoGuardModel.CONTENT_SAFETY,
            action=NemoGuardAction.BLOCK,
            triggered=True,
            category="hate speech",
            confidence=0.9,
        )
        with patch.object(guardrails.nemoguard, "check_content_safety", return_value=nemo_result):
            result = await guardrails.check_nemoguard_content_safety("Hateful content")
            assert result.triggered is True
            assert result.action == GuardAction.BLOCK
            assert result.category == GuardCategory.CONTENT_SAFETY

    @pytest.mark.asyncio
    async def test_check_all_passes(self, guardrails):
        """Test check_all passes for clean answer with citations."""
        citations = [{"content": "The answer is 42 according to the docs"}]
        response = await guardrails.check_all("The answer is 42", citations=citations)
        assert response.allowed is True
        assert len(response.results) == 2  # groundedness, pii

    @pytest.mark.asyncio
    async def test_check_all_blocks_pii_leak(self, guardrails):
        """Test check_all blocks on PII leak."""
        citations = [{"content": "Some content"}]
        response = await guardrails.check_all("Email: test@example.com", citations=citations)
        assert response.allowed is False
        assert any(r.category == GuardCategory.PII and r.triggered for r in response.results)

    @pytest.mark.asyncio
    async def test_check_all_flags_ungrounded(self, guardrails):
        """Test check_all flags ungrounded answer."""
        response = await guardrails.check_all("The answer is 42", citations=None)
        assert response.allowed is True  # FLAG doesn't block
        assert any(r.category == GuardCategory.GROUNDEDNESS and r.triggered for r in response.results)

    @pytest.mark.asyncio
    async def test_check_all_nemoguard_block(self, guardrails):
        """Test check_all blocks on NemoGuard content safety."""
        guardrails.use_nemoguard = True
        nemo_result = NemoGuardResult(
            model=NemoGuardModel.CONTENT_SAFETY,
            action=NemoGuardAction.BLOCK,
            triggered=True,
            category="hate speech",
            confidence=0.9,
        )
        with patch.object(guardrails.nemoguard, "check_content_safety", return_value=nemo_result):
            citations = [{"content": "Some content"}]
            response = await guardrails.check_all("Hateful content", citations=citations)
            assert response.allowed is False
            assert any(r.category == GuardCategory.CONTENT_SAFETY and r.triggered for r in response.results)


class TestOutputGuardrailsSingleton:
    """Tests for global OutputGuardrails instance."""

    def test_get_output_guardrails_singleton(self):
        """Test get_output_guardrails returns singleton."""
        reset_output_guardrails()
        g1 = get_output_guardrails()
        g2 = get_output_guardrails()
        assert g1 is g2
        reset_output_guardrails()

    def test_reset_output_guardrails(self):
        """Test reset_output_guardrails clears instance."""
        reset_output_guardrails()
        g1 = get_output_guardrails()
        reset_output_guardrails()
        g2 = get_output_guardrails()
        assert g1 is not g2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])