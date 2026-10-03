"""
Unit tests for MongoDB client and repositories.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bson import ObjectId
from nim_sentinel.core.errors import MongoConnectionError, TenantIsolationError
from nim_sentinel.db.client import MongoClient, close_mongo_client, get_mongo_client
from nim_sentinel.db.repositories import (
    BaseRepository,
    ChunkRepository,
    DocumentRepository,
    SessionRepository,
    get_chunk_repository,
    get_document_repository,
    get_session_repository,
)


class TestMongoClient:
    """Tests for MongoClient."""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings for testing."""
        with patch("nim_sentinel.db.client.get_settings") as mock:
            settings = MagicMock()
            settings.mongodb_uri = "mongodb://localhost:27017"
            settings.mongodb_local_uri = None
            settings.mongodb_database = "test_db"
            settings.mongodb_max_pool_size = 10
            settings.mongodb_min_pool_size = 1
            settings.mongodb_max_idle_time_ms = 30000
            settings.mongodb_server_selection_timeout_ms = 5000
            settings.mongodb_connect_timeout_ms = 10000
            settings.mongodb_socket_timeout_ms = 20000
            mock.return_value = settings
            yield settings

    @pytest.mark.asyncio
    async def test_connect_success(self, mock_settings):
        """Test successful connection."""
        with patch("nim_sentinel.db.client.AsyncMongoClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.admin.command = AsyncMock(return_value={"ok": 1})
            mock_client_class.return_value = mock_client

            client = MongoClient()
            await client.connect()

            assert client._connected is True
            assert client._db is not None
            mock_client.admin.command.assert_called_once_with("ping")

    @pytest.mark.asyncio
    async def test_connect_failure(self, mock_settings):
        """Test connection failure."""
        from pymongo.errors import ServerSelectionTimeoutError

        with patch("nim_sentinel.db.client.AsyncMongoClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.admin.command = AsyncMock(side_effect=ServerSelectionTimeoutError("timeout"))
            mock_client_class.return_value = mock_client

            client = MongoClient()
            with pytest.raises(MongoConnectionError):
                await client.connect()

            assert client._connected is False

    @pytest.mark.asyncio
    async def test_connect_no_uri(self, mock_settings):
        """Test connection with no URI configured."""
        mock_settings.mongodb_uri = None
        mock_settings.mongodb_local_uri = None

        client = MongoClient()
        with pytest.raises(MongoConnectionError, match="No MongoDB URI configured"):
            await client.connect()

    @pytest.mark.asyncio
    async def test_disconnect(self, mock_settings):
        """Test disconnection."""
        with patch("nim_sentinel.db.client.AsyncMongoClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.admin.command = AsyncMock(return_value={"ok": 1})
            mock_client_class.return_value = mock_client

            client = MongoClient()
            await client.connect()
            await client.disconnect()

            assert client._connected is False
            assert client._client is None
            assert client._db is None
            mock_client.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_health_check_connected(self, mock_settings):
        """Test health check when connected."""
        with patch("nim_sentinel.db.client.AsyncMongoClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.admin.command = AsyncMock(return_value={"ok": 1})
            mock_client_class.return_value = mock_client

            client = MongoClient()
            await client.connect()

            health = await client.health_check()
            assert health["healthy"] is True
            assert health["status"] == "connected"

    @pytest.mark.asyncio
    async def test_health_check_disconnected(self):
        """Test health check when disconnected."""
        client = MongoClient()
        health = await client.health_check()
        assert health["healthy"] is False
        assert health["status"] == "disconnected"

    @pytest.mark.asyncio
    async def test_database_property_not_connected(self):
        """Test database property raises when not connected."""
        client = MongoClient()
        with pytest.raises(MongoConnectionError, match="MongoDB not connected"):
            _ = client.database

    @pytest.mark.asyncio
    async def test_session_context_manager(self, mock_settings):
        """Test session context manager."""
        with patch("nim_sentinel.db.client.AsyncMongoClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.admin.command = AsyncMock(return_value={"ok": 1})
            mock_session = AsyncMock()
            mock_client.start_session = MagicMock(return_value=mock_session)
            mock_client_class.return_value = mock_client

            client = MongoClient()
            await client.connect()

            async with client.session() as session:
                # The session returned is the __aenter__ result
                assert session is not None


class TestBaseRepository:
    """Tests for BaseRepository tenant isolation."""

    @pytest.fixture
    def mock_db(self):
        """Mock database."""
        return MagicMock()

    @pytest.fixture
    def repo(self, mock_db):
        """Create a test repository."""
        class TestRepo(BaseRepository):
            collection_name = "test_collection"
            indexes = []

        return TestRepo(mock_db, "tenant_123")

    def test_tenant_id_required(self, mock_db):
        """Test that tenant_id is required."""
        class TestRepo(BaseRepository):
            collection_name = "test"
            indexes = []

        with pytest.raises(TenantIsolationError, match="tenant_id is required"):
            TestRepo(mock_db, "")

    def test_add_tenant_filter(self, repo):
        """Test tenant filter is added to query."""
        query = {"status": "active"}
        filtered = repo._add_tenant_filter(query)
        assert filtered["tenant_id"] == "tenant_123"
        assert filtered["status"] == "active"

    def test_add_tenant_filter_existing_match(self, repo):
        """Test tenant filter with matching existing tenant_id."""
        query = {"tenant_id": "tenant_123", "status": "active"}
        filtered = repo._add_tenant_filter(query)
        assert filtered["tenant_id"] == "tenant_123"

    def test_add_tenant_filter_conflict(self, repo):
        """Test tenant filter raises on conflicting tenant_id."""
        query = {"tenant_id": "tenant_456", "status": "active"}
        with pytest.raises(TenantIsolationError, match="does not match repository tenant_id"):
            repo._add_tenant_filter(query)


class TestDocumentRepository:
    """Tests for DocumentRepository."""

    @pytest.fixture
    def mock_db(self):
        """Mock database with collection."""
        db = MagicMock()
        db.__getitem__ = MagicMock(return_value=AsyncMock())
        return db

    @pytest.fixture
    def repo(self, mock_db):
        """Create DocumentRepository."""
        return DocumentRepository(mock_db, "tenant_123")

    @pytest.mark.asyncio
    async def test_create_document(self, repo):
        """Test creating a document."""
        repo._collection.insert_one = AsyncMock()
        mock_result = MagicMock()
        mock_result.inserted_id = ObjectId()
        repo._collection.insert_one.return_value = mock_result

        doc_id = await repo.create_document(
            filename="test.pdf",
            source_type="pdf",
            content_hash="abc123",
            metadata={"author": "test"},
        )

        assert doc_id is not None
        repo._collection.insert_one.assert_called_once()
        call_args = repo._collection.insert_one.call_args[0][0]
        assert call_args["filename"] == "test.pdf"
        assert call_args["tenant_id"] == "tenant_123"
        assert call_args["content_hash"] == "abc123"

    @pytest.mark.asyncio
    async def test_get_document(self, repo):
        """Test getting document by ID."""
        doc_id = str(ObjectId())
        expected_doc = {"_id": ObjectId(doc_id), "filename": "test.pdf"}
        repo._collection.find_one = AsyncMock(return_value=expected_doc)

        result = await repo.get_document(doc_id)

        assert result == expected_doc
        repo._collection.find_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_status(self, repo):
        """Test updating document status."""
        doc_id = str(ObjectId())
        repo._collection.update_one = AsyncMock()
        mock_result = MagicMock()
        mock_result.modified_count = 1
        repo._collection.update_one.return_value = mock_result

        result = await repo.update_status(doc_id, "completed", error=None)

        assert result is True
        repo._collection.update_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_stats(self, repo):
        """Test updating document stats."""
        doc_id = str(ObjectId())
        repo._collection.update_one = AsyncMock()
        mock_result = MagicMock()
        mock_result.modified_count = 1
        repo._collection.update_one.return_value = mock_result

        result = await repo.update_stats(doc_id, chunk_count=10, token_count=5000)

        assert result is True

    @pytest.mark.asyncio
    async def test_list_documents(self, repo):
        """Test listing documents."""
        expected_docs = [{"_id": ObjectId(), "filename": f"doc{i}.pdf"} for i in range(3)]
        repo._collection.find = MagicMock()
        mock_cursor = AsyncMock()
        mock_cursor.to_list = AsyncMock(return_value=expected_docs)
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.skip = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=mock_cursor)
        repo._collection.find.return_value = mock_cursor

        results = await repo.list_documents(status="completed", skip=0, limit=10)

        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_get_by_content_hash(self, repo):
        """Test getting document by content hash."""
        expected_doc = {"_id": ObjectId(), "content_hash": "abc123"}
        repo._collection.find_one = AsyncMock(return_value=expected_doc)

        result = await repo.get_by_content_hash("abc123")

        assert result == expected_doc
        # Check call was made with correct filter (order doesn't matter)
        call_args = repo._collection.find_one.call_args[0][0]
        assert call_args["tenant_id"] == "tenant_123"
        assert call_args["content_hash"] == "abc123"


class TestChunkRepository:
    """Tests for ChunkRepository."""

    @pytest.fixture
    def mock_db(self):
        """Mock database with collection."""
        db = MagicMock()
        db.__getitem__ = MagicMock(return_value=AsyncMock())
        return db

    @pytest.fixture
    def repo(self, mock_db):
        """Create ChunkRepository."""
        return ChunkRepository(mock_db, "tenant_123")

    @pytest.mark.asyncio
    async def test_create_chunks(self, repo):
        """Test creating chunks."""
        repo._collection.insert_many = AsyncMock()
        mock_result = MagicMock()
        mock_result.inserted_ids = [ObjectId(), ObjectId()]
        repo._collection.insert_many.return_value = mock_result

        chunks = [
            {"content": "chunk 1", "token_count": 100},
            {"content": "chunk 2", "token_count": 150},
        ]
        doc_id = str(ObjectId())

        result = await repo.create_chunks(doc_id, chunks, "nvidia/nv-embedqa-e5-v5")

        assert len(result) == 2
        repo._collection.insert_many.assert_called_once()
        call_args = repo._collection.insert_many.call_args[0][0]
        assert len(call_args) == 2
        assert call_args[0]["document_id"] == ObjectId(doc_id)
        assert call_args[0]["chunk_index"] == 0
        assert call_args[0]["embedding_model"] == "nvidia/nv-embedqa-e5-v5"

    @pytest.mark.asyncio
    async def test_get_chunks_by_document(self, repo):
        """Test getting chunks by document."""
        expected_chunks = [
            {"_id": ObjectId(), "chunk_index": 0, "content": "chunk 1"},
            {"_id": ObjectId(), "chunk_index": 1, "content": "chunk 2"},
        ]
        mock_cursor = AsyncMock()
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.skip = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=mock_cursor)
        mock_cursor.to_list = AsyncMock(return_value=expected_chunks)
        repo._collection.find = MagicMock(return_value=mock_cursor)

        doc_id = str(ObjectId())
        results = await repo.get_chunks_by_document(doc_id)

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_update_embeddings(self, repo):
        """Test updating embeddings."""
        repo._collection.update_one = AsyncMock()
        mock_result = MagicMock()
        mock_result.modified_count = 1
        repo._collection.update_one.return_value = mock_result

        chunk_ids = [str(ObjectId()), str(ObjectId())]
        embeddings = [[0.1] * 1024, [0.2] * 1024]

        updated = await repo.update_embeddings(chunk_ids, embeddings)

        assert updated == 2
        assert repo._collection.update_one.call_count == 2

    @pytest.mark.asyncio
    async def test_update_embeddings_length_mismatch(self, repo):
        """Test update_embeddings with length mismatch."""
        chunk_ids = [str(ObjectId())]
        embeddings = [[0.1] * 1024, [0.2] * 1024]

        with pytest.raises(ValueError, match="same length"):
            await repo.update_embeddings(chunk_ids, embeddings)

    @pytest.mark.asyncio
    async def test_vector_search(self, repo):
        """Test vector search."""
        expected_results = [
            {"_id": ObjectId(), "content": "result 1", "score": 0.95},
            {"_id": ObjectId(), "content": "result 2", "score": 0.85},
        ]
        mock_cursor = AsyncMock()
        mock_cursor.to_list = AsyncMock(return_value=expected_results)
        repo._collection.aggregate = AsyncMock(return_value=mock_cursor)

        query_embedding = [0.1] * 1024
        results = await repo.vector_search(query_embedding, "nvidia/nv-embedqa-e5-v5", top_k=5)

        assert len(results) == 2
        repo._collection.aggregate.assert_called_once()

    @pytest.mark.asyncio
    async def test_text_search(self, repo):
        """Test text search."""
        expected_results = [
            {"_id": ObjectId(), "content": "result 1", "score": 0.95},
        ]
        mock_cursor = AsyncMock()
        mock_cursor.to_list = AsyncMock(return_value=expected_results)
        repo._collection.aggregate = AsyncMock(return_value=mock_cursor)

        results = await repo.text_search("test query", top_k=5)

        assert len(results) == 1
        repo._collection.aggregate.assert_called_once()


class TestSessionRepository:
    """Tests for SessionRepository."""

    @pytest.fixture
    def mock_db(self):
        """Mock database with collection."""
        db = MagicMock()
        db.__getitem__ = MagicMock(return_value=AsyncMock())
        return db

    @pytest.fixture
    def repo(self, mock_db):
        """Create SessionRepository."""
        return SessionRepository(mock_db, "tenant_123")

    @pytest.mark.asyncio
    async def test_create_session(self, repo):
        """Test creating a session."""
        repo._collection.insert_one = AsyncMock()
        mock_result = MagicMock()
        mock_result.inserted_id = ObjectId()
        repo._collection.insert_one.return_value = mock_result

        session_id = await repo.create_session(
            thread_id="thread_123",
            user_id="user_456",
            title="Test Session",
        )

        assert session_id is not None
        repo._collection.insert_one.assert_called_once()
        call_args = repo._collection.insert_one.call_args[0][0]
        assert call_args["thread_id"] == "thread_123"
        assert call_args["user_id"] == "user_456"
        assert call_args["tenant_id"] == "tenant_123"

    @pytest.mark.asyncio
    async def test_get_session(self, repo):
        """Test getting session by thread_id."""
        expected_session = {"_id": ObjectId(), "thread_id": "thread_123"}
        repo._collection.find_one = AsyncMock(return_value=expected_session)

        result = await repo.get_session("thread_123")

        assert result == expected_session

    @pytest.mark.asyncio
    async def test_get_user_sessions(self, repo):
        """Test getting user sessions."""
        expected_sessions = [
            {"_id": ObjectId(), "thread_id": f"thread_{i}"} for i in range(3)
        ]
        repo._collection.find = MagicMock()
        mock_cursor = AsyncMock()
        mock_cursor.to_list = AsyncMock(return_value=expected_sessions)
        mock_cursor.sort = MagicMock(return_value=mock_cursor)
        mock_cursor.skip = MagicMock(return_value=mock_cursor)
        mock_cursor.limit = MagicMock(return_value=mock_cursor)
        repo._collection.find.return_value = mock_cursor

        results = await repo.get_user_sessions("user_456", status="active")

        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_increment_message_count(self, repo):
        """Test incrementing message count."""
        repo._collection.update_one = AsyncMock()
        mock_result = MagicMock()
        mock_result.modified_count = 1
        repo._collection.update_one.return_value = mock_result

        result = await repo.increment_message_count("thread_123")

        assert result is True
        repo._collection.update_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_archive_session(self, repo):
        """Test archiving session."""
        repo._collection.update_one = AsyncMock()
        mock_result = MagicMock()
        mock_result.modified_count = 1
        repo._collection.update_one.return_value = mock_result

        result = await repo.archive_session("thread_123")

        assert result is True


class TestRepositoryFactories:
    """Tests for repository factory functions."""

    @pytest.fixture
    def mock_db(self):
        """Mock database."""
        db = MagicMock()
        db.__getitem__ = MagicMock(return_value=AsyncMock())
        return db

    def test_get_document_repository(self, mock_db):
        """Test document repository factory."""
        repo = get_document_repository(mock_db, "tenant_123")
        assert isinstance(repo, DocumentRepository)
        assert repo.tenant_id == "tenant_123"

    def test_get_chunk_repository(self, mock_db):
        """Test chunk repository factory."""
        repo = get_chunk_repository(mock_db, "tenant_123")
        assert isinstance(repo, ChunkRepository)
        assert repo.tenant_id == "tenant_123"

    def test_get_session_repository(self, mock_db):
        """Test session repository factory."""
        repo = get_session_repository(mock_db, "tenant_123")
        assert isinstance(repo, SessionRepository)
        assert repo.tenant_id == "tenant_123"


class TestGlobalClient:
    """Tests for global client functions."""

    @pytest.mark.asyncio
    async def test_get_mongo_client_singleton(self):
        """Test global client singleton."""
        with patch("nim_sentinel.db.client.MongoClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.connect = AsyncMock()
            mock_client_class.return_value = mock_client

            # Reset global
            import nim_sentinel.db.client as client_module
            client_module._mongo_client = None

            client1 = await get_mongo_client()
            client2 = await get_mongo_client()

            assert client1 is client2
            mock_client.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_mongo_client(self):
        """Test closing global client."""
        import nim_sentinel.db.client as client_module

        mock_client = AsyncMock()
        mock_client.disconnect = AsyncMock()
        client_module._mongo_client = mock_client

        await close_mongo_client()

        mock_client.disconnect.assert_called_once()
        assert client_module._mongo_client is None
