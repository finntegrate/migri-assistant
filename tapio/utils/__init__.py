"""Utility modules for Tapio Assistant."""

# Import and expose functions from embedding_utils
from tapio.utils.embedding_utils import EmbeddingGenerator

# Import and expose functions from markdown_utils
from tapio.utils.markdown_utils import (
    find_markdown_files,
    read_markdown_file,
)

# Import and expose functions from text_utils
from tapio.utils.text_utils import (
    chunk_html_content,
    is_pdf_url,
    remove_javascript,
)

__all__ = [
    # Embedding utilities
    "EmbeddingGenerator",
    # Markdown utilities
    "read_markdown_file",
    "find_markdown_files",
    # Text utilities
    "chunk_html_content",
    "is_pdf_url",
    "remove_javascript",
]
