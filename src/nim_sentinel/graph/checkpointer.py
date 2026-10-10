"""
NIM Sentinel MongoDB Checkpointer

LangGraph checkpointer implementation using MongoDB for persistence.
"""

import logging
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
)
from nim_sentinel.db.client import get_database
from pymongo import ASCENDING
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.asynchronous.database import AsyncDatabase

logger = logging.getLogger(__name__)


class MongoDBCheckpointer(BaseCheckpointSaver[int]):
    """
    MongoDB-based checkpointer for LangGraph.

    Stores checkpoints in a MongoDB collection with tenant isolation.
    """

    def __init__(
        self,
        tenant_id: str,
        db: AsyncDatabase[Any] | None = None,
        collection: AsyncCollection[Any] | None = None,
    ) -> None:
        super().__init__()
        self.tenant_id = tenant_id
        self._db = db
        self._collection = collection
        self._indexes_created = False

    async def _get_collection(self) -> AsyncCollection[Any]:
        """Get or create the checkpoints collection."""
        if self._collection is not None:
            return self._collection

        if self._db is None:
            self._db = await get_database()
        self._collection = self._db["langgraph_checkpoints"]

        # Create indexes (only once per instance)
        if not self._indexes_created:
            await self._collection.create_index(
                [
                    ("tenant_id", ASCENDING),
                    ("thread_id", ASCENDING),
                    ("checkpoint_ns", ASCENDING),
                    ("checkpoint_id", ASCENDING),
                ],
                unique=True,
            )

            await self._collection.create_index(
                [
                    ("tenant_id", ASCENDING),
                    ("thread_id", ASCENDING),
                    ("updated_at", -1),
                ]
            )
            self._indexes_created = True

        return self._collection

    def _serialize_checkpoint(
        self, checkpoint: Checkpoint, config: RunnableConfig
    ) -> dict[str, Any]:
        """Serialize checkpoint to MongoDB document."""
        configurable = config.get("configurable", {}) if isinstance(config, dict) else {}

        def serialize_value(value: Any) -> Any:
            """Recursively serialize values to MongoDB-compatible types."""
            if hasattr(value, "__dataclass_fields__"):
                # It's a dataclass, convert to dict
                return {k: serialize_value(v) for k, v in value.__dict__.items()}
            elif isinstance(value, list):
                return [serialize_value(v) for v in value]
            elif isinstance(value, dict):
                return {k: serialize_value(v) for k, v in value.items()}
            elif hasattr(value, "__dict__"):
                # Generic object with __dict__
                return serialize_value(value.__dict__)
            else:
                return value

        # Convert channel_values to dict if it contains dataclass objects
        channel_values = checkpoint.get("channel_values", {})
        serialized_values = {}
        for key, value in channel_values.items():
            serialized_values[key] = serialize_value(value)

        return {
            "tenant_id": self.tenant_id,
            "thread_id": configurable.get("thread_id", ""),
            "checkpoint_ns": configurable.get("checkpoint_ns", ""),
            "checkpoint_id": checkpoint.get("id", ""),
            "parent_checkpoint_id": config.get("configurable", {}).get("checkpoint_id"),
            "checkpoint": serialized_values,
            "metadata": config.get("metadata", {}),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

    def _deserialize_checkpoint(self, doc: dict[str, Any]) -> CheckpointTuple:
        """Deserialize MongoDB document to CheckpointTuple."""
        config: RunnableConfig = {
            "configurable": {
                "thread_id": doc["thread_id"],
                "checkpoint_ns": doc["checkpoint_ns"],
            }
        }

        checkpoint: Checkpoint = {
            "v": 1,
            "ts": doc.get("updated_at", datetime.utcnow()).isoformat(),
            "id": doc["checkpoint_id"],
            "channel_values": doc.get("checkpoint", {}),
            "channel_versions": {},
            "versions_seen": {},
            "updated_channels": [],
        }

        metadata: CheckpointMetadata = doc.get("metadata", {})

        return CheckpointTuple(
            config=config,
            checkpoint=checkpoint,
            metadata=metadata,
            parent_config={
                "configurable": {
                    "thread_id": doc["thread_id"],
                    "checkpoint_ns": doc["checkpoint_ns"],
                }
            }
            if doc.get("parent_checkpoint_id")
            else None,
        )

    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: dict[str, str | int | float],
    ) -> RunnableConfig:
        """Store a checkpoint."""
        collection = await self._get_collection()

        doc = self._serialize_checkpoint(checkpoint, config)
        doc["metadata"] = metadata

        # Use upsert to handle both insert and update atomically
        await collection.update_one(
            {
                "tenant_id": self.tenant_id,
                "thread_id": doc["thread_id"],
                "checkpoint_ns": doc["checkpoint_ns"],
                "checkpoint_id": doc["checkpoint_id"],
            },
            {"$set": doc},
            upsert=True,
        )

        return {
            "configurable": {"thread_id": doc["thread_id"], "checkpoint_ns": doc["checkpoint_ns"]}
        }

    async def aget_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        """Get a checkpoint tuple by config."""
        collection = await self._get_collection()

        configurable = config.get("configurable", {})
        thread_id = configurable.get("thread_id", "")
        checkpoint_ns = configurable.get("checkpoint_ns", "")
        checkpoint_id = configurable.get("checkpoint_id")

        query: dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "thread_id": thread_id,
            "checkpoint_ns": checkpoint_ns,
        }

        if checkpoint_id:
            query["checkpoint_id"] = checkpoint_id
            doc = await collection.find_one(query)
        else:
            # Get latest checkpoint for thread
            doc = await collection.find_one(
                query,
                sort=[("updated_at", -1)],
            )

        if doc is None:
            return None

        return self._deserialize_checkpoint(doc)

    async def alist(
        self,
        config: RunnableConfig | None = None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[CheckpointTuple]:
        """List checkpoints."""
        collection = await self._get_collection()

        query: dict[str, Any] = {"tenant_id": self.tenant_id}

        if config:
            configurable = config.get("configurable", {})
            thread_id = configurable.get("thread_id", "")
            checkpoint_ns = configurable.get("checkpoint_ns", "")
            query["thread_id"] = thread_id
            query["checkpoint_ns"] = checkpoint_ns

        if filter:
            query.update(filter)

        if before:
            before_configurable = before.get("configurable", {})
            before_id = before_configurable.get("checkpoint_id")
            if before_id:
                query["checkpoint_id"] = {"$lt": before_id}

        cursor = collection.find(query).sort("updated_at", -1)

        if limit:
            cursor = cursor.limit(limit)

        async for doc in cursor:
            yield self._deserialize_checkpoint(doc)

    async def adelete_thread(self, thread_id: str) -> None:
        """Delete all checkpoints for a thread."""
        collection = await self._get_collection()
        await collection.delete_many(
            {
                "tenant_id": self.tenant_id,
                "thread_id": thread_id,
            }
        )

    async def aput_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        """Store writes (required by LangGraph)."""
        # For now, we don't need to store intermediate writes separately
        # The main checkpoint is stored via aput
        pass


@asynccontextmanager
async def get_checkpointer(tenant_id: str) -> AsyncIterator[MongoDBCheckpointer]:
    """Get a MongoDB checkpointer for a tenant."""
    checkpointer = MongoDBCheckpointer(tenant_id)
    try:
        yield checkpointer
    finally:
        # Checkpointer doesn't need explicit cleanup
        pass


def create_checkpointer(tenant_id: str) -> MongoDBCheckpointer:
    """Create a MongoDB checkpointer for a tenant (sync version for compatibility)."""
    return MongoDBCheckpointer(tenant_id)
