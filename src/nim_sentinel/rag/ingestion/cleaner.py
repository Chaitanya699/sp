"""
NIM Sentinel Text Cleaning

Text cleaning and normalization for document ingestion.
"""

import re
import unicodedata
from typing import Any


def clean_text(text: str, options: dict[str, Any] | None = None) -> str:
    """
    Clean and normalize text content.

    Args:
        text: Raw text to clean
        options: Cleaning options
            - normalize_unicode: Normalize unicode characters (default: True)
            - remove_control_chars: Remove control characters (default: True)
            - collapse_whitespace: Collapse multiple whitespace (default: True)
            - remove_empty_lines: Remove empty lines (default: False)
            - fix_hyphenation: Fix hyphenated line breaks (default: True)
            - remove_headers_footers: Attempt to remove repeated headers/footers (default: False)

    Returns:
        Cleaned text
    """
    if not text:
        return ""

    opts = {
        "normalize_unicode": True,
        "remove_control_chars": True,
        "collapse_whitespace": True,
        "remove_empty_lines": False,
        "fix_hyphenation": True,
        "remove_headers_footers": False,
    }
    if options:
        opts.update(options)

    # Normalize unicode
    if opts["normalize_unicode"]:
        text = unicodedata.normalize("NFKC", text)

    # Remove control characters (except newlines and tabs)
    if opts["remove_control_chars"]:
        text = "".join(ch for ch in text if ch in "\n\t" or unicodedata.category(ch)[0] != "C")

    # Fix hyphenated line breaks (word-\nword -> wordword)
    if opts["fix_hyphenation"]:
        text = re.sub(r"(\w+)-\n(\w+)", r"\1\2", text)

    # Collapse whitespace
    if opts["collapse_whitespace"]:
        # Replace multiple spaces/tabs with single space
        text = re.sub(r"[ \t]+", " ", text)
        # Replace multiple newlines with double newline (paragraph break)
        text = re.sub(r"\n{3,}", "\n\n", text)

    # Remove empty lines
    if opts["remove_empty_lines"]:
        text = "\n".join(line for line in text.splitlines() if line.strip())

    # Remove repeated headers/footers (simple heuristic)
    if opts["remove_headers_footers"]:
        text = _remove_repeated_lines(text)

    return text.strip()


def _remove_repeated_lines(text: str, min_occurrences: int = 3, min_line_length: int = 10) -> str:
    """
    Remove lines that appear repeatedly (likely headers/footers).

    Args:
        text: Input text
        min_occurrences: Minimum occurrences to consider as repeated
        min_line_length: Minimum line length to consider

    Returns:
        Text with repeated lines removed
    """
    lines = text.splitlines()
    if len(lines) < min_occurrences:
        return text

    # Count line occurrences
    line_counts: dict[str, int] = {}
    for line in lines:
        stripped = line.strip()
        if len(stripped) >= min_line_length:
            line_counts[stripped] = line_counts.get(stripped, 0) + 1

    # Find repeated lines
    repeated = {line for line, count in line_counts.items() if count >= min_occurrences}

    if not repeated:
        return text

    # Filter out repeated lines
    filtered = [line for line in lines if line.strip() not in repeated]
    return "\n".join(filtered)


def extract_metadata_from_text(text: str) -> dict[str, Any]:
    """
    Extract basic metadata from text content.

    Args:
        text: Text content

    Returns:
        Dictionary with metadata
    """
    lines = text.splitlines()
    words = text.split()

    return {
        "char_count": len(text),
        "word_count": len(words),
        "line_count": len(lines),
        "non_empty_line_count": sum(1 for line in lines if line.strip()),
        "avg_line_length": sum(len(line) for line in lines) / len(lines) if lines else 0,
    }


def split_into_paragraphs(text: str, min_paragraph_length: int = 50) -> list[str]:
    """
    Split text into paragraphs.

    Args:
        text: Input text
        min_paragraph_length: Minimum paragraph length to keep

    Returns:
        List of paragraphs
    """
    # Split on double newlines
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    # Filter by minimum length
    paragraphs = [p for p in paragraphs if len(p) >= min_paragraph_length]

    return paragraphs
