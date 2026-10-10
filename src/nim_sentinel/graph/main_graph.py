"""
NIM Sentinel Main LangGraph

Orchestrates the multi-agent RAG system with supervisor, RAG subgraph, and critic.
"""

import logging
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph
from nim_sentinel.graph.checkpointer import create_checkpointer
from nim_sentinel.graph.nodes.critic import critic_node
from nim_sentinel.graph.state import AgentState, create_initial_state
from nim_sentinel.graph.subgraphs.rag import rag_subgraph
from nim_sentinel.graph.supervisor import get_next_node, supervisor_node
from nim_sentinel.guardrails.input_guard import get_input_guardrails
from nim_sentinel.guardrails.output_guard import get_output_guardrails

logger = logging.getLogger(__name__)


async def input_guard_node(state: AgentState) -> AgentState:
    """Input guardrail node - checks query for safety issues."""
    guardrails = get_input_guardrails(use_nemoguard=True, redact_pii=True)
    response = await guardrails.check_all(state.query)

    # Update state with guardrail results
    state.metadata["input_guardrails"] = response.to_dict()

    if not response.allowed:
        # Block the query
        state.answer = "I cannot process this request due to safety concerns."
        state.confidence = 0.0
        state.metadata["blocked_by"] = "input_guardrails"
        # Route to end
        state.metadata["next_node"] = "end"
    elif response.modified_content:
        # Use redacted query
        state.query = response.modified_content
        state.metadata["pii_redacted"] = True

    return state


async def output_guard_node(state: AgentState) -> AgentState:
    """Output guardrail node - checks answer for safety, groundedness, PII leaks."""
    guardrails = get_output_guardrails(use_nemoguard=True)

    # Convert retrieval results to citations format
    citations = state.citations if state.citations else None

    response = await guardrails.check_all(state.answer, citations)

    # Update state with guardrail results
    state.metadata["output_guardrails"] = response.to_dict()

    if not response.allowed:
        # Block the answer
        state.answer = "I cannot provide this response due to safety concerns."
        state.confidence = 0.0
        state.metadata["blocked_by"] = "output_guardrails"

    return state


def create_graph(
    checkpointer: BaseCheckpointSaver[Any] | None = None,
) -> CompiledStateGraph[Any, Any, Any, Any]:
    """
    Create the main agent graph.

    Graph structure:
    - input_guard: Validates and sanitizes user query
    - supervisor: Analyzes query and routes to next node
    - rag_subgraph: Retrieves documents and generates answer
    - critic: Reviews answer for quality
    - output_guard: Validates generated answer
    - end: Terminal node

    Flow:
    input_guard -> supervisor -> rag_subgraph -> critic -> output_guard -> (supervisor or end)
    """

    # Create graph with AgentState
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("input_guard", input_guard_node)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("rag_subgraph", rag_subgraph)
    graph.add_node("critic", critic_node)
    graph.add_node("output_guard", output_guard_node)

    # Set entry point
    graph.set_entry_point("input_guard")

    # Add conditional edges from input_guard
    def route_after_input_guard(state: AgentState) -> str:
        next_node = state.metadata.get("next_node")
        return next_node if isinstance(next_node, str) else "supervisor"

    graph.add_conditional_edges(
        "input_guard",
        route_after_input_guard,
        {
            "supervisor": "supervisor",
            "end": END,
        },
    )

    # Add conditional edges from supervisor
    graph.add_conditional_edges(
        "supervisor",
        get_next_node,
        {
            "rag_subgraph": "rag_subgraph",
            "critic": "critic",
            "end": END,
        },
    )

    # RAG subgraph goes to critic
    graph.add_edge("rag_subgraph", "critic")

    # Critic goes to output_guard
    graph.add_edge("critic", "output_guard")

    # Output guard goes back to supervisor for routing decision
    graph.add_edge("output_guard", "supervisor")

    # Compile with checkpointer if provided
    if checkpointer:
        compiled = graph.compile(checkpointer=checkpointer)
    else:
        compiled = graph.compile()

    logger.info("Main graph compiled successfully")
    return compiled


async def run_graph(
    query: str,
    tenant_id: str,
    user_id: str,
    session_id: str,
    messages: list[Any] | None = None,
    checkpointer: BaseCheckpointSaver[Any] | None = None,
) -> AgentState:
    """
    Run the agent graph with the given inputs.

    Args:
        query: User query
        tenant_id: Tenant identifier
        user_id: User identifier
        session_id: Session identifier (used as thread_id for checkpointer)
        messages: Optional conversation history
        checkpointer: Optional checkpointer for persistence

    Returns:
        Final AgentState with answer and citations
    """
    # Create initial state
    initial_state = create_initial_state(
        query=query,
        tenant_id=tenant_id,
        user_id=user_id,
        session_id=session_id,
        messages=messages,
    )

    # Create graph
    graph = create_graph(checkpointer)

    # Config for checkpointer
    config: RunnableConfig = {
        "configurable": {
            "thread_id": session_id,
            "checkpoint_ns": tenant_id,
        }
    }

    # Run graph
    logger.info("Running graph for query: %s", query[:100])
    final_state = await graph.ainvoke(initial_state, config=config)

    # Convert back to AgentState if needed
    if isinstance(final_state, dict):
        final_state = AgentState(**final_state)

    logger.info(
        "Graph completed. Answer length: %d, confidence: %.2f",
        len(final_state.answer),
        final_state.confidence,
    )

    return final_state


def get_graph_for_tenant(tenant_id: str) -> CompiledStateGraph[Any, Any, Any, Any]:
    """Get a compiled graph with MongoDB checkpointer for a tenant."""
    checkpointer = create_checkpointer(tenant_id)
    return create_graph(checkpointer)
