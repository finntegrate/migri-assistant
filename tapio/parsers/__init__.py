"""
Parser module for migri-assistant.

This module contains the Parser class for extracting structured content
from HTML files saved by the crawler module.
"""

from tapio.parsers.config_models import (
    HtmlToMarkdownConfig,
    ParserConfigRegistry,
    SiteParserConfig,
)
from tapio.parsers.parser import Parser

__all__ = [
    "HtmlToMarkdownConfig",
    "Parser",
    "ParserConfigRegistry",
    "SiteParserConfig",
]
