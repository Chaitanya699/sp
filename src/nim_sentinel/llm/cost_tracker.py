"""
NIM Sentinel Cost Tracker

Tracks token usage, latency, and cost per model role.
Integrates with LangSmith metadata and Prometheus metrics.
"""

import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import Lock
from typing import Any

from nim_sentinel.core import ModelRole
from nim_sentinel.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class CostSnapshot:
    """Snapshot of cost metrics at a point in time."""
    timestamp: datetime
    role: str
    model_id: str
    tokens_in: int
    tokens_out: int
    latency_ms: float
    cost_usd: float
    success: bool
    error: str | None = None


@dataclass
class AggregatedCosts:
    """Aggregated cost metrics for a role."""
    role: str
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    total_latency_ms: float = 0.0
    total_cost_usd: float = 0.0
    by_model: dict[str, "AggregatedCosts"] = field(default_factory=dict)

    def add(self, snapshot: CostSnapshot) -> None:
        """Add a snapshot to aggregates."""
        self.total_calls += 1
        self.total_tokens_in += snapshot.tokens_in
        self.total_tokens_out += snapshot.tokens_out
        self.total_latency_ms += snapshot.latency_ms
        self.total_cost_usd += snapshot.cost_usd

        if snapshot.success:
            self.successful_calls += 1
        else:
            self.failed_calls += 1

        # Per-model aggregation
        if snapshot.model_id not in self.by_model:
            self.by_model[snapshot.model_id] = AggregatedCosts(role=snapshot.model_id)
        self.by_model[snapshot.model_id].add(snapshot)

    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / self.total_calls if self.total_calls > 0 else 0.0

    @property
    def success_rate(self) -> float:
        return self.successful_calls / self.total_calls if self.total_calls > 0 else 0.0

    @property
    def avg_cost_per_call(self) -> float:
        return self.total_cost_usd / self.total_calls if self.total_calls > 0 else 0.0


# Model pricing (USD per 1M tokens) - approximate, update from NVIDIA pricing
MODEL_PRICING = {
    # Chat models (input/output per 1M tokens)
    "meta/llama-3.1-8b-instruct": {"input": 0.10, "output": 0.10},
    "meta/llama-3.1-70b-instruct": {"input": 0.50, "output": 0.50},
    "meta/llama-3.3-70b-instruct": {"input": 0.50, "output": 0.50},
    "nvidia/nemotron-3-ultra-550b-a55b": {"input": 2.00, "output": 2.00},
    "nvidia/nemotron-3-super-120b-a12b": {"input": 1.00, "output": 1.00},
    "mistralai/mistral-large-3-675b-instruct-2512": {"input": 2.00, "output": 2.00},
    "mistralai/codestral-22b-instruct-v0.1": {"input": 0.50, "output": 0.50},
    "qwen/qwen2.5-coder-32b-instruct": {"input": 0.30, "output": 0.30},
    "google/gemma-2-27b-it": {"input": 0.20, "output": 0.20},
    "microsoft/phi-3.5-vision-instruct": {"input": 0.30, "output": 0.30},
    "meta/llama-3.2-90b-vision-instruct": {"input": 0.80, "output": 0.80},
    "meta/llama-3.2-11b-vision-instruct": {"input": 0.20, "output": 0.20},
    "nvidia/llama-3.1-nemoguard-8b-content-safety": {"input": 0.10, "output": 0.10},
    "nvidia/llama-3.1-nemoguard-8b-topic-control": {"input": 0.10, "output": 0.10},
    "ibm/granite-guardian-3.0-8b": {"input": 0.10, "output": 0.10},
    "meta/llama-guard-4-12b": {"input": 0.10, "output": 0.10},

    # Embedding models (per 1M tokens)
    "nvidia/nv-embedqa-e5-v5": {"input": 0.05, "output": 0},
    "nvidia/llama-3.2-nv-embedqa-1b-v2": {"input": 0.02, "output": 0},
    "nvidia/nv-embed-v1": {"input": 0.05, "output": 0},
    "baai/bge-m3": {"input": 0.02, "output": 0},

    # Rerank models (per 1M tokens)
    "nvidia/llama-3.2-nv-rerankqa-1b-v1": {"input": 0.10, "output": 0},
    "nvidia/llama-nemotron-rerank-1b-v2": {"input": 0.10, "output": 0},
}


