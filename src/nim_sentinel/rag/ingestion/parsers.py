"""
NIM Sentinel Document Parsers

Parsers for text and PDF documents.
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import pypdf
from nim_sentinel.core.errors import DocumentParseError, UnsupportedFileTypeError

logger = logging.getLogger(__name__)


class BaseParser(ABC):
    """Base parser interface."""

    supported_extensions: list[str] = []

    @abstractmethod
    def parse(self, file_path: Path) -> tuple[str, dict[str, Any]]:
        """
        Parse document and return (content, metadata).
        """
        pass

    def can_parse(self, file_path: Path) -> bool:
        """Check if parser supports this file type."""
        return file_path.suffix.lower().lstrip(".") in self.supported_extensions


class TextParser(BaseParser):
    """Parser for plain text files."""

    supported_extensions = ["txt", "md", "markdown", "rst", "csv", "json", "yaml", "yml"]

    def parse(self, file_path: Path) -> tuple[str, dict[str, Any]]:
        """Parse text file."""
        try:
            content = file_path.read_text(encoding="utf-8")
            metadata = {
                "parser": "text",
                "encoding": "utf-8",
                "size_bytes": file_path.stat().st_size,
            }
            return content, metadata
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                content = file_path.read_text(encoding="latin-1")
                metadata = {
                    "parser": "text",
                    "encoding": "latin-1",
                    "size_bytes": file_path.stat().st_size,
                }
                return content, metadata
            except Exception as e:
                raise DocumentParseError("text", str(e)) from e
        except Exception as e:
            raise DocumentParseError("text", str(e)) from e


class PDFParser(BaseParser):
    """Parser for PDF files using pypdf."""

    supported_extensions = ["pdf"]

    def parse(self, file_path: Path) -> tuple[str, dict[str, Any]]:
        """Parse PDF file."""
        try:
            content_parts = []
            metadata = {
                "parser": "pdf",
                "size_bytes": file_path.stat().st_size,
            }

            with open(file_path, "rb") as f:
                reader = pypdf.PdfReader(f)
                metadata["page_count"] = len(reader.pages)

                # Extract PDF metadata
                if reader.metadata:
                    metadata["pdf_metadata"] = {k: str(v) for k, v in reader.metadata.items()}

                for i, page in enumerate(reader.pages):
                    try:
                        text = page.extract_text()
                        if text:
                            content_parts.append(f"[Page {i + 1}]\n{text}")
                    except Exception as e:
                        logger.warning("Failed to extract page %d: %s", i + 1, e)

            content = "\n\n".join(content_parts)
            if not content.strip():
                raise DocumentParseError("pdf", "No text content extracted from PDF")

            return content, metadata

        except DocumentParseError:
            raise
        except Exception as e:
            raise DocumentParseError("pdf", str(e)) from e


class ParserRegistry:
    """Registry of document parsers."""

    def __init__(self) -> None:
        self._parsers: list[BaseParser] = [
            TextParser(),
            PDFParser(),
        ]

    def get_parser(self, file_path: Path) -> BaseParser:
        """Get appropriate parser for file."""
        for parser in self._parsers:
            if parser.can_parse(file_path):
                return parser
        raise UnsupportedFileTypeError(
            file_path.suffix.lower().lstrip("."),
            [ext for p in self._parsers for ext in p.supported_extensions],
        )

    def parse(self, file_path: Path) -> tuple[str, dict[str, Any]]:
        """Parse file using appropriate parser."""
        parser = self.get_parser(file_path)
        logger.info("Parsing %s with %s", file_path.name, parser.__class__.__name__)
        return parser.parse(file_path)

    def register_parser(self, parser: BaseParser) -> None:
        """Register a new parser."""
        self._parsers.insert(0, parser)  # New parsers take priority


# Global parser registry
_parser_registry: ParserRegistry | None = None


def get_parser_registry() -> ParserRegistry:
    """Get global parser registry."""
    global _parser_registry
    if _parser_registry is None:
        _parser_registry = ParserRegistry()
    return _parser_registry
