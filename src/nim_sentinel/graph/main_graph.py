"""
NIM Sentinel Main LangGraph

Orchestrates the multi-agent RAG system with supervisor, RAG subgraph, and critic.
"""

import logging
from typing import Any
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.base import BaseCheckpointSaver
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph

from nim_sentinel.graph.state import AgentState, create_initial_state
from nim_sentinel.graph.supervisor import supervisor_node, get_next_node
from nim_sentinel.graph.subgraphs.rag import rag_subgraph
from nim_sentinel.graph.nodes.critic import critic_node
from nim_sentinel.graph.checkpointer import MongoDBCheckpointer, create_checkpointer

logger = logging.getLogger(__name__)


def create_graph(checkpointer: BaseCheckpointSaver[Any] | None = None) -> CompiledStateGraph[Any, Any, Any, Any]:
    """
    Create the main agent graph.

    Graph structure:
    - supervisor: Analyzes query and routes to next node
    - rag_subgraph: Retrieves documents and generates answer
    - critic: Reviews answer for quality
    - end: Terminal node

    Flow:
    supervisor -> rag_subgraph -> critic -> (supervisor or end)
    """

    # Create graph with AgentState
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("rag_subgraph", rag_subgraph)
    graph.add_node("critic", critic_node)

    # Set entry point
    graph.set_entry_point("supervisor")

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

    # Critic goes back to supervisor for routing decision
    graph.add_edge("critic", "supervisor")

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

    logger.info("Graph completed. Answer length: %d, confidence: %.2f",
                len(final_state.answer), final_state.confidence)

    return final_state


def get_graph_for_tenant(tenant_id: str) -> CompiledStateGraph[Any, Any, Any, Any]:
    """Get a compiled graph with MongoDB checkpointer for a tenant."""
    checkpointer = create_checkpointer(tenant_id)
    return create_graph(checkpointer)