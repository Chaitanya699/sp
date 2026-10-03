"""
NIM Sentinel Ingestion Pipeline

Main pipeline orchestrating parse -> clean -> chunk -> embed -> store.
"""

import asyncio
import hashlib
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from nim_sentinel.core.config import get_settings
from nim_sentinel.core.errors import DocumentError, DocumentParseError, DocumentTooLargeError
from nim_sentinel.db.client import get_mongo_client
from nim_sentinel.db.repositories import (
    ChunkRepository,
    DocumentRepository,
    get_chunk_repository,
    get_document_repository,
)
from nim_sentinel.rag.ingestion.chunker import get_chunker
from nim_sentinel.rag.ingestion.cleaner import clean_text, extract_metadata_from_text
from nim_sentinel.rag.ingestion.embedder import EmbeddingClient
from nim_sentinel.rag.ingestion.parsers import get_parser_registry

logger = logging.getLogger(__name__)


@dataclass
class IngestionResult:
    """Result of document ingestion."""

    document_id: str
    filename: str
    status: str  # "completed", "failed", "skipped"
    chunk_count: int = 0
    token_count: int = 0
    error: str | None = None
    latency_ms: float = 0.0
    metadata: dict[str, Any] | None = None


@dataclass
class IngestionConfig:
    """Configuration for ingestion pipeline."""

    max_file_size_mb: float = 50.0
    chunk_strategy: str = "semantic"
    chunk_size: int = 512
    chunk_overlap: int = 50
    embedding_model: str | None = None
    embedding_batch_size: int = 32
    skip_duplicates: bool = True
    clean_options: dict[str, Any] | None = None


