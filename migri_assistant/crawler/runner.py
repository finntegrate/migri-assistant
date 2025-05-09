import logging
from collections.abc import Generator

from scrapy import signals
from scrapy.crawler import CrawlerRunner
from scrapy.utils.project import get_project_settings
from twisted.internet import defer, reactor  # type: ignore

from migri_assistant.crawler.crawler import BaseCrawler


class ScrapyRunner:
    """
    Runs a Scrapy crawler process to crawl websites and save HTML content.
    """

    def __init__(self) -> None:
        """Initialize Scrapy runner."""
        self.setup_logging()
        self.results = []

    def setup_logging(self) -> None:
        """Set up logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[logging.StreamHandler()],
        )
        self.logger = logging.getLogger(__name__)

    def _item_scraped(self, item, response, spider) -> None:
        """Callback function to collect scraped items."""
        self.results.append(item)

    def run(
        self,
        start_urls: list[str],
        depth: int = 1,
        allowed_domains: list[str] | None = None,
        output_dir: str = "crawled_content",
        custom_settings: dict | None = None,
    ) -> list[dict]:
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
        settings = get_project_settings()
        settings.update(
            {
                "LOG_LEVEL": "INFO",
                "DOWNLOAD_DELAY": 1,
                "ROBOTSTXT_OBEY": True,
                "COOKIES_ENABLED": False,  # Added to help with stability
                "RETRY_ENABLED": True,  # Added to improve reliability
                "RETRY_TIMES": 2,  # Added to improve reliability
                "DOWNLOAD_TIMEOUT": 30,  # Added to prevent hanging
                "TWISTED_REACTOR": "twisted.internet.selectreactor.SelectReactor",
            },
        )
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
