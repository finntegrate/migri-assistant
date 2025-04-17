import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

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
        site_name: str = None,
    ):
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

        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)

    def setup_logging(self):
        """Set up logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[logging.StreamHandler()],
        )
        self.logger = logging.getLogger(__name__)

    def parse_all(self, domain: Optional[str] = None) -> List[Dict]:
        """
        Parse all HTML files in the input directory, optionally filtered by domain.

        Args:
            domain: Optional domain to filter files by

        Returns:
            List of dictionaries containing information about the parsed files
        """
        results = []

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
        html_files = list(Path(html_dir).glob("**/*.html"))
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

    def parse_file(self, html_file: Union[str, Path]) -> Optional[Dict]:
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
            with open(html_file_path, "r", encoding="utf-8") as f:
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
                rel_path = html_file_path.name
                domain = "unknown"

            # Generate a filename for the output markdown
            output_filename = self._get_output_filename(html_file_path)

            # Parse the HTML content
            title, content = self._parse_html(html_content)

            # Create metadata for the markdown file
            metadata = {
                "source_file": str(html_file_path),
                "title": title,
                "domain": domain,
                "parse_timestamp": datetime.now().isoformat(),
                "parser": self.__class__.__name__,
            }

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
        self, filename: str, title: str, content: str, metadata: Dict
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

    def _create_index(self, results: List[Dict]) -> str:
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
