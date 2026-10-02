"""
NIM Sentinel MongoDB Client

Async MongoDB client with Motor, supporting both local and Atlas connections.
Tenant isolation is enforced at the repository layer.
"""

import logging
from contextlib import asynccontextmanager
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from nim_sentinel.core.config import get_settings
from nim_sentinel.core.errors import MongoConnectionError
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

logger = logging.getLogger(__name__)


class MongoClient:
    """
    Async MongoDB client wrapper with connection pooling and health checks.
    Supports both local (MONGODB_LOCAL_URI) and Atlas (MONGODB_URI) connections.
    """

    def __init__(self) -> None:
        self._client: AsyncIOMotorClient | None = None
        self._db: AsyncIOMotorDatabase | None = None
        self._connected = False

    async def connect(self) -> None:
        """Establish connection to MongoDB."""
        if self._connected:
            return

        settings = get_settings()

        # Prefer Atlas URI, fallback to local
        uri = settings.mongodb_uri or settings.mongodb_local_uri
        if not uri:
            raise MongoConnectionError(
                "No MongoDB URI configured. Set MONGODB_URI or MONGODB_LOCAL_URI.",
                {"reason": "No MongoDB URI configured. Set MONGODB_URI or MONGODB_LOCAL_URI."}
            )

        try:
            self._client = AsyncIOMotorClient(
                uri,
                maxPoolSize=settings.mongodb_max_pool_size,
                minPoolSize=settings.mongodb_min_pool_size,
                maxIdleTimeMS=settings.mongodb_max_idle_time_ms,
                serverSelectionTimeoutMS=settings.mongodb_server_selection_timeout_ms,
                connectTimeoutMS=settings.mongodb_connect_timeout_ms,
                socketTimeoutMS=settings.mongodb_socket_timeout_ms,
            )

            # Test connection
            await self._client.admin.command("ping")

            self._db = self._client[settings.mongodb_database]
            self._connected = True
            logger.info("MongoDB connected", database=settings.mongodb_database)

        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.error("MongoDB connection failed: %s", e)
            raise MongoConnectionError(
                f"Failed to connect to MongoDB: {e}",
                {"reason": f"Failed to connect to MongoDB: {e}"}
            ) from e

    async def disconnect(self) -> None:
        """Close MongoDB connection."""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            self._connected = False
            logger.info("MongoDB disconnected")

    @property
    def database(self) -> AsyncIOMotorDatabase:
        """Get the database instance."""
        if not self._connected or self._db is None:
            raise MongoConnectionError(
                "MongoDB not connected. Call connect() first.",
                {"reason": "MongoDB not connected. Call connect() first."}
            )
        return self._db

    @property
    def client(self) -> AsyncIOMotorClient:
        """Get the raw Motor client."""
        if not self._connected or self._client is None:
            raise MongoConnectionError(
                "MongoDB not connected. Call connect() first.",
                {"reason": "MongoDB not connected. Call connect() first."}
            )
        return self._client

    async def health_check(self) -> dict[str, Any]:
        """Perform health check."""
        if not self._connected:
            return {"status": "disconnected", "healthy": False}

        try:
            await self._client.admin.command("ping")
            return {"status": "connected", "healthy": True}
        except Exception as e:
            logger.error("MongoDB health check failed", error=str(e))
            return {"status": "error", "healthy": False, "error": str(e)}

    @asynccontextmanager
    async def session(self):
        """Create a client session for transactions."""
        if not self._connected:
            raise MongoConnectionError(
                "MongoDB not connected",
                {"reason": "MongoDB not connected"}
            )
        async with await self._client.start_session() as session:
            yield session


# Global client instance
_mongo_client: MongoClient | None = None


async def get_mongo_client() -> MongoClient:
    """Get the global MongoDB client instance."""
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = MongoClient()
        await _mongo_client.connect()
    return _mongo_client


async def close_mongo_client() -> None:
    """Close the global MongoDB client."""
    global _mongo_client
    if _mongo_client:
        await _mongo_client.disconnect()
        _mongo_client = None


@asynccontextmanager
async def mongo_session():
    """Context manager for MongoDB session."""
    client = await get_mongo_client()
    async with client.session() as session:
        yield session
