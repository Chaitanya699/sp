"""
Unit tests for CostTracker module.
"""

import time
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from nim_sentinel.core import ModelRole
from nim_sentinel.llm.cost_tracker import (
    MODEL_PRICING,
    AggregatedCosts,
    CostSnapshot,
    CostTracker,
    estimate_cost,
    get_cost_tracker,
    reset_cost_tracker,
    track_cost,
)


class TestCostSnapshot:
    """Tests for CostSnapshot dataclass."""

    def test_cost_snapshot_creation(self):
        """Test creating a CostSnapshot."""
        snapshot = CostSnapshot(
            timestamp=datetime.now(UTC),
            role="chat",
            model_id="meta/llama-3.1-8b-instruct",
            tokens_in=100,
            tokens_out=50,
            latency_ms=150.0,
            cost_usd=0.000015,
            success=True,
        )
        assert snapshot.role == "chat"
        assert snapshot.model_id == "meta/llama-3.1-8b-instruct"
        assert snapshot.tokens_in == 100
        assert snapshot.tokens_out == 50
        assert snapshot.latency_ms == 150.0
        assert snapshot.cost_usd == 0.000015
        assert snapshot.success is True
        assert snapshot.error is None

    def test_cost_snapshot_with_error(self):
        """Test CostSnapshot with error."""
        snapshot = CostSnapshot(
            timestamp=datetime.now(UTC),
            role="chat",
            model_id="meta/llama-3.1-8b-instruct",
            tokens_in=100,
            tokens_out=0,
            latency_ms=100.0,
            cost_usd=0.0,
            success=False,
            error="Model unavailable",
        )
        assert snapshot.success is False
        assert snapshot.error == "Model unavailable"


