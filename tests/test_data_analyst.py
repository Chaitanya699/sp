"""
Tests for Data Analyst Agent
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from nim_sentinel.agents.data_analyst import (
    DataAnalystAgent,
    AnalystQuery,
    AnalystResult,
    ALLOWED_STAGES,
    FORBIDDEN_STAGES,
    get_data_analyst,
    reset_data_analyst,
)


class TestDataAnalystAgent:
    """Tests for DataAnalystAgent class."""

    @pytest.fixture
    def agent(self):
        """Create a DataAnalystAgent instance."""
        reset_data_analyst()
        return DataAnalystAgent(max_rows=100, absolute_max_rows=1000)

    def test_validate_pipeline_valid(self, agent):
        """Test validation of valid pipeline."""
        pipeline = [
            {"$match": {"status": "active"}},
            {"$project": {"name": 1, "value": 1}},
            {"$sort": {"value": -1}},
            {"$limit": 10},
        ]
        is_valid, error = agent.validate_pipeline(pipeline)
        assert is_valid
        assert error == ""

    def test_validate_pipeline_forbidden_stage(self, agent):
        """Test validation rejects forbidden stages."""
        pipeline = [{"$out": "results"}]
        is_valid, error = agent.validate_pipeline(pipeline)
        assert not is_valid
        assert "Forbidden stage: $out" in error

    def test_validate_pipeline_not_allowlisted(self, agent):
        """Test validation rejects non-allowlisted stages."""
        pipeline = [{"$invalidStage": {}}]
        is_valid, error = agent.validate_pipeline(pipeline)
        assert not is_valid
        assert "not in allowlist" in error

    def test_validate_pipeline_not_list(self, agent):
        """Test validation rejects non-list pipeline."""
        is_valid, error = agent.validate_pipeline("not a list")
        assert not is_valid
        assert "must be a list" in error

    def test_validate_pipeline_stage_not_dict(self, agent):
        """Test validation rejects non-dict stage."""
        pipeline = ["not a dict"]
        is_valid, error = agent.validate_pipeline(pipeline)
        assert not is_valid
        assert "must be a dictionary" in error

    def test_validate_pipeline_multiple_keys(self, agent):
        """Test validation rejects stage with multiple keys."""
        pipeline = [{"$match": {}, "$project": {}}]
        is_valid, error = agent.validate_pipeline(pipeline)
        assert not is_valid
        assert "exactly one key" in error

    def test_validate_pipeline_lookup_valid(self, agent):
        """Test validation accepts valid $lookup."""
        pipeline = [{"$lookup": {"from": "other_collection", "localField": "id", "foreignField": "ref", "as": "joined"}}]
        is_valid, error = agent.validate_pipeline(pipeline)
        assert is_valid

    def test_validate_pipeline_lookup_missing_from(self, agent):
        """Test validation rejects $lookup without 'from'."""
        pipeline = [{"$lookup": {"localField": "id", "foreignField": "ref", "as": "joined"}}]
        is_valid, error = agent.validate_pipeline(pipeline)
        assert not is_valid
        assert "$lookup requires 'from' field" in error

    def test_inject_tenant_filter_empty_pipeline(self, agent):
        """Test tenant filter injection into empty pipeline."""
        pipeline = []
        result = agent.inject_tenant_filter(pipeline, "tenant_123")
        assert len(result) == 1
        assert result[0] == {"$match": {"tenant_id": "tenant_123"}}

    def test_inject_tenant_filter_existing_match(self, agent):
        """Test tenant filter merges with existing $match."""
        pipeline = [{"$match": {"status": "active"}}, {"$limit": 10}]
        result = agent.inject_tenant_filter(pipeline, "tenant_123")
        assert len(result) == 2
        assert "$match" in result[0]
        match = result[0]["$match"]
        # Implementation wraps in $and
        assert "$and" in match
        assert match["$and"][0] == {"tenant_id": "tenant_123"}
        assert match["$and"][1] == {"status": "active"}

    def test_inject_tenant_filter_existing_match_with_and(self, agent):
        """Test tenant filter merges with existing $match that has $and."""
        pipeline = [{"$match": {"$and": [{"status": "active"}, {"type": "doc"}]}}, {"$limit": 10}]
        result = agent.inject_tenant_filter(pipeline, "tenant_123")
        match = result[0]["$match"]
        assert "$and" in match
        assert len(match["$and"]) == 3
        assert match["$and"][0] == {"tenant_id": "tenant_123"}

    def test_enforce_row_limit_no_limit(self, agent):
        """Test row limit enforcement adds $limit when missing."""
        pipeline = [{"$match": {"status": "active"}}]
        result = agent.enforce_row_limit(pipeline, 50)
        assert len(result) == 2
        assert result[-1] == {"$limit": 50}

    def test_enforce_row_limit_caps_existing(self, agent):
        """Test row limit enforcement caps existing $limit."""
        pipeline = [{"$match": {"status": "active"}}, {"$limit": 200}]
        result = agent.enforce_row_limit(pipeline, 50)
        assert len(result) == 2
        assert result[-1] == {"$limit": 50}

    def test_enforce_row_limit_keeps_smaller(self, agent):
        """Test row limit enforcement keeps smaller existing $limit."""
        pipeline = [{"$match": {"status": "active"}}, {"$limit": 30}]
        result = agent.enforce_row_limit(pipeline, 50)
        assert len(result) == 2
        assert result[-1] == {"$limit": 30}

    def test_sanitize_pipeline_full(self, agent):
        """Test full pipeline sanitization."""
        pipeline = [
            {"$match": {"status": "active"}},
            {"$project": {"name": 1}},
            {"$sort": {"name": 1}},
        ]
        result = agent.sanitize_pipeline(pipeline, "tenant_123", 50)
        # Should have tenant match at start (wrapped in $and), limit at end
        assert "$match" in result[0]
        match = result[0]["$match"]
        assert "$and" in match
        assert match["$and"][0] == {"tenant_id": "tenant_123"}
        assert result[-1] == {"$limit": 50}

    def test_sanitize_pipeline_invalid_raises(self, agent):
        """Test sanitize_pipeline raises on invalid pipeline."""
        pipeline = [{"$out": "results"}]
        with pytest.raises(ValueError, match="Pipeline validation failed"):
            agent.sanitize_pipeline(pipeline, "tenant_123", 50)

    @pytest.mark.asyncio
    async def test_execute_simple(self, agent):
        """Test execute_simple builds correct pipeline."""
        mock_client = AsyncMock()
        mock_db = MagicMock()
        mock_coll = AsyncMock()
        mock_cursor = AsyncMock()

        mock_client.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_coll
        mock_coll.aggregate.return_value = mock_cursor

        # Mock async iteration
        async def mock_aiter(self):
            yield {"_id": "1", "name": "test", "tenant_id": "tenant_123"}
            yield {"_id": "2", "name": "test2", "tenant_id": "tenant_123"}

        mock_cursor.__aiter__ = mock_aiter

        with patch("nim_sentinel.agents.data_analyst.get_mongo_client", return_value=mock_client):
            with patch("nim_sentinel.agents.data_analyst.get_settings") as mock_settings:
                mock_settings.return_value.mongodb_database = "test_db"

                result = await agent.execute_simple(
                    collection="documents",
                    filter_query={"status": "active"},
                    projection={"name": 1},
                    sort=[("name", 1)],
                    limit=10,
                    tenant_id="tenant_123",
                )

        assert isinstance(result, AnalystResult)
        assert result.row_count == 2
        assert not result.truncated

    @pytest.mark.asyncio
    async def test_execute_with_mock(self, agent):
        """Test execute with mocked MongoDB."""
        mock_client = AsyncMock()
        mock_db = MagicMock()
        mock_coll = AsyncMock()
        mock_cursor = AsyncMock()

        mock_client.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_coll
        mock_coll.aggregate.return_value = mock_cursor

        async def mock_aiter(self):
            for i in range(5):
                yield {"_id": str(i), "value": i, "tenant_id": "tenant_123"}

        mock_cursor.__aiter__ = mock_aiter

        with patch("nim_sentinel.agents.data_analyst.get_mongo_client", return_value=mock_client):
            with patch("nim_sentinel.agents.data_analyst.get_settings") as mock_settings:
                mock_settings.return_value.mongodb_database = "test_db"

                result = await agent.execute(
                    collection="chunks",
                    pipeline=[{"$match": {"status": "ready"}}, {"$sort": {"value": -1}}],
                    tenant_id="tenant_123",
                    max_rows=10,
                )

        assert isinstance(result, AnalystResult)
        assert result.row_count == 5
        assert not result.truncated
        assert result.execution_time_ms > 0

    def test_global_instance(self):
        """Test global instance getter."""
        reset_data_analyst()
        agent1 = get_data_analyst()
        agent2 = get_data_analyst()
        assert agent1 is agent2
        reset_data_analyst()


class TestAllowedStages:
    """Tests for allowed/forbidden stage lists."""

    def test_allowed_stages_contains_basics(self):
        """Test basic stages are allowed."""
        assert "$match" in ALLOWED_STAGES
        assert "$project" in ALLOWED_STAGES
        assert "$group" in ALLOWED_STAGES
        assert "$sort" in ALLOWED_STAGES
        assert "$limit" in ALLOWED_STAGES
        assert "$skip" in ALLOWED_STAGES
        assert "$lookup" in ALLOWED_STAGES
        assert "$unwind" in ALLOWED_STAGES
        assert "$addFields" in ALLOWED_STAGES
        assert "$count" in ALLOWED_STAGES
        assert "$facet" in ALLOWED_STAGES
        assert "$search" in ALLOWED_STAGES
        assert "$vectorSearch" in ALLOWED_STAGES

    def test_forbidden_stages_contains_writes(self):
        """Test write stages are forbidden."""
        assert "$out" in FORBIDDEN_STAGES
        assert "$merge" in FORBIDDEN_STAGES

    def test_no_overlap(self):
        """Test no stage is both allowed and forbidden."""
        overlap = ALLOWED_STAGES & FORBIDDEN_STAGES
        assert len(overlap) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])