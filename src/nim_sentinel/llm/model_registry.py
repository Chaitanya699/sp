"""
NIM Sentinel LLM Model Registry

Manages model configurations, fallback chains, circuit breakers, and cost/latency tracking.
"""

import time
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from functools import wraps
from typing import Any, TypeVar

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_nvidia_ai_endpoints import ChatNVIDIA, NVIDIAEmbeddings, NVIDIARerank
from nim_sentinel.core import (
    FallbackExhaustedError,
    ModelRole,
    ModelUnavailableError,
    get_available_model_roles,
    get_model_config,
)
from nim_sentinel.core.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class CircuitState(StrEnum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreaker:
    """Circuit breaker for model endpoints."""
    failure_threshold: int = 5
    recovery_timeout: float = 60.0  # seconds
    half_open_max_calls: int = 3

    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    last_failure_time: float = 0
    half_open_calls: int = 0

    def record_success(self) -> None:
        """Record a successful call."""
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_calls += 1
            if self.half_open_calls >= self.half_open_max_calls:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.half_open_calls = 0
                logger.info("Circuit breaker closed after recovery")
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0

    def record_failure(self) -> None:
        """Record a failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            self.half_open_calls = 0
            logger.warning("Circuit breaker reopened after half-open failure")
        elif self.state == CircuitState.CLOSED and self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")

    def can_execute(self) -> bool:
        """Check if a call can be executed."""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.half_open_calls = 0
                logger.info("Circuit breaker entering half-open state")
                return True
            return False

        if self.state == CircuitState.HALF_OPEN:
            return self.half_open_calls < self.half_open_max_calls

        return False

    def reset(self) -> None:
        """Reset circuit breaker to closed state."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0
        self.half_open_calls = 0


@dataclass
class ModelMetrics:
    """Metrics for a model."""
    model_id: str
    role: str
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    total_latency_ms: float = 0.0
    total_cost_usd: float = 0.0
    last_used: datetime | None = None
    last_error: str | None = None

    def record_call(self, tokens_in: int, tokens_out: int, latency_ms: float, cost_usd: float, error: str | None = None) -> None:
        """Record a call."""
        self.total_calls += 1
        self.total_tokens_in += tokens_in
        self.total_tokens_out += tokens_out
        self.total_latency_ms += latency_ms
        self.total_cost_usd += cost_usd
        self.last_used = datetime.now(UTC)

        if error:
            self.failed_calls += 1
            self.last_error = error
        else:
            self.successful_calls += 1

    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / self.total_calls if self.total_calls > 0 else 0.0

    @property
    def success_rate(self) -> float:
        return self.successful_calls / self.total_calls if self.total_calls > 0 else 0.0

    @property
    def avg_cost_per_call(self) -> float:
        return self.total_cost_usd / self.total_calls if self.total_calls > 0 else 0.0


class ModelFactory:
    """Factory for creating model instances."""

    @staticmethod
    def create_chat_model(
        model_id: str,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        timeout: int = 30,
        **kwargs: Any,
    ) -> ChatNVIDIA:
        """Create a ChatNVIDIA instance."""
        return ChatNVIDIA(
            model=model_id,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            **kwargs,
        )

    @staticmethod
    def create_embedding_model(model_id: str, **kwargs: Any) -> NVIDIAEmbeddings:
        """Create an NVIDIAEmbeddings instance."""
        return NVIDIAEmbeddings(model=model_id, **kwargs)

    @staticmethod
    def create_rerank_model(model_id: str, **kwargs: Any) -> NVIDIARerank:
        """Create an NVIDIARerank instance."""
        return NVIDIARerank(model=model_id, **kwargs)


class ModelRegistry:
    """
    Central model registry with fallback chains, circuit breakers, and metrics.
    """

    def __init__(self) -> None:
        self._chat_models: dict[str, ChatNVIDIA] = {}
        self._embedding_models: dict[str, NVIDIAEmbeddings] = {}
        self._rerank_models: dict[str, NVIDIARerank] = {}
        self._circuit_breakers: dict[str, CircuitBreaker] = {}
        self._metrics: dict[str, ModelMetrics] = {}
        self._factory = ModelFactory()
        self._initialized = False

    def initialize(self) -> None:
        """Initialize the registry with configured models."""
        if self._initialized:
            return

        roles = get_available_model_roles()
        for role in roles:
            config = get_model_config(role)

            # Create circuit breaker for primary
            primary_key = f"{role}:primary"
            self._circuit_breakers[primary_key] = CircuitBreaker()
            self._metrics[primary_key] = ModelMetrics(
                model_id=config.primary,
                role=role,
            )

            # Create circuit breaker for fallback if exists
            if config.fallback:
                fallback_key = f"{role}:fallback"
                self._circuit_breakers[fallback_key] = CircuitBreaker()
                self._metrics[fallback_key] = ModelMetrics(
                    model_id=config.fallback,
                    role=role,
                )

        self._initialized = True
        logger.info("Model registry initialized", roles=roles)

    def get_chat_model(self, role: ModelRole | str, use_fallback: bool = False) -> ChatNVIDIA:
        """Get a chat model for the given role."""
        role_str = role.value if isinstance(role, ModelRole) else role
        config = get_model_config(role_str)

        model_id = config.fallback if use_fallback and config.fallback else config.primary
        key = f"{role_str}:{'fallback' if use_fallback else 'primary'}"

        # Check circuit breaker
        breaker = self._circuit_breakers.get(key)
        if breaker and not breaker.can_execute():
            if use_fallback:
                raise ModelUnavailableError(role_str, model_id)
            # Try fallback
            if config.fallback:
                logger.warning(f"Primary model circuit open for {role_str}, trying fallback")
                return self.get_chat_model(role_str, use_fallback=True)
            else:
                raise ModelUnavailableError(role_str, model_id)

        # Check if unverified
        if use_fallback and config.fallback_unverified:
            logger.warning(f"Using unverified fallback model: {model_id}")
        elif not use_fallback and config.primary_unverified:
            logger.warning(f"Using unverified primary model: {model_id}")

        # Create or get cached model
        if model_id not in self._chat_models:
            self._chat_models[model_id] = self._factory.create_chat_model(
                model_id=model_id,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                timeout=config.timeout_seconds,
            )
            logger.info(f"Created chat model: {model_id} for role: {role_str}")

        return self._chat_models[model_id]

    def get_embedding_model(self, role: ModelRole | str = ModelRole.EMBEDDING, use_fallback: bool = False) -> NVIDIAEmbeddings:
        """Get an embedding model."""
        role_str = role.value if isinstance(role, ModelRole) else role
        config = get_model_config(role_str)

        model_id = config.fallback if use_fallback and config.fallback else config.primary
        key = f"{role_str}:{'fallback' if use_fallback else 'primary'}"

        breaker = self._circuit_breakers.get(key)
        if breaker and not breaker.can_execute():
            if use_fallback:
                raise ModelUnavailableError(role_str, model_id)
            return self.get_embedding_model(role_str, use_fallback=True)

        if model_id not in self._embedding_models:
            self._embedding_models[model_id] = self._factory.create_embedding_model(model_id)
            logger.info(f"Created embedding model: {model_id}")

        return self._embedding_models[model_id]

    def get_rerank_model(self, role: ModelRole | str = ModelRole.RERANKER, use_fallback: bool = False) -> NVIDIARerank:
        """Get a rerank model."""
        role_str = role.value if isinstance(role, ModelRole) else role
        config = get_model_config(role_str)

        model_id = config.fallback if use_fallback and config.fallback else config.primary
        key = f"{role_str}:{'fallback' if use_fallback else 'primary'}"

        breaker = self._circuit_breakers.get(key)
        if breaker and not breaker.can_execute():
            if use_fallback:
                raise ModelUnavailableError(role_str, model_id)
            return self.get_rerank_model(role_str, use_fallback=True)

        if model_id not in self._rerank_models:
            self._rerank_models[model_id] = self._factory.create_rerank_model(model_id)
            logger.info(f"Created rerank model: {model_id}")

        return self._rerank_models[model_id]

    @asynccontextmanager
    async def tracked_call(
        self,
        role: ModelRole | str,
        model_type: str = "chat",
        use_fallback: bool = False,
    ) -> AsyncGenerator[BaseChatModel | Embeddings | NVIDIARerank, None]:
        """
        Context manager for tracked model calls with automatic metrics and circuit breaker updates.
        """
        role_str = role.value if isinstance(role, ModelRole) else role
        key = f"{role_str}:{'fallback' if use_fallback else 'primary'}"
        breaker = self._circuit_breakers.get(key)
        metrics = self._metrics.get(key)

        start_time = time.perf_counter()
        error = None
        tokens_in = 0
        tokens_out = 0
        cost_usd = 0.0

        try:
            if model_type == "chat":
                model: BaseChatModel | Embeddings | NVIDIARerank = self.get_chat_model(role_str, use_fallback)
            elif model_type == "embedding":
                model = self.get_embedding_model(role_str, use_fallback)
            elif model_type == "rerank":
                model = self.get_rerank_model(role_str, use_fallback)
            else:
                raise ValueError(f"Unknown model type: {model_type}")

            yield model

        except Exception as e:
            error = str(e)
            # Record failure in circuit breaker
            if breaker:
                breaker.record_failure()
            raise

        finally:
            latency_ms = (time.perf_counter() - start_time) * 1000

            # Record metrics
            if metrics:
                metrics.record_call(tokens_in, tokens_out, latency_ms, cost_usd, error)

            # Record success in circuit breaker
            if breaker and not error:
                breaker.record_success()

            # Log metrics
            logger.debug(
                "model_call_completed",
                role=role_str,
                model_type=model_type,
                use_fallback=use_fallback,
                latency_ms=latency_ms,
                error=error,
            )

    def get_metrics(self, role: ModelRole | str | None = None) -> dict[str, ModelMetrics]:
        """Get metrics for all models or a specific role."""
        if role:
            role_str = role.value if isinstance(role, ModelRole) else role
            return {
                k: v for k, v in self._metrics.items()
                if k.startswith(f"{role_str}:")
            }
        return self._metrics.copy()

    def get_circuit_states(self) -> dict[str, CircuitState]:
        """Get current circuit breaker states."""
        return {k: v.state for k, v in self._circuit_breakers.items()}

    def reset_circuit(self, role: ModelRole | str, use_fallback: bool = False) -> None:
        """Manually reset a circuit breaker."""
        role_str = role.value if isinstance(role, ModelRole) else role
        key = f"{role_str}:{'fallback' if use_fallback else 'primary'}"
        if key in self._circuit_breakers:
            self._circuit_breakers[key].reset()
            logger.info(f"Circuit breaker reset for {key}")

    def reset_all_circuits(self) -> None:
        """Reset all circuit breakers."""
        for breaker in self._circuit_breakers.values():
            breaker.reset()
        logger.info("All circuit breakers reset")


# Global registry instance
_model_registry: ModelRegistry | None = None


def get_model_registry() -> ModelRegistry:
    """Get the global model registry instance."""
    global _model_registry
    if _model_registry is None:
        _model_registry = ModelRegistry()
        _model_registry.initialize()
    return _model_registry


def reset_model_registry() -> None:
    """Reset the global model registry (for testing)."""
    global _model_registry
    _model_registry = None


# Convenience functions
def get_chat_model(role: ModelRole | str, use_fallback: bool = False) -> ChatNVIDIA:
    """Get a chat model from the global registry."""
    return get_model_registry().get_chat_model(role, use_fallback)


def get_embedding_model(role: ModelRole | str = ModelRole.EMBEDDING, use_fallback: bool = False) -> NVIDIAEmbeddings:
    """Get an embedding model from the global registry."""
    return get_model_registry().get_embedding_model(role, use_fallback)


def get_rerank_model(role: ModelRole | str = ModelRole.RERANKER, use_fallback: bool = False) -> NVIDIARerank:
    """Get a rerank model from the global registry."""
    return get_model_registry().get_rerank_model(role, use_fallback)


@asynccontextmanager
async def tracked_chat_call(
    role: ModelRole | str,
    use_fallback: bool = False,
) -> AsyncGenerator[ChatNVIDIA, None]:
    """Tracked chat model call."""
    async with get_model_registry().tracked_call(role, "chat", use_fallback) as model:
        yield model  # type: ignore[misc]


@asynccontextmanager
async def tracked_embedding_call(
    role: ModelRole | str = ModelRole.EMBEDDING,
    use_fallback: bool = False,
) -> AsyncGenerator[NVIDIAEmbeddings, None]:
    """Tracked embedding model call."""
    async with get_model_registry().tracked_call(role, "embedding", use_fallback) as model:
        yield model  # type: ignore[misc]


@asynccontextmanager
async def tracked_rerank_call(
    role: ModelRole | str = ModelRole.RERANKER,
    use_fallback: bool = False,
) -> AsyncGenerator[NVIDIARerank, None]:
    """Tracked rerank model call."""
    async with get_model_registry().tracked_call(role, "rerank", use_fallback) as model:
        yield model  # type: ignore[misc]


# Decorator for automatic fallback
F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


def with_fallback(role: ModelRole | str, model_type: str = "chat") -> Callable[[F], F]:
    """Decorator to automatically retry with fallback on failure."""
    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            registry = get_model_registry()
            role_str = role.value if isinstance(role, ModelRole) else role

            # Try primary
            try:
                async with registry.tracked_call(role_str, model_type, use_fallback=False) as model:
                    return await func(model, *args, **kwargs)
            except Exception as primary_error:
                logger.warning(f"Primary model failed for {role_str}: {primary_error}")

                # Try fallback
                config = get_model_config(role_str)
                if config.fallback:
                    try:
                        async with registry.tracked_call(role_str, model_type, use_fallback=True) as model:
                            return await func(model, *args, **kwargs)
                    except Exception as fallback_error:
                        logger.error(f"Fallback model also failed for {role_str}: {fallback_error}")
                        raise FallbackExhaustedError(role_str, [config.primary, config.fallback]) from fallback_error
                else:
                    raise FallbackExhaustedError(role_str, [config.primary]) from None

        return wrapper  # type: ignore[return-value]
    return decorator