class CostTracker:
    """
    Tracks cost, latency, and token usage per model role.
    Thread-safe for concurrent access.
    """

    def __init__(self) -> None:
        self._aggregates: dict[str, AggregatedCosts] = {}
        self._snapshots: list[CostSnapshot] = []
        self._lock = Lock()
        self._max_snapshots = 10000  # Keep last 10k snapshots in memory

    def calculate_cost(self, model_id: str, tokens_in: int, tokens_out: int) -> float:
        """Calculate cost for a model call."""
        pricing = MODEL_PRICING.get(model_id, {"input": 0.0, "output": 0.0})
        input_cost = (tokens_in / 1_000_000) * pricing["input"]
        output_cost = (tokens_out / 1_000_000) * pricing["output"]
        return input_cost + output_cost

    def record_call(
        self,
        role: str,
        model_id: str,
        tokens_in: int,
        tokens_out: int,
        latency_ms: float,
        success: bool = True,
        error: str | None = None,
    ) -> CostSnapshot:
        """Record a model call."""
        cost_usd = self.calculate_cost(model_id, tokens_in, tokens_out)

        snapshot = CostSnapshot(
            timestamp=datetime.now(UTC),
            role=role,
            model_id=model_id,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            success=success,
            error=error,
        )

        with self._lock:
            # Add to aggregates
            if role not in self._aggregates:
                self._aggregates[role] = AggregatedCosts(role=role)
            self._aggregates[role].add(snapshot)

            # Store snapshot
            self._snapshots.append(snapshot)
            if len(self._snapshots) > self._max_snapshots:
                self._snapshots = self._snapshots[-self._max_snapshots:]

        # Log to LangSmith metadata (would be done via callback in practice)
        logger.debug(
            "cost_recorded",
            role=role,
            model_id=model_id,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            success=success,
        )

        return snapshot

    def get_aggregates(self, role: str | None = None) -> dict[str, AggregatedCosts]:
        """Get aggregated costs."""
        with self._lock:
            if role:
                return {role: self._aggregates.get(role, AggregatedCosts(role=role))}
            return self._aggregates.copy()

    def get_snapshots(
        self,
        role: str | None = None,
        model_id: str | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[CostSnapshot]:
        """Get recent snapshots with optional filters."""
        with self._lock:
            snapshots = self._snapshots

            if role:
                snapshots = [s for s in snapshots if s.role == role]
            if model_id:
                snapshots = [s for s in snapshots if s.model_id == model_id]
            if since:
                snapshots = [s for s in snapshots if s.timestamp >= since]

            return snapshots[-limit:]

    def get_summary(self) -> dict[str, Any]:
        """Get cost summary across all roles."""
        with self._lock:
            total_calls = sum(a.total_calls for a in self._aggregates.values())
            total_cost = sum(a.total_cost_usd for a in self._aggregates.values())
            total_tokens = sum(a.total_tokens_in + a.total_tokens_out for a in self._aggregates.values())

            return {
                "total_calls": total_calls,
                "total_cost_usd": total_cost,
                "total_tokens": total_tokens,
                "by_role": {
                    role: {
                        "calls": agg.total_calls,
                        "cost_usd": agg.total_cost_usd,
                        "tokens_in": agg.total_tokens_in,
                        "tokens_out": agg.total_tokens_out,
                        "avg_latency_ms": agg.avg_latency_ms,
                        "success_rate": agg.success_rate,
                        "by_model": {
                            model: {
                                "calls": m.total_calls,
                                "cost_usd": m.total_cost_usd,
                                "avg_latency_ms": m.avg_latency_ms,
                            }
                            for model, m in agg.by_model.items()
                        },
                    }
                    for role, agg in self._aggregates.items()
                },
            }

    def reset(self) -> None:
        """Reset all tracked data."""
        with self._lock:
            self._aggregates.clear()
            self._snapshots.clear()
            logger.info("Cost tracker reset")


# Global cost tracker instance
_cost_tracker: CostTracker | None = None


def get_cost_tracker() -> CostTracker:
    """Get the global cost tracker instance."""
    global _cost_tracker
    if _cost_tracker is None:
        _cost_tracker = CostTracker()
    return _cost_tracker


def reset_cost_tracker() -> None:
    """Reset the global cost tracker (for testing)."""
    global _cost_tracker
    _cost_tracker = None


@asynccontextmanager
async def track_cost(role: ModelRole | str, model_id: str) -> AsyncGenerator[dict[str, Any], None]:
    """
    Context manager to track cost of an operation.
    Yields a dict to populate with tokens_in/tokens_out.
    """
    role_str = role.value if isinstance(role, ModelRole) else role
    start_time = time.perf_counter()
    tracker = get_cost_tracker()

    result: dict[str, Any] = {"tokens_in": 0, "tokens_out": 0, "success": True, "error": None}

    try:
        yield result
    except Exception as e:
        result["success"] = False
        result["error"] = str(e)
        raise
    finally:
        latency_ms = (time.perf_counter() - start_time) * 1000
        tracker.record_call(
            role=role_str,
            model_id=model_id,
            tokens_in=result["tokens_in"],
            tokens_out=result["tokens_out"],
            latency_ms=latency_ms,
            success=result["success"],
            error=result["error"],
        )


def estimate_cost(role: ModelRole | str, estimated_tokens_in: int, estimated_tokens_out: int) -> float:
    """Estimate cost for a model call."""
    from nim_sentinel.core import get_model_config
    config = get_model_config(role)
    model_id = config.primary
    tracker = get_cost_tracker()
    return tracker.calculate_cost(model_id, estimated_tokens_in, estimated_tokens_out)
