"""
NIM Sentinel RAG Subgraph

Handles retrieval and generation for RAG queries.
"""

import logging
from typing import Any
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from nim_sentinel.core.config import get_model_config, get_settings
from nim_sentinel.db.client import get_database
from nim_sentinel.db.repositories import get_chunk_repository
from nim_sentinel.rag.ingestion.embedder import get_embedding_client
from nim_sentinel.rag.retriever import HybridRetriever, get_hybrid_retriever
from nim_sentinel.graph.state import AgentState

logger = logging.getLogger(__name__)


async def retrieve_node(state: AgentState) -> AgentState:
    """Retrieve relevant documents using hybrid retriever."""
    logger.info("RAG Subgraph: Starting retrieval for query: %s", state.query[:100])

    try:
        # Get embedding for query
        embedding_client = await get_embedding_client()
        query_embedding = await embedding_client.embed_query(state.query)

        # Get database and chunk repository
        db = await get_database()
        chunk_repo = get_chunk_repository(db, state.tenant_id)
        retriever = await get_hybrid_retriever(chunk_repo)

        # Perform retrieval
        results = await retriever.retrieve(
            query=state.query,
            query_embedding=query_embedding,
        )

        state.retrieval_results = results
        state.citations = [r.to_citation() for r in results]

        logger.info("RAG Subgraph: Retrieved %d results", len(results))

    except Exception as e:
        logger.error("RAG Subgraph: Retrieval failed: %s", e)
        state.retrieval_results = []
        state.citations = []
        state.metadata["retrieval_error"] = str(e)

    state.updated_at = __import__("datetime").datetime.utcnow()
    return state


async def generate_node(state: AgentState) -> AgentState:
    """Generate answer using retrieved context."""
    logger.info("RAG Subgraph: Generating answer")

    if not state.retrieval_results:
        state.answer = "I couldn't find any relevant information to answer your query."
        state.confidence = 0.1
        state.needs_critique = False
        return state

    try:
        settings = get_settings()
        generator_config = get_model_config("generator_llm")

        llm = ChatNVIDIA(
            model=generator_config.primary,
            api_key=settings.nvidia_api_key,
            temperature=generator_config.temperature,
            max_tokens=generator_config.max_tokens,
            timeout=generator_config.timeout_seconds,
        )

        # Build context from retrieval results
        context_parts = []
        for i, result in enumerate(state.retrieval_results):
            context_parts.append(
                f"[Source {i+1}] {result.content}"
            )
        context = "\n\n".join(context_parts)

        # Build prompt
        system_prompt = """You are NIM Sentinel, an enterprise RAG assistant.
Answer the user's question using ONLY the provided context.
If the context doesn't contain enough information, say so.
Always cite your sources using [Source N] format.
Be concise and accurate."""

        user_prompt = f"""Context:
{context}

Question: {state.query}

Answer:"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        response = await llm.ainvoke(messages)
        # Handle response.content which can be str or list
        content = response.content
        if isinstance(content, list):
            content = " ".join(str(c) for c in content)
        state.answer = content

        # Calculate confidence based on retrieval scores
        if state.retrieval_results:
            avg_score = sum(r.score for r in state.retrieval_results) / len(state.retrieval_results)
            state.confidence = min(max(avg_score, 0.0), 1.0)
        else:
            state.confidence = 0.1

        state.needs_critique = True

        logger.info("RAG Subgraph: Generated answer (confidence: %.2f)", state.confidence)

    except Exception as e:
        logger.error("RAG Subgraph: Generation failed: %s", e)
        state.answer = f"Error generating answer: {str(e)}"
        state.confidence = 0.0
        state.needs_critique = False
        state.metadata["generation_error"] = str(e)

    state.updated_at = __import__("datetime").datetime.utcnow()
    return state


async def rag_subgraph(state: AgentState) -> AgentState:
    """Run the full RAG pipeline: retrieve -> generate."""
    state = await retrieve_node(state)
    state = await generate_node(state)
    return state