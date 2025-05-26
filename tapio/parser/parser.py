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
        Initializes a Parser instance for site-specific HTML parsing and content extraction.
        
        Sets up configuration, logging, URL mappings, and output directories for processing HTML files from the specified site.
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
        """
        Configures logging for the parser with a standard format and INFO level.
        
        Initializes a logger instance for use within the parser.
        """
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[logging.StreamHandler()],
        )
        self.logger = logging.getLogger(__name__)

    def _load_url_mappings(self) -> None:
        """
        Loads URL mappings from a JSON file in the input directory if available.
        
        If the file exists, populates the internal URL mappings dictionary; otherwise, logs a warning and continues without mappings.
        """
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
        Retrieves the original URL associated with a given HTML file path using loaded URL mappings.
        
        Attempts to match the file path against known mapping keys using various strategies, including suffix matching, relative path extraction, and filename matching. Returns the corresponding URL if found, or None otherwise.
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
        Loads and validates the configuration for a specific site.
        
        Args:
            site: The key identifying the site whose configuration should be loaded.
            config_path: Optional path to a custom configuration file.
        
        Returns:
            The validated site-specific configuration.
        
        Raises:
            ValueError: If the site configuration is missing or required fields are invalid.
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
        Converts HTML content to Markdown using site-specific formatting options.
        
        Args:
            html_content: The HTML content to be converted.
        
        Returns:
            The converted content as a Markdown-formatted string.
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
        Constructs a base URL for a file based on its path relative to the domain directory.
        
        If the file resides within the configured domain directory, the returned URL appends the file's relative path to the site's base URL. If the file is outside the domain directory or an error occurs, the base URL is returned as a fallback.
        
        Args:
            file_path: The path to the HTML file for which to construct the base URL.
        
        Returns:
            The constructed base URL as a string.
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

    def parse_file(self, html_file: str | Path) -> dict[str, Any] | None:
        """
        Parses a single HTML file, extracting content and metadata, and saves it as a Markdown file.
        
        Reads the HTML file, determines its original or constructed URL, extracts the title and main content, generates metadata, and writes the result as a Markdown file with YAML frontmatter. Returns a dictionary with details about the parsed file, or None if parsing fails.
        
        Args:
            html_file: Path to the HTML file to be parsed.
        
        Returns:
            A dictionary containing the source file path, output Markdown file path, extracted title, and domain, or None if an error occurs.
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
                # Extract the domain from the relative path (first directory)
                domain_parts = rel_path_obj.parts
                if len(domain_parts) > 0:
                    domain = domain_parts[0]
                else:
                    domain = "unknown"
            except ValueError:
                # If file is not inside input_dir, use the filename
                rel_path_obj = Path(html_file_path.name)
                domain = "unknown"

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
        Generates metadata for a parsed HTML file, including source path, title, domain, timestamp, parser name, and original URL if available.
        
        Returns:
            A dictionary containing metadata for the Markdown output.
        """
        # Try to get the domain from the path
        try:
            rel_path = Path(file_path).relative_to(self.input_dir)
            domain_parts = rel_path.parts
            if len(domain_parts) > 0:
                domain = domain_parts[0]
            else:
                domain = "unknown"
        except ValueError:
            domain = "unknown"

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
        Generates the output filename for a parsed Markdown file, preserving the directory structure relative to the input directory and removing the `.html` extension.
        
        Args:
            html_file_path: The path to the source HTML file.
        
        Returns:
            The output filename with its relative path, excluding the file extension.
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
        Saves Markdown content with YAML frontmatter to a file.
        
        Args:
            filename: The base filename (without extension) for the output file.
            title: The title to include at the top of the Markdown content.
            content: The main Markdown content to save.
            metadata: Metadata to include as YAML frontmatter.
        
        Returns:
            The full path to the saved Markdown file.
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
        Determines whether a file resides within the configured domain directory.
        
        Args:
            file_path: The path to the file to check.
        
        Returns:
            True if the file is located inside the domain directory; otherwise, False.
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
        Parses all HTML files within the site's configured directory and generates an index.
        
        Recursively processes each HTML file in the domain-specific directory, extracts content and metadata, saves the results as Markdown files, and creates an index file summarizing all parsed pages.
        
        Returns:
            A list of dictionaries, each containing information about a parsed file.
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
        Creates a Markdown index file listing all parsed pages with links, titles, and source files.
        
        Args:
            results: A list of dictionaries containing parsing results for each file.
        
        Returns:
            The file path to the generated index Markdown file.
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
        Lists all available site configuration keys from the configuration registry.
        
        Args:
            config_path: Optional path to a custom configuration file.
        
        Returns:
            A list of site configuration keys available in the registry.
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
        Retrieves the configuration for a specific site.
        
        Args:
            site: The site key to look up in the configuration registry.
            config_path: Optional path to a custom configuration file.
        
        Returns:
            The site-specific configuration if found, otherwise None.
        """
        config_registry = cls._load_config_registry(config_path)
        return config_registry.sites.get(site)
