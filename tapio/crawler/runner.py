import logging
from collections.abc import Generator
from typing import Any, TypedDict

from scrapy import signals
from scrapy.crawler import CrawlerRunner
from scrapy.settings import Settings
from twisted.internet import defer, reactor  # type: ignore

from tapio.config.settings import DEFAULT_DIRS
from tapio.crawler import settings as crawler_settings
from tapio.crawler.crawler import BaseCrawler


class ScrapySettings(TypedDict, total=False):
    """Type definition for Scrapy settings."""

    USER_AGENT: str
    CONCURRENT_REQUESTS: int
    DOWNLOAD_DELAY: int
    COOKIES_ENABLED: bool
    TELNETCONSOLE_ENABLED: bool
    ROBOTSTXT_OBEY: bool


class ScrapyRunner:
    """
    Runs a Scrapy crawler process to crawl websites and save HTML content.

    This class provides a high-level interface to run a Scrapy crawler
    and collect the scraped items.
    """

    def __init__(self) -> None:
        """
        Initialize Scrapy runner with logging configuration.
        """
        self.logger = logging.getLogger(__name__)
        self.setup_logging()
        self.results: list[dict[str, Any]] = []

    def setup_logging(self) -> None:
        """
        Set up logging configuration for the Scrapy runner.
        """
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[logging.StreamHandler()],
        )

    def _item_scraped(self, item: dict[str, Any], response: Any, spider: Any) -> None:
        """
        Callback function to collect scraped items.

        Args:
            item: The scraped item data.
            response: The HTTP response from which the item was scraped.
            spider: The spider that scraped the item.
        """
        self.results.append(item)

    def run(
        self,
        start_urls: list[str],
        depth: int = 1,
        allowed_domains: list[str] | None = None,
        output_dir: str = DEFAULT_DIRS["CRAWLED_DIR"],
        custom_settings: ScrapySettings | None = None,
    ) -> list[dict[str, Any]]:
        """
        Run the crawler and return basic information about crawled pages.

        Args:
            start_urls: List of URLs to start crawling from.
            depth: How many links deep to follow.
            allowed_domains: List of domains to restrict crawling to.
            output_dir: Directory to save crawled HTML files.
            custom_settings: Optional dictionary of Scrapy settings.

        Returns:
            List containing basic information about crawled pages.
        """
        self.logger.info(f"Starting crawl for URLs: {start_urls}, depth: {depth}")
        self.results = []  # Reset results for this run

        # Configure Scrapy settings
        settings = Settings()
        # Copy all settings from our crawler settings module
        for setting in dir(crawler_settings):
            if setting.isupper():
                settings.set(setting, getattr(crawler_settings, setting))

        # Update with additional settings from our settings module
        settings.update(crawler_settings.DEFAULT_SETTINGS)
        if custom_settings:
            settings.update(custom_settings)

        # Use CrawlerRunner for more control
        runner = CrawlerRunner(settings)

        # Create a deferrable that will run the crawler
        @defer.inlineCallbacks
        def crawl_with_cleanup() -> Generator[defer.Deferred, None, None]:
            try:
                # Create crawler and connect signals
                crawler = runner.create_crawler(BaseCrawler)
                crawler.signals.connect(self._item_scraped, signal=signals.item_scraped)

                # Start the crawl
                yield crawler.crawl(
                    start_urls=start_urls,
                    depth=depth,
                    allowed_domains=allowed_domains,
                    output_dir=output_dir,
                )

            except Exception as e:
                self.logger.error(f"Error during crawling: {e}")
            finally:
                # Stop the reactor if it's running
                if reactor.running:  # type: ignore[attr-defined]
                    reactor.stop()  # type: ignore[attr-defined]

        # Run the crawler
        crawl_with_cleanup()

        # Start the event loop
        if not reactor.running:  # type: ignore[attr-defined]
            reactor.run()  # type: ignore[attr-defined]

        self.logger.info(f"Crawling completed. Processed {len(self.results)} items.")
        return self.results