class TestAggregatedCosts:
    """Tests for AggregatedCosts dataclass."""

    def test_aggregated_costs_initialization(self):
        """Test AggregatedCosts initialization."""
        agg = AggregatedCosts(role="chat")
        assert agg.role == "chat"
        assert agg.total_calls == 0
        assert agg.successful_calls == 0
        assert agg.failed_calls == 0
        assert agg.total_tokens_in == 0
        assert agg.total_tokens_out == 0
        assert agg.total_latency_ms == 0.0
        assert agg.total_cost_usd == 0.0
        assert agg.by_model == {}

    def test_add_snapshot(self):
        """Test adding a snapshot to aggregates."""
        agg = AggregatedCosts(role="chat")
        snapshot = CostSnapshot(
            timestamp=datetime.now(UTC),
            role="chat",
            model_id="meta/llama-3.1-8b-instruct",
            tokens_in=100,
            tokens_out=50,
            latency_ms=150.0,
            cost_usd=0.000015,
            success=True,
        )
        agg.add(snapshot)

        assert agg.total_calls == 1
        assert agg.successful_calls == 1
        assert agg.failed_calls == 0
        assert agg.total_tokens_in == 100
        assert agg.total_tokens_out == 50
        assert agg.total_latency_ms == 150.0
        assert agg.total_cost_usd == 0.000015
        assert "meta/llama-3.1-8b-instruct" in agg.by_model

    def test_add_failed_snapshot(self):
        """Test adding a failed snapshot."""
        agg = AggregatedCosts(role="chat")
        snapshot = CostSnapshot(
            timestamp=datetime.now(UTC),
            role="chat",
            model_id="meta/llama-3.1-8b-instruct",
            tokens_in=100,
            tokens_out=0,
            latency_ms=100.0,
            cost_usd=0.0,
            success=False,
            error="Timeout",
        )
        agg.add(snapshot)

        assert agg.total_calls == 1
        assert agg.successful_calls == 0
        assert agg.failed_calls == 1

    def test_add_multiple_snapshots_same_model(self):
        """Test adding multiple snapshots for the same model."""
        agg = AggregatedCosts(role="chat")
        for _ in range(3):
            snapshot = CostSnapshot(
                timestamp=datetime.now(UTC),
                role="chat",
                model_id="meta/llama-3.1-8b-instruct",
                tokens_in=100,
                tokens_out=50,
                latency_ms=150.0,
                cost_usd=0.000015,
                success=True,
            )
            agg.add(snapshot)

        assert agg.total_calls == 3
        assert agg.successful_calls == 3
        assert agg.total_tokens_in == 300
        assert agg.total_tokens_out == 150
        assert agg.total_latency_ms == 450.0
        assert agg.total_cost_usd == 0.000045

    def test_add_snapshots_different_models(self):
        """Test adding snapshots for different models."""
        agg = AggregatedCosts(role="chat")
        models = ["meta/llama-3.1-8b-instruct", "meta/llama-3.1-70b-instruct"]
        for model in models:
            snapshot = CostSnapshot(
                timestamp=datetime.now(UTC),
                role="chat",
                model_id=model,
                tokens_in=100,
                tokens_out=50,
                latency_ms=150.0,
                cost_usd=0.000015,
                success=True,
            )
            agg.add(snapshot)

        assert agg.total_calls == 2
        assert len(agg.by_model) == 2
        assert all(m in agg.by_model for m in models)

    def test_avg_latency_ms(self):
        """Test average latency calculation."""
        agg = AggregatedCosts(role="chat")
        assert agg.avg_latency_ms == 0.0

        snapshot = CostSnapshot(
            timestamp=datetime.now(UTC),
            role="chat",
            model_id="meta/llama-3.1-8b-instruct",
            tokens_in=100,
            tokens_out=50,
            latency_ms=150.0,
            cost_usd=0.000015,
            success=True,
        )
        agg.add(snapshot)
        assert agg.avg_latency_ms == 150.0

        snapshot2 = CostSnapshot(
            timestamp=datetime.now(UTC),
            role="chat",
            model_id="meta/llama-3.1-8b-instruct",
            tokens_in=100,
            tokens_out=50,
            latency_ms=250.0,
            cost_usd=0.000015,
            success=True,
        )
        agg.add(snapshot2)
        assert agg.avg_latency_ms == 200.0

    def test_success_rate(self):
        """Test success rate calculation."""
        agg = AggregatedCosts(role="chat")
        assert agg.success_rate == 0.0

        # Add successful
        snapshot = CostSnapshot(
            timestamp=datetime.now(UTC),
            role="chat",
            model_id="meta/llama-3.1-8b-instruct",
            tokens_in=100,
            tokens_out=50,
            latency_ms=150.0,
            cost_usd=0.000015,
            success=True,
        )
        agg.add(snapshot)
        assert agg.success_rate == 1.0

        # Add failed
        snapshot2 = CostSnapshot(
            timestamp=datetime.now(UTC),
            role="chat",
            model_id="meta/llama-3.1-8b-instruct",
            tokens_in=100,
            tokens_out=0,
            latency_ms=100.0,
            cost_usd=0.0,
            success=False,
            error="Error",
        )
        agg.add(snapshot2)
        assert agg.success_rate == 0.5

    def test_avg_cost_per_call(self):
        """Test average cost per call calculation."""
        agg = AggregatedCosts(role="chat")
        assert agg.avg_cost_per_call == 0.0

        snapshot = CostSnapshot(
            timestamp=datetime.now(UTC),
            role="chat",
            model_id="meta/llama-3.1-8b-instruct",
            tokens_in=100,
            tokens_out=50,
            latency_ms=150.0,
            cost_usd=0.000015,
            success=True,
        )
        agg.add(snapshot)
        assert agg.avg_cost_per_call == 0.000015


