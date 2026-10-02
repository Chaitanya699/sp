"""
NIM Sentinel Database Module

MongoDB async client and repositories with tenant isolation.
"""

from nim_sentinel.db.client import (
    MongoClient,
    close_mongo_client,
    get_mongo_client,
    mongo_session,
)
from nim_sentinel.db.repositories import (
    ChunkRepository,
    DocumentRepository,
    SessionRepository,
    get_chunk_repository,
    get_document_repository,
    get_session_repository,
)

__all__ = [
    "MongoClient",
    "get_mongo_client",
    "close_mongo_client",
    "mongo_session",
    "DocumentRepository",
    "ChunkRepository",
    "SessionRepository",
    "get_document_repository",
    "get_chunk_repository",
    "get_session_repository",
]
