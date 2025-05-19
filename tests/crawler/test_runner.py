import unittest
from unittest.mock import MagicMock, patch

from tapio.crawler.runner import ScrapyRunner


class TestScrapyRunner(unittest.TestCase):
    """Test the ScrapyRunner class that manages the crawling process."""

    def setUp(self):
        self.runner = ScrapyRunner()
        self.runner.logger = MagicMock()  # Mock the logger

    @patch("tapio.crawler.runner.CrawlerRunner")
    @patch("tapio.crawler.runner.reactor")
    @patch("tapio.crawler.runner.Settings")
    def test_run_basic(self, mock_settings_class, mock_reactor, mock_crawler_runner):
        """Test the basic functionality of the run method."""
        # Mock Settings class
        mock_settings = MagicMock()
        mock_settings_class.return_value = mock_settings

        # Mock crawler runner and crawler
        mock_crawler_instance = MagicMock()
        mock_crawler_runner.return_value.create_crawler.return_value = mock_crawler_instance

        # Set up mock for crawler.crawl to return a deferred that calls its callback
        def mock_crawl(*args, **kwargs):
            d = MagicMock()
            # Simulate the deferred calling its callback immediately
            return d

        mock_crawler_instance.crawl.side_effect = mock_crawl

        # Mock reactor.run to do nothing
        mock_reactor.running = False

        # Call the run method
        start_urls = ["https://example.com"]
        depth = 1
        allowed_domains = ["example.com"]
        output_dir = "test_output"

        _ = self.runner.run(
            start_urls=start_urls,
            depth=depth,
            allowed_domains=allowed_domains,
            output_dir=output_dir,
        )

        # Verify CrawlerRunner was created with settings
        mock_crawler_runner.assert_called_once()

        # Verify create_crawler was called with BaseCrawler
        mock_crawler_runner.return_value.create_crawler.assert_called_once()

        # Verify crawler.crawl was called with our parameters
        mock_crawler_instance.crawl.assert_called_once()
        crawl_args, crawl_kwargs = mock_crawler_instance.crawl.call_args
        self.assertEqual(crawl_kwargs["start_urls"], start_urls)
        self.assertEqual(crawl_kwargs["depth"], depth)
        self.assertEqual(crawl_kwargs["allowed_domains"], allowed_domains)
        self.assertEqual(crawl_kwargs["output_dir"], output_dir)

        # Verify reactor.run was called
        mock_reactor.run.assert_called_once()

    @patch("tapio.crawler.runner.CrawlerRunner")
    @patch("tapio.crawler.runner.reactor")
    @patch("tapio.crawler.runner.Settings")
    def test_run_with_error(self, mock_settings_class, mock_reactor, mock_crawler_runner):
        """Test error handling in the run method."""
        # Mock Settings class
        mock_settings = MagicMock()
        mock_settings_class.return_value = mock_settings

        # Mock crawler runner to raise an exception
        mock_crawler_runner.return_value.create_crawler.side_effect = Exception(
            "Test error",
        )

        # Mock reactor
        mock_reactor.running = False

        # Call the run method
        self.runner.run(start_urls=["https://example.com"], depth=1)

        # Verify the logger.error was called with the error
        self.runner.logger.error.assert_called_once()
        self.assertIn("Test error", str(self.runner.logger.error.call_args))

        # Verify reactor.stop was called if running
        mock_reactor.stop.assert_not_called()  # Should not be called as reactor.running is False

    def test_item_scraped(self):
        """Test the _item_scraped method for collecting results."""
        # Setup
        self.runner.results = []
        item = {"url": "https://example.com", "html": "<html></html>"}
        response = MagicMock()
        spider = MagicMock()

        # Call the method
        self.runner._item_scraped(item, response, spider)

        # Verify the item was added to results
        self.assertEqual(len(self.runner.results), 1)
        self.assertEqual(self.runner.results[0], item)