class TestCostTracker:
    """Tests for CostTracker class."""

    @pytest.fixture
    def tracker(self):
        """Create a fresh CostTracker for each test."""
        return CostTracker()

    def test_calculate_cost_known_model(self, tracker):
        """Test cost calculation for a known model."""
        cost = tracker.calculate_cost("meta/llama-3.1-8b-instruct", 1_000_000, 1_000_000)
        # input: 1M * $0.10 = $0.10, output: 1M * $0.10 = $0.10, total = $0.20
        assert cost == 0.20

    def test_calculate_cost_unknown_model(self, tracker):
        """Test cost calculation for unknown model returns 0."""
        cost = tracker.calculate_cost("unknown/model", 1_000_000, 1_000_000)
        assert cost == 0.0

    def test_calculate_cost_embedding_model(self, tracker):
        """Test cost calculation for embedding model (output cost = 0)."""
        cost = tracker.calculate_cost("nvidia/nv-embedqa-e5-v5", 1_000_000, 1_000_000)
        # input: 1M * $0.05 = $0.05, output: 1M * $0 = $0, total = $0.05
        assert cost == 0.05

    def test_record_call(self, tracker):
        """Test recording a call."""
        snapshot = tracker.record_call(
            role="chat",
            model_id="meta/llama-3.1-8b-instruct",
            tokens_in=100,
            tokens_out=50,
            latency_ms=150.0,
            success=True,
        )
        assert snapshot.role == "chat"
        assert snapshot.model_id == "meta/llama-3.1-8b-instruct"
        assert snapshot.tokens_in == 100
        assert snapshot.tokens_out == 50
        assert snapshot.latency_ms == 150.0
        assert snapshot.success is True

        # Check aggregates
        aggregates = tracker.get_aggregates("chat")
        assert "chat" in aggregates
        assert aggregates["chat"].total_calls == 1

    def test_record_failed_call(self, tracker):
        """Test recording a failed call."""
        snapshot = tracker.record_call(
            role="chat",
            model_id="meta/llama-3.1-8b-instruct",
            tokens_in=100,
            tokens_out=0,
            latency_ms=100.0,
            success=False,
            error="Model unavailable",
        )
        assert snapshot.success is False
        assert snapshot.error == "Model unavailable"

        aggregates = tracker.get_aggregates("chat")
        assert aggregates["chat"].failed_calls == 1
        assert aggregates["chat"].successful_calls == 0

    def test_get_aggregates_all(self, tracker):
        """Test getting all aggregates."""
        tracker.record_call("chat", "model1", 100, 50, 150.0)
        tracker.record_call("embedding", "model2", 200, 0, 50.0)

        aggregates = tracker.get_aggregates()
        assert "chat" in aggregates
        assert "embedding" in aggregates

    def test_get_aggregates_specific_role(self, tracker):
        """Test getting aggregates for a specific role."""
        tracker.record_call("chat", "model1", 100, 50, 150.0)
        tracker.record_call("embedding", "model2", 200, 0, 50.0)

        aggregates = tracker.get_aggregates("chat")
        assert "chat" in aggregates
        assert "embedding" not in aggregates

    def test_get_aggregates_nonexistent_role(self, tracker):
        """Test getting aggregates for nonexistent role returns empty AggregatedCosts."""
        aggregates = tracker.get_aggregates("nonexistent")
        assert "nonexistent" in aggregates
        assert aggregates["nonexistent"].total_calls == 0

    def test_get_snapshots_no_filters(self, tracker):
        """Test getting snapshots without filters."""
        for i in range(5):
            tracker.record_call("chat", f"model{i}", 100, 50, 150.0)

        snapshots = tracker.get_snapshots()
        assert len(snapshots) == 5

    def test_get_snapshots_role_filter(self, tracker):
        """Test getting snapshots with role filter."""
        tracker.record_call("chat", "model1", 100, 50, 150.0)
        tracker.record_call("embedding", "model2", 200, 0, 50.0)

        snapshots = tracker.get_snapshots(role="chat")
        assert len(snapshots) == 1
        assert snapshots[0].role == "chat"

    def test_get_snapshots_model_filter(self, tracker):
        """Test getting snapshots with model filter."""
        tracker.record_call("chat", "model1", 100, 50, 150.0)
        tracker.record_call("chat", "model2", 200, 100, 200.0)

        snapshots = tracker.get_snapshots(model_id="model1")
        assert len(snapshots) == 1
        assert snapshots[0].model_id == "model1"

    def test_get_snapshots_since_filter(self, tracker):
        """Test getting snapshots with since filter."""
        tracker.record_call("chat", "model1", 100, 50, 150.0)
        time.sleep(0.01)
        since = datetime.now(UTC)
        time.sleep(0.01)
        tracker.record_call("chat", "model2", 200, 100, 200.0)

        snapshots = tracker.get_snapshots(since=since)
        assert len(snapshots) == 1
        assert snapshots[0].model_id == "model2"

    def test_get_snapshots_limit(self, tracker):
        """Test getting snapshots with limit."""
        for i in range(10):
            tracker.record_call("chat", f"model{i}", 100, 50, 150.0)

        snapshots = tracker.get_snapshots(limit=3)
        assert len(snapshots) == 3

    def test_get_summary(self, tracker):
        """Test getting cost summary."""
        tracker.record_call("chat", "model1", 100, 50, 150.0)
        tracker.record_call("chat", "model1", 200, 100, 200.0)
        tracker.record_call("embedding", "model2", 500, 0, 100.0)

        summary = tracker.get_summary()
        assert summary["total_calls"] == 3
        # total_tokens = tokens_in + tokens_out for all calls
        # chat: (100+50) + (200+100) = 450
        # embedding: (500+0) = 500
        # total = 950
        assert summary["total_tokens"] == 950
        assert "chat" in summary["by_role"]
        assert "embedding" in summary["by_role"]
        assert summary["by_role"]["chat"]["calls"] == 2
        assert summary["by_role"]["embedding"]["calls"] == 1

    def test_reset(self, tracker):
        """Test resetting the tracker."""
        tracker.record_call("chat", "model1", 100, 50, 150.0)
        tracker.reset()

        aggregates = tracker.get_aggregates()
        assert aggregates == {}
        snapshots = tracker.get_snapshots()
        assert snapshots == []

    def test_max_snapshots_limit(self, tracker):
        """Test that snapshots are limited to max_snapshots."""
        tracker._max_snapshots = 3
        for i in range(5):
            tracker.record_call("chat", f"model{i}", 100, 50, 150.0)

        snapshots = tracker.get_snapshots(limit=10)
        assert len(snapshots) == 3
        # Should keep the last 3
        assert snapshots[0].model_id == "model2"
        assert snapshots[1].model_id == "model3"
        assert snapshots[2].model_id == "model4"


