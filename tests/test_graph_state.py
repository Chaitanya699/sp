"""
Tests for NIM Sentinel Graph State Module (B1)
"""

from datetime import datetime

from langchain_core.messages import AIMessage, HumanMessage
from nim_sentinel.graph.state import (
    AgentState,
    CriticOutput,
    SupervisorDecision,
    create_initial_state,
)


class TestAgentState:
    """Tests for AgentState dataclass."""

    def test_default_initialization(self):
        """Test AgentState initializes with defaults."""
        state = AgentState()
        assert state.messages == []
        assert state.query == ""
        assert state.tenant_id == ""
        assert state.user_id == ""
        assert state.session_id == ""
        assert state.retrieval_results == []
        assert state.citations == []
        assert state.answer == ""
        assert state.confidence == 0.0
        assert state.needs_critique is True
        assert state.critique_feedback == ""
        assert state.retry_count == 0
        assert state.metadata == {}
        assert isinstance(state.created_at, datetime)
        assert isinstance(state.updated_at, datetime)

    def test_custom_initialization(self):
        """Test AgentState with custom values."""
        messages = [HumanMessage(content="Hello"), AIMessage(content="Hi")]
        state = AgentState(
            messages=messages,
            query="test query",
            tenant_id="tenant_1",
            user_id="user_1",
            session_id="session_1",
            answer="test answer",
            confidence=0.9,
            needs_critique=False,
        )
        assert state.messages == messages
        assert state.query == "test query"
        assert state.tenant_id == "tenant_1"
        assert state.user_id == "user_1"
        assert state.session_id == "session_1"
        assert state.answer == "test answer"
        assert state.confidence == 0.9
        assert state.needs_critique is False


class TestSupervisorDecision:
    """Tests for SupervisorDecision dataclass."""

    def test_valid_decision(self):
        """Test SupervisorDecision with valid values."""
        decision = SupervisorDecision(
            next_node="rag_subgraph",
            reasoning="Query requires RAG",
            confidence=0.9,
        )
        assert decision.next_node == "rag_subgraph"
        assert decision.reasoning == "Query requires RAG"
        assert decision.confidence == 0.9

    def test_all_valid_nodes(self):
        """Test all valid next_node values."""
        for node in ["rag_subgraph", "critic", "end"]:
            decision = SupervisorDecision(next_node=node, reasoning="test", confidence=0.5)
            assert decision.next_node == node


class TestCriticOutput:
    """Tests for CriticOutput dataclass."""

    def test_approved_output(self):
        """Test CriticOutput when approved."""
        output = CriticOutput(
            approved=True,
            feedback="Answer is accurate and well-cited",
            confidence=0.95,
            suggested_changes=[],
        )
        assert output.approved is True
        assert output.confidence == 0.95
        assert output.suggested_changes == []

    def test_rejected_output(self):
        """Test CriticOutput when rejected."""
        output = CriticOutput(
            approved=False,
            feedback="Missing citations",
            confidence=0.3,
            suggested_changes=["Add citations", "Verify facts"],
        )
        assert output.approved is False
        assert output.suggested_changes == ["Add citations", "Verify facts"]


class TestCreateInitialState:
    """Tests for create_initial_state factory function."""

    def test_basic_creation(self):
        """Test creating initial state with required params."""
        state = create_initial_state(
            query="What is NIM Sentinel?",
            tenant_id="tenant_1",
            user_id="user_1",
            session_id="session_1",
        )
        assert state.query == "What is NIM Sentinel?"
        assert state.tenant_id == "tenant_1"
        assert state.user_id == "user_1"
        assert state.session_id == "session_1"
        assert state.messages == []
        assert state.needs_critique is True

    def test_with_messages(self):
        """Test creating initial state with message history."""
        messages = [HumanMessage(content="Previous question")]
        state = create_initial_state(
            query="Follow up",
            tenant_id="tenant_1",
            user_id="user_1",
            session_id="session_1",
            messages=messages,
        )
        assert state.messages == messages
        assert len(state.messages) == 1
