#!/usr/bin/env python3
"""
Smoke test: upload document -> ingest -> query with citations.
Run with local MongoDB and mock embeddings (no NVIDIA API needed).
"""

import asyncio
import os
import sys
import numpy as np
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from httpx import AsyncClient, ASGITransport
from nim_sentinel.main import app
from nim_sentinel.core.security import create_access_token
from datetime import timedelta


# Word-based mock embedding that preserves semantic similarity
class WordEmbeddingMock:
    """Mock embedding that uses word vectors for semantic similarity."""

    def __init__(self, dim=1024):
        self.dim = dim
        self.word_vectors = {}

    def get_word_vector(self, word):
        if word not in self.word_vectors:
            np.random.seed(hash(word) % 2**32)
            vec = np.random.randn(self.dim).astype(np.float32)
            vec = vec / np.linalg.norm(vec)
            self.word_vectors[word] = vec
        return self.word_vectors[word]

    def embed(self, text):
        words = text.lower().split()
        if not words:
            return np.zeros(self.dim, dtype=np.float32)

        # Average word vectors
        vecs = [self.get_word_vector(w) for w in words]
        result = np.mean(vecs, axis=0)
        norm = np.linalg.norm(result)
        if norm > 0:
            result = result / norm
        return result.tolist()


# Global instance for consistency across calls
_word_embedder = WordEmbeddingMock(2048)


def mock_embed(text: str) -> list[float]:
    """Generate deterministic mock embedding for testing using word vectors."""
    return _word_embedder.embed(text)


class MockEmbeddingClient:
    """Mock embedding client for testing."""

    def __init__(self, *args, **kwargs):
        print(f"MockEmbeddingClient created with args={args}, kwargs={kwargs}")
        pass

    async def embed_texts(self, texts, model=None):
        print(f"embed_texts called with {len(texts)} texts, model={model}")
        from nim_sentinel.rag.ingestion.embedder import EmbeddingResult
        embeddings = [mock_embed(t) for t in texts]
        print(f"Generated {len(embeddings)} embeddings")
        return EmbeddingResult(
            embeddings=embeddings,
            token_count=sum(len(t.split()) for t in texts),
            model="mock-embedding",
            latency_ms=1.0,
        )

    async def embed_query(self, text, model=None):
        print(f"embed_query called with text={text[:50]}, model={model}")
        return mock_embed(text)


async def test_smoke():
    """Run smoke test with mock embeddings."""
    # Patch the embedding client to use mock for both ingestion and query
    import nim_sentinel.rag.ingestion.embedder as embedder_module
    import nim_sentinel.rag.ingestion.pipeline as pipeline_module

    # Store originals
    original_get_embedding_client = embedder_module.get_embedding_client
    original_EmbeddingClient = embedder_module.EmbeddingClient

    # Patch embedder module
    async def mock_get_embedding_client():
        print("mock_get_embedding_client called")
        return MockEmbeddingClient()

    embedder_module.get_embedding_client = mock_get_embedding_client
    embedder_module.EmbeddingClient = MockEmbeddingClient

    # Also patch the pipeline's embedding_client property
    original_embedding_client_prop = pipeline_module.IngestionPipeline.embedding_client

    @property
    def mock_embedding_client_prop(self):
        print("mock_embedding_client_prop accessed")
        if self._embedding_client is None:
            self._embedding_client = MockEmbeddingClient()
        return self._embedding_client

    pipeline_module.IngestionPipeline.embedding_client = mock_embedding_client_prop

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create dev token
        token = create_access_token(
            user_id="test_user",
            username="test",
            roles=["analyst"],
            tenant_id="test_tenant",
            expires_delta=timedelta(hours=1)
        )
        print(f"Token: {token[:20]}...{token[-10:]}")

        # Test document upload with unique content (include timestamp)
        print("\n=== Testing Document Upload ===")
        unique_id = str(int(time.time() * 1000))
        test_content = f"""NIM Sentinel Smoke Test Document - Unique ID: {unique_id}
This is a test document for the smoke test to verify the RAG pipeline works.
It contains unique content about NIM Sentinel enterprise multi-agent RAG system.
The system provides document ingestion, hybrid retrieval with vector and full-text search,
and citation-backed query responses with tenant isolation and JWT authentication.
Test timestamp: {time.ctime()}""".encode()

        response = await client.post(
            "/v1/documents",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": (f"test_nim_sentinel_{unique_id}.txt", test_content, "text/plain")},
        )

        print(f"Upload status: {response.status_code}")
        print(f"Upload response: {response.json()}")

        if response.status_code != 201:
            print("FAIL: Document upload failed")
            return False

        doc_data = response.json()
        document_id = doc_data.get("document_id")
        print(f"Document ID: {document_id}")

        # Wait for ingestion to complete (poll status)
        print("\n=== Waiting for Ingestion ===")
        for i in range(30):  # Wait up to 30 seconds
            await asyncio.sleep(1)
            status_response = await client.get(
                f"/v1/documents/{document_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            if status_response.status_code == 200:
                status_data = status_response.json()
                status = status_data.get("status")
                print(f"  Status: {status}")
                if status in ("ready", "completed"):
                    print("Document ready!")
                    break
                elif status == "error":
                    print(f"FAIL: Ingestion error: {status_data.get('error')}")
                    return False
        else:
            print("FAIL: Ingestion timeout")
            return False

        # Test query
        print("\n=== Testing Query ===")
        query_response = await client.post(
            "/v1/query",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "query": "What is NIM Sentinel?",
                "top_k": 5,
            },
        )

        print(f"Query status: {query_response.status_code}")
        query_data = query_response.json()
        print(f"Query response: {query_data}")

        if query_response.status_code != 200:
            print("FAIL: Query failed")
            return False

        # Verify response structure
        assert "results" in query_data, "Missing results"
        assert "citations" in query_data, "Missing citations"
        assert isinstance(query_data["citations"], list), "Citations should be list"
        assert query_data["total_results"] > 0, "Should have at least one result"

        print(f"\nResults count: {query_data['total_results']}")
        print(f"Citations count: {len(query_data['citations'])}")

        for i, citation in enumerate(query_data["citations"]):
            print(f"  Citation {i+1}: doc={citation.get('document_id')}, chunk={citation.get('chunk_index')}, score={citation.get('score', 0):.4f}")

        print("\n=== SMOKE TEST PASSED ===")
        return True


if __name__ == "__main__":
    success = asyncio.run(test_smoke())
    sys.exit(0 if success else 1)