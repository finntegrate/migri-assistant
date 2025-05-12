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

from migri_assistant.config.settings import DEFAULT_DIRS
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
        site: str,
        input_dir: str = DEFAULT_DIRS["CRAWLED_DIR"],
        output_dir: str = DEFAULT_DIRS["PARSED_DIR"],
        config_path: str | None = None,
    ):
        """
        Initialize the universal parser.

        Args:
            site: Site to parse (must match a key in config)
            input_dir: Directory containing HTML files to parse
            output_dir: Directory to save parsed content
            config_path: Optional path to custom config file
        """
        self.site = site
        self.config = self._load_site_config(site, config_path)
        self.current_base_url: str | None = None  # Will store the base URL of the current document

        super().__init__(
            input_dir=input_dir,
            output_dir=output_dir,
            site_name=self.config.site_name,
        )

        logging.info(f"Initialized UniversalParser for {self.config.site_name}")

    def _load_site_config(self, site: str, config_path: str | None = None) -> SiteParserConfig:
        """
        Load site-specific configuration and validate required fields.

        Args:
            site: Site to load config for
            config_path: Optional path to custom config file

        Returns:
            SiteParserConfig for the specified site

        Raises:
            ValueError: If the site doesn't exist or configuration is invalid
        """
        # Load default or custom configs
        config_registry = self._load_config_registry(config_path)

        # Check if the site exists in our registry
        if site not in config_registry.sites:
            raise ValueError(f"No configuration found for site: {site}")

        config = config_registry.sites[site]

        # Validate required fields
        if not config.base_url or not config.base_url.startswith(("http://", "https://")):
            raise ValueError(
                f"Invalid base_url '{config.base_url}' for site '{site}'. "
                "Must be a valid absolute URL starting with http:// or https://",
            )

        if not config.base_dir:
            raise ValueError(
                f"Missing base_dir for site '{site}'. "
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

    @staticmethod
    def _convert_element_link_to_absolute(
        element: html.HtmlElement,
        attribute: str,
        base_url: str,
        absolute_prefixes: tuple[str, ...],
    ) -> bool:
        """
        Convert a single element's link attribute to absolute URL if it's relative.

        Args:
            element: HTML element to process
            attribute: Attribute name (e.g., 'href', 'src')
            base_url: Base URL to use for conversion
            absolute_prefixes: Tuple of prefixes that indicate absolute URLs

        Returns:
            True if the link was converted, False otherwise
        """
        link = element.get(attribute)
        if not link or link.startswith(absolute_prefixes):
            return False

        absolute_url = urljoin(base_url, link)
        element.set(attribute, absolute_url)
        return True

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

            # Define absolute prefixes for different attribute types
            href_prefixes = ("http://", "https://", "//", "mailto:", "#", "tel:")
            src_prefixes = ("http://", "https://", "//", "data:")

            # Find all links and process them
            for element in tree.xpath("//*[@href]"):
                self._convert_element_link_to_absolute(
                    element,
                    "href",
                    self.current_base_url,
                    href_prefixes,
                )

            # Find all images and process them
            for element in tree.xpath("//*[@src]"):
                self._convert_element_link_to_absolute(
                    element,
                    "src",
                    self.current_base_url,
                    src_prefixes,
                )

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
        site: str,
        config_path: str | None = None,
    ) -> SiteParserConfig | None:
        """
        Get detailed information about a specific site configuration.

        Args:
            site: Site to get configuration for
            config_path: Optional path to custom config file

        Returns:
            SiteParserConfig for the specified site, or None if not found
        """
        config_registry = cls._load_config_registry(config_path)
        return config_registry.sites.get(site)

    def parse_file(self, html_file: str | Path) -> dict[str, Any] | None:
        """
        Parse a single HTML file from the configured domain.

        Args:
            html_file: Path to the HTML file

        Returns:
            Dictionary containing information about the parsed file
        """
        # Get the original URL of this file from URL mappings if available
        self.current_base_url = self._get_original_url(html_file)

        # If no URL mapping found, construct URL from configuration and file path
        if not self.current_base_url:
            file_path_str = str(html_file)

            # Create a relative path from the file path
            try:
                # Get the path relative to the input_dir/base_dir
                domain_dir = os.path.join(self.input_dir, self.config.base_dir)
                rel_path = os.path.relpath(file_path_str, domain_dir)

                # Only use relative path if it doesn't start with '..' (outside domain dir)
                if not rel_path.startswith(".."):
                    rel_path = rel_path.replace("\\", "/")  # Normalize path separators
                    self.current_base_url = urljoin(self.config.base_url, rel_path)
                    self.logger.info(
                        f"Constructed base URL: {self.current_base_url}",
                    )
                else:
                    # Fallback to base_url if file is not in domain dir
                    self.current_base_url = self.config.base_url
                    self.logger.info(f"Using base URL fallback: {self.current_base_url}")
            except ValueError:
                # Fallback to base_url if there's an error
                self.current_base_url = self.config.base_url
                self.logger.info(f"Using base URL fallback: {self.current_base_url}")

        # Call the parent method to continue with parsing
        return super().parse_file(html_file)

    def _is_file_in_domain_dir(self, file_path: str | Path) -> bool:
        """
        Check if a file is within the specified domain directory.

        This is a utility method used internally to verify file locations.

        Args:
            file_path: Path to the file to check

        Returns:
            True if the file is within the domain directory, False otherwise
        """
        domain_dir = os.path.join(self.input_dir, self.config.base_dir)
        file_path_str = str(file_path)

        try:
            rel_path = os.path.relpath(file_path_str, domain_dir)
            return not rel_path.startswith("..")
        except ValueError:
            return False

    def parse_all(self) -> list[dict[str, Any]]:
        """
        Parse all HTML files in the configured site's directory.

        This parser is focused on processing only files within the specific
        domain directory defined in the configuration.

        Returns:
            List of dictionaries containing information about parsed files
        """
        self.logger.info(
            f"Parsing HTML files for site '{self.site}' from directory '{self.config.base_dir}'",
        )

        # To limit processing to only files in the site's configured directory,
        # we need to temporarily change the input_dir
        original_input_dir = self.input_dir
        self.input_dir = os.path.join(original_input_dir, self.config.base_dir)

        try:
            return super().parse_all()
        finally:
            # Restore the original input directory
            self.input_dir = original_input_dir
