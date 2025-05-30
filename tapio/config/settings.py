"""Global configuration settings for the migri-assistant application.

This module contains common configuration settings used across different
components of the migri-assistant application, including default directories
for storing crawled and parsed content.
"""

DEFAULT_CONTENT_DIR = "content"

# Default directory paths
DEFAULT_DIRS = {
    "CRAWLED_DIR": "crawled",
    "PARSED_DIR": "parsed",
    "CHROMA_DIR": "chroma_db",
}

DEFAULT_CHROMA_COLLECTION = "tapio_knowledge"
DEFAULT_CRAWLER_TIMEOUT = 30
