import asyncio
import logging
from typing import Any, TypedDict

from tapio.config.settings import DEFAULT_DIRS
from tapio.crawler.crawler import BaseCrawler, CrawlResult


class CrawlerSettings(TypedDict, total=False):
    """Type definition for crawler settings."""

    timeout: int
    max_concurrent: int
    delay_between_requests: float


class CrawlerRunner:
    """
    Runs an async crawler process to crawl websites and save HTML content.

    This class provides a high-level interface to run an async crawler
    and collect the scraped results.
    """

    def __init__(self) -> None:
        """
        Initialize the crawler runner with logging configuration.
        """
        self.logger = logging.getLogger(__name__)
        self.setup_logging()

    def setup_logging(self) -> None:
        """
        Set up logging configuration for the crawler runner.
        """
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[logging.StreamHandler()],
        )

    async def run_async(
        self,
        start_urls: list[str],
        depth: int = 1,
        allowed_domains: list[str] | None = None,
        output_dir: str = DEFAULT_DIRS["CRAWLED_DIR"],
        custom_settings: CrawlerSettings | None = None,
    ) -> list[CrawlResult]:
        """
        Run the crawler asynchronously and return crawled page data.

        Args:
            start_urls: List of URLs to start crawling from.
            depth: How many links deep to follow.
            allowed_domains: List of domains to restrict crawling to.
            output_dir: Directory to save crawled HTML files.
            custom_settings: Optional dictionary of crawler settings.

        Returns:
            List of CrawlResult dictionaries containing page data.
        """
        self.logger.info(f"Starting async crawl for URLs: {start_urls}, depth: {depth}")

        # Apply custom settings
        kwargs: dict[str, Any] = {}
        if custom_settings:
            if "timeout" in custom_settings:
                kwargs["timeout"] = custom_settings["timeout"]
            if "max_concurrent" in custom_settings:
                kwargs["max_concurrent"] = custom_settings["max_concurrent"]
            if "delay_between_requests" in custom_settings:
                kwargs["delay_between_requests"] = custom_settings["delay_between_requests"]

        # Create and configure the crawler
        crawler = BaseCrawler(
            start_urls=start_urls,
            allowed_domains=allowed_domains,
            depth=depth,
            output_dir=output_dir,
            **kwargs,
        )

        # Run the crawler
        results = await crawler.crawl()

        self.logger.info(f"Async crawling completed. Processed {len(results)} items.")
        return results

    def run(
        self,
        start_urls: list[str],
        depth: int = 1,
        allowed_domains: list[str] | None = None,
        output_dir: str = DEFAULT_DIRS["CRAWLED_DIR"],
        custom_settings: CrawlerSettings | None = None,
    ) -> list[CrawlResult]:
        """
        Run the crawler synchronously and return crawled page data.

        This is a convenience method that wraps the async version.

        Args:
            start_urls: List of URLs to start crawling from.
            depth: How many links deep to follow.
            allowed_domains: List of domains to restrict crawling to.
            output_dir: Directory to save crawled HTML files.
            custom_settings: Optional dictionary of crawler settings.

        Returns:
            List of CrawlResult dictionaries containing page data.
        """
        return asyncio.run(
            self.run_async(
                start_urls=start_urls,
                depth=depth,
                allowed_domains=allowed_domains,
                output_dir=output_dir,
                custom_settings=custom_settings,
            ),
        )
