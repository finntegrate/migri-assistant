"""HTML content parser module.

This module contains the Parser class, which loads site-specific
configurations and extracts content from HTML pages accordingly.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import html2text
import yaml
from lxml import html

from tapio.config.settings import DEFAULT_DIRS
from tapio.parser.config_models import (
    ParserConfigRegistry,
    SiteParserConfig,
)


class Parser:
    """
    HTML content parser that uses site-specific configurations.

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
        Initialize the parser.

        Args:
            site: Site to parse (must match a key in config)
            input_dir: Directory containing HTML files to parse
            output_dir: Directory to save parsed content
            config_path: Optional path to custom config file
        """
        self.site = site
        self.config = self._load_site_config(site, config_path)
        self.current_base_url: str | None = None  # Will store the base URL of the current document
        
        self.input_dir = input_dir
        self.output_dir = os.path.join(output_dir, self.config.site_name or "default")
        self.site_name = self.config.site_name
        self.setup_logging()

        # Load URL mappings if available
        self.url_mappings: dict[str, dict[str, str]] = {}
        self._load_url_mappings()

        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)

        logging.info(f"Initialized Parser for {self.config.site_name}")

    def setup_logging(self) -> None:
        """Set up logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[logging.StreamHandler()],
        )
        self.logger = logging.getLogger(__name__)

    def _load_url_mappings(self) -> None:
        """Load URL mappings from the JSON file"""
        mapping_file = os.path.join(self.input_dir, "url_mappings.json")
        if os.path.exists(mapping_file):
            try:
                with open(mapping_file, encoding="utf-8") as f:
                    self.url_mappings = json.load(f)
                self.logger.info(f"Loaded {len(self.url_mappings)} URL mappings")
            except Exception as e:
                self.logger.error(f"Error loading URL mappings: {str(e)}")
        else:
            self.logger.warning(f"URL mapping file not found: {mapping_file}")
            # Still continue processing - URL mappings are optional

    def _get_original_url(self, file_path: str | Path) -> str | None:
        """
        Get the original URL for a file path from the URL mappings.

        Args:
            file_path: Path to the HTML file

        Returns:
            Original URL or None if not found
        """
        # Handle Path objects by converting to string
        file_path_str = str(file_path)

        # Try to find the file in our mappings
        for key, value in self.url_mappings.items():
            # Check if the path ends with our key
            if file_path_str.endswith(key):
                return value.get("url")

        # Try to infer the key from the file path
        try:
            # Extract relative path from input_dir
            rel_path = os.path.relpath(file_path, self.input_dir)

            # Check for both slash directions (OS compatibility)
            if rel_path in self.url_mappings:
                return self.url_mappings[rel_path].get("url")

            # Try with forward slashes (URL style)
            rel_path_fwd = rel_path.replace("\\", "/")
            if rel_path_fwd in self.url_mappings:
                return self.url_mappings[rel_path_fwd].get("url")

            # Try with the filename only
            filename = os.path.basename(file_path)
            for key, value in self.url_mappings.items():
                if key.endswith(filename):
                    return value.get("url")
        except Exception as e:
            self.logger.debug(f"Error finding URL mapping for {file_path}: {e}")

        self.logger.debug(f"No URL mapping found for {file_path}")
        return None

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

    def _construct_base_url_from_path(self, file_path: str) -> str:
        """
        Construct base URL from file path when no URL mapping exists.

        Args:
            file_path: Path to the HTML file

        Returns:
            Constructed base URL
        """
        try:
            # Get the path relative to the input_dir/base_dir
            domain_dir = os.path.join(self.input_dir, self.config.base_dir)
            rel_path = os.path.relpath(file_path, domain_dir)
            
            # Only use relative path if it doesn't start with '..' (outside domain dir)
            if not rel_path.startswith(".."):
                rel_path = rel_path.replace("\\", "/")  # Normalize path separators
                constructed_url = urljoin(self.config.base_url, rel_path)
                self.logger.info(f"Constructed base URL: {constructed_url}")
                return constructed_url
            else:
                # Fallback to base_url if file is not in domain dir
                self.logger.info(f"Using base URL fallback: {self.config.base_url}")
                return self.config.base_url
        except ValueError:
            # Fallback to base_url if there's an error
            self.logger.info(f"Using base URL fallback: {self.config.base_url}")
            return self.config.base_url

    def _extract_domain_from_path(self, file_path: str | Path) -> str:
        """
        Extract domain name from a file path.

        Args:
            file_path: Path to the HTML file

        Returns:
            Domain name extracted from the file path or "unknown" if not found
        """
        try:
            # Get the path relative to the input directory
            rel_path = Path(file_path).relative_to(self.input_dir)
            domain_parts = rel_path.parts
            if len(domain_parts) > 0:
                domain = domain_parts[0]
            else:
                domain = "unknown"
            return domain
        except ValueError:
            return "unknown"

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
            self.current_base_url = self._construct_base_url_from_path(file_path_str)

        # Parse the file
        html_file_path = Path(html_file)
        self.logger.info(f"Parsing {html_file_path}")

        try:
            # Read the HTML content
            with open(html_file_path, encoding="utf-8") as f:
                html_content = f.read()

            # Get relative path from input directory for generating output file path
            try:
                # Convert rel_path from Path to str after getting the relative path
                rel_path_obj = html_file_path.relative_to(Path(self.input_dir))
                    # Get the relative path for generating output file path
                rel_path_obj = rel_path_obj
            except ValueError:
                # If file is not inside input_dir, use the filename
                rel_path_obj = Path(html_file_path.name)
            
            # Extract the domain from the file path
            domain = self._extract_domain_from_path(html_file_path)

            # Generate a filename for the output markdown
            output_filename = self._get_output_filename(html_file_path)

            # Parse the HTML content
            title, content = self._parse_html(html_content)

            # Create metadata for the markdown file
            metadata = self._create_metadata(html_file_path, title)

            # Save the content as Markdown with frontmatter
            output_path = self._save_markdown(output_filename, title, content, metadata)

            return {
                "source_file": str(html_file_path),
                "output_file": output_path,
                "title": title,
                "domain": domain,
            }

        except Exception as e:
            self.logger.error(f"Error parsing {html_file_path}: {str(e)}")
            return None

    def _create_metadata(self, file_path: str | Path, title: str) -> dict[str, Any]:
        """
        Create metadata for the markdown file including the original URL.

        Args:
            file_path: Path to the HTML file
            title: Title of the page

        Returns:
            Dictionary with metadata
        """
        # Extract domain using the helper method
        domain = self._extract_domain_from_path(file_path)

        # Basic metadata
        metadata = {
            "source_file": str(file_path),
            "title": title,
            "domain": domain,
            "parse_timestamp": datetime.now().isoformat(),
            "parser": self.__class__.__name__,
        }

        # Add the original URL to the metadata if available
        original_url = self._get_original_url(file_path)
        if original_url:
            metadata["source_url"] = original_url

        return metadata

    def _get_output_filename(self, html_file_path: Path) -> str:
        """
        Generate an output filename for the parsed markdown file.
        Preserves the directory structure from the input directory.

        Args:
            html_file_path: Path to the source HTML file

        Returns:
            Output filename with path (without extension)
        """
        # Try to extract relative path from the file path
        try:
            rel_path = html_file_path.relative_to(self.input_dir)
            parts = rel_path.parts

            # If there are parts (domain and path), preserve the structure
            if len(parts) >= 2:
                # Preserve the original directory structure but replace .html extension
                rel_output_path = str(rel_path).replace(".html", "")
                return rel_output_path
            else:
                # Just use filename if there's only one part
                return html_file_path.stem
        except ValueError:
            # If the file is not in the input directory, just use its name
            return html_file_path.stem

    def _save_markdown(
        self,
        filename: str,
        title: str,
        content: str,
        metadata: dict[str, Any],
    ) -> str:
        """
        Save content as a markdown file with YAML frontmatter.

        Args:
            filename: Base filename (without extension)
            title: Content title
            content: Markdown content
            metadata: Dictionary of metadata

        Returns:
            Path to the saved file
        """
        # Ensure filename has .md extension
        if not filename.endswith(".md"):
            filename = f"{filename}.md"

        # Create the full output path
        output_path = os.path.join(self.output_dir, filename)

        # Create parent directories if needed
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Prepare the markdown content with frontmatter
        frontmatter = yaml.dump(metadata, default_flow_style=False)
        markdown_content = f"---\n{frontmatter}---\n\n# {title}\n\n{content}\n"

        # Save the file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        self.logger.info(f"Saved markdown to {output_path}")
        return output_path

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
            results: list[dict[str, Any]] = []

            # Get all HTML files
            html_dir = self.input_dir

            # Find all HTML files recursively
            html_files = []
            for root, _, files in os.walk(html_dir):
                for file in files:
                    if file.endswith(".html"):
                        html_files.append(os.path.join(root, file))

            self.logger.info(f"Found {len(html_files)} HTML files to parse")

            # Parse each file
            for html_file in html_files:
                try:
                    result = self.parse_file(html_file)
                    if result:
                        results.append(result)
                except Exception as e:
                    self.logger.error(f"Error parsing {html_file}: {str(e)}")

            # Create an index file for all parsed files
            if results:
                self._create_index(results)

            self.logger.info(f"Parsed {len(results)} files")
            return results
        finally:
            # Restore the original input directory
            self.input_dir = original_input_dir

    def _create_index(self, results: list[dict[str, Any]]) -> str:
        """
        Create an index markdown file for all parsed content.

        Args:
            results: List of parsing results

        Returns:
            Path to the index file
        """
        index_path = os.path.join(self.output_dir, "index.md")

        with open(index_path, "w", encoding="utf-8") as f:
            f.write(f"# {self.site_name or 'Site'} Parsed Content Index\n\n")
            f.write(f"Total pages parsed: {len(results)}\n\n")
            f.write("| Title | Source File | Output File |\n")
            f.write("|-------|-------------|-------------|\n")

            for result in results:
                title = result.get("title", "Untitled")
                source = os.path.basename(result.get("source_file", ""))
                output = os.path.basename(result.get("output_file", ""))

                # Create relative links to the files
                f.write(f"| {title} | {source} | [{output}]({output}) |\n")

        self.logger.info(f"Created index at {index_path}")
        return index_path

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
