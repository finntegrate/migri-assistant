"""
Parser module for migri-assistant.

This module contains parser classes for extracting structured content
from HTML files saved by the crawler module.
"""

from migri_assistant.parsers.base_parser import BaseParser
from migri_assistant.parsers.config_models import (
    HtmlToMarkdownConfig,
    ParserConfigRegistry,
    SiteParserConfig,
)
from migri_assistant.parsers.universal_parser import UniversalParser

__all__ = [
    "BaseParser",
    "HtmlToMarkdownConfig",
    "ParserConfigRegistry",
    "SiteParserConfig",
    "UniversalParser",
]
