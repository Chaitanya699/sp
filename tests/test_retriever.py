"""
Tests for NIM Sentinel Hybrid Retriever
"""

from unittest.mock import AsyncMock, patch

import pytest
from nim_sentinel.rag.retriever import HybridRetriever, RetrievalResult


class TestHybridRetriever:
    """Tests for HybridRetriever class."""

    @pytest.fixture
    def mock_chunk_repo(self):
        """Create a mock ChunkRepository."""
        repo = AsyncMock()
        repo.vector_search = AsyncMock(return_value=[])
        repo.text_search = AsyncMock(return_value=[])
        return repo

    @pytest.fixture
    def retriever(self, mock_chunk_repo):
        """Create a HybridRetriever with mocked dependencies."""
        with patch("nim_sentinel.rag.retriever.get_settings") as mock_settings:
            mock_settings.return_value.embedding_model = "nvidia/test-embedding"
            mock_settings.return_value.nvidia_api_key = "test-key"

            with patch("nim_sentinel.rag.retriever.get_model_config") as mock_model_config:
                mock_model_config.return_value.primary = "nvidia/test-reranker"

                retriever = HybridRetriever(
                    chunk_repository=mock_chunk_repo,
                    vector_top_k=10,
                    text_top_k=10,
                    final_top_k=5,
                    rrf_k=60,
                )
                return retriever

    @pytest.mark.asyncio
    async def test_retrieve_empty_results(self, retriever, mock_chunk_repo):
        """Test retrieval with no results."""
        mock_chunk_repo.vector_search.return_value = []
        mock_chunk_repo.text_search.return_value = []

        results = await retriever.retrieve(
            query="test query",
            query_embedding=[0.1] * 1024,
        )

        assert results == []

    @pytest.mark.asyncio
    async def test_retrieve_vector_only(self, retriever, mock_chunk_repo):
        """Test retrieval with only vector results."""
        mock_chunk_repo.vector_search.return_value = [
            {
                "document_id": "doc1",
                "chunk_index": 0,
                "content": "Vector result content",
                "metadata": {"tag": "test"},
                "embedding_model": "nvidia/test-embedding",
                "score": 0.95,
            }
        ]
        mock_chunk_repo.text_search.return_value = []

        with patch.object(retriever, "_get_reranker") as mock_get_reranker:
            mock_reranker = AsyncMock()
            mock_reranker.acompress_documents.return_value = [
                ("Vector result content", 0.9)
            ]
            mock_get_reranker.return_value = mock_reranker

            results = await retriever.retrieve(
                query="test query",
                query_embedding=[0.1] * 1024,
            )

            assert len(results) == 1
            assert results[0].content == "Vector result content"
            assert results[0].document_id == "doc1"
            assert results[0].chunk_index == 0
            assert results[0].source == "reranked"

    @pytest.mark.asyncio
    async def test_retrieve_text_only(self, retriever, mock_chunk_repo):
        """Test retrieval with only text results."""
        mock_chunk_repo.vector_search.return_value = []
        mock_chunk_repo.text_search.return_value = [
            {
                "document_id": "doc2",
                "chunk_index": 1,
                "content": "Text result content",
                "metadata": {"tag": "test"},
                "embedding_model": "nvidia/test-embedding",
                "score": 0.85,
            }
        ]

        with patch.object(retriever, "_get_reranker") as mock_get_reranker:
            mock_reranker = AsyncMock()
            mock_reranker.acompress_documents.return_value = [
                ("Text result content", 0.8)
            ]
            mock_get_reranker.return_value = mock_reranker

            results = await retriever.retrieve(
                query="test query",
                query_embedding=[0.1] * 1024,
            )

            assert len(results) == 1
            assert results[0].content == "Text result content"
            assert results[0].source == "reranked"

    @pytest.mark.asyncio
    async def test_retrieve_both_sources_rrf(self, retriever, mock_chunk_repo):
        """Test RRF fusion with results from both sources."""
        mock_chunk_repo.vector_search.return_value = [
            {
                "document_id": "doc1",
                "chunk_index": 0,
                "content": "Shared content",
                "metadata": {},
                "embedding_model": "nvidia/test-embedding",
                "score": 0.9,
            },
            {
                "document_id": "doc2",
                "chunk_index": 0,
                "content": "Vector only content",
                "metadata": {},
                "embedding_model": "nvidia/test-embedding",
                "score": 0.8,
            },
        ]
        mock_chunk_repo.text_search.return_value = [
            {
                "document_id": "doc1",
                "chunk_index": 0,
                "content": "Shared content",
                "metadata": {},
                "embedding_model": "nvidia/test-embedding",
                "score": 0.85,
            },
            {
                "document_id": "doc3",
                "chunk_index": 0,
                "content": "Text only content",
                "metadata": {},
                "embedding_model": "nvidia/test-embedding",
                "score": 0.75,
            },
        ]

        with patch.object(retriever, "_get_reranker") as mock_get_reranker:
            mock_reranker = AsyncMock()
            mock_reranker.acompress_documents.return_value = [
                ("Shared content", 0.95),
                ("Vector only content", 0.7),
                ("Text only content", 0.6),
            ]
            mock_get_reranker.return_value = mock_reranker

            results = await retriever.retrieve(
                query="test query",
                query_embedding=[0.1] * 1024,
            )

            # Should have 3 unique results (doc1 appears in both)
            assert len(results) == 3
            # Shared content should rank highest due to RRF boost
            assert results[0].content == "Shared content"

    @pytest.mark.asyncio
    async def test_rrf_fusion_scoring(self, retriever):
        """Test RRF fusion scoring logic."""
        vector_results = [
            {"document_id": "doc1", "chunk_index": 0, "content": "A", "metadata": {}, "embedding_model": "test", "score": 0.9},
            {"document_id": "doc2", "chunk_index": 0, "content": "B", "metadata": {}, "embedding_model": "test", "score": 0.8},
            {"document_id": "doc3", "chunk_index": 0, "content": "C", "metadata": {}, "embedding_model": "test", "score": 0.7},
        ]
        text_results = [
            {"document_id": "doc2", "chunk_index": 0, "content": "B", "metadata": {}, "embedding_model": "test", "score": 0.85},
            {"document_id": "doc1", "chunk_index": 0, "content": "A", "metadata": {}, "embedding_model": "test", "score": 0.75},
            {"document_id": "doc4", "chunk_index": 0, "content": "D", "metadata": {}, "embedding_model": "test", "score": 0.65},
        ]

        fused = retriever._rrf_fusion(vector_results, text_results)

        # doc1 and doc2 appear in both, should have higher RRF scores
        doc1_score = next(f["rrf_score"] for f in fused if f["document_id"] == "doc1" and f["chunk_index"] == 0)
        doc2_score = next(f["rrf_score"] for f in fused if f["document_id"] == "doc2" and f["chunk_index"] == 0)
        doc3_score = next(f["rrf_score"] for f in fused if f["document_id"] == "doc3" and f["chunk_index"] == 0)
        doc4_score = next(f["rrf_score"] for f in fused if f["document_id"] == "doc4" and f["chunk_index"] == 0)

        # Both in vector and text -> higher score
        assert doc1_score > doc3_score
        assert doc2_score > doc3_score
        assert doc1_score > doc4_score
        assert doc2_score > doc4_score

    @pytest.mark.asyncio
    async def test_rerank_fallback_on_error(self, retriever, mock_chunk_repo):
        """Test fallback to RRF scores when reranking fails."""
        mock_chunk_repo.vector_search.return_value = [
            {
                "document_id": "doc1",
                "chunk_index": 0,
                "content": "Content 1",
                "metadata": {},
                "embedding_model": "nvidia/test-embedding",
                "score": 0.9,
            },
            {
                "document_id": "doc2",
                "chunk_index": 0,
                "content": "Content 2",
                "metadata": {},
                "embedding_model": "nvidia/test-embedding",
                "score": 0.8,
            },
        ]
        mock_chunk_repo.text_search.return_value = []

        with patch.object(retriever, "_get_reranker") as mock_get_reranker:
            mock_reranker = AsyncMock()
            mock_reranker.acompress_documents.side_effect = Exception("Rerank failed")
            mock_get_reranker.return_value = mock_reranker

            results = await retriever.retrieve(
                query="test query",
                query_embedding=[0.1] * 1024,
            )

            assert len(results) == 2
            # Should fall back to RRF scores
            assert results[0].source == "rrf_fallback"
            assert results[1].source == "rrf_fallback"

    @pytest.mark.asyncio
    async def test_to_citation(self, retriever):
        """Test citation conversion."""
        result = RetrievalResult(
            content="This is a long piece of content that should be truncated in the citation",
            document_id="doc1",
            chunk_index=0,
            score=0.95,
            metadata={"page": 1},
            embedding_model="nvidia/test-embedding",
            source="reranked",
        )

        citation = result.to_citation()

        assert citation["document_id"] == "doc1"
        assert citation["chunk_index"] == 0
        assert citation["score"] == 0.95
        assert citation["metadata"] == {"page": 1}
        assert len(citation["content"]) <= 500

    @pytest.mark.asyncio
    async def test_retrieve_with_filter(self, retriever, mock_chunk_repo):
        """Test retrieval with filter query."""
        mock_chunk_repo.vector_search.return_value = []
        mock_chunk_repo.text_search.return_value = []

        await retriever.retrieve(
            query="test query",
            query_embedding=[0.1] * 1024,
            filter_query={"metadata.tags": "important"},
        )

        # Verify filter was passed to both searches
        mock_chunk_repo.vector_search.assert_called_once()
        call_args = mock_chunk_repo.vector_search.call_args
        assert call_args.kwargs["filter_query"] == {"metadata.tags": "important"}

        mock_chunk_repo.text_search.assert_called_once()
        call_args = mock_chunk_repo.text_search.call_args
        assert call_args.kwargs["filter_query"] == {"metadata.tags": "important"}

    @pytest.mark.asyncio
    async def test_final_top_k_limit(self, retriever, mock_chunk_repo):
        """Test that final results are limited to final_top_k."""
        # Create many results
        mock_chunk_repo.vector_search.return_value = [
            {
                "document_id": f"doc{i}",
                "chunk_index": 0,
                "content": f"Content {i}",
                "metadata": {},
                "embedding_model": "nvidia/test-embedding",
                "score": 0.9 - i * 0.01,
            }
            for i in range(20)
        ]
        mock_chunk_repo.text_search.return_value = []

        with patch.object(retriever, "_get_reranker") as mock_get_reranker:
            mock_reranker = AsyncMock()
            mock_reranker.acompress_documents.return_value = [
                (f"Content {i}", 0.9 - i * 0.01) for i in range(20)
            ]
            mock_get_reranker.return_value = mock_reranker

            results = await retriever.retrieve(
                query="test query",
                query_embedding=[0.1] * 1024,
            )

            # Should be limited to final_top_k (5)
            assert len(results) == 5


class TestRetrievalResult:
    """Tests for RetrievalResult dataclass."""

    def test_to_citation_truncates_content(self):
        """Test that citation truncates long content."""
        long_content = "x" * 1000
        result = RetrievalResult(
            content=long_content,
            document_id="doc1",
            chunk_index=0,
            score=0.9,
            metadata={},
            embedding_model="test",
            source="vector",
        )

        citation = result.to_citation()
        assert len(citation["content"]) == 500

    def test_to_citation_preserves_metadata(self):
        """Test that citation preserves metadata."""
        result = RetrievalResult(
            content="test",
            document_id="doc1",
            chunk_index=0,
            score=0.9,
            metadata={"page": 5, "section": "intro"},
            embedding_model="test",
            source="vector",
        )

        citation = result.to_citation()
        assert citation["metadata"] == {"page": 5, "section": "intro"}
