"""
NIM Sentinel RAG Subgraph

Handles retrieval and generation for RAG queries.
"""

import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from nim_sentinel.db.client import get_database
from nim_sentinel.db.repositories import get_chunk_repository
from nim_sentinel.graph.state import AgentState
from nim_sentinel.observability.decorators import traced_rag_node, traced_retriever
from nim_sentinel.rag.ingestion.embedder import get_embedding_client
from nim_sentinel.rag.retriever import get_hybrid_retriever

logger = logging.getLogger(__name__)


@traced_retriever
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


@traced_rag_node
async def generate_node(state: AgentState) -> AgentState:
    """Generate answer using retrieved context."""
    logger.info("RAG Subgraph: Generating answer")

    if not state.retrieval_results:
        state.answer = "I couldn't find any relevant information to answer your query."
        state.confidence = 0.1
        state.needs_critique = False
        return state

    try:
        from nim_sentinel.llm.model_registry import get_model_registry

        registry = get_model_registry()

        async def _generate(model: ChatNVIDIA) -> str:
            # Build context from retrieval results
            context_parts = []
            for i, result in enumerate(state.retrieval_results):
                context_parts.append(f"[Source {i+1}] {result.content}")
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

            response = await model.ainvoke(messages)
            # Handle response.content which can be str or list
            content = response.content
            if isinstance(content, list):
                content = " ".join(str(c) for c in content)
            return content

        # Use retry with fallback
        answer = await registry.call_with_retry_and_fallback(
            role="generator_llm",
            model_type="chat",
            func=_generate,
        )

        # Check if fallback was used
        fallback_used = False
        if isinstance(answer, dict):
            fallback_used = answer.get("llm_fallback_used", False)
            answer = answer.get("answer", str(answer))

        state.answer = answer
        state.metadata["llm_fallback_used"] = fallback_used

        # Calculate confidence based on retrieval scores
        if state.retrieval_results:
            avg_score = sum(r.score for r in state.retrieval_results) / len(state.retrieval_results)
            state.confidence = min(max(avg_score, 0.0), 1.0)
        else:
            state.confidence = 0.1

        state.needs_critique = True

        logger.info(
            "RAG Subgraph: Generated answer (confidence: %.2f, fallback: %s)",
            state.confidence,
            fallback_used,
        )

    except Exception as e:
        logger.error("RAG Subgraph: Generation failed: %s", e)
        # Re-raise to let the API layer handle it with proper HTTP 503
        raise

    state.updated_at = __import__("datetime").datetime.utcnow()
    return state


async def rag_subgraph(state: AgentState) -> AgentState:
    """Run the full RAG pipeline: retrieve -> generate."""
    state = await retrieve_node(state)  # type: ignore[arg-type, misc]
    state = await generate_node(state)
    return state