class TestGlobalCostTracker:
    """Tests for global cost tracker functions."""

    def test_get_cost_tracker_singleton(self):
        """Test that get_cost_tracker returns singleton."""
        reset_cost_tracker()
        tracker1 = get_cost_tracker()
        tracker2 = get_cost_tracker()
        assert tracker1 is tracker2
        reset_cost_tracker()

    def test_reset_cost_tracker(self):
        """Test resetting global cost tracker."""
        reset_cost_tracker()
        tracker = get_cost_tracker()
        tracker.record_call("chat", "model1", 100, 50, 150.0)

        reset_cost_tracker()
        tracker2 = get_cost_tracker()
        aggregates = tracker2.get_aggregates()
        assert aggregates == {}


class TestTrackCostContextManager:
    """Tests for track_cost async context manager."""

    @pytest.mark.asyncio
    async def test_track_cost_success(self):
        """Test track_cost with successful completion."""
        reset_cost_tracker()
        try:
            async with track_cost(ModelRole.GENERATOR_LLM, "meta/llama-3.1-8b-instruct") as result:
                result["tokens_in"] = 100
                result["tokens_out"] = 50

            tracker = get_cost_tracker()
            aggregates = tracker.get_aggregates("generator_llm")
            assert aggregates["generator_llm"].total_calls == 1
            assert aggregates["generator_llm"].successful_calls == 1
            assert aggregates["generator_llm"].total_tokens_in == 100
            assert aggregates["generator_llm"].total_tokens_out == 50
        finally:
            reset_cost_tracker()

    @pytest.mark.asyncio
    async def test_track_cost_exception(self):
        """Test track_cost with exception."""
        reset_cost_tracker()
        try:
            with pytest.raises(ValueError):
                async with track_cost(ModelRole.GENERATOR_LLM, "meta/llama-3.1-8b-instruct") as result:
                    result["tokens_in"] = 100
                    result["tokens_out"] = 50
                    raise ValueError("Test error")

            tracker = get_cost_tracker()
            aggregates = tracker.get_aggregates("generator_llm")
            assert aggregates["generator_llm"].total_calls == 1
            assert aggregates["generator_llm"].failed_calls == 1
            assert aggregates["generator_llm"].successful_calls == 0
        finally:
            reset_cost_tracker()

    @pytest.mark.asyncio
    async def test_track_cost_string_role(self):
        """Test track_cost with string role."""
        reset_cost_tracker()
        try:
            async with track_cost("custom_role", "meta/llama-3.1-8b-instruct") as result:
                result["tokens_in"] = 100
                result["tokens_out"] = 50

            tracker = get_cost_tracker()
            aggregates = tracker.get_aggregates("custom_role")
            assert aggregates["custom_role"].total_calls == 1
        finally:
            reset_cost_tracker()


