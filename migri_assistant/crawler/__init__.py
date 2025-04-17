"""
Crawler module for migri-assistant.

This module contains the base crawler class and runner for crawling websites
and saving HTML content. The crawler focuses solely on retrieving and saving
HTML content without parsing or processing it.
"""

from migri_assistant.crawler.crawler import BaseCrawler
from migri_assistant.crawler.runner import ScrapyRunner

__all__ = ["BaseCrawler", "ScrapyRunner"]
