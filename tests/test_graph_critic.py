"""
Tests for NIM Sentinel Graph Critic Module (B4)
"""

from unittest.mock import AsyncMock, patch

import pytest
from nim_sentinel.graph.nodes.critic import Critic, critic_node
from nim_sentinel.graph.state import AgentState, CriticOutput


class TestCritic:
    """Tests for Critic class."""

    @pytest.fixture
    def mock_registry(self):
        """Create a mock model registry."""
        with patch("nim_sentinel.graph.nodes.critic.get_model_registry") as mock:
            mock_registry = AsyncMock()
            mock_registry.call_with_retry_and_fallback = AsyncMock()
            mock.return_value = mock_registry
            yield mock_registry

    @pytest.fixture
    def critic(self, mock_registry):
        """Create Critic instance with mocked registry."""
        with patch("nim_sentinel.graph.nodes.critic.get_settings") as mock_settings:
            mock_settings.return_value.nvidia_api_key = "test-key"
            with patch("nim_sentinel.graph.nodes.critic.get_model_config") as mock_config:
                mock_config.return_value.primary = "test-model"
                mock_config.return_value.temperature = 0.1
                mock_config.return_value.max_tokens = 500
                mock_config.return_value.timeout_seconds = 30
                c = Critic()
                return c

    @pytest.mark.asyncio
    async def test_review_approves_good_answer(self, critic, mock_registry):
        """Test that critic approves a well-cited, accurate answer."""
        mock_registry.call_with_retry_and_fallback.return_value = {
            "approved": True,
            "feedback": "Answer is accurate, well-cited, and complete.",
            "confidence": 0.95,
            "suggested_changes": [],
        }

        state = AgentState(
            query="What is NIM Sentinel?",
            tenant_id="tenant_1",
            user_id="user_1",
            session_id="session_1",
            answer="NIM Sentinel is an enterprise RAG system with NVIDIA NIM integration.",
            citations=[
                {
                    "document_id": "doc1",
                    "chunk_index": 0,
                    "content": "NIM Sentinel is an enterprise RAG system.",
                    "score": 0.9,
                },
                {
                    "document_id": "doc2",
                    "chunk_index": 1,
                    "content": "It uses NVIDIA NIM for embeddings.",
                    "score": 0.85,
                },
            ],
            confidence=0.85,
        )

        result = await critic.review(state)

        assert result.approved is True
        assert result.confidence >= 0.9
        assert len(result.suggested_changes) == 0

    @pytest.mark.asyncio
    async def test_review_rejects_missing_citations(self, critic, mock_registry):
        """Test that critic rejects answer without citations."""
        mock_registry.call_with_retry_and_fallback.return_value = {
            "approved": False,
            "feedback": "Answer lacks citations for key claims.",
            "confidence": 0.3,
            "suggested_changes": [
                "Add citations for all factual claims",
                "Reference source documents",
            ],
        }

        state = AgentState(
            query="What is NIM Sentinel?",
            tenant_id="tenant_1",
            user_id="user_1",
            session_id="session_1",
            answer="NIM Sentinel is an enterprise RAG system.",
            citations=[],
            confidence=0.5,
        )

        result = await critic.review(state)

        assert result.approved is False
        assert "citation" in result.feedback.lower()
        assert len(result.suggested_changes) > 0

    @pytest.mark.asyncio
    async def test_review_rejects_hallucination(self, critic, mock_registry):
        """Test that critic rejects answer with hallucinated content."""
        mock_registry.call_with_retry_and_fallback.return_value = {
            "approved": False,
            "feedback": "Answer contains information not supported by citations.",
            "confidence": 0.2,
            "suggested_changes": [
                "Remove unsupported claims",
                "Only use information from provided sources",
            ],
        }

        state = AgentState(
            query="What is NIM Sentinel?",
            tenant_id="tenant_1",
            user_id="user_1",
            session_id="session_1",
            answer="NIM Sentinel was founded in 2020 by Elon Musk and uses quantum computing.",
            citations=[
                {
                    "document_id": "doc1",
                    "chunk_index": 0,
                    "content": "NIM Sentinel is an enterprise RAG system.",
                    "score": 0.9,
                },
            ],
            confidence=0.6,
        )

        result = await critic.review(state)

        assert result.approved is False
        assert "not supported" in result.feedback.lower() or "hallucinat" in result.feedback.lower()
        assert len(result.suggested_changes) > 0

    @pytest.mark.asyncio
    async def test_review_rejects_incomplete_answer(self, critic, mock_registry):
        """Test that critic rejects incomplete answer."""
        mock_registry.call_with_retry_and_fallback.return_value = {
            "approved": False,
            "feedback": "Answer does not fully address the question.",
            "confidence": 0.4,
            "suggested_changes": [
                "Address all parts of the question",
                "Provide more detail on architecture",
            ],
        }

        state = AgentState(
            query="What is NIM Sentinel and how does it work?",
            tenant_id="tenant_1",
            user_id="user_1",
            session_id="session_1",
            answer="NIM Sentinel is a RAG system.",
            citations=[
                {
                    "document_id": "doc1",
                    "chunk_index": 0,
                    "content": "NIM Sentinel is an enterprise RAG system.",
                    "score": 0.9,
                },
            ],
            confidence=0.7,
        )

        result = await critic.review(state)

        assert result.approved is False
        assert "fully address" in result.feedback.lower() or "incomplete" in result.feedback.lower()
        assert len(result.suggested_changes) > 0


