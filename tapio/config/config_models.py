"""Configuration models for HTML content parsers.

This module contains Pydantic models that define the configuration for
site-specific HTML parsing, including content selectors and HTML-to-Markdown
conversion settings.
"""

from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator


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

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str) -> str:
        """Validate that base_url is a properly formatted URL.

        Args:
            v: URL value to validate

        Returns:
            The validated URL

        Raises:
            ValueError: If the URL is not valid (missing or has invalid scheme/netloc)
        """
        if not v:
            raise ValueError("base_url cannot be empty")

        parsed = urlparse(v)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError(f"Invalid URL: {v}. Must be a valid http or https URL with a domain name.")
        return v

    @property
    def base_dir(self) -> str:
        """Derive base directory from base_url.

        Extracts the domain from the base URL to use as the directory name.

        Returns:
            Domain name without protocol prefix (e.g., 'migri.fi')
        """
        parsed = urlparse(self.base_url or "")
        # Use hostname to strip any port, and ensure a non-empty result
        host = parsed.hostname
        if not host:
            raise ValueError(f"Invalid base_url: {self.base_url!r}")
        return host

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
