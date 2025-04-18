"""Utilities for text and HTML processing."""

import logging
import re
from typing import Any

# Import LangChain text splitters
from langchain_text_splitters import (
    HTMLHeaderTextSplitter,
    HTMLSectionSplitter,
    RecursiveCharacterTextSplitter,
)


def is_pdf_url(url: str) -> bool:
    """
    Check if a URL points to a PDF file.

    Args:
        url: URL to check

    Returns:
        True if the URL points to a PDF, False otherwise
    """
    # Check if URL ends with .pdf (case insensitive)
    if url.lower().endswith(".pdf"):
        return True

    # Check for PDF in the URL path
    if "pdf" in url.split("/")[-1].lower():
        return True

    return False


def chunk_html_content(
    html_content: str,
    content_type: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    splitter_type: str = "semantic",
    max_chunks: int = 50,  # Add a safety limit to prevent infinite chunking
) -> list[dict[str, Any]]:
    """
    Split HTML content into chunks using appropriate LangChain text splitters.

    Args:
        html_content: HTML content as string
        content_type: Content type string (to determine if it's HTML)
        chunk_size: Maximum chunk size in characters
        chunk_overlap: Overlap between chunks in characters
        splitter_type: Type of splitter to use ("semantic", "header", "section")
        max_chunks: Maximum number of chunks to prevent infinite chunking

    Returns:
        List of dictionaries with chunks and their metadata
    """
    # First, aggressively remove JavaScript code from HTML
    html_content = remove_javascript(html_content)

    # Sanity check for empty content
    if not html_content or len(html_content.strip()) < 100:
        logging.warning("Content is too short or empty, not chunking")
        return [{"content": html_content.strip(), "metadata": {}}]

    # Extract plain text for size estimation
    plain_text = re.sub(r"<[^>]+>", " ", html_content)
    plain_text = re.sub(r"\s+", " ", plain_text).strip()

    # If the content is already small, don't bother chunking
    if len(plain_text) <= chunk_size:
        logging.info(
            f"Content size ({len(plain_text)} chars) is smaller than chunk_size ({chunk_size}), skipping chunking"
        )
        return [{"content": plain_text, "metadata": {}}]

    # Estimate reasonable number of chunks based on content size
    estimated_chunks = len(plain_text) // (chunk_size - chunk_overlap) + 1
    if estimated_chunks > max_chunks:
        logging.warning(
            f"Content would generate too many chunks ({estimated_chunks}). Using simpler chunking method."
        )
        # Fall back to simple text splitting for very large content
        return _chunk_text_safely(plain_text, chunk_size, chunk_overlap, max_chunks)

    # If not HTML content, use default recursive text splitter
    if not content_type or "text/html" not in content_type.lower():
        return _chunk_text_safely(plain_text, chunk_size, chunk_overlap, max_chunks)

    # For HTML content, use the appropriate splitter based on the type
    try:
        if splitter_type == "header":
            # Use header-based chunking
            logging.info("Using header-based HTML chunking")
            headers_to_split_on = [
                ("h1", "Header 1"),
                ("h2", "Header 2"),
                ("h3", "Header 3"),
                ("h4", "Header 4"),
                ("h5", "Header 5"),
            ]
            html_splitter = HTMLHeaderTextSplitter(headers_to_split_on)
            split_docs = html_splitter.split_text(html_content)

        elif splitter_type == "section":
            # Use section-based chunking
            logging.info("Using section-based HTML chunking")
            headers_to_split_on = [
                ("h1", "Header 1"),
                ("h2", "Header 2"),
                ("h3", "Header 3"),
                ("h4", "Header 4"),
                ("h5", "Header 5"),
            ]
            html_splitter = HTMLSectionSplitter(headers_to_split_on)
            split_docs = html_splitter.split_text(html_content)

        else:
            # For semantic chunking, try simpler approach first for better reliability
            logging.info("Using recursive character-based text chunking for HTML")
            # Extract text and chunk it, preserving some basic HTML structure
            cleaned_html = _basic_clean_html(html_content)
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separators=["\n\n", "\n", ". ", " ", ""],
            )
            split_docs = text_splitter.create_documents([cleaned_html])

        # Apply safety checks
        if len(split_docs) > max_chunks:
            logging.warning(
                f"HTML splitting produced too many chunks ({len(split_docs)}). Limiting to {max_chunks}."
            )
            split_docs = split_docs[:max_chunks]

        # Convert to our expected format
        return [
            {"content": doc.page_content, "metadata": doc.metadata}
            for doc in split_docs
        ]

    except Exception as e:
        logging.warning(
            f"Error using HTML splitter: {str(e)}. Falling back to default chunker."
        )
        # Fallback to basic text splitting
        return _chunk_text_safely(plain_text, chunk_size, chunk_overlap, max_chunks)


