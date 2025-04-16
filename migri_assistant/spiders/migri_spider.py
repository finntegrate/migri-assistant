import logging
from typing import Dict, Optional

import html2text
from lxml import html

from migri_assistant.spiders.web_spider import WebSpider


class MigriSpider(WebSpider):
    """
    Specialized spider for crawling and extracting content from Migri.fi website.

    This spider specifically targets the content within <section id="content" role="main">
    to avoid duplicating navigation menus and footers in the extracted content.
    """

    name = "migri_spider"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        logging.info("Initialized MigriSpider for Migri.fi content extraction")

    def _extract_html_content(self, response):
        """
        Extract only the main content from Migri.fi pages, targeting the section with id="content".

        Args:
            response: Scrapy response object

        Returns:
            str: HTML content of the main section, or the full HTML if the targeted section isn't found
        """
        try:
            # Parse the response body with lxml
            tree = html.fromstring(response.body)

            # Find the main content section
            content_section = tree.xpath('//div[@id="main-content"]')
            content_section = (
                content_section
                if content_section and len(content_section) == 1
                else None
            )

            # If we found the content section, extract only its HTML
            if content_section:
                # Get the HTML of just this element
                content_html = html.tostring(
                    content_section[0], encoding="unicode", pretty_print=True
                )
                logging.info(f"Successfully extracted main content from {response.url}")
                return content_html
            else:
                logging.warning(
                    f"Could not find main content section on {response.url}, using full HTML"
                )
                return response.text

        except Exception as e:
            logging.error(f"Error extracting content from {response.url}: {str(e)}")
            return response.text

    def _extract_content(self, response):
        """
        Extract and convert the HTML content to plain text, focusing on the main content area.

        Args:
            response: Scrapy response object

        Returns:
            str: Plain text content
        """
        # Get the focused HTML content
        html_content = self._extract_html_content(response)

        # Convert to plain text using html2text
        return self._get_html2text_converter().handle(html_content)

    def _get_html2text_converter(self):
        """
        Create and configure an HTML2Text converter with optimal settings.

        Returns:
            html2text.HTML2Text: Configured converter
        """
        text_maker = html2text.HTML2Text()
        text_maker.ignore_links = False  # Preserve links in the output
        text_maker.body_width = 0  # Don't wrap text at a specific width
        text_maker.protect_links = True  # Don't wrap links at the end of lines
        text_maker.unicode_snob = True  # Use Unicode instead of ASCII
        text_maker.ignore_images = False  # Include images in the output
        text_maker.ignore_tables = False  # Include tables in the output
        return text_maker

    def _extract_metadata(self, response) -> Dict[str, Optional[str]]:
        """
        Extract metadata from the Migri.fi page, such as publication date, language, etc.

        Args:
            response: Scrapy response object

        Returns:
            Dict: Dictionary of metadata
        """
        metadata = {}
        try:
            tree = html.fromstring(response.body)

            # Try to extract language
            lang_elements = tree.xpath("//html[@lang]")
            if lang_elements:
                metadata["language"] = lang_elements[0].attrib["lang"]

            # Extract any other specific metadata elements that might be useful
            # Example: publication date, last updated, categories, etc.

        except Exception as e:
            logging.error(f"Error extracting metadata from {response.url}: {str(e)}")

        return metadata
