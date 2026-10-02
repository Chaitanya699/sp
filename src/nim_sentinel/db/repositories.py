"""
NIM Sentinel MongoDB Repositories

Repository classes for documents, chunks, and sessions with tenant isolation.
All queries require tenant_id - no query runs without it.
"""

import logging
from abc import ABC
from datetime import UTC, datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from nim_sentinel.core.constants import (
    COLLECTION_CHUNKS,
    COLLECTION_DOCUMENTS,
    COLLECTION_SESSIONS,
)
from nim_sentinel.core.errors import (
    DatabaseError,
    TenantIsolationError,
)
from pymongo import ASCENDING, DESCENDING, IndexModel
from pymongo.errors import DuplicateKeyError, OperationFailure

logger = logging.getLogger(__name__)


class BaseRepository(ABC):
    """Base repository with tenant isolation enforcement."""

    collection_name: str
    indexes: list[IndexModel] = []

    def __init__(self, database: AsyncIOMotorDatabase, tenant_id: str):
        if not tenant_id:
            raise TenantIsolationError("tenant_id is required for all repository operations")
        self._db = database
        self._tenant_id = tenant_id
        self._collection: AsyncIOMotorCollection = database[self.collection_name]

    @property
    def tenant_id(self) -> str:
        return self._tenant_id

    @property
    def collection(self) -> AsyncIOMotorCollection:
        return self._collection

    def _add_tenant_filter(self, query: dict[str, Any]) -> dict[str, Any]:
        """Add tenant_id filter to query. Raises if query already has conflicting tenant_id."""
        if "tenant_id" in query:
            if query["tenant_id"] != self._tenant_id:
                raise TenantIsolationError(
                    f"Query tenant_id '{query['tenant_id']}' does not match repository tenant_id '{self._tenant_id}'"
                )
        return {**query, "tenant_id": self._tenant_id}

    async def create_indexes(self) -> None:
        """Create collection indexes."""
        if self.indexes:
            try:
                await self._collection.create_indexes(self.indexes)
                logger.info("Indexes created", collection=self.collection_name, tenant_id=self._tenant_id)
            except OperationFailure as e:
                logger.error("Failed to create indexes", collection=self.collection_name, error=str(e))
                raise DatabaseError(f"Failed to create indexes: {e}") from e

    async def find_one(self, query: dict[str, Any], projection: dict[str, Any] | None = None) -> dict[str, Any] | None:
        """Find single document with tenant isolation."""
        filtered_query = self._add_tenant_filter(query)
        return await self._collection.find_one(filtered_query, projection=projection)

    async def find_many(
        self,
        query: dict[str, Any],
        projection: dict[str, Any] | None = None,
        sort: list[tuple[str, int]] | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Find multiple documents with tenant isolation."""
        filtered_query = self._add_tenant_filter(query)
        cursor = self._collection.find(filtered_query, projection=projection)
        if sort:
            cursor = cursor.sort(sort)
        if skip:
            cursor = cursor.skip(skip)
        if limit:
            cursor = cursor.limit(limit)
        return await cursor.to_list(length=limit)

    async def count(self, query: dict[str, Any]) -> int:
        """Count documents with tenant isolation."""
        filtered_query = self._add_tenant_filter(query)
        return await self._collection.count_documents(filtered_query)

    async def insert_one(self, document: dict[str, Any]) -> str:
        """Insert document with tenant_id."""
        document = {**document, "tenant_id": self._tenant_id, "created_at": datetime.now(UTC)}
        try:
            result = await self._collection.insert_one(document)
            return str(result.inserted_id)
        except DuplicateKeyError as e:
            raise DatabaseError(f"Duplicate key error: {e}") from e

    async def insert_many(self, documents: list[dict[str, Any]]) -> list[str]:
        """Insert multiple documents with tenant_id."""
        if not documents:
            return []
        docs_with_tenant = [
            {**doc, "tenant_id": self._tenant_id, "created_at": datetime.now(UTC)}
            for doc in documents
        ]
        try:
            result = await self._collection.insert_many(docs_with_tenant)
            return [str(id_) for id_ in result.inserted_ids]
        except DuplicateKeyError as e:
            raise DatabaseError(f"Duplicate key error: {e}") from e

    async def update_one(
        self,
        query: dict[str, Any],
        update: dict[str, Any],
        upsert: bool = False,
    ) -> bool:
        """Update single document with tenant isolation."""
        filtered_query = self._add_tenant_filter(query)
        update_doc = {"$set": {**update, "updated_at": datetime.now(UTC)}}
        result = await self._collection.update_one(filtered_query, update_doc, upsert=upsert)
        return result.modified_count > 0 or (upsert and result.upserted_id is not None)

    async def update_many(self, query: dict[str, Any], update: dict[str, Any]) -> int:
        """Update multiple documents with tenant isolation."""
        filtered_query = self._add_tenant_filter(query)
        update_doc = {"$set": {**update, "updated_at": datetime.now(UTC)}}
        result = await self._collection.update_many(filtered_query, update_doc)
        return result.modified_count

    async def delete_one(self, query: dict[str, Any]) -> bool:
        """Delete single document with tenant isolation."""
        filtered_query = self._add_tenant_filter(query)
        result = await self._collection.delete_one(filtered_query)
        return result.deleted_count > 0

    async def delete_many(self, query: dict[str, Any]) -> int:
        """Delete multiple documents with tenant isolation."""
        filtered_query = self._add_tenant_filter(query)
        result = await self._collection.delete_many(filtered_query)
        return result.deleted_count

    async def aggregate(self, pipeline: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Run aggregation pipeline with tenant isolation injected at first $match."""
        # Inject tenant_id at the beginning of pipeline
        tenant_match = {"$match": {"tenant_id": self._tenant_id}}
        full_pipeline = [tenant_match, *pipeline]
        cursor = self._collection.aggregate(full_pipeline)
        return await cursor.to_list(length=None)


class DocumentRepository(BaseRepository):
    """Repository for documents collection."""

    collection_name = COLLECTION_DOCUMENTS
    indexes = [
        IndexModel([("tenant_id", ASCENDING), ("status", ASCENDING)]),
        IndexModel([("tenant_id", ASCENDING), ("created_at", DESCENDING)]),
        IndexModel([("tenant_id", ASCENDING), ("source_type", ASCENDING)]),
        IndexModel([("tenant_id", ASCENDING), ("metadata.tags", ASCENDING)]),
        IndexModel([("content_hash", ASCENDING)], unique=True, sparse=True),
    ]

    async def create_document(
        self,
        filename: str,
        source_type: str,
        content_hash: str,
        metadata: dict[str, Any] | None = None,
        status: str = "pending",
    ) -> str:
        """Create a new document record."""
        doc = {
            "filename": filename,
            "source_type": source_type,
            "content_hash": content_hash,
            "metadata": metadata or {},
            "status": status,
            "chunk_count": 0,
            "token_count": 0,
            "error": None,
        }
        return await self.insert_one(doc)

    async def get_document(self, document_id: str) -> dict[str, Any] | None:
        """Get document by ID."""
        from bson import ObjectId
        return await self.find_one({"_id": ObjectId(document_id)})

    async def update_status(self, document_id: str, status: str, error: str | None = None) -> bool:
        """Update document processing status."""
        from bson import ObjectId
        update = {"status": status}
        if error:
            update["error"] = error
        return await self.update_one({"_id": ObjectId(document_id)}, update)

    async def update_stats(self, document_id: str, chunk_count: int, token_count: int) -> bool:
        """Update document chunk and token counts."""
        from bson import ObjectId
        return await self.update_one(
            {"_id": ObjectId(document_id)},
            {"chunk_count": chunk_count, "token_count": token_count},
        )

    async def list_documents(
        self,
        status: str | None = None,
        source_type: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """List documents with optional filters."""
        query = {}
        if status:
            query["status"] = status
        if source_type:
            query["source_type"] = source_type
        return await self.find_many(
            query,
            sort=[("created_at", DESCENDING)],
            skip=skip,
            limit=limit,
        )

    async def get_by_content_hash(self, content_hash: str) -> dict[str, Any] | None:
        """Get document by content hash (for deduplication)."""
        return await self.find_one({"content_hash": content_hash})


class ChunkRepository(BaseRepository):
    """Repository for chunks collection with vector search support."""

    collection_name = COLLECTION_CHUNKS
    indexes = [
        IndexModel([("tenant_id", ASCENDING), ("document_id", ASCENDING)]),
        IndexModel([("tenant_id", ASCENDING), ("document_id", ASCENDING), ("chunk_index", ASCENDING)]),
        IndexModel([("tenant_id", ASCENDING), ("embedding_model", ASCENDING)]),
        # Vector search index created separately via create_indexes.py
    ]

    async def create_chunks(
        self,
        document_id: str,
        chunks: list[dict[str, Any]],
        embedding_model: str,
    ) -> list[str]:
        """Create multiple chunks for a document."""
        from bson import ObjectId

        docs = []
        for i, chunk in enumerate(chunks):
            doc = {
                "document_id": ObjectId(document_id),
                "chunk_index": i,
                "content": chunk["content"],
                "token_count": chunk.get("token_count", 0),
                "embedding": chunk.get("embedding"),
                "embedding_model": embedding_model,
                "metadata": chunk.get("metadata", {}),
            }
            docs.append(doc)
        return await self.insert_many(docs)

    async def get_chunks_by_document(self, document_id: str) -> list[dict[str, Any]]:
        """Get all chunks for a document."""
        from bson import ObjectId
        return await self.find_many(
            {"document_id": ObjectId(document_id)},
            sort=[("chunk_index", ASCENDING)],
        )

    async def get_chunk(self, chunk_id: str) -> dict[str, Any] | None:
        """Get chunk by ID."""
        from bson import ObjectId
        return await self.find_one({"_id": ObjectId(chunk_id)})

    async def update_embeddings(self, chunk_ids: list[str], embeddings: list[list[float]]) -> int:
        """Update embeddings for multiple chunks."""
        from bson import ObjectId

        if len(chunk_ids) != len(embeddings):
            raise ValueError("chunk_ids and embeddings must have same length")

        updated = 0
        for chunk_id, embedding in zip(chunk_ids, embeddings, strict=False):
            result = await self.update_one(
                {"_id": ObjectId(chunk_id)},
                {"embedding": embedding},
            )
            if result:
                updated += 1
        return updated

    async def vector_search(
        self,
        query_embedding: list[float],
        embedding_model: str,
        top_k: int = 20,
        filter_query: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Perform vector search using MongoDB Atlas Vector Search.
        Requires vector search index to be created.
        """
        pipeline: list[dict[str, Any]] = [
            {
                "$vectorSearch": {
                    "index": "vector_index",
                    "path": "embedding",
                    "queryVector": query_embedding,
                    "numCandidates": top_k * 10,
                    "limit": top_k,
                    "filter": self._add_tenant_filter(filter_query or {}),
                }
            },
            {
                "$project": {
                    "content": 1,
                    "document_id": 1,
                    "chunk_index": 1,
                    "metadata": 1,
                    "embedding_model": 1,
                    "score": {"$meta": "vectorSearchScore"},
                }
            },
        ]

        try:
            return await self.aggregate(pipeline)
        except OperationFailure as e:
            if "vectorSearch" in str(e):
                raise DatabaseError(
                    "Vector search index not found. Run create_indexes.py first."
                ) from e
            raise

    async def text_search(
        self,
        query: str,
        top_k: int = 20,
        filter_query: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Perform full-text search using MongoDB Atlas Search.
        Requires text search index to be created.
        """
        pipeline: list[dict[str, Any]] = [
            {
                "$search": {
                    "index": "fulltext_index",
                    "text": {
                        "query": query,
                        "path": "content",
                    },
                }
            },
            {"$limit": top_k},
            {
                "$project": {
                    "content": 1,
                    "document_id": 1,
                    "chunk_index": 1,
                    "metadata": 1,
                    "embedding_model": 1,
                    "score": {"$meta": "searchScore"},
                }
            },
        ]

        try:
            return await self.aggregate(pipeline)
        except OperationFailure as e:
            if "search" in str(e).lower():
                raise DatabaseError(
                    "Full-text search index not found. Run create_indexes.py first."
                ) from e
            raise


class SessionRepository(BaseRepository):
    """Repository for conversation sessions."""

    collection_name = COLLECTION_SESSIONS
    indexes = [
        IndexModel([("tenant_id", ASCENDING), ("user_id", ASCENDING), ("updated_at", DESCENDING)]),
        IndexModel([("tenant_id", ASCENDING), ("status", ASCENDING)]),
        IndexModel([("thread_id", ASCENDING)], unique=True),
    ]

    async def create_session(
        self,
        thread_id: str,
        user_id: str,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Create a new session."""
        doc = {
            "thread_id": thread_id,
            "user_id": user_id,
            "title": title or "New Conversation",
            "status": "active",
            "metadata": metadata or {},
            "message_count": 0,
            "last_message_at": None,
        }
        return await self.insert_one(doc)

    async def get_session(self, thread_id: str) -> dict[str, Any] | None:
        """Get session by thread_id."""
        return await self.find_one({"thread_id": thread_id})

    async def get_user_sessions(
        self,
        user_id: str,
        status: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Get sessions for a user."""
        query = {"user_id": user_id}
        if status:
            query["status"] = status
        return await self.find_many(
            query,
            sort=[("updated_at", DESCENDING)],
            skip=skip,
            limit=limit,
        )

    async def update_session(
        self,
        thread_id: str,
        update: dict[str, Any],
    ) -> bool:
        """Update session."""
        return await self.update_one({"thread_id": thread_id}, update)

    async def increment_message_count(self, thread_id: str) -> bool:
        """Increment message count and update last_message_at."""
        from datetime import UTC, datetime
        return await self.update_one(
            {"thread_id": thread_id},
            {
                "$inc": {"message_count": 1},
                "$set": {"last_message_at": datetime.now(UTC)},
            },
        )

    async def archive_session(self, thread_id: str) -> bool:
        """Archive a session."""
        return await self.update_one({"thread_id": thread_id}, {"status": "archived"})

    async def delete_session(self, thread_id: str) -> bool:
        """Delete a session (soft delete - mark as deleted)."""
        return await self.update_one({"thread_id": thread_id}, {"status": "deleted"})


def get_document_repository(database: AsyncIOMotorDatabase, tenant_id: str) -> DocumentRepository:
    """Factory for DocumentRepository."""
    return DocumentRepository(database, tenant_id)


def get_chunk_repository(database: AsyncIOMotorDatabase, tenant_id: str) -> ChunkRepository:
    """Factory for ChunkRepository."""
    return ChunkRepository(database, tenant_id)


def get_session_repository(database: AsyncIOMotorDatabase, tenant_id: str) -> SessionRepository:
    """Factory for SessionRepository."""
    return SessionRepository(database, tenant_id)
