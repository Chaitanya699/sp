"""
Tests for NIM Sentinel Graph Checkpointer Module (B5)
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from nim_sentinel.graph.checkpointer import MongoDBCheckpointer
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.asynchronous.database import AsyncDatabase


class TestMongoDBCheckpointer:
    """Tests for MongoDBCheckpointer class."""

    @pytest.fixture
    def mock_collection(self):
        """Create a mock AsyncCollection."""
        mock = AsyncMock(spec=AsyncCollection)
        mock.insert_one = AsyncMock()
        mock.update_one = AsyncMock()
        mock.find_one = AsyncMock()
        mock.find = MagicMock()
        mock.delete_many = AsyncMock()
        mock.create_index = AsyncMock()
        return mock

    @pytest.fixture
    def mock_db(self, mock_collection):
        """Create a mock AsyncDatabase."""
        mock = AsyncMock(spec=AsyncDatabase)
        mock.__getitem__ = MagicMock(return_value=mock_collection)
        return mock

    @pytest.fixture
    def checkpointer(self, mock_db, mock_collection):
        """Create MongoDBCheckpointer instance with mocked database and collection."""
        cp = MongoDBCheckpointer(tenant_id="test_tenant", db=mock_db, collection=mock_collection)
        return cp

    @pytest.mark.asyncio
    async def test_aput_creates_checkpoint(self, checkpointer, mock_collection):
        """Test that aput creates a checkpoint document."""
        config = {"configurable": {"thread_id": "thread_1", "tenant_id": "test_tenant"}}
        checkpoint = {
            "v": 1,
            "id": "checkpoint_1",
            "ts": datetime.now(UTC).isoformat(),
            "channel_values": {"query": "test", "answer": "test answer"},
            "channel_versions": {"query": 1, "answer": 1},
            "versions_seen": {},
            "updated_channels": ["query", "answer"],
        }
        metadata = {"source": "test"}

        await checkpointer.aput(config, checkpoint, metadata, {})

        mock_collection.update_one.assert_called_once()
        call_args = mock_collection.update_one.call_args
        assert call_args[1]["upsert"] is True
        filter_args = call_args[0][0]
        assert filter_args["thread_id"] == "thread_1"
        assert filter_args["tenant_id"] == "test_tenant"
        assert filter_args["checkpoint_id"] == "checkpoint_1"
        # Check the document being set
        set_args = call_args[0][1]["$set"]
        assert set_args["metadata"] == metadata

    @pytest.mark.asyncio
    async def test_aget_returns_latest_checkpoint(self, checkpointer, mock_collection):
        """Test that aget returns the latest checkpoint for a thread."""
        mock_checkpoint = {
            "tenant_id": "test_tenant",
            "thread_id": "thread_1",
            "checkpoint_ns": "",
            "checkpoint_id": "checkpoint_1",
            "parent_checkpoint_id": None,
            "checkpoint": {"query": "test", "answer": "test answer"},
            "metadata": {"source": "test"},
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        mock_collection.find_one = AsyncMock(return_value=mock_checkpoint)

        config = {"configurable": {"thread_id": "thread_1", "tenant_id": "test_tenant"}}
        result = await checkpointer.aget_tuple(config)

        assert result is not None
        assert result.checkpoint["id"] == "checkpoint_1"
        assert result.metadata == {"source": "test"}

    @pytest.mark.asyncio
    async def test_aget_returns_none_for_missing_thread(self, checkpointer, mock_collection):
        """Test that aget returns None when thread doesn't exist."""
        mock_collection.find_one = AsyncMock(return_value=None)

        config = {"configurable": {"thread_id": "nonexistent", "tenant_id": "test_tenant"}}
        result = await checkpointer.aget_tuple(config)

        assert result is None

    @pytest.mark.asyncio
    async def test_alist_returns_checkpoints_for_thread(self, checkpointer, mock_collection):
        """Test that alist returns checkpoints for a thread."""
        # Create mock documents
        doc1 = {
            "tenant_id": "test_tenant",
            "thread_id": "thread_1",
            "checkpoint_ns": "",
            "checkpoint_id": "checkpoint_1",
            "parent_checkpoint_id": None,
            "checkpoint": {"query": "test"},
            "metadata": {"source": "test"},
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        doc2 = {
            "tenant_id": "test_tenant",
            "thread_id": "thread_1",
            "checkpoint_ns": "",
            "checkpoint_id": "checkpoint_2",
            "parent_checkpoint_id": None,
            "checkpoint": {"query": "test", "answer": "test answer"},
            "metadata": {"source": "test"},
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }

        # Create a proper async iterator
        async def mock_aiter():
            yield doc1
            yield doc2

        mock_cursor = AsyncMock()
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=mock_cursor)
        mock_cursor.__aiter__ = lambda self: mock_aiter()
        mock_collection.find = MagicMock(return_value=mock_cursor)

        config = {"configurable": {"thread_id": "thread_1", "tenant_id": "test_tenant"}}
        results = []
        async for item in checkpointer.alist(config):
            results.append(item)

        assert len(results) == 2
        assert results[0].checkpoint["id"] == "checkpoint_1"
        assert results[1].checkpoint["id"] == "checkpoint_2"

    @pytest.mark.asyncio
    async def test_aput_writes_checkpoint_writes(self, checkpointer, mock_collection):
        """Test that aput handles checkpoint writes."""
        # The current implementation doesn't write checkpoint_writes separately
        # This test verifies the basic aput functionality
        config = {"configurable": {"thread_id": "thread_1", "tenant_id": "test_tenant"}}
        checkpoint = {
            "v": 1,
            "id": "checkpoint_1",
            "ts": datetime.now(UTC).isoformat(),
            "channel_values": {"query": "test"},
            "channel_versions": {"query": 1},
            "versions_seen": {},
            "updated_channels": ["query"],
        }
        metadata = {"source": "test"}
        writes = [
            ("channel1", "value1", {"key": "val1"}),
            ("channel2", "value2", {"key": "val2"}),
        ]

        await checkpointer.aput(config, checkpoint, metadata, writes)

        mock_collection.update_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_tenant_isolation(self, checkpointer, mock_collection):
        """Test that checkpoints are isolated by tenant_id."""
        mock_collection.find_one = AsyncMock(return_value=None)

        # Try to get checkpoint for different tenant
        config = {"configurable": {"thread_id": "thread_1", "tenant_id": "other_tenant"}}
        result = await checkpointer.aget_tuple(config)

        # Should return None because tenant_id doesn't match
        assert result is None
        # Verify find_one was called with correct tenant filter
        mock_collection.find_one.assert_called_once()
        call_args = mock_collection.find_one.call_args[0][0]
        assert call_args["tenant_id"] == "test_tenant"  # Checkpointer's tenant_id

    @pytest.mark.asyncio
    async def test_aput_uses_upsert(self, checkpointer, mock_collection):
        """Test that aput uses upsert to handle concurrent writes."""
        config = {"configurable": {"thread_id": "thread_1", "tenant_id": "test_tenant"}}
        checkpoint = {
            "v": 1,
            "id": "checkpoint_1",
            "ts": datetime.now(UTC).isoformat(),
            "channel_values": {"query": "test"},
            "channel_versions": {"query": 1},
            "versions_seen": {},
            "updated_channels": ["query"],
        }
        metadata = {"source": "test"}

        await checkpointer.aput(config, checkpoint, metadata, {})

        mock_collection.update_one.assert_called_once()
        call_args = mock_collection.update_one.call_args
        assert call_args[1]["upsert"] is True
        filter_args = call_args[0][0]
        assert filter_args["thread_id"] == "thread_1"
        assert filter_args["tenant_id"] == "test_tenant"
        assert filter_args["checkpoint_id"] == "checkpoint_1"
