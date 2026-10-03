"""
NIM Sentinel Embedding Module

Batch async embedding using NVIDIA embeddings with rate limiting and retries.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any

from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings
from nim_sentinel.core.config import get_settings
from nim_sentinel.core.errors import ModelError, ModelRateLimitError, ModelTimeoutError

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingResult:
    """Result of embedding operation."""

    embeddings: list[list[float]]
    token_count: int
    model: str
    latency_ms: float
    errors: list[str] | None = None

    def __post_init__(self) -> None:
        if self.model is None:
            self.model = "unknown"


class EmbeddingClient:
    """Async embedding client with batching, rate limiting, and retries."""

    def __init__(
        self,
        model: str | None = None,
        batch_size: int = 32,
        max_concurrent: int = 4,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
    ) -> None:
        self.model = model
        self.batch_size = batch_size
        self.max_concurrent = max_concurrent
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay

        self._embeddings: NVIDIAEmbeddings | None = None
        self._semaphore: asyncio.Semaphore | None = None
        self._rate_limit_remaining: int | None = None
        self._rate_limit_reset: float | None = None

    async def _get_embeddings(self) -> NVIDIAEmbeddings:
        """Get or create NVIDIAEmbeddings instance."""
        if self._embeddings is None:
            settings = get_settings()
            model_id = self.model or settings.embedding_model

            # Get API key from settings
            api_key = settings.nvidia_api_key
            if not api_key:
                raise ModelError(
                    "NVIDIA API key not configured",
                    model_role="embedding",
                    model_id=model_id,
                )

            self._embeddings = NVIDIAEmbeddings(
                model=model_id,
                api_key=api_key,
                truncate="END",  # Truncate long inputs
            )

            # Initialize semaphore for concurrency control
            self._semaphore = asyncio.Semaphore(self.max_concurrent)

        return self._embeddings

    async def embed_texts(
        self,
        texts: list[str],
        model: str | None = None,
    ) -> EmbeddingResult:
        """
        Embed a list of texts with batching and retries.

        Args:
            texts: List of texts to embed
            model: Override model (optional)

        Returns:
            EmbeddingResult with embeddings and metadata
        """
        if not texts:
            return EmbeddingResult(
                embeddings=[],
                token_count=0,
                model=model or self.model or "unknown",
                latency_ms=0.0,
            )

        start_time = time.perf_counter()
        embeddings_client = await self._get_embeddings()

        # Use provided model or default
        target_model = model or self.model
        if target_model and target_model != embeddings_client.model:
            # Create new client for different model
            settings = get_settings()
            api_key = settings.nvidia_api_key
            embeddings_client = NVIDIAEmbeddings(
                model=target_model,
                api_key=api_key,
                truncate="END",
            )

        # Process in batches
        all_embeddings = []
        total_tokens = 0
        errors = []

        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            batch_embeddings, batch_tokens, batch_errors = await self._embed_batch_with_retry(
                embeddings_client, batch, target_model
            )
            all_embeddings.extend(batch_embeddings)
            total_tokens += batch_tokens
            errors.extend(batch_errors)

        latency_ms = (time.perf_counter() - start_time) * 1000

        return EmbeddingResult(
            embeddings=all_embeddings,
            token_count=total_tokens,
            model=target_model or embeddings_client.model or "unknown",
            latency_ms=latency_ms,
            errors=errors if errors else None,
        )

    async def _embed_batch_with_retry(
        self,
        client: NVIDIAEmbeddings,
        texts: list[str],
        model: str | None,
    ) -> tuple[list[list[float]], int, list[str]]:
        """Embed a batch with retry logic."""
        last_error: BaseException | None = None

        for attempt in range(self.max_retries + 1):
            try:
                return await self._embed_batch(client, texts)
            except ModelRateLimitError as e:
                last_error = e
                if attempt < self.max_retries:
                    delay = min(self.base_delay * (2**attempt), self.max_delay)
                    # Respect retry_after if provided
                    if hasattr(e, "details") and e.details.get("retry_after"):
                        delay = max(delay, e.details["retry_after"])
                    logger.warning(
                        "Rate limited, retrying in %.1fs (attempt %d/%d)",
                        delay,
                        attempt + 1,
                        self.max_retries,
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error("Max retries exceeded for rate limit")
            except ModelTimeoutError as e:
                last_error = e
                if attempt < self.max_retries:
                    delay = min(self.base_delay * (2**attempt), self.max_delay)
                    logger.warning(
                        "Timeout, retrying in %.1fs (attempt %d/%d)",
                        delay,
                        attempt + 1,
                        self.max_retries,
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error("Max retries exceeded for timeout")
            except Exception as e:
                last_error = e
                logger.error("Embedding error: %s", e)
                if attempt < self.max_retries:
                    delay = min(self.base_delay * (2**attempt), self.max_delay)
                    await asyncio.sleep(delay)
                else:
                    break

        # All retries exhausted
        error_msg = str(last_error) if last_error else "Unknown error"
        return [], 0, [f"Batch failed after {self.max_retries} retries: {error_msg}"]

    async def _embed_batch(
        self,
        client: NVIDIAEmbeddings,
        texts: list[str],
    ) -> tuple[list[list[float]], int, list[str]]:
        """Embed a single batch."""
        # Ensure semaphore is initialized
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.max_concurrent)
        async with self._semaphore:
            # Check rate limit
            await self._check_rate_limit()

            try:
                # Use async embed_documents
                embeddings = await client.aembed_documents(texts)

                # Estimate token count (rough approximation)
                token_count = sum(len(t.split()) * 1.3 for t in texts)

                return embeddings, int(token_count), []

            except Exception as e:
                error_str = str(e).lower()

                # Check for rate limit
                if "rate limit" in error_str or "429" in error_str:
                    retry_after = 60
                    # Try to extract retry-after
                    import re

                    match = re.search(r"retry[_-]?after[=:]\s*(\d+)", error_str)
                    if match:
                        retry_after = int(match.group(1))
                    raise ModelRateLimitError(
                        model_role="embedding",
                        model_id=client.model or "unknown",
                        retry_after=retry_after,
                        details={"retry_after": retry_after},
                    ) from e

                # Check for timeout
                if "timeout" in error_str or "timed out" in error_str:
                    raise ModelTimeoutError(
                        model_role="embedding",
                        model_id=client.model or "unknown",
                        timeout=30,
                    ) from e

                # Generic model error
                raise ModelError(
                    f"Embedding failed: {e}",
                    model_role="embedding",
                    model_id=client.model or "unknown",
                ) from e

    async def _check_rate_limit(self) -> None:
        """Check and wait for rate limit if needed."""
        if self._rate_limit_remaining is not None and self._rate_limit_remaining <= 0:
            if self._rate_limit_reset:
                wait_time = max(0, self._rate_limit_reset - time.time())
                if wait_time > 0:
                    logger.info("Rate limit reached, waiting %.1fs", wait_time)
                    await asyncio.sleep(wait_time)
            self._rate_limit_remaining = None
            self._rate_limit_reset = None

    def update_rate_limit(self, remaining: int, reset_time: float) -> None:
        """Update rate limit info from response headers."""
        self._rate_limit_remaining = remaining
        self._rate_limit_reset = reset_time

    async def embed_query(self, text: str, model: str | None = None) -> list[float]:
        """Embed a single query text."""
        result = await self.embed_texts([text], model)
        if result.embeddings:
            return result.embeddings[0]
        raise ModelError(
            "Failed to embed query",
            model_role="embedding",
            model_id=model or self.model or "unknown",
        )


# Global embedding client
_embedding_client: EmbeddingClient | None = None


async def get_embedding_client() -> EmbeddingClient:
    """Get global embedding client."""
    global _embedding_client
    if _embedding_client is None:
        settings = get_settings()
        # Use model registry for embedding model (not settings.embedding_model which defaults to empty)
        from nim_sentinel.core.config import get_model_config
        embedding_config = get_model_config("embedding")
        _embedding_client = EmbeddingClient(
            model=embedding_config.primary,
            batch_size=settings.embedding_batch_size,
            max_concurrent=settings.embedding_max_concurrent,
        )
    return _embedding_client


async def close_embedding_client() -> None:
    """Close global embedding client."""
    global _embedding_client
    _embedding_client = None


async def embed_chunks(
    chunks: list[dict[str, Any]],
    model: str | None = None,
) -> list[dict[str, Any]]:
    """
    Embed a list of chunks and add embeddings to them.

    Args:
        chunks: List of chunk dicts with 'content' key
        model: Override embedding model

    Returns:
        Chunks with 'embedding' key added
    """
    client = await get_embedding_client()

    texts = [chunk["content"] for chunk in chunks]
    result = await client.embed_texts(texts, model)

    if result.errors:
        logger.warning("Embedding errors: %s", result.errors)

    # Add embeddings to chunks
    for i, chunk in enumerate(chunks):
        if i < len(result.embeddings):
            chunk["embedding"] = result.embeddings[i]
        else:
            chunk["embedding"] = None
            logger.warning("Missing embedding for chunk %d", i)

    return chunks
