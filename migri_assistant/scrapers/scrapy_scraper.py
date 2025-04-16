import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from migri_assistant.scrapers.base_scraper import BaseScraper
from migri_assistant.spiders.web_spider import WebSpider


class ScrapyScraper(BaseScraper):
    """
    Scraper implementation using Scrapy framework to scrape web content
    with configurable depth and save output as Markdown files.
    """

    def __init__(
        self,
        output_dir: str = "scraped_content",
        output_file: str = None,
        pdf_output_file: str = "pdfs.json",
    ):
        """
        Initialize Scrapy scraper with output directory for saving Markdown files

        Args:
            output_dir: Directory to save scraped content as Markdown files
            output_file: Path to save scraped results index as JSON
            pdf_output_file: Path to save PDF URLs as JSON
        """
        self.output_dir = output_dir
        self.output_file = output_file
        self.pdf_output_file = pdf_output_file
        self.process = None
        self.setup_logging()

    def setup_logging(self):
        """Set up logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[logging.StreamHandler()],
        )
        self.logger = logging.getLogger(__name__)

    def scrape(
        self, url: str, depth: int = 1, allowed_domains: Optional[List[str]] = None
    ) -> List[dict]:
        """
        Scrape the given URL up to the specified depth and save content as Markdown files

        Args:
            url: The URL to start scraping from
            depth: How many links deep to follow (1 means just the main page)
            allowed_domains: List of domains to restrict scraping to

        Returns:
            List of dictionaries containing basic metadata about the scraped pages
        """
        self.logger.info(f"Starting scrape of {url} with depth {depth}")
        self.logger.info(f"Saving Markdown files to {self.output_dir}")

        # Create a temporary file to store results if no output file is specified
        if self.output_file is None:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
                output_file = tmp.name
        else:
            output_file = self.output_file

        # Configure and start the Scrapy crawler
        settings = get_project_settings()
        settings.update(
            {
                "LOG_LEVEL": "INFO",
                "DOWNLOAD_DELAY": 1,  # Be respectful to servers
                "ROBOTSTXT_OBEY": True,  # Follow robots.txt rules
            }
        )

        self.process = CrawlerProcess(settings)
        self.process.crawl(
            WebSpider,
            start_urls=url,
            depth=depth,
            allowed_domains=allowed_domains,
            output_dir=self.output_dir,
            output_file=output_file,
            pdf_output_file=self.pdf_output_file,
        )
        self.process.start()  # This will block until crawling is finished

        # Read the results from the output file
        results = []
        try:
            if os.path.exists(output_file):
                with open(output_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "results" in data:
                        results = data["results"]
                    self.logger.info(
                        f"Read metadata for {len(results)} pages from {output_file}"
                    )
        except Exception as e:
            self.logger.error(f"Failed to read results from {output_file}: {e}")

        # Create an index file for all Markdown files
        if results:
            self._create_markdown_index(results)

        # Clean up the temporary file if we created one
        if self.output_file is None and os.path.exists(output_file):
            Path(output_file).unlink(missing_ok=True)

        self.logger.info(
            f"Scraping completed. Scraped {len(results)} documents from {url}"
        )
        return results

    def _create_markdown_index(self, results: List[Dict]) -> None:
        """
        Create an index.md file listing all scraped pages

        Args:
            results: List of scraped page metadata
        """
        index_path = os.path.join(self.output_dir, "index.md")

        with open(index_path, "w", encoding="utf-8") as f:
            f.write("# Scraped Content Index\n\n")
            f.write(f"Total pages scraped: {len(results)}\n\n")
            f.write("| Title | URL | Depth |\n")
            f.write("|-------|-----|-------|\n")

            for page in results:
                title = page.get("title", "Untitled")
                url = page.get("url", "")
                depth = page.get("depth", 0)

                # Create a link to the file using the URL
                f.write(f"| {title} | [{url}]({url}) | {depth} |\n")

        self.logger.info(f"Created Markdown index at {index_path}")
