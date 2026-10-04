"""
NIM Sentinel LangGraph State Definitions

Defines the state schema for the multi-agent RAG system.
"""

from typing import Any, Literal
from dataclasses import dataclass, field
from datetime import datetime
from langchain_core.messages import BaseMessage
from nim_sentinel.rag.retriever import RetrievalResult


@dataclass
class AgentState:
    """
    Main state for the agent graph.

    Attributes:
        messages: Conversation history
        query: Current user query
        tenant_id: Tenant identifier for isolation
        user_id: User identifier
        session_id: Session identifier
        retrieval_results: Results from RAG retrieval
        citations: Citation metadata for response
        answer: Final generated answer
        confidence: Confidence score (0-1)
        needs_critique: Whether critic should review
        critique_feedback: Feedback from critic
        retry_count: Number of retries
        metadata: Additional metadata
    """
    messages: list[BaseMessage] = field(default_factory=list)
    query: str = ""
    tenant_id: str = ""
    user_id: str = ""
    session_id: str = ""
    retrieval_results: list[RetrievalResult] = field(default_factory=list)
    citations: list[dict[str, Any]] = field(default_factory=list)
    answer: str = ""
    confidence: float = 0.0
    needs_critique: bool = True
    critique_feedback: str = ""
    retry_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SupervisorDecision:
    """Decision output from supervisor node."""
    next_node: Literal["rag_subgraph", "critic", "end"]
    reasoning: str
    confidence: float


@dataclass
class CriticOutput:
    """Output from critic node."""
    approved: bool
    feedback: str
    confidence: float
    suggested_changes: list[str] = field(default_factory=list)


def create_initial_state(
    query: str,
    tenant_id: str,
    user_id: str,
    session_id: str,
    messages: list[BaseMessage] | None = None,
) -> AgentState:
    """Create initial agent state."""
    return AgentState(
        messages=messages or [],
        query=query,
        tenant_id=tenant_id,
        user_id=user_id,
        session_id=session_id,
    )