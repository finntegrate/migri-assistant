import json
import logging
import os
import tempfile
from pathlib import Path
from typing import List, Optional

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from migri_assistant.scrapers.base_scraper import BaseScraper
from migri_assistant.spiders.web_spider import WebSpider  # Updated import path


class ScrapyScraper(BaseScraper):
    """
    Scraper implementation using Scrapy framework to scrape web content
    with configurable depth.
    """

    def __init__(self, collection_name: str = "migri_documents"):
        """
        Initialize Scrapy scraper with collection name for storing documents

        Args:
            collection_name: Name of the ChromaDB collection to store documents
        """
        self.collection_name = collection_name
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
        Scrape the given URL up to the specified depth

        Args:
            url: The URL to start scraping from
            depth: How many links deep to follow (1 means just the main page)
            allowed_domains: List of domains to restrict scraping to

        Returns:
            List of document dictionaries containing the scraped content
        """
        self.logger.info(f"Starting scrape of {url} with depth {depth}")

        # Create a temporary file to store results
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jl") as tmp:
            output_file = tmp.name

        # Configure and start the Scrapy crawler
        settings = get_project_settings()
        settings.update(
            {
                "FEEDS": {
                    output_file: {
                        "format": "jsonlines",
                        "encoding": "utf8",
                        "overwrite": True,
                    },
                },
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
            collection_name=self.collection_name,
        )
        self.process.start()  # This will block until crawling is finished

        # Read and return the scraped results
        results = []
        if os.path.exists(output_file):
            with open(output_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        results.append(json.loads(line))
                    except json.JSONDecodeError:
                        self.logger.error(f"Failed to parse JSON line: {line}")

            # Clean up the temporary file
            Path(output_file).unlink(missing_ok=True)

        self.logger.info(f"Scraped {len(results)} documents from {url}")
        return results
