import json
import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


class BaseParser(ABC):
    """
    Abstract base class for HTML content parsers.

    Parsers extract content from HTML files saved by the crawler and
    convert them to structured formats like Markdown.
    """

    def __init__(
        self,
        input_dir: str = "crawled_content",
        output_dir: str = "parsed_content",
        site_name: str | None = None,
    ) -> None:
        """
        Initialize the parser.

        Args:
            input_dir: Directory containing the HTML files to parse
            output_dir: Directory to save parsed content
            site_name: Name of the site (used for creating the output subdirectory)
        """
        self.input_dir = input_dir
        self.output_dir = os.path.join(output_dir, site_name or "default")
        self.site_name = site_name
        self.setup_logging()

        # Load URL mappings if available
        self.url_mappings: dict[str, dict[str, str]] = {}
        self._load_url_mappings()

        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)

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
        # Handle Path objects
        if hasattr(file_path, "as_posix"):
            file_path = file_path.as_posix()

        # Try to find the file in our mappings
        for key, value in self.url_mappings.items():
            # Check if the path ends with our key
            if file_path.endswith(key):
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

    def parse_all(self, domain: str | None = None) -> list[dict[str, Any]]:
        """
        Parse all HTML files in the input directory, optionally filtered by domain.

        Args:
            domain: Optional domain to filter files by

        Returns:
            List of dictionaries containing information about the parsed files
        """
        results: list[dict[str, Any]] = []

        # Get all HTML files
        if domain:
            # If domain is specified, look in that subdirectory
            html_dir = os.path.join(self.input_dir, domain)
            if not os.path.exists(html_dir):
                self.logger.warning(f"Domain directory not found: {html_dir}")
                return results
        else:
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

    def parse_file(self, html_file: str | Path) -> dict[str, Any] | None:
        """
        Parse a single HTML file.

        Args:
            html_file: Path to the HTML file

        Returns:
            Dictionary containing information about the parsed file
        """
        html_file_path = Path(html_file)
        self.logger.info(f"Parsing {html_file_path}")

        try:
            # Read the HTML content
            with open(html_file_path, encoding="utf-8") as f:
                html_content = f.read()

            # Get relative path from input directory for generating output file path
            try:
                rel_path = html_file_path.relative_to(self.input_dir)
                # Extract the domain from the relative path (first directory)
                domain_parts = rel_path.parts
                if len(domain_parts) > 0:
                    domain = domain_parts[0]
                else:
                    domain = "unknown"
            except ValueError:
                # If file is not inside input_dir, use the filename
                rel_path = Path(html_file_path.name)
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
        Create metadata for the markdown file including the original URL.

        Args:
            file_path: Path to the HTML file
            title: Title of the page

        Returns:
            Dictionary with metadata
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

    @abstractmethod
    def _parse_html(self, html_content: str) -> tuple[str, str]:
        """
        Parse HTML content and extract title and main content.

        Args:
            html_content: Raw HTML content

        Returns:
            Tuple containing (title, content)
        """
        pass

    def _get_output_filename(self, html_file_path: Path) -> str:
        """
        Generate an output filename for the parsed markdown file.

        Args:
            html_file_path: Path to the source HTML file

        Returns:
            Output filename (without extension)
        """
        # Try to extract domain from the file path
        try:
            rel_path = html_file_path.relative_to(self.input_dir)
            parts = rel_path.parts
            # If there are at least two parts (domain and path), use them
            if len(parts) >= 2:
                # Join all parts except the first (domain) with underscores
                file_stem = "_".join(parts[1:]).replace(".html", "")
            else:
                file_stem = html_file_path.stem
        except ValueError:
            # If the file is not in the input directory, just use its name
            file_stem = html_file_path.stem

        return file_stem

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