def remove_javascript(html_content: str) -> str:
    """
    Aggressively remove all JavaScript code from HTML.

    Args:
        html_content: HTML content as string

    Returns:
        HTML content with JavaScript removed
    """
    # Remove all <script> tags and their contents
    cleaned = re.sub(r"<script[^>]*>.*?</script>", "", html_content, flags=re.DOTALL)

    # Remove onclick, onload and other JavaScript event attributes
    cleaned = re.sub(r' on\w+="[^"]*"', "", cleaned)
    cleaned = re.sub(r" on\w+='[^']*'", "", cleaned)

    # Remove JavaScript: URLs
    cleaned = re.sub(r'href="javascript:[^"]*"', 'href="#"', cleaned)
    cleaned = re.sub(r"href='javascript:[^']*'", "href='#'", cleaned)

    # Remove inline JS that might have been missed
    cleaned = re.sub(r"(\s)javascript:", r"\1", cleaned)

    return cleaned


def _chunk_text_safely(
    text: str, chunk_size: int = 1000, chunk_overlap: int = 200, max_chunks: int = 50
) -> list[dict[str, Any]]:
    """Safe text chunking with limits to prevent infinite loops"""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    try:
        docs = text_splitter.create_documents([text])

        # Safety check for too many chunks
        if len(docs) > max_chunks:
            logging.warning(
                f"Generated too many chunks ({len(docs)}). Limiting to {max_chunks}."
            )
            docs = docs[:max_chunks]

        return [{"content": doc.page_content, "metadata": {}} for doc in docs]
    except Exception as e:
        logging.error(f"Error chunking text: {str(e)}")
        # Last resort: manual chunking
        chunks = []
        for i in range(0, len(text), chunk_size - chunk_overlap):
            chunk = text[i : i + chunk_size]
            chunks.append({"content": chunk, "metadata": {}})
            if len(chunks) >= max_chunks:
                break
        return chunks


def _basic_clean_html(html_content: str) -> str:
    """
    Perform basic HTML cleaning to make text chunking more reliable
    while preserving important structural elements
    """
    # Remove script and style tags with their content
    cleaned = re.sub(r"<script[^>]*>.*?</script>", "", html_content, flags=re.DOTALL)
    cleaned = re.sub(r"<style[^>]*>.*?</style>", "", cleaned, flags=re.DOTALL)

    # Remove comments
    cleaned = re.sub(r"<!--.*?-->", "", cleaned, flags=re.DOTALL)

    # Convert headers to plain text with newlines
    cleaned = re.sub(r"<h1[^>]*>(.*?)</h1>", r"\n\n# \1\n\n", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"<h2[^>]*>(.*?)</h2>", r"\n\n## \1\n\n", cleaned, flags=re.DOTALL)
    cleaned = re.sub(
        r"<h3[^>]*>(.*?)</h3>", r"\n\n### \1\n\n", cleaned, flags=re.DOTALL
    )

    # Convert paragraphs and breaks to newlines
    cleaned = re.sub(r"<p[^>]*>(.*?)</p>", r"\n\n\1\n\n", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"<br[^>]*>", "\n", cleaned)

    # Convert lists to text with bullet points
    cleaned = re.sub(r"<li[^>]*>(.*?)</li>", r"\n• \1", cleaned, flags=re.DOTALL)

    # Remove other HTML tags
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)

    # Fix whitespace
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"\n\s+\n", "\n\n", cleaned)

    return cleaned.strip()
