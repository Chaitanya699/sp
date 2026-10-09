"""
NIM Sentinel Observability

Decorators for tracing nodes, tools, and LLM calls with LangSmith integration
and PII redaction.
"""

import functools
import logging
import time
from collections.abc import Callable
from typing import Any, TypeVar

from langsmith import traceable
from nim_sentinel.guardrails import get_input_guardrails, get_output_guardrails

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def _redact_pii(text: str) -> str:
    """Redact PII from text for logging/tracing."""
    if not text:
        return text

    guardrails = get_input_guardrails()
    _, redacted = guardrails.check_pii(text, redact=True)
    return redacted


def _redact_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Recursively redact PII from dictionary values."""
    if not isinstance(data, dict):
        return data

    redacted: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, str):
            redacted[key] = _redact_pii(value)
        elif isinstance(value, dict):
            redacted[key] = _redact_dict(value)
        elif isinstance(value, list):
            redacted[key] = [
                _redact_pii(item) if isinstance(item, str) else
                _redact_dict(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            redacted[key] = value
    return redacted


def traced_node(name: str | None = None, redact: bool = True) -> Callable[[F], F]:
    """
    Decorator for tracing LangGraph nodes.

    Args:
        name: Custom trace name (defaults to function name)
        redact: Whether to redact PII from inputs/outputs

    Usage:
        @traced_node("retrieve")
        async def retrieve_node(state: GraphState) -> GraphState:
            ...
    """
    def decorator(func: F) -> F:
        trace_name = name or func.__name__

        @functools.wraps(func)
        @traceable(name=trace_name, run_type="chain")
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.perf_counter()

            # Redact inputs for logging
            if redact and args:
                logged_args = _redact_dict(args[0]) if isinstance(args[0], dict) else args
                logger.debug(f"Node {trace_name} started", extra={"inputs": logged_args})
            else:
                logger.debug(f"Node {trace_name} started")

            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start_time) * 1000

                if redact and isinstance(result, dict):
                    logged_result = _redact_dict(result)
                    logger.debug(
                        f"Node {trace_name} completed",
                        extra={"duration_ms": duration_ms, "outputs": logged_result},
                    )
                else:
                    logger.debug(f"Node {trace_name} completed", extra={"duration_ms": duration_ms})

                return result
            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000
                logger.error(
                    f"Node {trace_name} failed",
                    extra={"duration_ms": duration_ms, "error": str(e)},
                )
                raise

        @functools.wraps(func)
        @traceable(name=trace_name, run_type="chain")
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.perf_counter()

            if redact and args:
                logged_args = _redact_dict(args[0]) if isinstance(args[0], dict) else args
                logger.debug(f"Node {trace_name} started", extra={"inputs": logged_args})
            else:
                logger.debug(f"Node {trace_name} started")

            try:
                result = func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start_time) * 1000

                if redact and isinstance(result, dict):
                    logged_result = _redact_dict(result)
                    logger.debug(
                        f"Node {trace_name} completed",
                        extra={"duration_ms": duration_ms, "outputs": logged_result},
                    )
                else:
                    logger.debug(f"Node {trace_name} completed", extra={"duration_ms": duration_ms})

                return result
            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000
                logger.error(
                    f"Node {trace_name} failed",
                    extra={"duration_ms": duration_ms, "error": str(e)},
                )
                raise

        # Return appropriate wrapper based on whether function is async
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore[return-value]
        return sync_wrapper  # type: ignore[return-value]

    return decorator


def traced_tool(name: str | None = None, redact: bool = True) -> Callable[[F], F]:
    """
    Decorator for tracing tool calls.

    Args:
        name: Custom trace name (defaults to function name)
        redact: Whether to redact PII from inputs/outputs

    Usage:
        @traced_tool("vector_search")
        async def vector_search(query: str, tenant_id: str) -> list[Document]:
            ...
    """
    def decorator(func: F) -> F:
        trace_name = name or func.__name__

        @functools.wraps(func)
        @traceable(name=trace_name, run_type="tool")
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.perf_counter()

            # Redact inputs for logging
            if redact:
                logged_kwargs = _redact_dict(kwargs)
                logger.debug(f"Tool {trace_name} started", extra={"inputs": logged_kwargs})
            else:
                logger.debug(f"Tool {trace_name} started", extra={"inputs": kwargs})

            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start_time) * 1000

                if redact:
                    logged_result = _redact_pii(str(result)) if isinstance(result, str) else result
                    logger.debug(
                        f"Tool {trace_name} completed",
                        extra={"duration_ms": duration_ms, "output": logged_result},
                    )
                else:
                    logger.debug(f"Tool {trace_name} completed", extra={"duration_ms": duration_ms})

                return result
            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000
                logger.error(
                    f"Tool {trace_name} failed",
                    extra={"duration_ms": duration_ms, "error": str(e)},
                )
                raise

        @functools.wraps(func)
        @traceable(name=trace_name, run_type="tool")
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.perf_counter()

            if redact:
                logged_kwargs = _redact_dict(kwargs)
                logger.debug(f"Tool {trace_name} started", extra={"inputs": logged_kwargs})
            else:
                logger.debug(f"Tool {trace_name} started", extra={"inputs": kwargs})

            try:
                result = func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start_time) * 1000

                if redact:
                    logged_result = _redact_pii(str(result)) if isinstance(result, str) else result
                    logger.debug(
                        f"Tool {trace_name} completed",
                        extra={"duration_ms": duration_ms, "output": logged_result},
                    )
                else:
                    logger.debug(f"Tool {trace_name} completed", extra={"duration_ms": duration_ms})

                return result
            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000
                logger.error(
                    f"Tool {trace_name} failed",
                    extra={"duration_ms": duration_ms, "error": str(e)},
                )
                raise

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore[return-value]
        return sync_wrapper  # type: ignore[return-value]

    return decorator


def traced_llm_call(
    name: str | None = None,
    role: str | None = None,
    redact: bool = True,
) -> Callable[[F], F]:
    """
    Decorator for tracing LLM calls with cost tracking.

    Args:
        name: Custom trace name (defaults to function name)
        role: Model role for cost tracking (supervisor, critic, generator, etc.)
        redact: Whether to redact PII from prompts/responses

    Usage:
        @traced_llm_call("supervisor_decision", role="supervisor")
        async def call_supervisor(prompt: str) -> str:
            ...
    """
    def decorator(func: F) -> F:
        trace_name = name or func.__name__

        @functools.wraps(func)
        @traceable(name=trace_name, run_type="llm")
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.perf_counter()

            # Extract prompt from args/kwargs for logging
            prompt = kwargs.get("prompt") or (args[0] if args else "")
            if redact and prompt:
                logged_prompt = _redact_pii(str(prompt))
                logger.debug(f"LLM {trace_name} started", extra={"prompt": logged_prompt, "role": role})
            else:
                logger.debug(f"LLM {trace_name} started", extra={"role": role})

            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start_time) * 1000

                if redact and result:
                    logged_result = _redact_pii(str(result))
                    logger.debug(
                        f"LLM {trace_name} completed",
                        extra={"duration_ms": duration_ms, "response": logged_result, "role": role},
                    )
                else:
                    logger.debug(f"LLM {trace_name} completed", extra={"duration_ms": duration_ms, "role": role})

                return result
            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000
                logger.error(
                    f"LLM {trace_name} failed",
                    extra={"duration_ms": duration_ms, "error": str(e), "role": role},
                )
                raise

        @functools.wraps(func)
        @traceable(name=trace_name, run_type="llm")
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.perf_counter()

            prompt = kwargs.get("prompt") or (args[0] if args else "")
            if redact and prompt:
                logged_prompt = _redact_pii(str(prompt))
                logger.debug(f"LLM {trace_name} started", extra={"prompt": logged_prompt, "role": role})
            else:
                logger.debug(f"LLM {trace_name} started", extra={"role": role})

            try:
                result = func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start_time) * 1000

                if redact and result:
                    logged_result = _redact_pii(str(result))
                    logger.debug(
                        f"LLM {trace_name} completed",
                        extra={"duration_ms": duration_ms, "response": logged_result, "role": role},
                    )
                else:
                    logger.debug(f"LLM {trace_name} completed", extra={"duration_ms": duration_ms, "role": role})

                return result
            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000
                logger.error(
                    f"LLM {trace_name} failed",
                    extra={"duration_ms": duration_ms, "error": str(e), "role": role},
                )
                raise

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore[return-value]
        return sync_wrapper  # type: ignore[return-value]

    return decorator


def traced_retriever(name: str | None = None, redact: bool = True) -> Callable[[F], F]:
    """
    Decorator for tracing retriever calls.

    Args:
        name: Custom trace name (defaults to function name)
        redact: Whether to redact PII from query/results

    Usage:
        @traced_retriever("hybrid_retrieve")
        async def retrieve(query: str, tenant_id: str) -> list[Document]:
            ...
    """
    def decorator(func: F) -> F:
        trace_name = name or func.__name__

        @functools.wraps(func)
        @traceable(name=trace_name, run_type="retriever")
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.perf_counter()

            query = kwargs.get("query") or (args[0] if args else "")
            if redact and query:
                logged_query = _redact_pii(str(query))
                logger.debug(f"Retriever {trace_name} started", extra={"query": logged_query})
            else:
                logger.debug(f"Retriever {trace_name} started", extra={"query": query})

            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start_time) * 1000

                result_count = len(result) if hasattr(result, "__len__") else 1
                logger.debug(
                    f"Retriever {trace_name} completed",
                    extra={"duration_ms": duration_ms, "result_count": result_count},
                )

                return result
            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000
                logger.error(
                    f"Retriever {trace_name} failed",
                    extra={"duration_ms": duration_ms, "error": str(e)},
                )
                raise

        @functools.wraps(func)
        @traceable(name=trace_name, run_type="retriever")
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.perf_counter()

            query = kwargs.get("query") or (args[0] if args else "")
            if redact and query:
                logged_query = _redact_pii(str(query))
                logger.debug(f"Retriever {trace_name} started", extra={"query": logged_query})
            else:
                logger.debug(f"Retriever {trace_name} started", extra={"query": query})

            try:
                result = func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start_time) * 1000

                result_count = len(result) if hasattr(result, "__len__") else 1
                logger.debug(
                    f"Retriever {trace_name} completed",
                    extra={"duration_ms": duration_ms, "result_count": result_count},
                )

                return result
            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000
                logger.error(
                    f"Retriever {trace_name} failed",
                    extra={"duration_ms": duration_ms, "error": str(e)},
                )
                raise

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore[return-value]
        return sync_wrapper  # type: ignore[return-value]

    return decorator


# Convenience decorators with common configurations
def traced_supervisor_node(func: F) -> F:
    """Decorator for supervisor node with standard config."""
    return traced_node("supervisor", redact=True)(func)


def traced_rag_node(func: F) -> F:
    """Decorator for RAG subgraph nodes with standard config."""
    return traced_node("rag", redact=True)(func)


def traced_critic_node(func: F) -> F:
    """Decorator for critic node with standard config."""
    return traced_node("critic", redact=True)(func)


def traced_embedder(func: F) -> F:
    """Decorator for embedding calls."""
    return traced_tool("embedder", redact=True)(func)


def traced_reranker(func: F) -> F:
    """Decorator for reranker calls."""
    return traced_tool("reranker", redact=True)(func)


def traced_vector_search(func: F) -> F:
    """Decorator for vector search calls."""
    return traced_retriever("vector_search", redact=True)(func)


def traced_text_search(func: F) -> F:
    """Decorator for text search calls."""
    return traced_retriever("text_search", redact=True)(func)


def traced_hybrid_retrieve(func: F) -> F:
    """Decorator for hybrid retrieval."""
    return traced_retriever("hybrid_retrieve", redact=True)(func)


# Export all decorators
__all__ = [
    "traced_node",
    "traced_tool",
    "traced_llm_call",
    "traced_retriever",
    "traced_supervisor_node",
    "traced_rag_node",
    "traced_critic_node",
    "traced_embedder",
    "traced_reranker",
    "traced_vector_search",
    "traced_text_search",
    "traced_hybrid_retrieve",
    "_redact_pii",
    "_redact_dict",
]