"""
NIM Sentinel RAG Ingestion Module

Document ingestion pipeline: parse -> clean -> chunk -> embed -> store.
"""

from nim_sentinel.rag.ingestion.chunker import (
    BaseChunker,
    Chunk,
    FixedSizeChunker,
    SemanticChunker,
    TokenChunker,
    generate_chunk_id,
    get_chunker,
)
from nim_sentinel.rag.ingestion.cleaner import (
    clean_text,
    extract_metadata_from_text,
    split_into_paragraphs,
)
from nim_sentinel.rag.ingestion.embedder import (
    EmbeddingClient,
    EmbeddingResult,
    embed_chunks,
    get_embedding_client,
)
from nim_sentinel.rag.ingestion.parsers import (
    BaseParser,
    ParserRegistry,
    PDFParser,
    TextParser,
    get_parser_registry,
)
from nim_sentinel.rag.ingestion.pipeline import (
    IngestionConfig,
    IngestionPipeline,
    IngestionResult,
    create_ingestion_pipeline,
    ingest_directory,
    ingest_file,
)

__all__ = [
    # Parsers
    "BaseParser",
    "TextParser",
    "PDFParser",
    "ParserRegistry",
    "get_parser_registry",
    # Cleaner
    "clean_text",
    "extract_metadata_from_text",
    "split_into_paragraphs",
    # Chunker
    "BaseChunker",
    "TokenChunker",
    "SemanticChunker",
    "FixedSizeChunker",
    "Chunk",
    "generate_chunk_id",
    "get_chunker",
    # Embedder
    "EmbeddingClient",
    "EmbeddingResult",
    "get_embedding_client",
    "embed_chunks",
    # Pipeline
    "IngestionPipeline",
    "IngestionConfig",
    "IngestionResult",
    "create_ingestion_pipeline",
    "ingest_file",
    "ingest_directory",
]
