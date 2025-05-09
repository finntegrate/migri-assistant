"""Universal HTML content parser module.

This module contains the UniversalParser class, which loads site-specific
configurations and extracts content from HTML pages accordingly.
"""

import logging
import os

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

            # Convert HTML to Markdown using site-specific settings
            markdown_content = self._html_to_markdown(content_html)

            return title, markdown_content

        except Exception as e:
            self.logger.error(f"Error parsing HTML: {str(e)}")
            return "Error Parsing Page", f"Error parsing the HTML content: {str(e)}"

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
