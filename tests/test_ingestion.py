"""
Unit tests for RAG ingestion pipeline.
"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from nim_sentinel.core.errors import DocumentParseError, UnsupportedFileTypeError
from nim_sentinel.rag.ingestion.chunker import (
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
    get_embedding_client,
)
from nim_sentinel.rag.ingestion.parsers import (
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


class TestTextCleaner:
    """Tests for text cleaning functions."""

    def test_clean_text_basic(self):
        """Test basic text cleaning."""
        text = "  Hello   world  \n\n\n  This is a test.  "
        result = clean_text(text)
        assert "Hello world" in result
        assert "This is a test." in result

    def test_clean_text_unicode_normalization(self):
        """Test unicode normalization."""
        text = "café"  # composed
        result = clean_text(text, {"normalize_unicode": True})
        assert "café" in result

    def test_clean_text_control_chars(self):
        """Test control character removal."""
        text = "Hello\x00world\x1ftest"
        result = clean_text(text, {"remove_control_chars": True})
        assert "\x00" not in result
        assert "\x1f" not in result
        assert "Helloworldtest" == result

    def test_clean_text_hyphenation(self):
        """Test hyphenation fix."""
        text = "This is a long-\nword break."
        result = clean_text(text, {"fix_hyphenation": True})
        assert "longword" in result

    def test_clean_text_whitespace_collapse(self):
        """Test whitespace collapsing."""
        text = "Hello    world\n\n\n\nTest"
        result = clean_text(text, {"collapse_whitespace": True})
        assert "Hello world" in result
        assert "Test" in result
        # Should have at most double newlines
        assert "\n\n\n" not in result

    def test_clean_text_empty_lines(self):
        """Test empty line removal."""
        text = "Line 1\n\n\nLine 2\n\nLine 3"
        result = clean_text(text, {"remove_empty_lines": True})
        assert result == "Line 1\nLine 2\nLine 3"

    def test_extract_metadata(self):
        """Test metadata extraction."""
        text = "Hello world\nThis is a test\nThird line"
        metadata = extract_metadata_from_text(text)
        assert metadata["line_count"] == 3
        assert metadata["word_count"] == 8  # "Hello world This is a test Third line" = 8 words
        assert metadata["char_count"] > 0

    def test_split_into_paragraphs(self):
        """Test paragraph splitting."""
        text = "Para 1\n\nPara 2\n\n\nPara 3"
        paragraphs = split_into_paragraphs(text, min_paragraph_length=1)
        assert len(paragraphs) == 3
        assert paragraphs[0] == "Para 1"
        assert paragraphs[1] == "Para 2"
        assert paragraphs[2] == "Para 3"

    def test_split_into_paragraphs_min_length(self):
        """Test paragraph splitting with min length."""
        text = "Short\n\nThis is a longer paragraph that should be kept\n\nTiny"
        paragraphs = split_into_paragraphs(text, min_paragraph_length=20)
        assert len(paragraphs) == 1
        assert "longer paragraph" in paragraphs[0]


class TestParsers:
    """Tests for document parsers."""

    def test_text_parser(self):
        """Test text parser."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Hello world\nThis is a test.")
            temp_path = Path(f.name)

        try:
            parser = TextParser()
            content, metadata = parser.parse(temp_path)
            assert "Hello world" in content
            assert "This is a test." in content
            assert metadata["parser"] == "text"
            assert metadata["encoding"] == "utf-8"
        finally:
            temp_path.unlink()

    def test_text_parser_encoding_fallback(self):
        """Test text parser encoding fallback."""
        # Create file with latin-1 encoding
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".txt", delete=False) as f:
            f.write("café".encode("latin-1"))
            temp_path = Path(f.name)

        try:
            parser = TextParser()
            content, metadata = parser.parse(temp_path)
            assert "café" in content or "caf" in content  # May not decode perfectly
            assert metadata["encoding"] in ["utf-8", "latin-1"]
        finally:
            temp_path.unlink()

    def test_pdf_parser(self):
        """Test PDF parser."""
        # Create a simple PDF with text content
        from pypdf import PdfWriter

        writer = PdfWriter()
        writer.add_blank_page(width=612, height=792)

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            writer.write(f)
            temp_path = Path(f.name)

        try:
            parser = PDFParser()
            # Blank PDF has no text content, should raise DocumentParseError
            with pytest.raises(DocumentParseError, match="No text content extracted"):
                parser.parse(temp_path)
        finally:
            temp_path.unlink()

    def test_parser_registry(self):
        """Test parser registry."""
        registry = ParserRegistry()

        # Test text file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("test")
            temp_path = Path(f.name)

        try:
            parser = registry.get_parser(temp_path)
            assert isinstance(parser, TextParser)
        finally:
            temp_path.unlink()

        # Test PDF file
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            temp_path = Path(f.name)

        try:
            parser = registry.get_parser(temp_path)
            assert isinstance(parser, PDFParser)
        finally:
            temp_path.unlink()

    def test_parser_registry_unsupported(self):
        """Test parser registry with unsupported file."""
        registry = ParserRegistry()

        with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as f:
            temp_path = Path(f.name)

        try:
            with pytest.raises(UnsupportedFileTypeError):
                registry.get_parser(temp_path)
        finally:
            temp_path.unlink()

    def test_global_parser_registry(self):
        """Test global parser registry singleton."""
        registry1 = get_parser_registry()
        registry2 = get_parser_registry()
        assert registry1 is registry2


