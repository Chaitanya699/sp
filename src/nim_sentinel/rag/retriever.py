"""
NIM Sentinel Hybrid Retriever

Combines vector search, full-text search, and NVIDIA reranking with RRF fusion.
Supports citations and tenant isolation.
"""

import logging
from dataclasses import dataclass
from typing import Any

from langchain_nvidia_ai_endpoints import NVIDIARerank
from nim_sentinel.core.config import get_model_config, get_settings
from nim_sentinel.core.errors import ModelError
from nim_sentinel.db.repositories import ChunkRepository

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """Result of a retrieval operation with citation metadata."""

    content: str
    document_id: str
    chunk_index: int
    score: float
    metadata: dict[str, Any]
    embedding_model: str
    source: str  # "vector", "text", "reranked"

    def to_citation(self) -> dict[str, Any]:
        """Convert to citation format for responses."""
        return {
            "document_id": self.document_id,
            "chunk_index": self.chunk_index,
            "content": self.content[:500],  # Truncate for citation
            "score": self.score,
            "metadata": self.metadata,
        }


class HybridRetriever:
    """
    Hybrid retriever combining vector search, text search, and reranking.

    Pipeline:
    1. Vector search (semantic similarity)
    2. Full-text search (keyword matching)
    3. RRF fusion to combine results
    4. NVIDIA reranker for final ranking
    5. Return top-k with citations
    """

    def __init__(
        self,
        chunk_repository: ChunkRepository,
        embedding_model: str | None = None,
        rerank_model: str | None = None,
        vector_top_k: int = 50,
        text_top_k: int = 50,
        final_top_k: int = 10,
        rrf_k: int = 60,
    ) -> None:
        self.chunk_repo = chunk_repository
        self.embedding_model = embedding_model or get_settings().embedding_model
        self.rerank_model = rerank_model or get_model_config("reranker").primary
        self.vector_top_k = vector_top_k
        self.text_top_k = text_top_k
        self.final_top_k = final_top_k
        self.rrf_k = rrf_k

        self._reranker: NVIDIARerank | None = None

    async def _get_reranker(self) -> NVIDIARerank:
        """Get or create NVIDIARerank instance."""
        if self._reranker is None:
            settings = get_settings()
            api_key = settings.nvidia_api_key
            if not api_key:
                raise ModelError(
                    "NVIDIA API key not configured",
                    model_role="reranker",
                    model_id=self.rerank_model,
                )

            self._reranker = NVIDIARerank(
                model=self.rerank_model,
                api_key=api_key,
                top_n=self.final_top_k,
            )
        return self._reranker

    async def retrieve(
        self,
        query: str,
        query_embedding: list[float],
        filter_query: dict[str, Any] | None = None,
    ) -> list[RetrievalResult]:
        """
        Perform hybrid retrieval with RRF fusion and reranking.

        Args:
            query: Original query text
            query_embedding: Pre-computed query embedding
            filter_query: Additional filters (e.g., document_ids, tags)

        Returns:
            List of RetrievalResult sorted by relevance
        """
        # Step 1: Vector search
        vector_results = await self._vector_search(query_embedding, filter_query)

        # Step 2: Text search
        text_results = await self._text_search(query, filter_query)

        # Step 3: RRF fusion
        fused_results = self._rrf_fusion(vector_results, text_results)

        # Step 4: Rerank
        reranked_results = await self._rerank(query, fused_results)

        # Step 5: Convert to RetrievalResult with citations
        return self._to_retrieval_results(reranked_results)

    async def _vector_search(
        self,
        query_embedding: list[float],
        filter_query: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        """Perform vector search."""
        try:
            results = await self.chunk_repo.vector_search(
                query_embedding=query_embedding,
                embedding_model=self.embedding_model,
                top_k=self.vector_top_k,
                filter_query=filter_query,
            )
            for r in results:
                r["_source"] = "vector"
            return results
        except Exception as e:
            logger.warning("Vector search failed: %s", e)
            return []

    async def _text_search(
        self,
        query: str,
        filter_query: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        """Perform full-text search."""
        try:
            results = await self.chunk_repo.text_search(
                query=query,
                top_k=self.text_top_k,
                filter_query=filter_query,
            )
            for r in results:
                r["_source"] = "text"
            return results
        except Exception as e:
            logger.warning("Text search failed: %s", e)
            return []

    def _rrf_fusion(
        self,
        vector_results: list[dict[str, Any]],
        text_results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Reciprocal Rank Fusion (RRF) to combine search results.

        RRF score = sum(1 / (k + rank)) for each result across all sources.
        """
        # Create unique key for each chunk (document_id + chunk_index)
        def make_key(doc: dict[str, Any]) -> str:
            return f"{doc['document_id']}_{doc['chunk_index']}"

        # Track ranks for each source
        vector_ranks = {make_key(doc): i for i, doc in enumerate(vector_results)}
        text_ranks = {make_key(doc): i for i, doc in enumerate(text_results)}

        # All unique keys
        all_keys = set(vector_ranks.keys()) | set(text_ranks.keys())

        # Calculate RRF scores
        fused = []
        for key in all_keys:
            vector_rank = vector_ranks.get(key)
            text_rank = text_ranks.get(key)

            rrf_score = 0.0
            if vector_rank is not None:
                rrf_score += 1.0 / (self.rrf_k + vector_rank + 1)
            if text_rank is not None:
                rrf_score += 1.0 / (self.rrf_k + text_rank + 1)

            # Get the document (prefer vector result for embedding_model)
            doc = None
            if vector_rank is not None:
                doc = vector_results[vector_rank]
            elif text_rank is not None:
                doc = text_results[text_rank]

            if doc:
                fused.append({**doc, "rrf_score": rrf_score})

        # Sort by RRF score descending
        fused.sort(key=lambda x: x["rrf_score"], reverse=True)

        # Return top candidates for reranking (more than final_top_k for better reranking)
        return fused[: self.final_top_k * 3]

    async def _rerank(
        self,
        query: str,
        candidates: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Rerank candidates using NVIDIA reranker."""
        if not candidates:
            return []

        try:
            reranker = await self._get_reranker()

            # Prepare documents for reranking
            documents = [c["content"] for c in candidates]

            # Rerank
            rerank_results = await reranker.acompress_documents(
                documents=documents,
                query=query,
            )

            # Map reranked results back to candidates
            # rerank_results contains (doc, score) tuples
            reranked = []
            for _, (doc, score) in enumerate(rerank_results):
                # Find original candidate
                orig_idx = next(
                    (j for j, c in enumerate(candidates) if c["content"] == doc),
                    None,
                )
                if orig_idx is not None:
                    candidate = candidates[orig_idx].copy()
                    candidate["rerank_score"] = score
                    candidate["_source"] = "reranked"
                    reranked.append(candidate)

            # Sort by rerank score
            reranked.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)

            return reranked[: self.final_top_k]

        except Exception as e:
            logger.warning("Reranking failed, using RRF scores: %s", e)
            # Fallback to RRF scores
            candidates.sort(key=lambda x: x.get("rrf_score", 0), reverse=True)
            for c in candidates:
                c["_source"] = "rrf_fallback"
            return candidates[: self.final_top_k]

    def _to_retrieval_results(
        self,
        candidates: list[dict[str, Any]],
    ) -> list[RetrievalResult]:
        """Convert candidates to RetrievalResult with citation metadata."""
        results = []
        for c in candidates:
            # Use rerank_score if available, otherwise rrf_score, otherwise original score
            score = c.get("rerank_score", c.get("rrf_score", c.get("score", 0.0)))

            result = RetrievalResult(
                content=c["content"],
                document_id=str(c["document_id"]),
                chunk_index=c["chunk_index"],
                score=float(score),
                metadata=c.get("metadata", {}),
                embedding_model=c.get("embedding_model", self.embedding_model),
                source=c.get("_source", "unknown"),
            )
            results.append(result)

        return results


async def get_hybrid_retriever(
    chunk_repository: ChunkRepository,
    embedding_model: str | None = None,
    rerank_model: str | None = None,
) -> HybridRetriever:
    """Factory for HybridRetriever with default settings."""
    return HybridRetriever(
        chunk_repository=chunk_repository,
        embedding_model=embedding_model,
        rerank_model=rerank_model,
    )
