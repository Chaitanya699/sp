"""
Tests for NIM Sentinel Graph RAG Subgraph Module (B3)
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from nim_sentinel.graph.state import AgentState
from nim_sentinel.graph.subgraphs.rag import generate_node, rag_subgraph, retrieve_node


class TestRetrieveNode:
    """Tests for retrieve_node function."""

    @pytest.mark.asyncio
    async def test_retrieve_node_calls_retriever(self):
        """Test that retrieve_node calls the hybrid retriever."""
        with (
            patch("nim_sentinel.graph.subgraphs.rag.get_embedding_client") as mock_get_embedding,
            patch("nim_sentinel.graph.subgraphs.rag.get_database") as mock_get_db,
            patch("nim_sentinel.graph.subgraphs.rag.get_chunk_repository") as mock_get_chunk_repo,
            patch("nim_sentinel.graph.subgraphs.rag.get_hybrid_retriever") as mock_get_retriever,
        ):
            # Mock embedding client
            mock_embedding_client = AsyncMock()
            mock_embedding_client.embed_query = AsyncMock(return_value=[0.1] * 2048)
            mock_get_embedding.return_value = mock_embedding_client

            # Mock database and chunk repo
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            mock_chunk_repo = MagicMock()
            mock_get_chunk_repo.return_value = mock_chunk_repo

            # Mock retriever
            mock_retriever = AsyncMock()
            mock_retriever.retrieve = AsyncMock(
                return_value=[
                    MagicMock(
                        content="Test content 1",
                        score=0.9,
                        metadata={"document_id": "doc1", "chunk_id": "chunk1", "chunk_index": 0},
                        to_citation=lambda: {
                            "document_id": "doc1",
                            "chunk_index": 0,
                            "content": "Test content 1",
                            "score": 0.9,
                        },
                    ),
                    MagicMock(
                        content="Test content 2",
                        score=0.8,
                        metadata={"document_id": "doc2", "chunk_id": "chunk2", "chunk_index": 1},
                        to_citation=lambda: {
                            "document_id": "doc2",
                            "chunk_index": 1,
                            "content": "Test content 2",
                            "score": 0.8,
                        },
                    ),
                ]
            )
            mock_get_retriever.return_value = mock_retriever

            state = AgentState(
                query="What is NIM Sentinel?",
                tenant_id="tenant_1",
                user_id="user_1",
                session_id="session_1",
            )
            result = await retrieve_node(state)

            assert result.retrieval_results is not None
            assert len(result.retrieval_results) == 2
            assert result.retrieval_results[0].content == "Test content 1"
            assert result.retrieval_results[0].score == 0.9
            assert result.retrieval_results[0].metadata["document_id"] == "doc1"
            assert len(result.citations) == 2

    @pytest.mark.asyncio
    async def test_retrieve_node_empty_results(self):
        """Test retrieve_node with empty results."""
        with (
            patch("nim_sentinel.graph.subgraphs.rag.get_embedding_client") as mock_get_embedding,
            patch("nim_sentinel.graph.subgraphs.rag.get_database") as mock_get_db,
            patch("nim_sentinel.graph.subgraphs.rag.get_chunk_repository") as mock_get_chunk_repo,
            patch("nim_sentinel.graph.subgraphs.rag.get_hybrid_retriever") as mock_get_retriever,
        ):
            # Mock embedding client
            mock_embedding_client = AsyncMock()
            mock_embedding_client.embed_query = AsyncMock(return_value=[0.1] * 2048)
            mock_get_embedding.return_value = mock_embedding_client

            # Mock database and chunk repo
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            mock_chunk_repo = MagicMock()
            mock_get_chunk_repo.return_value = mock_chunk_repo

            # Mock retriever with empty results
            mock_retriever = AsyncMock()
            mock_retriever.retrieve = AsyncMock(return_value=[])
            mock_get_retriever.return_value = mock_retriever

            state = AgentState(
                query="Unknown query",
                tenant_id="tenant_1",
                user_id="user_1",
                session_id="session_1",
            )
            result = await retrieve_node(state)

            assert result.retrieval_results == []
            assert result.citations == []


class TestGenerateNode:
    """Tests for generate_node function."""

    @pytest.mark.asyncio
    async def test_generate_node_with_results(self):
        """Test generate_node with retrieval results."""
        with (
            patch("nim_sentinel.llm.model_registry.get_model_registry") as mock_get_registry,
            patch("nim_sentinel.core.config.get_settings") as mock_settings,
            patch("nim_sentinel.core.config.get_model_config") as mock_model_config,
        ):
            # Mock model registry
            mock_registry = AsyncMock()
            mock_registry.call_with_retry_and_fallback = AsyncMock(
                return_value="NIM Sentinel is an enterprise RAG system."
            )
            mock_get_registry.return_value = mock_registry

            mock_settings.return_value.nvidia_api_key = "test-key"
            mock_model_config.return_value.primary = "test-model"
            mock_model_config.return_value.temperature = 0.1
            mock_model_config.return_value.max_tokens = 100
            mock_model_config.return_value.timeout_seconds = 30

            # Create mock retrieval results
            mock_results = [
                MagicMock(
                    content="NIM Sentinel is an enterprise multi-agent RAG system.",
                    score=0.9,
                    metadata={"document_id": "doc1", "chunk_id": "chunk1", "chunk_index": 0},
                ),
                MagicMock(
                    content="It uses MongoDB Atlas for vector storage.",
                    score=0.8,
                    metadata={"document_id": "doc2", "chunk_id": "chunk2", "chunk_index": 1},
                ),
            ]

            state = AgentState(
                query="What is NIM Sentinel?",
                tenant_id="tenant_1",
                user_id="user_1",
                session_id="session_1",
                retrieval_results=mock_results,
            )
            result = await generate_node(state)

            assert result.answer == "NIM Sentinel is an enterprise RAG system."
            # generate_node doesn't create citations - that's done in retrieve_node
            # but it should calculate confidence from retrieval scores
            assert result.confidence > 0
            assert result.needs_critique is True

    @pytest.mark.asyncio
    async def test_generate_node_no_results(self):
        """Test generate_node with no retrieval results."""
        state = AgentState(
            query="Unknown query",
            tenant_id="tenant_1",
            user_id="user_1",
            session_id="session_1",
            retrieval_results=[],
        )
        result = await generate_node(state)

        assert "couldn't find any relevant information" in result.answer.lower()
        assert result.citations == []
        assert result.confidence == 0.1
        assert result.needs_critique is False


class TestRAGSubgraph:
    """Tests for rag_subgraph function."""

    @pytest.mark.asyncio
    async def test_rag_subgraph_full_flow(self):
        """Test full RAG subgraph flow: retrieve -> generate."""
        with (
            patch("nim_sentinel.graph.subgraphs.rag.get_embedding_client") as mock_get_embedding,
            patch("nim_sentinel.graph.subgraphs.rag.get_database") as mock_get_db,
            patch("nim_sentinel.graph.subgraphs.rag.get_chunk_repository") as mock_get_chunk_repo,
            patch("nim_sentinel.graph.subgraphs.rag.get_hybrid_retriever") as mock_get_retriever,
            patch("nim_sentinel.llm.model_registry.get_model_registry") as mock_get_registry,
            patch("nim_sentinel.core.config.get_settings") as mock_settings,
            patch("nim_sentinel.core.config.get_model_config") as mock_model_config,
        ):
            # Mock embedding client
            mock_embedding_client = AsyncMock()
            mock_embedding_client.embed_query = AsyncMock(return_value=[0.1] * 2048)
            mock_get_embedding.return_value = mock_embedding_client

            # Mock database and chunk repo
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            mock_chunk_repo = MagicMock()
            mock_get_chunk_repo.return_value = mock_chunk_repo

            # Mock retriever
            mock_retriever = AsyncMock()
            mock_retriever.retrieve = AsyncMock(
                return_value=[
                    MagicMock(
                        content="NIM Sentinel is an enterprise multi-agent RAG system.",
                        score=0.9,
                        metadata={"document_id": "doc1", "chunk_id": "chunk1", "chunk_index": 0},
                        to_citation=lambda: {
                            "document_id": "doc1",
                            "chunk_index": 0,
                            "content": "NIM Sentinel is an enterprise multi-agent RAG system.",
                            "score": 0.9,
                        },
                    ),
                ]
            )
            mock_get_retriever.return_value = mock_retriever

            # Mock model registry
            mock_registry = AsyncMock()
            mock_registry.call_with_retry_and_fallback = AsyncMock(
                return_value="NIM Sentinel is an enterprise RAG system with NVIDIA NIM integration."
            )
            mock_get_registry.return_value = mock_registry

            mock_settings.return_value.nvidia_api_key = "test-key"
            mock_model_config.return_value.primary = "test-model"
            mock_model_config.return_value.temperature = 0.1
            mock_model_config.return_value.max_tokens = 100
            mock_model_config.return_value.timeout_seconds = 30

            state = AgentState(
                query="What is NIM Sentinel?",
                tenant_id="tenant_1",
                user_id="user_1",
                session_id="session_1",
            )
            result = await rag_subgraph(state)

            assert result.answer is not None
            assert len(result.answer) > 0
            assert len(result.citations) == 1
            assert result.citations[0]["document_id"] == "doc1"
            assert result.confidence > 0
