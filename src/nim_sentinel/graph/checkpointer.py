"""
NIM Sentinel MongoDB Checkpointer

LangGraph checkpointer implementation using MongoDB for persistence.
"""

import logging
from typing import Any, Optional, AsyncIterator
from datetime import datetime
from contextlib import asynccontextmanager

from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
)
from langchain_core.runnables import RunnableConfig
from pymongo import ASCENDING
from pymongo.errors import DuplicateKeyError
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.asynchronous.collection import AsyncCollection

from nim_sentinel.db.client import get_mongo_client, get_database
from nim_sentinel.core.config import get_settings

logger = logging.getLogger(__name__)


class MongoDBCheckpointer(BaseCheckpointSaver[int]):
    """
    MongoDB-based checkpointer for LangGraph.

    Stores checkpoints in a MongoDB collection with tenant isolation.
    """

    def __init__(self, tenant_id: str) -> None:
        super().__init__()
        self.tenant_id = tenant_id
        self._db: AsyncDatabase[Any] | None = None
        self._collection: AsyncCollection[Any] | None = None

    async def _get_collection(self) -> AsyncCollection[Any]:
        """Get or create the checkpoints collection."""
        if self._collection is not None:
            return self._collection

        self._db = await get_database()
        self._collection = self._db["langgraph_checkpoints"]

        # Create indexes
        await self._collection.create_index([
            ("tenant_id", ASCENDING),
            ("thread_id", ASCENDING),
            ("checkpoint_ns", ASCENDING),
            ("checkpoint_id", ASCENDING),
        ], unique=True)

        await self._collection.create_index([
            ("tenant_id", ASCENDING),
            ("thread_id", ASCENDING),
            ("updated_at", -1),
        ])

        return self._collection

    def _serialize_checkpoint(self, checkpoint: Checkpoint, config: RunnableConfig) -> dict[str, Any]:
        """Serialize checkpoint to MongoDB document."""
        configurable = config.get("configurable", {}) if isinstance(config, dict) else {}
        return {
            "tenant_id": self.tenant_id,
            "thread_id": configurable.get("thread_id", ""),
            "checkpoint_ns": configurable.get("checkpoint_ns", ""),
            "checkpoint_id": checkpoint.get("id", ""),
            "parent_checkpoint_id": config.get("configurable", {}).get("checkpoint_id"),
            "checkpoint": checkpoint.get("channel_values", {}),
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
            } if doc.get("parent_checkpoint_id") else None,
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

        try:
            await collection.insert_one(doc)
        except DuplicateKeyError:
            # Update existing
            await collection.update_one(
                {
                    "tenant_id": self.tenant_id,
                    "thread_id": doc["thread_id"],
                    "checkpoint_ns": doc["checkpoint_ns"],
                    "checkpoint_id": doc["checkpoint_id"],
                },
                {"$set": doc},
            )

        return {"configurable": {"thread_id": doc["thread_id"], "checkpoint_ns": doc["checkpoint_ns"]}}

    async def aget_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
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
        config: Optional[RunnableConfig] = None,
        *,
        filter: Optional[dict[str, Any]] = None,
        before: Optional[RunnableConfig] = None,
        limit: Optional[int] = None,
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
        await collection.delete_many({
            "tenant_id": self.tenant_id,
            "thread_id": thread_id,
        })


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