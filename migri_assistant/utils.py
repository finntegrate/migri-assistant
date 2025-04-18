"""
DEPRECATED: Utility functions for the migri-assistant package.

This module is deprecated and will be removed in a future version.
Please import from migri_assistant.utils.text_utils instead.
"""

import warnings

# Emit deprecation warning
warnings.warn(
    "The module migri_assistant.utils is deprecated. "
    "Please use migri_assistant.utils.text_utils instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export utilities from the new modules
from migri_assistant.utils.text_utils import (
    chunk_html_content,
    is_pdf_url,
    remove_javascript,
)

# These imports are kept here for backwards compatibility

# All exports from this module
__all__ = [
    "is_pdf_url",
    "chunk_html_content",
    "remove_javascript",
]
