"""
NIM Sentinel Observability - Decorators

Tracing decorators for LangGraph nodes, tools, LLM calls, and retrievers
with LangSmith integration and PII redaction.
"""

import functools
import logging
import os
import time
from collections.abc import Callable
from typing import Any, TypeVar

from langsmith import traceable
from nim_sentinel.observability.redaction import (
    redact_for_logging,
    redact_messages_for_logging,
    redact_state_for_logging,
)

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def _get_git_sha() -> str:
    """Get current git SHA for trace metadata."""
    try:
        import subprocess

        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"


def _get_prompt_version() -> str:
    """Get prompt/graph version from environment or config."""
    return os.getenv("PROMPT_VERSION", "1.0")


def _get_model_metadata(role: str | None = None, model_id: str | None = None) -> dict[str, Any]:
    """Get standard metadata for traces."""
    return {
        "tenant_hash": os.getenv("TENANT_HASH", "unknown"),
        "model_role": role or "unknown",
        "model_id": model_id or "unknown",
        "prompt_version": _get_prompt_version(),
        "git_sha": _get_git_sha(),
    }


def traced_node(
    func: F | None = None,
    *,
    name: str | None = None,
    redact: bool = True,
    role: str | None = None,
) -> Callable[[F], F] | F:
    """
    Decorator for tracing LangGraph nodes.

    Args:
        name: Custom trace name (defaults to function name)
        redact: Whether to redact PII from inputs/outputs
        role: Model role for metadata

    Usage:
        @traced_node
        async def retrieve_node(state: GraphState) -> GraphState:
            ...

        @traced_node(name="retrieve", role="retriever")
        async def retrieve_node(state: GraphState) -> GraphState:
            ...
    """

    def decorator(func: F) -> F:
        trace_name = name or func.__name__

        @functools.wraps(func)
        @traceable(
            name=trace_name,
            run_type="chain",
            metadata=_get_model_metadata(role=role),
        )
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.perf_counter()

            # Redact inputs for logging
            if redact and args:
                logged_args = redact_for_logging(args[0]) if isinstance(args[0], dict) else args
                logger.debug(f"Node {trace_name} started", extra={"inputs": logged_args})
            else:
                logger.debug(f"Node {trace_name} started")

            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start_time) * 1000

                if redact and isinstance(result, dict):
                    logged_result = redact_for_logging(result)
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
        @traceable(
            name=trace_name,
            run_type="chain",
            metadata=_get_model_metadata(role=role),
        )
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.perf_counter()

            if redact and args:
                logged_args = redact_for_logging(args[0]) if isinstance(args[0], dict) else args
                logger.debug(f"Node {trace_name} started", extra={"inputs": logged_args})
            else:
                logger.debug(f"Node {trace_name} started")

            try:
                result = func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start_time) * 1000

                if redact and isinstance(result, dict):
                    logged_result = redact_for_logging(result)
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

    # Support both @traced_node and @traced_node() syntax
    if func is not None:
        return decorator(func)
    return decorator


def traced_tool(
    func: F | None = None,
    *,
    name: str | None = None,
    redact: bool = True,
    role: str | None = None,
) -> Callable[[F], F] | F:
    """
    Decorator for tracing tool calls.

    Args:
        name: Custom trace name (defaults to function name)
        redact: Whether to redact PII from inputs/outputs
        role: Model role for metadata

    Usage:
        @traced_tool
        async def vector_search(query: str, tenant_id: str) -> list[Document]:
            ...

        @traced_tool(name="vector_search", role="retriever")
        async def vector_search(query: str, tenant_id: str) -> list[Document]:
            ...
    """

    def decorator(func: F) -> F:
        trace_name = name or func.__name__

        @functools.wraps(func)
        @traceable(
            name=trace_name,
            run_type="tool",
            metadata=_get_model_metadata(role=role),
        )
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.perf_counter()

            # Redact inputs for logging
            if redact:
                logged_kwargs = redact_for_logging(kwargs)
                logger.debug(f"Tool {trace_name} started", extra={"inputs": logged_kwargs})
            else:
                logger.debug(f"Tool {trace_name} started", extra={"inputs": kwargs})

            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start_time) * 1000

                if redact:
                    logged_result = redact_for_logging(result)
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
        @traceable(
            name=trace_name,
            run_type="tool",
            metadata=_get_model_metadata(role=role),
        )
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.perf_counter()

            if redact:
                logged_kwargs = redact_for_logging(kwargs)
                logger.debug(f"Tool {trace_name} started", extra={"inputs": logged_kwargs})
            else:
                logger.debug(f"Tool {trace_name} started", extra={"inputs": kwargs})

            try:
                result = func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start_time) * 1000

                if redact:
                    logged_result = redact_for_logging(result)
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

    # Support both @traced_tool and @traced_tool() syntax
    if func is not None:
        return decorator(func)
    return decorator