class TestChunkers:
    """Tests for document chunkers."""

    def test_token_chunker_basic(self):
        """Test token chunker basic functionality."""
        chunker = TokenChunker(chunk_size=100, chunk_overlap=20)
        text = "This is a test sentence. " * 20  # ~100 tokens
        chunks = chunker.chunk(text, {"source": "test"})

        assert len(chunks) > 0
        for chunk in chunks:
            assert isinstance(chunk, Chunk)
            assert chunk.token_count > 0
            assert chunk.chunk_index >= 0
            assert chunk.metadata["source"] == "test"

    def test_token_chunker_empty(self):
        """Test token chunker with empty text."""
        chunker = TokenChunker()
        chunks = chunker.chunk("")
        assert chunks == []

    def test_token_chunker_overlap(self):
        """Test token chunker overlap."""
        chunker = TokenChunker(chunk_size=50, chunk_overlap=10)
        text = "word " * 100
        chunks = chunker.chunk(text)

        assert len(chunks) > 1
        # Check overlap by verifying token counts
        for chunk in chunks:
            assert chunk.token_count <= 50 + 10  # Allow some flexibility

    def test_semantic_chunker_basic(self):
        """Test semantic chunker."""
        chunker = SemanticChunker(chunk_size=100, chunk_overlap=20)
        text = "Paragraph 1.\n\nParagraph 2.\n\nParagraph 3."
        chunks = chunker.chunk(text, {"source": "test"})

        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk.metadata.get("semantic_chunk") is True

    def test_semantic_chunker_paragraphs(self):
        """Test semantic chunker respects paragraphs."""
        chunker = SemanticChunker(chunk_size=200, chunk_overlap=20)
        text = "Para 1.\n\nPara 2.\n\nPara 3.\n\nPara 4."
        chunks = chunker.chunk(text)

        # Should create chunks respecting paragraph boundaries
        assert len(chunks) >= 1

    def test_fixed_size_chunker(self):
        """Test fixed size chunker."""
        chunker = FixedSizeChunker(chunk_size=100, chunk_overlap=20)
        text = "Sentence 1. " * 30
        chunks = chunker.chunk(text)

        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk.metadata.get("fixed_size_chunk") is True

    def test_get_chunker(self):
        """Test get_chunker factory."""
        token_chunker = get_chunker("token", chunk_size=100)
        assert isinstance(token_chunker, TokenChunker)

        semantic_chunker = get_chunker("semantic", chunk_size=100)
        assert isinstance(semantic_chunker, SemanticChunker)

        fixed_chunker = get_chunker("fixed", chunk_size=100)
        assert isinstance(fixed_chunker, FixedSizeChunker)

        # Unknown strategy defaults to semantic
        unknown_chunker = get_chunker("unknown", chunk_size=100)
        assert isinstance(unknown_chunker, SemanticChunker)

    def test_generate_chunk_id(self):
        """Test chunk ID generation."""
        id1 = generate_chunk_id("doc123", 0, "content")
        id2 = generate_chunk_id("doc123", 0, "content")
        id3 = generate_chunk_id("doc123", 1, "content")

        assert id1 == id2  # Deterministic
        assert id1 != id3  # Different index
        assert "doc123" in id1
        assert "_0_" in id1


