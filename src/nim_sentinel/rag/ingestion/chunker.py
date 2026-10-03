"""
NIM Sentinel Document Chunking

Chunking strategies for document ingestion with metadata preservation.
"""

import hashlib
import logging
from dataclasses import dataclass
from typing import Any

from nim_sentinel.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """Represents a document chunk with metadata."""

    content: str
    chunk_index: int
    token_count: int
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "content": self.content,
            "chunk_index": self.chunk_index,
            "token_count": self.token_count,
            "metadata": self.metadata,
        }


class BaseChunker:
    """Base chunker interface."""

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(self, text: str, metadata: dict[str, Any] | None = None) -> list[Chunk]:
        """
        Chunk text into pieces.

        Args:
            text: Text to chunk
            metadata: Base metadata to include in all chunks

        Returns:
            List of chunks
        """
        raise NotImplementedError


class TokenChunker(BaseChunker):
    """Token-based chunker using approximate token counting."""

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        encoding_name: str = "cl100k_base",
    ) -> None:
        super().__init__(chunk_size, chunk_overlap)
        self.encoding_name = encoding_name
        self._encoding: Any = None

    def _get_encoding(self) -> Any:
        """Lazy load tiktoken encoding."""
        if self._encoding is None:
            try:
                import tiktoken

                self._encoding = tiktoken.get_encoding(self.encoding_name)
            except ImportError:
                logger.warning("tiktoken not available, using character-based estimation")
                self._encoding = None
        return self._encoding

    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        encoding = self._get_encoding()
        if encoding:
            return len(encoding.encode(text))
        # Fallback: rough estimation (1 token ≈ 4 chars)
        return len(text) // 4

    def chunk(self, text: str, metadata: dict[str, Any] | None = None) -> list[Chunk]:
        """Chunk text by token count with overlap."""
        if not text.strip():
            return []

        encoding = self._get_encoding()
        base_metadata = metadata or {}

        if encoding:
            # Token-based chunking
            tokens = encoding.encode(text)
            chunks = []

            start = 0
            chunk_index = 0

            while start < len(tokens):
                end = min(start + self.chunk_size, len(tokens))
                chunk_tokens = tokens[start:end]
                chunk_text = encoding.decode(chunk_tokens)

                # Calculate overlap for next chunk
                overlap_tokens = min(self.chunk_overlap, len(chunk_tokens))
                next_start = end - overlap_tokens

                # Ensure progress
                if next_start <= start:
                    next_start = end

                chunk_metadata = {
                    **base_metadata,
                    "chunk_start_token": start,
                    "chunk_end_token": end,
                    "chunk_token_count": len(chunk_tokens),
                }

                chunks.append(
                    Chunk(
                        content=chunk_text,
                        chunk_index=chunk_index,
                        token_count=len(chunk_tokens),
                        metadata=chunk_metadata,
                    )
                )

                start = next_start
                chunk_index += 1

            return chunks
        else:
            # Character-based fallback
            return self._chunk_by_chars(text, base_metadata)

    def _chunk_by_chars(self, text: str, base_metadata: dict[str, Any]) -> list[Chunk]:
        """Fallback character-based chunking."""
        # Approximate: 1 token ≈ 4 chars
        char_chunk_size = self.chunk_size * 4
        char_overlap = self.chunk_overlap * 4

        chunks = []
        start = 0
        chunk_index = 0

        while start < len(text):
            end = min(start + char_chunk_size, len(text))
            chunk_text = text[start:end]

            # Try to break at sentence boundary
            if end < len(text):
                last_period = chunk_text.rfind(". ")
                last_newline = chunk_text.rfind("\n")
                break_point = max(last_period, last_newline)
                if break_point > char_chunk_size // 2:
                    end = start + break_point + 1
                    chunk_text = text[start:end]

            token_count = self.count_tokens(chunk_text)

            chunk_metadata = {
                **base_metadata,
                "chunk_start_char": start,
                "chunk_end_char": end,
                "chunk_token_count": token_count,
            }

            chunks.append(
                Chunk(
                    content=chunk_text,
                    chunk_index=chunk_index,
                    token_count=token_count,
                    metadata=chunk_metadata,
                )
            )

            start = end - char_overlap
            if start < 0:
                start = 0
            chunk_index += 1

        return chunks