def traced_llm_call(
    func: F | None = None,
    *,
    name: str | None = None,
    role: str | None = None,
    model_id: str | None = None,
    redact: bool = True,
) -> Callable[[F], F] | F:
    """
    Decorator for tracing LLM calls with cost tracking.

    Args:
        name: Custom trace name (defaults to function name)
        role: Model role for cost tracking (supervisor, critic, generator, etc.)
        model_id: Specific model ID being used
        redact: Whether to redact PII from prompts/responses

    Usage:
        @traced_llm_call
        async def call_supervisor(prompt: str) -> str:
            ...

        @traced_llm_call(role="supervisor", model_id="nemotron-3-super")
        async def call_supervisor(prompt: str) -> str:
            ...
    """

    def decorator(func: F) -> F:
        trace_name = name or func.__name__

        @functools.wraps(func)
        @traceable(
            name=trace_name,
            run_type="llm",
            metadata=_get_model_metadata(role=role, model_id=model_id),
        )
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.perf_counter()

            # Extract prompt from args/kwargs for logging
            prompt = kwargs.get("prompt") or (args[0] if args else "")
            if redact and prompt:
                logged_prompt = redact_for_logging(str(prompt))
                logger.debug(
                    f"LLM {trace_name} started", extra={"prompt": logged_prompt, "role": role}
                )
            else:
                logger.debug(f"LLM {trace_name} started", extra={"role": role})

            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start_time) * 1000

                if redact and result:
                    logged_result = redact_for_logging(str(result))
                    logger.debug(
                        f"LLM {trace_name} completed",
                        extra={"duration_ms": duration_ms, "response": logged_result, "role": role},
                    )
                else:
                    logger.debug(
                        f"LLM {trace_name} completed",
                        extra={"duration_ms": duration_ms, "role": role},
                    )

                return result
            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000
                logger.error(
                    f"LLM {trace_name} failed",
                    extra={"duration_ms": duration_ms, "error": str(e), "role": role},
                )
                raise

        @functools.wraps(func)
        @traceable(
            name=trace_name,
            run_type="llm",
            metadata=_get_model_metadata(role=role, model_id=model_id),
        )
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.perf_counter()

            prompt = kwargs.get("prompt") or (args[0] if args else "")
            if redact and prompt:
                logged_prompt = redact_for_logging(str(prompt))
                logger.debug(
                    f"LLM {trace_name} started", extra={"prompt": logged_prompt, "role": role}
                )
            else:
                logger.debug(f"LLM {trace_name} started", extra={"role": role})

            try:
                result = func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start_time) * 1000

                if redact and result:
                    logged_result = redact_for_logging(str(result))
                    logger.debug(
                        f"LLM {trace_name} completed",
                        extra={"duration_ms": duration_ms, "response": logged_result, "role": role},
                    )
                else:
                    logger.debug(
                        f"LLM {trace_name} completed",
                        extra={"duration_ms": duration_ms, "role": role},
                    )

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

    # Support both @traced_llm_call and @traced_llm_call() syntax
    if func is not None:
        return decorator(func)
    return decorator


def traced_retriever(
    func: F | None = None,
    *,
    name: str | None = None,
    redact: bool = True,
    role: str | None = None,
) -> Callable[[F], F] | F:
    """
    Decorator for tracing retriever calls.

    Args:
        name: Custom trace name (defaults to function name)
        redact: Whether to redact PII from query/results
        role: Model role for metadata

    Usage:
        @traced_retriever
        async def retrieve(query: str, tenant_id: str) -> list[Document]:
            ...

        @traced_retriever(name="hybrid_retrieve", role="retriever")
        async def retrieve(query: str, tenant_id: str) -> list[Document]:
            ...
    """

    def decorator(func: F) -> F:
        trace_name = name or func.__name__

        @functools.wraps(func)
        @traceable(
            name=trace_name,
            run_type="retriever",
            metadata=_get_model_metadata(role=role),
        )
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.perf_counter()

            query = kwargs.get("query") or (args[0] if args else "")
            if redact and query:
                logged_query = redact_for_logging(str(query))
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
        @traceable(
            name=trace_name,
            run_type="retriever",
            metadata=_get_model_metadata(role=role),
        )
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.perf_counter()

            query = kwargs.get("query") or (args[0] if args else "")
            if redact and query:
                logged_query = redact_for_logging(str(query))
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

    # Support both @traced_retriever and @traced_retriever() syntax
    if func is not None:
        return decorator(func)
    return decorator


# Convenience decorators with common configurations
def traced_supervisor_node(func: F) -> F:
    """Decorator for supervisor node with standard config."""
    return traced_node(func, name="supervisor", redact=True, role="supervisor")  # type: ignore[return-value]


def traced_rag_node(func: F) -> F:
    """Decorator for RAG subgraph nodes with standard config."""
    return traced_node(func, name="rag", redact=True, role="generator")  # type: ignore[return-value]


def traced_critic_node(func: F) -> F:
    """Decorator for critic node with standard config."""
    return traced_node(func, name="critic", redact=True, role="critic")  # type: ignore[return-value]


def traced_embedder(func: F) -> F:
    """Decorator for embedding calls."""
    return traced_tool(func, name="embedder", redact=True, role="embedder")  # type: ignore[return-value]


def traced_reranker(func: F) -> F:
    """Decorator for reranker calls."""
    return traced_tool(func, name="reranker", redact=True, role="reranker")  # type: ignore[return-value]


def traced_vector_search(func: F) -> F:
    """Decorator for vector search calls."""
    return traced_retriever(func, name="vector_search", redact=True, role="retriever")  # type: ignore[return-value]


def traced_text_search(func: F) -> F:
    """Decorator for text search calls."""
    return traced_retriever(func, name="text_search", redact=True, role="retriever")  # type: ignore[return-value]


def traced_hybrid_retrieve(func: F) -> F:
    """Decorator for hybrid retrieval."""
    return traced_retriever(func, name="hybrid_retrieve", redact=True, role="retriever")  # type: ignore[return-value]


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
    "redact_for_logging",
    "redact_state_for_logging",
    "redact_messages_for_logging",
]
