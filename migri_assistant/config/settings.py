"""Global configuration settings for the migri-assistant application.

This module contains common configuration settings used across different
components of the migri-assistant application, including default directories
for storing crawled and parsed content.
"""

# Default directory paths
DEFAULT_DIRS = {
    "CRAWLED_DIR": "content/crawled",
    "PARSED_DIR": "content/parsed",
    "CHROMA_DIR": "chroma_db",
}
