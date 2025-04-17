"""
Parser module for migri-assistant.

This module contains parser classes for extracting structured content
from HTML files saved by the crawler module.
"""

from migri_assistant.parsers.base_parser import BaseParser
from migri_assistant.parsers.migri_parser import MigriParser

__all__ = ["BaseParser", "MigriParser"]
