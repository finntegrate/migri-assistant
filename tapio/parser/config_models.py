"""Configuration models for HTML content parsers.

This module contains Pydantic models that define the configuration for
site-specific HTML parsing, including content selectors and HTML-to-Markdown
conversion settings.
"""

from typing import Any

from pydantic import BaseModel, Field


class HtmlToMarkdownConfig(BaseModel):
    """Configuration settings for HTML to Markdown conversion.

    Customizes how HTML elements are converted to Markdown. These settings are
    mapped to html2text options.
    """

    ignore_links: bool = False
    body_width: int = 0  # Don't wrap text
    protect_links: bool = True  # Don't wrap links
    unicode_snob: bool = True  # Use Unicode instead of ASCII
    ignore_images: bool = False  # Include images
    ignore_tables: bool = False  # Include tables


class SiteParserConfig(BaseModel):
    """Configuration for site-specific HTML parsing.

    Defines how content is extracted from HTML pages, including the selectors
    used to identify important page elements and conversion settings.
    """

    site_name: str
    base_url: str = Field(
        "https://example.com",
        description="Base URL of the website (e.g., 'https://migri.fi')",
    )
    title_selector: str = "//title"
    content_selectors: list[str] = Field(
        ...,
        description="Priority-ordered list of XPath selectors to find content",
    )
    fallback_to_body: bool = True
    description: str | None = None
    markdown_config: HtmlToMarkdownConfig = Field(default_factory=HtmlToMarkdownConfig)

    @property
    def base_dir(self) -> str:
        """Derive base directory from base_url.

        Extracts the domain from the base URL to use as the directory name.

        Returns:
            Domain name without protocol prefix (e.g., 'migri.fi')
        """
        from urllib.parse import urlparse

        parsed_url = urlparse(self.base_url)
        return parsed_url.netloc

    def get_content_selector(self, tree: Any) -> Any | None:
        """Find the first matching content element using the configured selectors.

        Args:
            tree: An lxml HTML tree to search

        Returns:
            The first matching element or None if no match is found
        """
        for selector in self.content_selectors:
            elements = tree.xpath(selector)
            if elements:
                return elements[0]
        return None


class ParserConfigRegistry(BaseModel):
    """Registry of all site parser configurations."""

    sites: dict[str, SiteParserConfig]
