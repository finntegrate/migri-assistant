import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from tapio.config.settings import DEFAULT_DIRS
from tapio.crawler.runner import CrawlerRunner


class TestCrawlerRunner(unittest.TestCase):
    """Test the CrawlerRunner class that manages the crawling process."""

    def setUp(self):
        self.runner = CrawlerRunner()

    @patch("tapio.crawler.runner.BaseCrawler")
    def test_run_basic(self, mock_base_crawler):
        """Test the basic functionality of the run method."""
        # Mock BaseCrawler instance
        mock_crawler_instance = MagicMock()
        mock_crawler_instance.crawl = AsyncMock(
            return_value=[
                {
                    "url": "https://example.com",
                    "html": "<html><body>Test</body></html>",
                    "depth": 0,
                    "crawl_timestamp": "2023-01-01T00:00:00",
                    "content_type": "text/html",
                },
            ],
        )
        mock_base_crawler.return_value = mock_crawler_instance

        # Call the run method
        start_urls = ["https://example.com"]
        depth = 1
        allowed_domains = ["example.com"]
        output_dir = "test_output"

        results = self.runner.run(
            start_urls=start_urls,
            depth=depth,
            allowed_domains=allowed_domains,
            output_dir=output_dir,
        )

        # Verify BaseCrawler was instantiated with correct parameters
        mock_base_crawler.assert_called_once_with(
            start_urls=start_urls,
            allowed_domains=allowed_domains,
            depth=depth,
            output_dir=output_dir,
        )

        # Verify crawler.crawl was called
        mock_crawler_instance.crawl.assert_called_once()

        # Verify results were returned
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["url"], "https://example.com")

    @patch("tapio.crawler.runner.BaseCrawler")
    def test_run_with_custom_settings(self, mock_base_crawler):
        """Test the run method with custom settings."""
        # Mock BaseCrawler instance
        mock_crawler_instance = MagicMock()
        mock_crawler_instance.crawl = AsyncMock(return_value=[])
        mock_base_crawler.return_value = mock_crawler_instance

        # Call the run method with custom settings
        from tapio.crawler.runner import CrawlerSettings

        custom_settings: CrawlerSettings = {"timeout": 60, "max_concurrent": 5}

        self.runner.run(
            start_urls=["https://example.com"],
            custom_settings=custom_settings,
        )

        # Verify BaseCrawler was instantiated with custom settings
        mock_base_crawler.assert_called_once_with(
            start_urls=["https://example.com"],
            allowed_domains=None,
            depth=1,
            output_dir=DEFAULT_DIRS["CRAWLED_DIR"],
            timeout=60,
            max_concurrent=5,
        )

    @patch("tapio.crawler.runner.BaseCrawler")
    async def test_run_async(self, mock_base_crawler):
        """Test the async run_async method."""
        # Mock BaseCrawler instance
        mock_crawler_instance = MagicMock()
        mock_crawler_instance.crawl = AsyncMock(
            return_value=[
                {
                    "url": "https://example.com",
                    "html": "<html><body>Test</body></html>",
                    "depth": 0,
                    "crawl_timestamp": "2023-01-01T00:00:00",
                    "content_type": "text/html",
                },
            ],
        )
        mock_base_crawler.return_value = mock_crawler_instance

        # Call the async run method
        results = await self.runner.run_async(
            start_urls=["https://example.com"],
            depth=2,
        )

        # Verify BaseCrawler was instantiated correctly
        mock_base_crawler.assert_called_once_with(
            start_urls=["https://example.com"],
            allowed_domains=None,
            depth=2,
            output_dir=DEFAULT_DIRS["CRAWLED_DIR"],
        )

        # Verify crawler.crawl was called
        mock_crawler_instance.crawl.assert_called_once()

        # Verify results were returned
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["url"], "https://example.com")