class SemanticChunker(BaseChunker):
    """Semantic chunker that respects paragraph/sentence boundaries."""

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        min_chunk_size: int = 100,
    ) -> None:
        super().__init__(chunk_size, chunk_overlap)
        self.min_chunk_size = min_chunk_size
        self._token_chunker = TokenChunker(chunk_size, chunk_overlap)

    def chunk(self, text: str, metadata: dict[str, Any] | None = None) -> list[Chunk]:
        """Chunk text semantically by paragraphs and sentences."""
        if not text.strip():
            return []

        base_metadata = metadata or {}

        # First split into paragraphs
        paragraphs = self._split_paragraphs(text)

        chunks = []
        current_chunk = ""
        current_tokens = 0
        chunk_index = 0
        paragraph_start = 0

        for para in paragraphs:
            para_tokens = self._token_chunker.count_tokens(para)

            # If paragraph alone exceeds chunk size, split it
            if para_tokens > self.chunk_size:
                # Flush current chunk
                if current_chunk:
                    chunks.append(
                        self._create_chunk(
                            current_chunk,
                            chunk_index,
                            current_tokens,
                            base_metadata,
                            paragraph_start,
                        )
                    )
                    chunk_index += 1
                    current_chunk = ""
                    current_tokens = 0

                # Split large paragraph using token chunker
                sub_chunks = self._token_chunker.chunk(para, base_metadata)
                for sub_chunk in sub_chunks:
                    sub_chunk.chunk_index = chunk_index
                    sub_chunk.metadata["semantic_split"] = True
                    chunks.append(sub_chunk)
                    chunk_index += 1
                continue

            # Check if adding paragraph exceeds chunk size
            if current_tokens + para_tokens > self.chunk_size and current_chunk:
                # Flush current chunk
                chunks.append(
                    self._create_chunk(
                        current_chunk,
                        chunk_index,
                        current_tokens,
                        base_metadata,
                        paragraph_start,
                    )
                )
                chunk_index += 1
                current_chunk = para
                current_tokens = para_tokens
                paragraph_start = len(chunks)  # Approximate
            else:
                # Add to current chunk
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para
                current_tokens += para_tokens

        # Flush remaining
        if current_chunk:
            chunks.append(
                self._create_chunk(
                    current_chunk,
                    chunk_index,
                    current_tokens,
                    base_metadata,
                    paragraph_start,
                )
            )

        # Apply overlap by adding context from previous chunk
        chunks = self._apply_overlap(chunks)

        return chunks

    def _split_paragraphs(self, text: str) -> list[str]:
        """Split text into paragraphs."""
        # Split on double newlines
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        # Further split very long paragraphs by sentences
        result = []
        for para in paragraphs:
            if self._token_chunker.count_tokens(para) <= self.chunk_size:
                result.append(para)
            else:
                # Split by sentences
                sentences = self._split_sentences(para)
                current = ""
                for sent in sentences:
                    if self._token_chunker.count_tokens(current + " " + sent) > self.chunk_size:
                        if current:
                            result.append(current)
                        current = sent
                    else:
                        current = current + " " + sent if current else sent
                if current:
                    result.append(current)

        return result

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences (simple heuristic)."""
        # Simple sentence splitting - can be improved with nltk/spacy
        import re

        sentences = re.split(r"(?<=[.!?])\s+", text)
        return [s.strip() for s in sentences if s.strip()]

    def _create_chunk(
        self,
        content: str,
        chunk_index: int,
        token_count: int,
        base_metadata: dict[str, Any],
        paragraph_start: int,
    ) -> Chunk:
        """Create a chunk with metadata."""
        chunk_metadata = {
            **base_metadata,
            "chunk_start_paragraph": paragraph_start,
            "chunk_token_count": token_count,
            "semantic_chunk": True,
        }
        return Chunk(
            content=content,
            chunk_index=chunk_index,
            token_count=token_count,
            metadata=chunk_metadata,
        )

    def _apply_overlap(self, chunks: list[Chunk]) -> list[Chunk]:
        """Apply overlap between chunks by adding context."""
        if len(chunks) <= 1 or self.chunk_overlap <= 0:
            return chunks

        # For semantic chunks, overlap is handled by paragraph boundaries
        # This is a simplified version - full overlap would require re-chunking
        return chunks


class FixedSizeChunker(BaseChunker):
    """Fixed-size chunker with configurable overlap."""

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        separator: str = "\n\n",
    ) -> None:
        super().__init__(chunk_size, chunk_overlap)
        self.separator = separator
        self._token_chunker = TokenChunker(chunk_size, chunk_overlap)

    def chunk(self, text: str, metadata: dict[str, Any] | None = None) -> list[Chunk]:
        """Chunk text by fixed token size with separator awareness."""
        if not text.strip():
            return []

        base_metadata = metadata or {}

        # Use token chunker as base
        token_chunks = self._token_chunker.chunk(text, base_metadata)

        # Adjust chunk boundaries to respect separators
        adjusted_chunks = []
        for i, chunk in enumerate(token_chunks):
            # Try to extend to next separator
            adjusted_content = self._adjust_to_separator(chunk.content, text)
            token_count = self._token_chunker.count_tokens(adjusted_content)

            chunk_metadata = {
                **chunk.metadata,
                "fixed_size_chunk": True,
                "adjusted_for_separator": adjusted_content != chunk.content,
            }

            adjusted_chunks.append(
                Chunk(
                    content=adjusted_content,
                    chunk_index=i,
                    token_count=token_count,
                    metadata=chunk_metadata,
                )
            )

        return adjusted_chunks

    def _adjust_to_separator(self, chunk_text: str, full_text: str) -> str:
        """Adjust chunk to end at a separator."""
        # Find chunk in full text
        idx = full_text.find(chunk_text)
        if idx == -1:
            return chunk_text

        # Look for separator after chunk
        search_start = idx + len(chunk_text)
        sep_idx = full_text.find(self.separator, search_start)

        if sep_idx != -1 and sep_idx - search_start < self.chunk_overlap * 4:
            # Extend to separator
            return full_text[idx : sep_idx + len(self.separator)]

        return chunk_text


def get_chunker(
    strategy: str = "semantic",
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> BaseChunker:
    """
    Get chunker by strategy name.

    Args:
        strategy: Chunking strategy ("token", "semantic", "fixed")
        chunk_size: Override default chunk size
        chunk_overlap: Override default overlap

    Returns:
        Chunker instance
    """
    settings = get_settings()

    size = chunk_size or settings.chunk_size
    overlap = chunk_overlap or settings.chunk_overlap

    if strategy == "token":
        return TokenChunker(size, overlap)
    elif strategy == "semantic":
        return SemanticChunker(size, overlap)
    elif strategy == "fixed":
        return FixedSizeChunker(size, overlap)
    else:
        logger.warning("Unknown chunker strategy: %s, using semantic", strategy)
        return SemanticChunker(size, overlap)


def generate_chunk_id(document_id: str, chunk_index: int, content: str) -> str:
    """Generate deterministic chunk ID."""
    content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
    return f"{document_id}_{chunk_index}_{content_hash}"
