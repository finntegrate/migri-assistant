"""Utilities for working with markdown content."""

import logging
import os

import frontmatter

logger = logging.getLogger(__name__)


def read_markdown_file(file_path: str) -> tuple[dict, str]:
    """
    Read a markdown file with frontmatter and return the metadata and content separately.

    Args:
        file_path: Path to the markdown file

    Returns:
        Tuple containing the metadata dictionary and content string
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            post = frontmatter.load(f)
            metadata = post.metadata
            content = post.content

            # Handle source URL from metadata - prioritize source_url added by parser
            if "source_url" in metadata:
                # A direct URL from our crawler mapping
                metadata["url"] = metadata["source_url"]
            elif "source_file" in metadata:
                # Fallback to legacy handling
                source_file = metadata["source_file"]
                if isinstance(source_file, str):
                    metadata["url"] = source_file.replace("crawled_content/", "")

            return metadata, content
    except Exception as e:
        logger.error(f"Error reading markdown file {file_path}: {e}")
        return {}, ""


def find_markdown_files(directory: str, domain_filter: str | None = None) -> list[str]:
    """
    Find all markdown files in a directory, optionally filtering by domain.

    Args:
        directory: Directory to search for markdown files
        domain_filter: Optional domain name to filter by (e.g. 'migri.fi')

    Returns:
        List of paths to markdown files
    """
    markdown_files = []

    try:
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith(".md"):
                    file_path = os.path.join(root, file)

                    # Apply domain filter if specified
                    if domain_filter:
                        # Read just the metadata to check domain
                        try:
                            with open(file_path, encoding="utf-8") as f:
                                post = frontmatter.load(f)
                                if (
                                    "domain" in post.metadata
                                    and domain_filter in post.metadata["domain"]
                                ):
                                    markdown_files.append(file_path)
                        except Exception:
                            # Skip files that can't be parsed
                            pass
                    else:
                        markdown_files.append(file_path)
    except Exception as e:
        logger.error(f"Error finding markdown files: {e}")

    return markdown_files
