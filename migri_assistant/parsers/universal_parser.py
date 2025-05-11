"""Universal HTML content parser module.

This module contains the UniversalParser class, which loads site-specific
configurations and extracts content from HTML pages accordingly.
"""

import logging
import os
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import html2text
import yaml
from lxml import html

from migri_assistant.parsers.base_parser import BaseParser
from migri_assistant.parsers.config_models import (
    ParserConfigRegistry,
    SiteParserConfig,
)


class UniversalParser(BaseParser):
    """
    Universal HTML content parser that uses site-specific configurations.

    This parser loads configurations for different websites and extracts
    content using the appropriate selectors for each site.
    """

    def __init__(
        self,
        site_type: str,
        input_dir: str = "crawled_content",
        output_dir: str = "parsed_content",
        config_path: str | None = None,
    ):
        """
        Initialize the universal parser.

        Args:
            site_type: Type of site to parse (must match a key in config)
            input_dir: Directory containing HTML files to parse
            output_dir: Directory to save parsed content
            config_path: Optional path to custom config file
        """
        self.site_type = site_type
        self.config = self._load_site_config(site_type, config_path)
        self.current_base_url: str | None = None  # Will store the base URL of the current document

        super().__init__(
            input_dir=input_dir,
            output_dir=output_dir,
            site_name=self.config.site_name,
        )

        logging.info(f"Initialized UniversalParser for {self.config.site_name}")

    def _load_site_config(self, site_type: str, config_path: str | None = None) -> SiteParserConfig:
        """
        Load site-specific configuration.

        Args:
            site_type: Type of site to load config for
            config_path: Optional path to custom config file

        Returns:
            SiteParserConfig for the specified site type
        """
        # Load default or custom configs
        config_registry = self._load_config_registry(config_path)

        # Check if the site type exists in our registry
        if site_type not in config_registry.sites:
            raise ValueError(f"No configuration found for site type: {site_type}")

        return config_registry.sites[site_type]

    @staticmethod
    def _load_config_registry(config_path: str | None = None) -> ParserConfigRegistry:
        """
        Load the configuration registry from file.

        Args:
            config_path: Optional path to custom config file

        Returns:
            ParserConfigRegistry containing all site configurations
        """
        # Default config path in the package
        if not config_path:
            config_path = os.path.join(os.path.dirname(__file__), "../config/parser_configs.yaml")

        try:
            with open(config_path) as f:
                config_data = yaml.safe_load(f)
                return ParserConfigRegistry.model_validate(config_data)
        except Exception as e:
            logging.error(f"Error loading parser config: {str(e)}")
            raise

    def _parse_html(self, html_content: str) -> tuple[str, str]:
        """
        Parse HTML content using site-specific selectors.

        Args:
            html_content: Raw HTML content

        Returns:
            Tuple containing (title, content)
        """
        try:
            # Parse the HTML content
            tree = html.fromstring(html_content)

            # Extract the title using the configured selector
            title_elements = tree.xpath(self.config.title_selector)
            title = title_elements[0].text if title_elements else "Untitled"

            # Find content using the configured selectors
            content_section = self.config.get_content_selector(tree)

            # Prepare HTML content for conversion
            if content_section is not None:
                # Get the HTML of just this element
                content_html = html.tostring(
                    content_section,
                    encoding="unicode",
                    pretty_print=True,
                )
                self.logger.info("Successfully extracted content section")
            elif self.config.fallback_to_body:
                # If no content section found and fallback is enabled, use the body
                body = tree.xpath("//body")
                content_html = (
                    html.tostring(body[0], encoding="unicode", pretty_print=True)
                    if body
                    else html_content
                )
                self.logger.warning(
                    "Could not find specific content section, using body content",
                )
            else:
                # Return empty content if no fallback and no match
                self.logger.warning("No content found and no fallback configured")
                content_html = ""

            # Convert relative links to absolute links
            content_html = self._convert_relative_links_to_absolute(content_html)

            # Convert HTML to Markdown using site-specific settings
            markdown_content = self._html_to_markdown(content_html)

            return title, markdown_content

        except Exception as e:
            self.logger.error(f"Error parsing HTML: {str(e)}")
            return "Error Parsing Page", f"Error parsing the HTML content: {str(e)}"

    def _convert_relative_links_to_absolute(self, html_content: str) -> str:
        """
        Convert relative links in HTML content to absolute URLs.

        Args:
            html_content: HTML content with potentially relative links

        Returns:
            HTML content with relative links converted to absolute URLs
        """
        if not self.current_base_url:
            return html_content  # No base URL available, return unchanged

        try:
            # Parse the HTML
            tree = html.fromstring(html_content)

            # Find all links and image sources
            for element in tree.xpath("//*[@href]"):
                href = element.get("href")
                if href and not href.startswith(("http://", "https://", "mailto:", "#", "tel:")):
                    absolute_url = urljoin(self.current_base_url, href)
                    element.set("href", absolute_url)

            # Find all images
            for element in tree.xpath("//*[@src]"):
                src = element.get("src")
                if src and not src.startswith(("http://", "https://", "data:")):
                    absolute_url = urljoin(self.current_base_url, src)
                    element.set("src", absolute_url)

            # Convert back to string
            return html.tostring(tree, encoding="unicode", pretty_print=True)
        except Exception as e:
            self.logger.error(f"Error converting relative links: {str(e)}")
            return html_content  # Return original content if there's an error

    def _html_to_markdown(self, html_content: str) -> str:
        """
        Convert HTML to Markdown using site-specific configuration.

        Args:
            html_content: HTML content to convert

        Returns:
            Markdown formatted text
        """
        # First convert any relative links to absolute links
        if self.current_base_url:
            html_content = self._convert_relative_links_to_absolute(html_content)

        # Configure html2text with site-specific settings
        config = self.config.markdown_config
        text_maker = html2text.HTML2Text()
        text_maker.ignore_links = config.ignore_links
        text_maker.body_width = config.body_width
        text_maker.protect_links = config.protect_links
        text_maker.unicode_snob = config.unicode_snob
        text_maker.ignore_images = config.ignore_images
        text_maker.ignore_tables = config.ignore_tables

        # Convert HTML to Markdown
        markdown_text = text_maker.handle(html_content)

        return markdown_text

    @classmethod
    def list_available_site_configs(cls, config_path: str | None = None) -> list[str]:
        """
        List all available site configurations.

        Args:
            config_path: Optional path to custom config file

        Returns:
            List of available site configuration keys
        """
        config_registry = cls._load_config_registry(config_path)
        return list(config_registry.sites.keys())

    @classmethod
    def get_site_config(
        cls,
        site_type: str,
        config_path: str | None = None,
    ) -> SiteParserConfig | None:
        """
        Get detailed information about a specific site configuration.

        Args:
            site_type: Site type to get configuration for
            config_path: Optional path to custom config file

        Returns:
            SiteParserConfig for the specified site, or None if not found
        """
        config_registry = cls._load_config_registry(config_path)
        return config_registry.sites.get(site_type)

    def parse_file(self, html_file: str | Path) -> dict[str, Any] | None:
        """
        Parse a single HTML file.

        Args:
            html_file: Path to the HTML file

        Returns:
            Dictionary containing information about the parsed file
        """
        # Get the original URL of this file to use as base URL for relative links
        self.current_base_url = self._get_original_url(html_file)
        if self.current_base_url:
            self.logger.info(f"Using base URL: {self.current_base_url}")
        else:
            self.logger.warning(
                f"No base URL found for {html_file}, relative links won't be converted",
            )

        # Call the parent method to continue with parsing
        return super().parse_file(html_file)
