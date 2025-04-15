"""Utility functions for the migri-assistant package."""

import re
from typing import List


def chunk_text(
    text: str, chunk_size: int = 1000, chunk_overlap: int = 200
) -> List[str]:
    """
    Split a long text into overlapping chunks of approximately chunk_size characters.

    Args:
        text: The text to split into chunks
        chunk_size: The target size of each chunk in characters
        chunk_overlap: The number of characters to overlap between chunks

    Returns:
        A list of text chunks
    """
    if not text or chunk_size <= 0:
        return []

    if len(text) <= chunk_size:
        return [text]

    # Ensure chunk_overlap is smaller than chunk_size
    chunk_overlap = min(chunk_overlap, chunk_size - 100)

    # Split text into paragraphs first
    paragraphs = re.split(r"\n\s*\n", text)

    chunks = []
    current_chunk = ""

    for paragraph in paragraphs:
        # If adding this paragraph would exceed chunk_size
        if len(current_chunk) + len(paragraph) > chunk_size:
            # If the current chunk has content, add it to chunks
            if current_chunk:
                chunks.append(current_chunk.strip())

            # Start a new chunk with this paragraph
            current_chunk = paragraph
        else:
            # Add paragraph to the current chunk
            if current_chunk:
                current_chunk += "\n\n" + paragraph
            else:
                current_chunk = paragraph

    # Add the last chunk if it has content
    if current_chunk:
        chunks.append(current_chunk.strip())

    # Create overlapping chunks if needed
    if chunk_overlap > 0 and len(chunks) > 1:
        overlapped_chunks = []

        for i, chunk in enumerate(chunks):
            if i > 0:
                # Get the end of the previous chunk to create overlap
                prev_chunk = chunks[i - 1]
                overlap_text = (
                    prev_chunk[-chunk_overlap:]
                    if len(prev_chunk) > chunk_overlap
                    else prev_chunk
                )
                # Add the overlap to the beginning of this chunk
                chunk = overlap_text + "\n\n" + chunk

            overlapped_chunks.append(chunk)

        return overlapped_chunks

    return chunks


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