class IngestionPipeline:
    """Main ingestion pipeline."""

    def __init__(
        self,
        tenant_id: str,
        config: IngestionConfig | None = None,
        document_repo: DocumentRepository | None = None,
        chunk_repo: ChunkRepository | None = None,
        embedding_client: EmbeddingClient | None = None,
    ) -> None:
        self.tenant_id = tenant_id
        self.config = config or IngestionConfig()
        self._document_repo = document_repo
        self._chunk_repo = chunk_repo
        self._embedding_client = embedding_client
        self._parser_registry = get_parser_registry()
        self._chunker = get_chunker(
            strategy=self.config.chunk_strategy,
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
        )

    async def _get_document_repo(self) -> DocumentRepository:
        """Get document repository (lazy init)."""
        if self._document_repo is None:
            client = await get_mongo_client()
            self._document_repo = get_document_repository(client.database, self.tenant_id)
        return self._document_repo

    async def _get_chunk_repo(self) -> ChunkRepository:
        """Get chunk repository (lazy init)."""
        if self._chunk_repo is None:
            client = await get_mongo_client()
            self._chunk_repo = get_chunk_repository(client.database, self.tenant_id)
        return self._chunk_repo

    @property
    def embedding_client(self) -> EmbeddingClient:
        """Get embedding client (lazy init)."""
        if self._embedding_client is None:
            self._embedding_client = EmbeddingClient(
                model=self.config.embedding_model,
                batch_size=self.config.embedding_batch_size,
            )
        return self._embedding_client

    async def ingest_bytes(
        self,
        content: bytes,
        filename: str,
        source_type: str,
        document_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> IngestionResult:
        """
        Ingest document from bytes content.

        Args:
            content: Raw document content
            filename: Original filename
            source_type: Source type (e.g., "txt", "pdf")
            document_id: Pre-created document ID
            metadata: Additional metadata

        Returns:
            IngestionResult
        """
        start_time = time.perf_counter()

        try:
            # Check content size
            content_size_mb = len(content) / (1024 * 1024)
            if content_size_mb > self.config.max_file_size_mb:
                raise DocumentTooLargeError(content_size_mb, self.config.max_file_size_mb)

            # Compute content hash for deduplication
            content_hash = hashlib.sha256(content).hexdigest()

            # Check for duplicate
            if self.config.skip_duplicates:
                doc_repo = await self._get_document_repo()
                existing = await doc_repo.get_by_content_hash(content_hash)
                if existing:
                    logger.info("Skipping duplicate: %s", filename)
                    return IngestionResult(
                        document_id=str(existing["_id"]),
                        filename=filename,
                        status="skipped",
                        metadata={"duplicate_of": str(existing["_id"])},
                    )

            # Parse document
            parse_metadata = {"parser": "bytes", "source_type": source_type}

            # Decode content
            try:
                text_content = content.decode("utf-8")
            except UnicodeDecodeError:
                text_content = content.decode("utf-8", errors="replace")

            # Clean text
            clean_content = clean_text(text_content, self.config.clean_options)
            clean_metadata = extract_metadata_from_text(clean_content)

            # Update document status to processing
            doc_repo = await self._get_document_repo()
            await doc_repo.update_status(document_id, "processing")

            # Chunk document
            chunks = self._chunker.chunk(
                clean_content,
                metadata={
                    "document_id": document_id,
                    "filename": filename,
                    "tenant_id": self.tenant_id,
                },
            )

            if not chunks:
                await doc_repo.update_status(
                    document_id, "failed", error="No chunks generated"
                )
                return IngestionResult(
                    document_id=document_id,
                    filename=filename,
                    status="failed",
                    error="No chunks generated",
                    latency_ms=(time.perf_counter() - start_time) * 1000,
                )

            # Prepare chunks for embedding
            chunk_dicts = [chunk.to_dict() for chunk in chunks]

            # Embed chunks
            embedded_chunks_result = await self.embedding_client.embed_texts(
                [c["content"] for c in chunk_dicts], self.config.embedding_model
            )
            # Convert EmbeddingResult to list of dicts with embeddings
            embedded_chunks = []
            for i, chunk_dict in enumerate(chunk_dicts):
                new_chunk = chunk_dict.copy()
                if i < len(embedded_chunks_result.embeddings):
                    new_chunk["embedding"] = embedded_chunks_result.embeddings[i]
                else:
                    new_chunk["embedding"] = None
                embedded_chunks.append(new_chunk)

            # Filter out chunks without embeddings
            valid_chunks = [c for c in embedded_chunks if c.get("embedding") is not None]
            if len(valid_chunks) != len(embedded_chunks):
                logger.warning(
                    "%d/%d chunks missing embeddings for %s",
                    len(embedded_chunks) - len(valid_chunks),
                    len(embedded_chunks),
                    filename,
                )

            # Store chunks
            chunk_repo = await self._get_chunk_repo()
            _ = await chunk_repo.create_chunks(
                document_id,
                valid_chunks,
                self.config.embedding_model or get_settings().embedding_model,
            )

            # Update document with stats
            total_tokens = sum(c.get("token_count", 0) for c in valid_chunks)
            doc_repo = await self._get_document_repo()
            await doc_repo.update_stats(
                document_id, chunk_count=len(valid_chunks), token_count=total_tokens
            )
            await doc_repo.update_status(document_id, "completed")

            latency_ms = (time.perf_counter() - start_time) * 1000

            logger.info(
                "Ingested %s: %d chunks, %d tokens in %.1fms",
                filename,
                len(valid_chunks),
                total_tokens,
                latency_ms,
            )

            return IngestionResult(
                document_id=document_id,
                filename=filename,
                status="completed",
                chunk_count=len(valid_chunks),
                token_count=total_tokens,
                latency_ms=latency_ms,
                metadata={
                    "parser": parse_metadata.get("parser"),
                    "file_size_mb": content_size_mb,
                },
            )

        except DocumentParseError as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.error("Parse error for %s: %s", filename, e)
            return IngestionResult(
                document_id=document_id,
                filename=filename,
                status="failed",
                error=str(e),
                latency_ms=latency_ms,
            )
        except DocumentError as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.error("Document error for %s: %s", filename, e)
            return IngestionResult(
                document_id=document_id,
                filename=filename,
                status="failed",
                error=str(e),
                latency_ms=latency_ms,
            )
        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.exception("Unexpected error ingesting %s", filename)
            return IngestionResult(
                document_id=document_id,
                filename=filename,
                status="failed",
                error=f"Unexpected error: {e}",
                latency_ms=latency_ms,
            )

    async def ingest_file(self, file_path: Path) -> IngestionResult:
        """
        Ingest a single file.

        Args:
            file_path: Path to file to ingest

        Returns:
            IngestionResult
        """
        start_time = time.perf_counter()
        filename = file_path.name

        try:
            # Check file size
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            if file_size_mb > self.config.max_file_size_mb:
                raise DocumentTooLargeError(file_size_mb, self.config.max_file_size_mb)

            # Compute content hash for deduplication
            content_hash = self._compute_file_hash(file_path)

            # Check for duplicate
            if self.config.skip_duplicates:
                doc_repo = await self._get_document_repo()
                existing = await doc_repo.get_by_content_hash(content_hash)
                if existing:
                    logger.info("Skipping duplicate: %s", filename)
                    return IngestionResult(
                        document_id=str(existing["_id"]),
                        filename=filename,
                        status="skipped",
                        metadata={"duplicate_of": str(existing["_id"])},
                    )

            # Parse document
            content, parse_metadata = await asyncio.to_thread(
                self._parser_registry.parse, file_path
            )

            # Clean text
            clean_content = clean_text(content, self.config.clean_options)
            clean_metadata = extract_metadata_from_text(clean_content)

            # Create document record
            doc_repo = await self._get_document_repo()
            doc_id = await doc_repo.create_document(
                filename=filename,
                source_type=file_path.suffix.lower().lstrip("."),
                content_hash=content_hash,
                metadata={
                    **parse_metadata,
                    **clean_metadata,
                    "file_size_mb": file_size_mb,
                },
            )

            # Update status to processing
            await doc_repo.update_status(doc_id, "processing")

            # Chunk document
            chunks = self._chunker.chunk(
                clean_content,
                metadata={
                    "document_id": doc_id,
                    "filename": filename,
                    "tenant_id": self.tenant_id,
                },
            )

            if not chunks:
                await doc_repo.update_status(
                    doc_id, "failed", error="No chunks generated"
                )
                return IngestionResult(
                    document_id=doc_id,
                    filename=filename,
                    status="failed",
                    error="No chunks generated",
                    latency_ms=(time.perf_counter() - start_time) * 1000,
                )

            # Prepare chunks for embedding
            chunk_dicts = [chunk.to_dict() for chunk in chunks]

            # Embed chunks
            embedded_chunks_result = await self.embedding_client.embed_texts(
                [c["content"] for c in chunk_dicts], self.config.embedding_model
            )
            # Convert EmbeddingResult to list of dicts with embeddings
            embedded_chunks = []
            for i, chunk_dict in enumerate(chunk_dicts):
                new_chunk = chunk_dict.copy()
                if i < len(embedded_chunks_result.embeddings):
                    new_chunk["embedding"] = embedded_chunks_result.embeddings[i]
                else:
                    new_chunk["embedding"] = None
                embedded_chunks.append(new_chunk)

            # Filter out chunks without embeddings
            valid_chunks = [c for c in embedded_chunks if c.get("embedding") is not None]
            if len(valid_chunks) != len(embedded_chunks):
                logger.warning(
                    "%d/%d chunks missing embeddings for %s",
                    len(embedded_chunks) - len(valid_chunks),
                    len(embedded_chunks),
                    filename,
                )

            # Store chunks
            chunk_repo = await self._get_chunk_repo()
            _ = await chunk_repo.create_chunks(
                doc_id,
                valid_chunks,
                self.config.embedding_model or get_settings().embedding_model,
            )

            # Update document with stats
            total_tokens = sum(c.get("token_count", 0) for c in valid_chunks)
            doc_repo = await self._get_document_repo()
            await doc_repo.update_stats(
                doc_id, chunk_count=len(valid_chunks), token_count=total_tokens
            )
            await doc_repo.update_status(doc_id, "completed")

            latency_ms = (time.perf_counter() - start_time) * 1000

            logger.info(
                "Ingested %s: %d chunks, %d tokens in %.1fms",
                filename,
                len(valid_chunks),
                total_tokens,
                latency_ms,
            )

            return IngestionResult(
                document_id=doc_id,
                filename=filename,
                status="completed",
                chunk_count=len(valid_chunks),
                token_count=total_tokens,
                latency_ms=latency_ms,
                metadata={
                    "parser": parse_metadata.get("parser"),
                    "file_size_mb": file_size_mb,
                },
            )

        except DocumentParseError as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.error("Parse error for %s: %s", filename, e)
            return IngestionResult(
                document_id="",
                filename=filename,
                status="failed",
                error=str(e),
                latency_ms=latency_ms,
            )
        except DocumentError as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.error("Document error for %s: %s", filename, e)
            return IngestionResult(
                document_id="",
                filename=filename,
                status="failed",
                error=str(e),
                latency_ms=latency_ms,
            )
        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.exception("Unexpected error ingesting %s", filename)
            return IngestionResult(
                document_id="",
                filename=filename,
                status="failed",
                error=f"Unexpected error: {e}",
                latency_ms=latency_ms,
            )

    async def ingest_directory(
        self,
        directory: Path,
        recursive: bool = True,
        extensions: list[str] | None = None,
    ) -> list[IngestionResult]:
        """
        Ingest all supported files in a directory.

        Args:
            directory: Directory to ingest
            recursive: Whether to recurse into subdirectories
            extensions: Optional list of extensions to filter (e.g., ["pdf", "txt"])

        Returns:
            List of IngestionResult
        """
        if not directory.is_dir():
            raise ValueError(f"Not a directory: {directory}")

        # Find files
        pattern = "**/*" if recursive else "*"
        files: list[Path] = []
        for ext in (extensions or ["pdf", "txt", "md", "markdown"]):
            files.extend(directory.glob(f"{pattern}.{ext}"))

        # Also check for files without extension that might be text
        if not extensions:
            for file_path in directory.glob(pattern):
                if file_path.is_file() and file_path.suffix == "":
                    # Check if it's likely text
                    try:
                        file_path.read_text(encoding="utf-8")
                        files.append(file_path)
                    except Exception:
                        pass

        logger.info("Found %d files to ingest in %s", len(files), directory)

        # Ingest files concurrently with limit
        semaphore = asyncio.Semaphore(4)

        async def ingest_with_semaphore(file_path: Path) -> IngestionResult:
            async with semaphore:
                return await self.ingest_file(file_path)

        tasks = [ingest_with_semaphore(f) for f in files]
        results: list[IngestionResult | BaseException] = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions
        final_results: list[IngestionResult] = []
        for i, result in enumerate(results):
            if isinstance(result, BaseException):
                final_results.append(
                    IngestionResult(
                        document_id="",
                        filename=files[i].name,
                        status="failed",
                        error=str(result),
                    )
                )
            else:
                final_results.append(result)

        return final_results

    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA256 hash of file content."""
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()


async def create_ingestion_pipeline(
    tenant_id: str,
    config: IngestionConfig | None = None,
) -> IngestionPipeline:
    """Factory function to create ingestion pipeline."""
    return IngestionPipeline(tenant_id, config)


async def ingest_file(
    tenant_id: str,
    file_path: Path,
    config: IngestionConfig | None = None,
) -> IngestionResult:
    """Convenience function to ingest a single file."""
    pipeline = await create_ingestion_pipeline(tenant_id, config)
    return await pipeline.ingest_file(file_path)


async def ingest_directory(
    tenant_id: str,
    directory: Path,
    config: IngestionConfig | None = None,
    recursive: bool = True,
    extensions: list[str] | None = None,
) -> list[IngestionResult]:
    """Convenience function to ingest a directory."""
    pipeline = await create_ingestion_pipeline(tenant_id, config)
    return await pipeline.ingest_directory(directory, recursive, extensions)
