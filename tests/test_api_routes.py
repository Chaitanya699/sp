"""
Tests for API Routes - Chat Endpoints

Tests for /v1/chat and /v1/chat/stream endpoints with JWT authentication.
Uses httpx.AsyncClient with ASGITransport and mocks database calls.
"""

import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from nim_sentinel.main import app
from nim_sentinel.core.security import create_dev_token, create_access_token


def create_async_client():
    """Create async test client."""
    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture
def auth_headers():
    """Create auth headers with dev token (all permissions)."""
    token = create_dev_token(tenant_id="test_tenant", permissions=["chat", "documents:read", "documents:write", "documents:delete"])
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_read():
    """Create auth headers with read-only permissions."""
    token = create_dev_token(tenant_id="test_tenant", permissions=["documents:read", "chat"])
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_write():
    """Create auth headers with write permissions."""
    token = create_dev_token(tenant_id="test_tenant", permissions=["documents:write", "chat"])
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_no_tenant():
    """Create auth headers without tenant_id."""
    token = create_access_token(
        user_id="test_user",
        username="test",
        roles=["analyst"],
        tenant_id=None,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_chat_only():
    """Create auth headers with only chat permission."""
    token = create_dev_token(tenant_id="test_tenant", permissions=["chat"])
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_invalid():
    """Create auth headers with invalid token."""
    return {"Authorization": "Bearer invalid_token"}


@pytest.fixture(autouse=True)
def mock_database():
    """Mock database calls to avoid event loop issues."""
    with patch("nim_sentinel.api.routes.get_database") as mock_get_db:
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db

        # Mock repositories
        with patch("nim_sentinel.api.routes.get_document_repository") as mock_doc_repo, \
             patch("nim_sentinel.api.routes.get_chunk_repository") as mock_chunk_repo, \
             patch("nim_sentinel.rag.ingestion.embedder.get_embedding_client") as mock_embedding, \
             patch("nim_sentinel.api.routes.get_hybrid_retriever") as mock_retriever, \
             patch("nim_sentinel.api.routes.run_graph") as mock_run_graph, \
             patch("nim_sentinel.api.routes.get_graph_for_tenant") as mock_get_graph, \
             patch("nim_sentinel.api.routes.create_checkpointer") as mock_checkpointer:

            # Setup mock returns
            mock_doc_repo.return_value = AsyncMock()
            mock_doc_repo.return_value.get_document.return_value = None
            mock_doc_repo.return_value.get_by_content_hash.return_value = None
            mock_doc_repo.return_value.create_document.return_value = "test_doc_id"
            mock_doc_repo.return_value.update_status.return_value = None
            mock_doc_repo.return_value.update_stats.return_value = None
            mock_doc_repo.return_value.list_documents.return_value = []
            mock_doc_repo.return_value.count.return_value = 0
            mock_doc_repo.return_value.delete_one.return_value = None

            mock_chunk_repo.return_value = AsyncMock()
            mock_chunk_repo.return_value.delete_many.return_value = None

            mock_embedding.return_value = AsyncMock()
            mock_embedding.return_value.embed_query.return_value = [0.1] * 2048

            mock_retriever.return_value = AsyncMock()
            mock_retriever.return_value.retrieve.return_value = []

            mock_run_graph.return_value = MagicMock(
                answer="Test answer",
                confidence=0.9,
                citations=[],
                retrieval_results=[],
            )
            mock_get_graph.return_value = AsyncMock()
            mock_checkpointer.return_value = AsyncMock()

            yield


class TestChatEndpoints:
    """Test chat endpoints."""

    @pytest.mark.asyncio
    async def test_chat_endpoint_validation(self, auth_headers):
        """Test that /v1/chat validates request body."""
        async with create_async_client() as client:
            # Missing query
            response = await client.post(
                "/v1/chat",
                headers=auth_headers,
                json={"session_id": "test_session"}
            )
            assert response.status_code == 422

            # Missing session_id
            response = await client.post(
                "/v1/chat",
                headers=auth_headers,
                json={"query": "What is NIM Sentinel?"}
            )
            assert response.status_code == 422

            # Empty query
            response = await client.post(
                "/v1/chat",
                headers=auth_headers,
                json={"query": "", "session_id": "test_session"}
            )
            assert response.status_code == 422

            # Query too long
            response = await client.post(
                "/v1/chat",
                headers=auth_headers,
                json={"query": "x" * 10001, "session_id": "test_session"}
            )
            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_chat_stream_endpoint_validation(self, auth_headers):
        """Test that /v1/chat/stream validates request body."""
        async with create_async_client() as client:
            # Missing query
            response = await client.post(
                "/v1/chat/stream",
                headers=auth_headers,
                json={"session_id": "test_session"}
            )
            assert response.status_code == 422

            # Missing session_id
            response = await client.post(
                "/v1/chat/stream",
                headers=auth_headers,
                json={"query": "What is NIM Sentinel?"}
            )
            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_chat_stream_sse_headers(self, auth_headers):
        """Test that /v1/chat/stream returns SSE headers."""
        async with create_async_client() as client:
            response = await client.post(
                "/v1/chat/stream",
                headers=auth_headers,
                json={
                    "query": "What is NIM Sentinel?",
                    "session_id": "test_session",
                }
            )
            # Should return 200 with SSE content type
            assert response.status_code == 200
            assert "text/event-stream" in response.headers.get("content-type", "")
            assert response.headers.get("cache-control") == "no-cache"
            assert response.headers.get("connection") == "keep-alive"


class TestAgentQueryEndpoint:
    """Test /v1/agent/query endpoint."""

    @pytest.mark.asyncio
    async def test_agent_query_validation(self, auth_headers):
        async with create_async_client() as client:
            response = await client.post(
                "/v1/agent/query",
                headers=auth_headers,
                json={"session_id": "test_session"}
            )
            assert response.status_code == 422

            response = await client.post(
                "/v1/agent/query",
                headers=auth_headers,
                json={"query": "What is NIM Sentinel?"}
            )
            assert response.status_code == 422


class TestDocumentEndpoints:
    """Test document endpoints."""

    @pytest.mark.asyncio
    async def test_upload_document_validation(self, auth_headers_write):
        """Test upload validation."""
        async with create_async_client() as client:
            # No file
            response = await client.post("/v1/documents", headers=auth_headers_write)
            assert response.status_code == 422


class TestQueryEndpoint:
    """Test /v1/query endpoint."""

    @pytest.mark.asyncio
    async def test_query_validation(self, auth_headers):
        async with create_async_client() as client:
            # Missing query
            response = await client.post("/v1/query", headers=auth_headers, json={})
            assert response.status_code == 422

            # Empty query
            response = await client.post("/v1/query", headers=auth_headers, json={"query": ""})
            assert response.status_code == 422

            # Query too long
            response = await client.post("/v1/query", headers=auth_headers, json={"query": "x" * 10001})
            assert response.status_code == 422

            # Invalid top_k
            response = await client.post("/v1/query", headers=auth_headers, json={"query": "test", "top_k": 0})
            assert response.status_code == 422

            response = await client.post("/v1/query", headers=auth_headers, json={"query": "test", "top_k": 51})
            assert response.status_code == 422


class TestHealthEndpoint:
    """Test health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_check(self):
        async with create_async_client() as client:
            response = await client.get("/v1/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "nim-sentinel-api"


class TestRootEndpoint:
    """Test root endpoint."""

    @pytest.mark.asyncio
    async def test_root(self):
        async with create_async_client() as client:
            response = await client.get("/")
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "NIM Sentinel API"
            assert data["version"] == "0.1.0"
            assert data["docs"] == "/docs"
            assert data["health"] == "/v1/health"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])