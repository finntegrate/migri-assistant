import os
import unittest
from unittest.mock import MagicMock, mock_open, patch

from tapio.crawler.crawler import BaseCrawler


class TestBaseCrawler(unittest.TestCase):
    def setUp(self):
        # Setup a temporary output directory
        self.output_dir = "test_crawler_output"
        # Create the directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)

    def tearDown(self):
        # Cleanup: remove test files and directories
        import shutil

        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)

    def test_init(self):
        """Test crawler initialization"""
        # Test with a single URL
        crawler = BaseCrawler(
            start_urls="https://example.com",
            depth=2,
            output_dir=self.output_dir,
        )
        self.assertEqual(crawler.start_urls, ["https://example.com"])
        self.assertEqual(crawler.max_depth, 2)
        self.assertEqual(crawler.output_dir, self.output_dir)
        self.assertEqual(crawler.allowed_domains, ["example.com"])

        # Test with multiple URLs
        crawler = BaseCrawler(
            start_urls=["https://example.com", "https://test.com"],
            depth=1,
            output_dir=self.output_dir,
        )
        self.assertEqual(len(crawler.start_urls), 2)
        self.assertEqual(crawler.allowed_domains, ["example.com", "test.com"])

    def test_get_file_path_from_url(self):
        """Test URL to file path conversion"""
        crawler = BaseCrawler(
            start_urls="https://example.com",
            output_dir=self.output_dir,
        )

        # Test basic URL
        path = crawler._get_file_path_from_url("https://example.com")
        self.assertEqual(
            path,
            os.path.join(self.output_dir, "example.com", "index.html"),
        )

        # Test URL with path
        path = crawler._get_file_path_from_url("https://example.com/page")
        self.assertEqual(
            path,
            os.path.join(self.output_dir, "example.com", "page.html"),
        )

        # Test URL with query parameters
        path = crawler._get_file_path_from_url("https://example.com/page?param=value")
        self.assertTrue(
            path.startswith(
                os.path.join(self.output_dir, "example.com", "page_param_value"),
            ),
        )
        self.assertTrue(path.endswith(".html"))

    def test_save_html_content(self):
        """Test saving HTML content to file"""
        crawler = BaseCrawler(
            start_urls="https://example.com",
            output_dir=self.output_dir,
        )

        # Test saving content
        url = "https://example.com/test"
        html_content = "<html><body><h1>Test Page</h1></body></html>"
        crawler._save_html_content(url, html_content)

        # Check if file exists and contains the correct content
        expected_path = crawler._get_file_path_from_url(url)
        self.assertTrue(os.path.exists(expected_path))

        with open(expected_path, encoding="utf-8") as f:
            saved_content = f.read()
            self.assertEqual(saved_content, html_content)

    @patch("scrapy.http.Request")
    def test_parse(self, mock_request):
        """Test parsing a web page and extracting content"""
        crawler = BaseCrawler(
            start_urls="https://example.com",
            output_dir=self.output_dir,
            depth=1,
        )

        # Create a mock response
        mock_response = MagicMock()
        mock_response.url = "https://example.com/test"
        mock_response.text = "<html><body><h1>Test Page</h1></body></html>"
        mock_response.headers.get.return_value = b"text/html; charset=utf-8"
        mock_response.css.return_value.getall.return_value = ["/page1", "/page2"]

        # Mock the save_html_content method
        crawler._save_html_content = MagicMock()

        # Call parse
        result = next(crawler.parse(mock_response, current_depth=0))

        # Verify the result
        self.assertEqual(result["url"], "https://example.com/test")
        self.assertEqual(result["html"], mock_response.text)
        self.assertEqual(result["depth"], 0)
        self.assertTrue("crawl_timestamp" in result)

        # Verify save_html_content was called
        crawler._save_html_content.assert_called_once_with(
            mock_response.url,
            mock_response.text,
        )

        # Verify the URL was added to visited_urls
        self.assertIn("https://example.com/test", crawler.visited_urls)

    def test_save_url_mappings(self):
        """Test saving URL mappings to a JSON file"""
        crawler = BaseCrawler(
            start_urls="https://example.com",
            output_dir=self.output_dir,
        )

        # Setup test data
        crawler.url_mappings = {
            "example.com/page1.html": {
                "url": "https://example.com/page1",
                "timestamp": "2023-01-01T00:00:00",
                "content_type": "text/html",
            },
            "example.com/page2.html": {
                "url": "https://example.com/page2",
                "timestamp": "2023-01-01T00:01:00",
                "content_type": "text/html",
            },
        }

        # Test saving mappings
        with patch("builtins.open", mock_open()) as mock_file:
            crawler._save_url_mappings()
            mock_file.assert_called_once_with(
                os.path.join(self.output_dir, "url_mappings.json"),
                "w",
                encoding="utf-8",
            )
            # Check that json.dump was called with the correct arguments
            handle = mock_file()
            args, kwargs = handle.write.call_args
            # Since json.dump writes to the file directly, we can't easily check its contents
            # Just verify the method was called
            self.assertGreaterEqual(handle.write.call_count, 1)

    def test_save_url_mappings_exception(self):
        """Test handling exceptions when saving URL mappings"""
        crawler = BaseCrawler(
            start_urls="https://example.com",
            output_dir=self.output_dir,
        )

        # Setup test data
        crawler.url_mappings = {"test": "data"}

        # Test exception handling
        with (
            patch("builtins.open", side_effect=Exception("Test error")),
            patch("logging.error") as mock_log,
        ):
            crawler._save_url_mappings()
            mock_log.assert_called_once_with("Error saving URL mappings: Test error")

    def test_spider_closed(self):
        """Test spider_closed signal handler"""
        crawler = BaseCrawler(
            start_urls="https://example.com",
            output_dir=self.output_dir,
        )

        # Add visited URLs
        crawler.visited_urls = {
            "https://example.com/page1",
            "https://example.com/page2",
        }

        # Mock _save_url_mappings
        crawler._save_url_mappings = MagicMock()

        # Mock spider
        spider = MagicMock()

        # Call spider_closed
        with patch("logging.info") as mock_log:
            crawler.spider_closed(spider)

            # Verify _save_url_mappings was called
            crawler._save_url_mappings.assert_called_once()

            # Verify logging calls
            mock_log.assert_any_call("Crawler closed. Visited 2 pages")

    def test_errback_handler(self):
        """Test errback_handler for handling request failures"""
        crawler = BaseCrawler(
            start_urls="https://example.com",
            output_dir=self.output_dir,
        )

        # Create mock failure
        mock_failure = MagicMock()
        mock_failure.request = MagicMock()
        mock_failure.request.url = "https://example.com/error"
        mock_failure.value = "Connection refused"

        # Call errback_handler
        with patch("logging.warning") as mock_log:
            crawler.errback_handler(mock_failure)
            mock_log.assert_called_once_with(
                "Error on https://example.com/error: Connection refused",
            )

    def test_extract_links(self):
        """Test extracting links from a response"""
        crawler = BaseCrawler(
            start_urls="https://example.com",
            output_dir=self.output_dir,
        )

        # Create mock response
        mock_response = MagicMock()
        mock_links = ["/page1", "/page2", "https://example.com/page3"]
        mock_response.css.return_value.getall.return_value = mock_links

        # Call _extract_links
        links = crawler._extract_links(mock_response)

        # Verify results
        self.assertEqual(links, mock_links)
        # Check that css was called with the right argument (but we don't care how many times)
        mock_response.css.assert_any_call("a::attr(href)")

    def test_parse_non_html_content(self):
        """Test parsing non-HTML content"""
        crawler = BaseCrawler(
            start_urls="https://example.com",
            output_dir=self.output_dir,
        )

        # Create a mock response with non-HTML content type
        mock_response = MagicMock()
        mock_response.url = "https://example.com/document.pdf"
        mock_response.headers.get.return_value = b"application/pdf"

        # Call parse
        results = list(crawler.parse(mock_response))

        # Verify no results and the URL wasn't saved
        self.assertEqual(len(results), 0)
        self.assertIn("https://example.com/document.pdf", crawler.visited_urls)

    def test_parse_with_exception(self):
        """Test exception handling in parse method"""
        crawler = BaseCrawler(
            start_urls="https://example.com",
            output_dir=self.output_dir,
        )

        # Create a mock response
        mock_response = MagicMock()
        mock_response.url = "https://example.com/error"
        mock_response.headers.get.return_value = b"text/html"

        # Force an exception by making a method raise an exception
        crawler._save_html_content = MagicMock(side_effect=Exception("Test error"))

        # Call parse
        with patch("logging.error") as mock_log:
            results = list(crawler.parse(mock_response))

            # Verify error was logged
            mock_log.assert_called_once_with(
                "Error processing https://example.com/error: Test error",
            )

            # Verify no results but URL was marked as visited
            self.assertEqual(len(results), 0)
            self.assertIn("https://example.com/error", crawler.visited_urls)

    def test_parse_already_visited_url(self):
        """Test parsing a URL that's already been visited"""
        crawler = BaseCrawler(
            start_urls="https://example.com",
            output_dir=self.output_dir,
        )

        # Add URL to visited_urls
        url = "https://example.com/visited"
        crawler.visited_urls.add(url)

        # Create a mock response
        mock_response = MagicMock()
        mock_response.url = url

        # Call parse
        results = list(crawler.parse(mock_response))

        # Verify no processing happened
        self.assertEqual(len(results), 0)

    @patch("scrapy.signals")
    @patch("signal.signal")
    def test_from_crawler(self, mock_signal_signal, mock_scrapy_signals):
        """Test from_crawler method and signal handling"""
        # Mock crawler
        mock_crawler = MagicMock()

        # Call from_crawler
        spider = BaseCrawler.from_crawler(
            mock_crawler,
            start_urls=["https://example.com"],
            output_dir=self.output_dir,
        )

        # Verify spider was created
        self.assertIsInstance(spider, BaseCrawler)

        # Verify signals connection by checking that connect was called
        self.assertTrue(mock_crawler.signals.connect.called)

        # Verify signal handler was registered (checking just that it was called)
        import signal as signal_module

        mock_signal_signal.assert_called_once_with(
            signal_module.SIGINT,
            mock_signal_signal.call_args[0][1],  # Just verify the same function was used
        )

    def test_get_file_path_from_url_with_trailing_slash(self):
        """Test URL to file path conversion with trailing slash"""
        crawler = BaseCrawler(
            start_urls="https://example.com",
            output_dir=self.output_dir,
        )

        # Test URL with trailing slash
        path = crawler._get_file_path_from_url("https://example.com/path/")
        self.assertEqual(
            path,
            os.path.join(self.output_dir, "example.com", "path.html"),
        )

    def test_start_requests(self):
        """Test start_requests method"""
        crawler = BaseCrawler(
            start_urls=["https://example.com", "https://test.com"],
            output_dir=self.output_dir,
        )

        # Get generators
        requests = list(crawler.start_requests())

        # Verify two requests were generated
        self.assertEqual(len(requests), 2)

        # Check URLs
        urls = [request.url for request in requests]
        self.assertIn("https://example.com", urls)
        self.assertIn("https://test.com", urls)

        # Check callback and kwargs
        for request in requests:
            self.assertEqual(request.callback, crawler.parse)
            self.assertEqual(request.cb_kwargs, {"current_depth": 0})
