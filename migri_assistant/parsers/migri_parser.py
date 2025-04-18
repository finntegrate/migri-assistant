import logging

import html2text
from lxml import html

from migri_assistant.parsers.base_parser import BaseParser


class MigriParser(BaseParser):
    """
    Parser for Migri.fi website content.

    This parser extracts content specifically from migri.fi HTML pages,
    focusing on the main content area and preserving the structure.
    """

    def __init__(self, input_dir="crawled_content", output_dir="parsed_content"):
        """
        Initialize the MigriParser.

        Args:
            input_dir: Directory containing the HTML files to parse
            output_dir: Directory to save parsed content
        """
        super().__init__(input_dir, output_dir, site_name="migri")
        logging.info("Initialized MigriParser for Migri.fi content")
        # URL mappings are already loaded in BaseParser

    def _parse_html(self, html_content: str) -> tuple[str, str]:
        """
        Extract content from Migri.fi HTML pages, focusing on main content area.

        Args:
            html_content: Raw HTML content

        Returns:
            Tuple containing (title, content)
        """
        try:
            # Parse the HTML content
            tree = html.fromstring(html_content)

            # Extract the title
            title_elements = tree.xpath("//title")
            title = title_elements[0].text if title_elements else "Untitled"

            # Find the main content section - Migri.fi specific
            content_section = tree.xpath('//div[@id="main-content"]')
            if not content_section:
                # Try alternative content selectors if main-content not found
                content_section = (
                    tree.xpath("//main")
                    or tree.xpath("//article")
                    or tree.xpath('//div[@class="content"]')
                )

            if content_section:
                # Get the HTML of just this element
                content_html = html.tostring(
                    content_section[0],
                    encoding="unicode",
                    pretty_print=True,
                )
                self.logger.info("Successfully extracted main content section")
            else:
                # If no content section found, use the body
                body = tree.xpath("//body")
                content_html = (
                    html.tostring(body[0], encoding="unicode", pretty_print=True)
                    if body
                    else html_content
                )
                self.logger.warning(
                    "Could not find specific content section, using body content",
                )

            # Convert HTML to Markdown
            markdown_content = self._html_to_markdown(content_html)

            return title, markdown_content

        except Exception as e:
            self.logger.error(f"Error parsing HTML: {str(e)}")
            return "Error Parsing Page", f"Error parsing the HTML content: {str(e)}"

    def _html_to_markdown(self, html_content: str) -> str:
        """
        Convert HTML to Markdown using html2text with optimal settings.

        Args:
            html_content: HTML content to convert

        Returns:
            Markdown formatted text
        """
        # Configure html2text for optimal conversion
        text_maker = html2text.HTML2Text()
        text_maker.ignore_links = False  # Preserve links in the output
        text_maker.body_width = 0  # Don't wrap text
        text_maker.protect_links = True  # Don't wrap links
        text_maker.unicode_snob = True  # Use Unicode instead of ASCII
        text_maker.ignore_images = False  # Include images
        text_maker.ignore_tables = False  # Include tables

        # Convert HTML to Markdown
        markdown_text = text_maker.handle(html_content)

        return markdown_text
