"""
Tests for NIM Sentinel Graph Supervisor Module (B2)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from nim_sentinel.graph.state import AgentState, SupervisorDecision
from nim_sentinel.graph.supervisor import Supervisor, supervisor_node, get_next_node


class TestSupervisor:
    """Tests for Supervisor class."""

    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM."""
        with patch("nim_sentinel.graph.supervisor.ChatNVIDIA") as mock:
            mock_instance = AsyncMock()
            mock_instance.ainvoke = AsyncMock()
            mock.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def supervisor(self, mock_llm):
        """Create Supervisor instance with mocked LLM."""
        with patch("nim_sentinel.graph.supervisor.get_settings") as mock_settings:
            mock_settings.return_value.nvidia_api_key = "test-key"
            with patch("nim_sentinel.graph.supervisor.get_model_config") as mock_config:
                mock_config.return_value.primary = "test-model"
                mock_config.return_value.temperature = 0.1
                mock_config.return_value.max_tokens = 100
                mock_config.return_value.timeout_seconds = 30
                sup = Supervisor()
                sup.llm = mock_llm
                return sup

    @pytest.mark.asyncio
    async def test_decide_greeting_ends(self, supervisor):
        """Test that greetings route to end."""
        state = AgentState(query="hello", tenant_id="t1", user_id="u1", session_id="s1")
        decision = await supervisor.decide(state)
        assert decision.next_node == "end"
        assert "greeting" in decision.reasoning.lower()

    @pytest.mark.asyncio
    async def test_decide_answer_needs_critique(self, supervisor):
        """Test that answer with needs_critique routes to critic."""
        state = AgentState(
            query="test",
            tenant_id="t1",
            user_id="u1",
            session_id="s1",
            answer="some answer",
            needs_critique=True,
            retry_count=0,
        )
        decision = await supervisor.decide(state)
        assert decision.next_node == "critic"
        assert "critic" in decision.reasoning.lower()

    @pytest.mark.asyncio
    async def test_decide_max_retries_ends(self, supervisor):
        """Test that max retries routes to end."""
        state = AgentState(
            query="test",
            tenant_id="t1",
            user_id="u1",
            session_id="s1",
            answer="some answer",
            needs_critique=True,
            retry_count=3,
        )
        decision = await supervisor.decide(state)
        assert decision.next_node == "end"
        assert "max retries" in decision.reasoning.lower()

    @pytest.mark.asyncio
    async def test_decide_critic_approved_ends(self, supervisor):
        """Test that critic approval routes to end."""
        state = AgentState(
            query="test",
            tenant_id="t1",
            user_id="u1",
            session_id="s1",
            answer="some answer",
            critique_feedback="approved",
            needs_critique=False,
            metadata={"critic_output": {"approved": True, "feedback": "approved", "confidence": 0.9}},
        )
        decision = await supervisor.decide(state)
        assert decision.next_node == "end"
        assert "approved" in decision.reasoning.lower()

    @pytest.mark.asyncio
    async def test_decide_default_rag(self, supervisor):
        """Test that normal queries route to rag_subgraph."""
        state = AgentState(query="What is NIM Sentinel?", tenant_id="t1", user_id="u1", session_id="s1")
        decision = await supervisor.decide(state)
        assert decision.next_node == "rag_subgraph"
        assert "rag" in decision.reasoning.lower()


class TestSupervisorNode:
    """Tests for supervisor_node function."""

    @pytest.mark.asyncio
    async def test_supervisor_node_updates_state(self):
        """Test that supervisor_node updates state metadata."""
        with patch("nim_sentinel.graph.supervisor.Supervisor") as mock_supervisor_class:
            mock_supervisor = AsyncMock()
            mock_supervisor.decide = AsyncMock(return_value=SupervisorDecision(
                next_node="rag_subgraph",
                reasoning="Test reasoning",
                confidence=0.9,
            ))
            mock_supervisor_class.return_value = mock_supervisor

            state = AgentState(query="test", tenant_id="t1", user_id="u1", session_id="s1")
            result = await supervisor_node(state)

            assert "supervisor_decision" in result.metadata
            assert result.metadata["supervisor_decision"]["next_node"] == "rag_subgraph"
            assert result.metadata["supervisor_decision"]["reasoning"] == "Test reasoning"
            assert result.metadata["supervisor_decision"]["confidence"] == 0.9


class TestGetNextNode:
    """Tests for get_next_node function."""

    def test_get_next_node_from_metadata(self):
        """Test extracting next_node from state metadata."""
        state = AgentState(
            query="test",
            tenant_id="t1",
            user_id="u1",
            session_id="s1",
            metadata={"supervisor_decision": {"next_node": "critic"}},
        )
        next_node = get_next_node(state)
        assert next_node == "critic"

    def test_get_next_node_default(self):
        """Test default next_node when not in metadata."""
        state = AgentState(query="test", tenant_id="t1", user_id="u1", session_id="s1")
        next_node = get_next_node(state)
        assert next_node == "rag_subgraph"

    def test_get_next_node_invalid_fallback(self):
        """Test fallback for invalid next_node."""
        state = AgentState(
            query="test",
            tenant_id="t1",
            user_id="u1",
            session_id="s1",
            metadata={"supervisor_decision": {"next_node": "invalid"}},
        )
        next_node = get_next_node(state)
        assert next_node == "rag_subgraph"