class TestEmbedder:
    """Tests for embedding client."""

    @pytest.fixture
    def mock_embeddings(self):
        """Mock NVIDIAEmbeddings."""
        with patch("nim_sentinel.rag.ingestion.embedder.NVIDIAEmbeddings") as mock_class:
            mock_instance = AsyncMock()
            mock_instance.aembed_documents = AsyncMock(return_value=[[0.1] * 1024, [0.2] * 1024])
            mock_instance.model = "nvidia/nv-embedqa-e5-v5"
            mock_class.return_value = mock_instance
            yield mock_instance

    @pytest.mark.asyncio
    async def test_embed_texts_success(self, mock_embeddings):
        """Test successful embedding."""
        with patch("nim_sentinel.rag.ingestion.embedder.get_settings") as mock_settings:
            mock_settings.return_value.nvidia_api_key = "test-key"
            mock_settings.return_value.embedding_model = "nvidia/nv-embedqa-e5-v5"
            mock_settings.return_value.embedding_batch_size = 32
            mock_settings.return_value.embedding_max_concurrent = 4

            client = EmbeddingClient(batch_size=2, max_concurrent=2)
            result = await client.embed_texts(["text 1", "text 2"])

            assert len(result.embeddings) == 2
            assert result.token_count > 0
            assert result.model == "nvidia/nv-embedqa-e5-v5"
            assert result.latency_ms > 0

    @pytest.mark.asyncio
    async def test_embed_texts_empty(self, mock_embeddings):
        """Test embedding empty list."""
        with patch("nim_sentinel.rag.ingestion.embedder.get_settings") as mock_settings:
            mock_settings.return_value.nvidia_api_key = "test-key"

            client = EmbeddingClient()
            result = await client.embed_texts([])

            assert result.embeddings == []
            assert result.token_count == 0

    @pytest.mark.asyncio
    async def test_embed_texts_rate_limit_retry(self, mock_embeddings):
        """Test embedding with rate limit retry."""
        from nim_sentinel.core.errors import ModelRateLimitError

        with patch("nim_sentinel.rag.ingestion.embedder.get_settings") as mock_settings:
            mock_settings.return_value.nvidia_api_key = "test-key"

            # First call raises rate limit, second succeeds
            mock_embeddings.aembed_documents.side_effect = [
                ModelRateLimitError("embedding", "model", retry_after=1),
                [[0.1] * 1024, [0.2] * 1024],
            ]

            client = EmbeddingClient(max_retries=1, base_delay=0.01)
            result = await client.embed_texts(["text 1", "text 2"])

            assert len(result.embeddings) == 2
            assert mock_embeddings.aembed_documents.call_count == 2

    @pytest.mark.asyncio
    async def test_embed_texts_max_retries_exceeded(self, mock_embeddings):
        """Test embedding with max retries exceeded."""
        from nim_sentinel.core.errors import ModelRateLimitError

        with patch("nim_sentinel.rag.ingestion.embedder.get_settings") as mock_settings:
            mock_settings.return_value.nvidia_api_key = "test-key"

            mock_embeddings.aembed_documents.side_effect = ModelRateLimitError(
                "embedding", "model", retry_after=60
            )

            client = EmbeddingClient(max_retries=1, base_delay=0.01)
            result = await client.embed_texts(["text 1"])

            assert result.embeddings == []
            assert result.errors is not None
            assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_embed_query(self, mock_embeddings):
        """Test single query embedding."""
        with patch("nim_sentinel.rag.ingestion.embedder.get_settings") as mock_settings:
            mock_settings.return_value.nvidia_api_key = "test-key"

            client = EmbeddingClient()
            embedding = await client.embed_query("test query")

            assert len(embedding) == 1024

    @pytest.mark.asyncio
    async def test_global_embedding_client(self, mock_embeddings):
        """Test global embedding client singleton."""
        with patch("nim_sentinel.rag.ingestion.embedder.get_settings") as mock_settings:
            mock_settings.return_value.nvidia_api_key = "test-key"
            mock_settings.return_value.embedding_model = "nvidia/nv-embedqa-e5-v5"
            mock_settings.return_value.embedding_batch_size = 32
            mock_settings.return_value.embedding_max_concurrent = 4

            import nim_sentinel.rag.ingestion.embedder as embedder_module

            embedder_module._embedding_client = None

            client1 = await get_embedding_client()
            client2 = await get_embedding_client()

            assert client1 is client2


