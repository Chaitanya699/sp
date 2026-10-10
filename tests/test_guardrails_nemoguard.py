"""
Tests for Guardrails - NemoGuard module
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from nim_sentinel.guardrails.nemoguard import (
    NemoGuardClient,
    NemoGuardResult,
    NemoGuardModel,
    NemoGuardAction,
    get_nemo_guard_client,
    reset_nemo_guard_client,
)


class TestNemoGuardClient:
    """Tests for NemoGuardClient class."""

    @pytest.fixture
    def client(self):
        """Create NemoGuardClient instance."""
        reset_nemo_guard_client()
        return NemoGuardClient()

    @pytest.mark.asyncio
    async def test_check_content_safety_no_model(self, client):
        """Test content safety when model unavailable."""
        with patch("nim_sentinel.guardrails.nemoguard.get_model_registry") as mock_registry:
            mock_registry.return_value.get_chat_model.return_value = None
            result = await client.check_content_safety("Hello world")
            assert result.triggered is False
            assert result.action == NemoGuardAction.ALLOW
            assert result.available is False
            assert result.error == "Model not available"

    @pytest.mark.asyncio
    async def test_check_jailbreak_no_model(self, client):
        """Test jailbreak when model unavailable."""
        with patch("nim_sentinel.guardrails.nemoguard.get_model_registry") as mock_registry:
            mock_registry.return_value.get_chat_model.return_value = None
            result = await client.check_jailbreak("Hello world")
            assert result.triggered is False
            assert result.action == NemoGuardAction.ALLOW
            assert result.available is False

    @pytest.mark.asyncio
    async def test_check_topic_no_model(self, client):
        """Test topic when model unavailable."""
        with patch("nim_sentinel.guardrails.nemoguard.get_model_registry") as mock_registry:
            mock_registry.return_value.get_chat_model.return_value = None
            result = await client.check_topic("Hello world")
            assert result.triggered is False
            assert result.action == NemoGuardAction.ALLOW
            assert result.available is False

    @pytest.mark.asyncio
    async def test_check_content_safety_safe(self, client):
        """Test content safety returns SAFE."""
        mock_model = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = "SAFE"
        mock_model.ainvoke.return_value = mock_response

        with patch("nim_sentinel.guardrails.nemoguard.get_model_registry") as mock_registry:
            mock_registry.return_value.get_chat_model.return_value = mock_model
            result = await client.check_content_safety("Hello world")
            assert result.triggered is False
            assert result.action == NemoGuardAction.ALLOW
            assert result.confidence == 0.9

    @pytest.mark.asyncio
    async def test_check_content_safety_unsafe(self, client):
        """Test content safety returns UNSAFE."""
        mock_model = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = "UNSAFE: hate speech"
        mock_model.ainvoke.return_value = mock_response

        with patch("nim_sentinel.guardrails.nemoguard.get_model_registry") as mock_registry:
            mock_registry.return_value.get_chat_model.return_value = mock_model
            result = await client.check_content_safety("Hateful content")
            assert result.triggered is True
            assert result.action == NemoGuardAction.BLOCK
            assert result.category == "hate speech"
            assert result.confidence == 0.9

    @pytest.mark.asyncio
    async def test_check_jailbreak_safe(self, client):
        """Test jailbreak returns SAFE."""
        mock_model = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = "SAFE"
        mock_model.ainvoke.return_value = mock_response

        with patch("nim_sentinel.guardrails.nemoguard.get_model_registry") as mock_registry:
            mock_registry.return_value.get_chat_model.return_value = mock_model
            result = await client.check_jailbreak("Hello world")
            assert result.triggered is False
            assert result.action == NemoGuardAction.ALLOW

    @pytest.mark.asyncio
    async def test_check_jailbreak_detected(self, client):
        """Test jailbreak detected."""
        mock_model = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = "JAILBREAK: roleplay"
        mock_model.ainvoke.return_value = mock_response

        with patch("nim_sentinel.guardrails.nemoguard.get_model_registry") as mock_registry:
            mock_registry.return_value.get_chat_model.return_value = mock_model
            result = await client.check_jailbreak("Roleplay as a hacker")
            assert result.triggered is True
            assert result.action == NemoGuardAction.BLOCK
            assert result.category == "roleplay"
            assert result.confidence == 0.95

    @pytest.mark.asyncio
    async def test_check_topic_on_topic(self, client):
        """Test topic returns ON_TOPIC."""
        mock_model = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = "ON_TOPIC"
        mock_model.ainvoke.return_value = mock_response

        with patch("nim_sentinel.guardrails.nemoguard.get_model_registry") as mock_registry:
            mock_registry.return_value.get_chat_model.return_value = mock_model
            result = await client.check_topic("How do I query documents?")
            assert result.triggered is False
            assert result.action == NemoGuardAction.ALLOW

    @pytest.mark.asyncio
    async def test_check_topic_off_topic(self, client):
        """Test topic returns OFF_TOPIC."""
        mock_model = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = "OFF_TOPIC: unrelated to RAG"
        mock_model.ainvoke.return_value = mock_response

        with patch("nim_sentinel.guardrails.nemoguard.get_model_registry") as mock_registry:
            mock_registry.return_value.get_chat_model.return_value = mock_model
            result = await client.check_topic("How to make a bomb")
            assert result.triggered is True
            assert result.action == NemoGuardAction.FLAG
            assert result.category == "unrelated to rag"  # normalized to lowercase
            assert result.confidence == 0.8

    @pytest.mark.asyncio
    async def test_check_all(self, client):
        """Test check_all runs all checks."""
        mock_model = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = "SAFE"
        mock_model.ainvoke.return_value = mock_response

        with patch("nim_sentinel.guardrails.nemoguard.get_model_registry") as mock_registry:
            mock_registry.return_value.get_chat_model.return_value = mock_model
            results = await client.check_all("Hello world")
            assert "content_safety" in results
            assert "jailbreak" in results
            assert "topic" in results
            assert all(isinstance(r, NemoGuardResult) for r in results.values())

    @pytest.mark.asyncio
    async def test_check_all_exception_handling(self, client):
        """Test check_all handles exceptions."""
        with patch("nim_sentinel.guardrails.nemoguard.get_model_registry") as mock_registry:
            mock_registry.return_value.get_chat_model.side_effect = Exception("API error")
            results = await client.check_all("Hello world")
            assert all(isinstance(r, NemoGuardResult) for r in results.values())
            assert all(r.error is not None for r in results.values())


class TestNemoGuardClientSingleton:
    """Tests for global NemoGuardClient instance."""

    def test_get_nemo_guard_client_singleton(self):
        """Test get_nemo_guard_client returns singleton."""
        reset_nemo_guard_client()
        c1 = get_nemo_guard_client()
        c2 = get_nemo_guard_client()
        assert c1 is c2
        reset_nemo_guard_client()

    def test_reset_nemo_guard_client(self):
        """Test reset_nemo_guard_client clears instance."""
        reset_nemo_guard_client()
        c1 = get_nemo_guard_client()
        reset_nemo_guard_client()
        c2 = get_nemo_guard_client()
        assert c1 is not c2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])