class TestEstimateCost:
    """Tests for estimate_cost function."""

    @patch("nim_sentinel.core.get_model_config")
    def test_estimate_cost(self, mock_get_model_config):
        """Test cost estimation."""
        mock_config = MagicMock()
        mock_config.primary = "meta/llama-3.1-8b-instruct"
        mock_get_model_config.return_value = mock_config

        reset_cost_tracker()
        try:
            cost = estimate_cost(ModelRole.GENERATOR_LLM, 1_000_000, 1_000_000)
            # input: 1M * $0.10 = $0.10, output: 1M * $0.10 = $0.10, total = $0.20
            assert cost == 0.20
        finally:
            reset_cost_tracker()

    @patch("nim_sentinel.core.get_model_config")
    def test_estimate_cost_string_role(self, mock_get_model_config):
        """Test cost estimation with string role."""
        mock_config = MagicMock()
        mock_config.primary = "nvidia/nv-embedqa-e5-v5"
        mock_get_model_config.return_value = mock_config

        reset_cost_tracker()
        try:
            cost = estimate_cost("embedding", 1_000_000, 0)
            # input: 1M * $0.05 = $0.05, output: 0
            assert cost == 0.05
        finally:
            reset_cost_tracker()


class TestModelPricing:
    """Tests for MODEL_PRICING dictionary."""

    def test_pricing_has_chat_models(self):
        """Test that pricing includes chat models."""
        assert "meta/llama-3.1-8b-instruct" in MODEL_PRICING
        assert "meta/llama-3.1-70b-instruct" in MODEL_PRICING
        assert "nvidia/nemotron-3-ultra-550b-a55b" in MODEL_PRICING

    def test_pricing_has_embedding_models(self):
        """Test that pricing includes embedding models."""
        assert "nvidia/nv-embedqa-e5-v5" in MODEL_PRICING
        assert "nvidia/llama-3.2-nv-embedqa-1b-v2" in MODEL_PRICING
        assert "baai/bge-m3" in MODEL_PRICING

    def test_pricing_has_rerank_models(self):
        """Test that pricing includes rerank models."""
        assert "nvidia/llama-3.2-nv-rerankqa-1b-v1" in MODEL_PRICING
        assert "nvidia/llama-nemotron-rerank-1b-v2" in MODEL_PRICING

    def test_pricing_structure(self):
        """Test that pricing entries have correct structure."""
        for _, pricing in MODEL_PRICING.items():
            assert "input" in pricing
            assert "output" in pricing
            assert isinstance(pricing["input"], int | float)
            assert isinstance(pricing["output"], int | float)
            assert pricing["input"] >= 0
            assert pricing["output"] >= 0


class TestCostTrackerThreadSafety:
    """Tests for thread safety of CostTracker."""

    @pytest.fixture
    def tracker(self):
        """Create a fresh CostTracker for each test."""
        return CostTracker()

    def test_concurrent_record_calls(self, tracker):
        """Test concurrent record_call calls."""
        import threading

        def record_calls(role, count):
            for i in range(count):
                tracker.record_call(role, f"model{i}", 100, 50, 150.0)

        threads = [
            threading.Thread(target=record_calls, args=("chat", 10)),
            threading.Thread(target=record_calls, args=("embedding", 10)),
            threading.Thread(target=record_calls, args=("reranker", 10)),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        aggregates = tracker.get_aggregates()
        assert aggregates["chat"].total_calls == 10
        assert aggregates["embedding"].total_calls == 10
        assert aggregates["reranker"].total_calls == 10

    def test_concurrent_get_aggregates(self, tracker):
        """Test concurrent get_aggregates calls."""
        import threading

        tracker.record_call("chat", "model1", 100, 50, 150.0)

        results = []

        def get_aggregates():
            for _ in range(100):
                aggregates = tracker.get_aggregates()
                results.append(aggregates)

        threads = [threading.Thread(target=get_aggregates) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All calls should succeed without errors
        assert len(results) == 500
        for aggregates in results:
            assert "chat" in aggregates