class TestCriticNode:
    """Tests for critic_node function."""

    @pytest.mark.asyncio
    async def test_critic_node_updates_state_approved(self):
        """Test that critic_node updates state when approved."""
        with patch("nim_sentinel.graph.nodes.critic.Critic") as mock_critic_class:
            mock_critic = AsyncMock()
            mock_critic.review = AsyncMock(
                return_value=CriticOutput(
                    approved=True,
                    feedback="Answer is accurate and well-cited",
                    confidence=0.95,
                    suggested_changes=[],
                )
            )
            mock_critic_class.return_value = mock_critic

            state = AgentState(
                query="What is NIM Sentinel?",
                tenant_id="tenant_1",
                user_id="user_1",
                session_id="session_1",
                answer="NIM Sentinel is an enterprise RAG system.",
                citations=[
                    {"document_id": "doc1", "chunk_index": 0, "content": "test", "score": 0.9}
                ],
                confidence=0.85,
            )
            result = await critic_node(state)

            assert result.critique_feedback == "Answer is accurate and well-cited"
            assert result.needs_critique is False
            assert result.retry_count == 0
            assert "critic_output" in result.metadata
            assert result.metadata["critic_output"]["approved"] is True

    @pytest.mark.asyncio
    async def test_critic_node_updates_state_rejected(self):
        """Test that critic_node updates state when rejected."""
        with patch("nim_sentinel.graph.nodes.critic.Critic") as mock_critic_class:
            mock_critic = AsyncMock()
            mock_critic.review = AsyncMock(
                return_value=CriticOutput(
                    approved=False,
                    feedback="Missing citations",
                    confidence=0.3,
                    suggested_changes=["Add citations"],
                )
            )
            mock_critic_class.return_value = mock_critic

            state = AgentState(
                query="What is NIM Sentinel?",
                tenant_id="tenant_1",
                user_id="user_1",
                session_id="session_1",
                answer="NIM Sentinel is an enterprise RAG system.",
                citations=[],
                confidence=0.5,
            )
            result = await critic_node(state)

            assert result.critique_feedback == "Missing citations"
            assert result.needs_critique is True
            assert result.retry_count == 1
            assert "critic_output" in result.metadata
            assert result.metadata["critic_output"]["approved"] is False

    @pytest.mark.asyncio
    async def test_critic_node_max_retries(self):
        """Test that critic_node doesn't increment retry_count beyond max."""
        with patch("nim_sentinel.graph.nodes.critic.Critic") as mock_critic_class:
            mock_critic = AsyncMock()
            mock_critic.review = AsyncMock(
                return_value=CriticOutput(
                    approved=False,
                    feedback="Still missing citations",
                    confidence=0.3,
                    suggested_changes=["Add citations"],
                )
            )
            mock_critic_class.return_value = mock_critic

            state = AgentState(
                query="What is NIM Sentinel?",
                tenant_id="tenant_1",
                user_id="user_1",
                session_id="session_1",
                answer="NIM Sentinel is an enterprise RAG system.",
                citations=[],
                confidence=0.5,
                retry_count=3,  # Already at max
            )
            result = await critic_node(state)

            # Should not increment beyond max (3)
            assert result.retry_count == 3
            assert result.needs_critique is True
