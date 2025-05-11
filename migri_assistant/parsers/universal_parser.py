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
        Load site-specific configuration and validate required fields.

        Args:
            site_type: Type of site to load config for
            config_path: Optional path to custom config file

        Returns:
            SiteParserConfig for the specified site type

        Raises:
            ValueError: If the site type doesn't exist or configuration is invalid
        """
        # Load default or custom configs
        config_registry = self._load_config_registry(config_path)

        # Check if the site type exists in our registry
        if site_type not in config_registry.sites:
            raise ValueError(f"No configuration found for site type: {site_type}")

        config = config_registry.sites[site_type]

        # Validate required fields
        if not config.base_url or not config.base_url.startswith(("http://", "https://")):
            raise ValueError(
                f"Invalid base_url '{config.base_url}' for site type '{site_type}'. "
                "Must be a valid absolute URL starting with http:// or https://",
            )

        if not config.base_dir:
            raise ValueError(
                f"Missing base_dir for site type '{site_type}'. "
                "This field is required for domain-specific URL handling",
            )

        return config

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
            Dictionary containing information about the parsed file or None if the
            file doesn't belong to the configured site
        """
        # Verify the file belongs to the specified site before parsing
        file_domain = self._extract_domain_from_path(html_file)

        if not file_domain or file_domain != self.config.base_dir:
            self.logger.info(
                f"Skipping {html_file}: Does not belong to {self.site_type} site "
                f"(expected domain: {self.config.base_dir}, found: {file_domain})",
            )
            return None

        # Get the original URL of this file from URL mappings if available
        self.current_base_url = self._get_original_url(html_file)

        # If no URL mapping found, construct the URL from configuration and file path
        if not self.current_base_url:
            file_path_str = str(html_file)
            # Extract path after base_dir
            path_parts = file_path_str.split(self.config.base_dir)
            if len(path_parts) > 1:
                relative_path = path_parts[1].lstrip("/")
                # Construct URL from base_url and the relative path
                self.current_base_url = f"{self.config.base_url}/{relative_path}"
                self.logger.info(f"Constructed base URL from config: {self.current_base_url}")
            else:
                # If we can't extract a path, use the base_url as fallback
                self.current_base_url = self.config.base_url
                self.logger.info(f"Using config base URL as fallback: {self.current_base_url}")

        self.logger.info(f"Using base URL: {self.current_base_url}")

        # Call the parent method to continue with parsing
        return super().parse_file(html_file)

    def _file_belongs_to_domain(self, file_path: str | Path) -> bool:
        """
        Check if a file belongs to the configured domain based on its path.

        Args:
            file_path: Path to the file to check

        Returns:
            True if the file belongs to the configured domain, False otherwise
        """
        # Get the domain from the file path
        domain = self._extract_domain_from_path(file_path)

        # Check if the domain matches the configured domain
        return domain == self.config.base_dir

    def _extract_domain_from_path(self, file_path: str | Path) -> str | None:
        """
        Extract the domain part from a file path.

        Args:
            file_path: Path to the file

        Returns:
            Domain name or None if not found
        """
        try:
            path = Path(file_path)
            # Try to extract domain from the path structure:
            # input_dir/domain/path/to/file.html
            relative_to_input = path.relative_to(self.input_dir)
            if len(relative_to_input.parts) > 0:
                return relative_to_input.parts[0]
        except (ValueError, IndexError):
            # If the file is not relative to input_dir, check if it contains the domain directly
            file_path_str = str(file_path)
            if self.config.base_dir in file_path_str:
                return self.config.base_dir

        return None

    def parse_all(self, domain: str | None = None) -> list[dict[str, Any]]:
        """
        Parse all HTML files in the input directory for the configured site.

        This override ensures we only parse files for the specific site
        we've been configured to handle.

        Args:
            domain: If provided, this will override the configured domain
                   (maintained for backward compatibility)

        Returns:
            List of dictionaries containing information about the parsed files
        """
        # If no domain is explicitly provided, use the one from the configuration
        domain_to_use = domain if domain is not None else self.config.base_dir

        self.logger.info(
            f"Parsing all HTML files for site '{self.site_type}' with domain '{domain_to_use}'",
        )

        # Use the specified domain or the configured one
        return super().parse_all(domain=domain_to_use)