class TestIngestionPipeline:
    """Tests for ingestion pipeline."""

    @pytest.fixture
    def mock_document_repo(self):
        """Mock document repository."""
        repo = AsyncMock()
        repo.create_document = AsyncMock(return_value="doc_123")
        repo.update_status = AsyncMock(return_value=True)
        repo.update_stats = AsyncMock(return_value=True)
        repo.get_by_content_hash = AsyncMock(return_value=None)
        return repo

    @pytest.fixture
    def mock_chunk_repo(self):
        """Mock chunk repository."""
        repo = AsyncMock()
        repo.create_chunks = AsyncMock(return_value=["chunk_1", "chunk_2"])
        return repo

    @pytest.fixture
    def mock_embedding_client(self):
        """Mock embedding client."""
        client = AsyncMock()
        client.embed_texts = AsyncMock(
            return_value=EmbeddingResult(
                embeddings=[[0.1] * 1024, [0.2] * 1024],
                token_count=100,
                model="nvidia/nv-embedqa-e5-v5",
                latency_ms=100.0,
            )
        )
        return client

    @pytest.mark.asyncio
    async def test_ingest_file_success(
        self, mock_document_repo, mock_chunk_repo, mock_embedding_client
    ):
        """Test successful file ingestion."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("This is a test document. " * 50)
            temp_path = Path(f.name)

        try:
            pipeline = IngestionPipeline(
                tenant_id="tenant_123",
                document_repo=mock_document_repo,
                chunk_repo=mock_chunk_repo,
                embedding_client=mock_embedding_client,
            )

            result = await pipeline.ingest_file(temp_path)

            assert result.status == "completed"
            assert result.document_id == "doc_123"
            assert result.chunk_count > 0
            assert result.token_count > 0
            assert result.latency_ms > 0

            mock_document_repo.create_document.assert_called_once()
            mock_document_repo.update_status.assert_called()
            mock_chunk_repo.create_chunks.assert_called_once()
        finally:
            temp_path.unlink()

    @pytest.mark.asyncio
    async def test_ingest_file_duplicate(
        self, mock_document_repo, mock_chunk_repo, mock_embedding_client
    ):
        """Test duplicate file skipping."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Duplicate content")
            temp_path = Path(f.name)

        try:
            # Mock existing document
            mock_document_repo.get_by_content_hash = AsyncMock(return_value={"_id": "existing_doc"})

            pipeline = IngestionPipeline(
                tenant_id="tenant_123",
                config=IngestionConfig(skip_duplicates=True),
                document_repo=mock_document_repo,
                chunk_repo=mock_chunk_repo,
                embedding_client=mock_embedding_client,
            )

            result = await pipeline.ingest_file(temp_path)

            assert result.status == "skipped"
            assert result.document_id == "existing_doc"
            assert result.metadata["duplicate_of"] == "existing_doc"

            # Should not create new document
            mock_document_repo.create_document.assert_not_called()
        finally:
            temp_path.unlink()

    @pytest.mark.asyncio
    async def test_ingest_file_too_large(
        self, mock_document_repo, mock_chunk_repo, mock_embedding_client
    ):
        """Test file size limit."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Small content")
            temp_path = Path(f.name)

        try:
            pipeline = IngestionPipeline(
                tenant_id="tenant_123",
                config=IngestionConfig(max_file_size_mb=0.000001),  # Very small limit (1 byte)
                document_repo=mock_document_repo,
                chunk_repo=mock_chunk_repo,
                embedding_client=mock_embedding_client,
            )

            result = await pipeline.ingest_file(temp_path)

            assert result.status == "failed"
            assert "exceeds limit" in result.error
        finally:
            temp_path.unlink()

    @pytest.mark.asyncio
    async def test_ingest_file_parse_error(
        self, mock_document_repo, mock_chunk_repo, mock_embedding_client
    ):
        """Test ingestion with parse error."""
        with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as f:
            temp_path = Path(f.name)

        try:
            pipeline = IngestionPipeline(
                tenant_id="tenant_123",
                document_repo=mock_document_repo,
                chunk_repo=mock_chunk_repo,
                embedding_client=mock_embedding_client,
            )

            result = await pipeline.ingest_file(temp_path)

            assert result.status == "failed"
            assert "Unsupported file type" in result.error
        finally:
            temp_path.unlink()

    @pytest.mark.asyncio
    async def test_ingest_directory(
        self, mock_document_repo, mock_chunk_repo, mock_embedding_client
    ):
        """Test directory ingestion."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dir_path = Path(tmpdir)

            # Create test files
            (dir_path / "doc1.txt").write_text("Content 1")
            (dir_path / "doc2.txt").write_text("Content 2")
            (dir_path / "doc3.md").write_text("Content 3")

            pipeline = IngestionPipeline(
                tenant_id="tenant_123",
                document_repo=mock_document_repo,
                chunk_repo=mock_chunk_repo,
                embedding_client=mock_embedding_client,
            )

            results = await pipeline.ingest_directory(dir_path, extensions=["txt", "md"])

            assert len(results) == 3
            for result in results:
                assert result.status == "completed"

    @pytest.mark.asyncio
    async def test_create_ingestion_pipeline(self):
        """Test pipeline factory."""
        pipeline = await create_ingestion_pipeline("tenant_123")
        assert isinstance(pipeline, IngestionPipeline)
        assert pipeline.tenant_id == "tenant_123"

    @pytest.mark.asyncio
    async def test_ingest_file_convenience(
        self, mock_document_repo, mock_chunk_repo, mock_embedding_client
    ):
        """Test ingest_file convenience function."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Test content")
            temp_path = Path(f.name)

        try:
            with patch(
                "nim_sentinel.rag.ingestion.pipeline.create_ingestion_pipeline"
            ) as mock_create:
                mock_pipeline = AsyncMock()
                mock_pipeline.ingest_file = AsyncMock(
                    return_value=IngestionResult(
                        document_id="doc_123",
                        filename="test.txt",
                        status="completed",
                        chunk_count=1,
                        token_count=10,
                    )
                )
                mock_create.return_value = mock_pipeline

                result = await ingest_file("tenant_123", temp_path)

                assert result.status == "completed"
                assert result.document_id == "doc_123"
        finally:
            temp_path.unlink()

    @pytest.mark.asyncio
    async def test_ingest_directory_convenience(
        self, mock_document_repo, mock_chunk_repo, mock_embedding_client
    ):
        """Test ingest_directory convenience function."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dir_path = Path(tmpdir)
            (dir_path / "doc1.txt").write_text("Content 1")

            with patch(
                "nim_sentinel.rag.ingestion.pipeline.create_ingestion_pipeline"
            ) as mock_create:
                mock_pipeline = AsyncMock()
                mock_pipeline.ingest_directory = AsyncMock(
                    return_value=[
                        IngestionResult(
                            document_id="doc_123",
                            filename="doc1.txt",
                            status="completed",
                            chunk_count=1,
                            token_count=10,
                        )
                    ]
                )
                mock_create.return_value = mock_pipeline

                results = await ingest_directory("tenant_123", dir_path)

                assert len(results) == 1
                assert results[0].status == "completed"


class TestIngestionConfig:
    """Tests for ingestion configuration."""

    def test_default_config(self):
        """Test default configuration."""
        config = IngestionConfig()
        assert config.max_file_size_mb == 50.0
        assert config.chunk_strategy == "semantic"
        assert config.chunk_size == 512
        assert config.chunk_overlap == 50
        assert config.skip_duplicates is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = IngestionConfig(
            max_file_size_mb=10.0,
            chunk_strategy="token",
            chunk_size=256,
            chunk_overlap=25,
            skip_duplicates=False,
        )
        assert config.max_file_size_mb == 10.0
        assert config.chunk_strategy == "token"
        assert config.chunk_size == 256
        assert config.chunk_overlap == 25
        assert config.skip_duplicates is False
