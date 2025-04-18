import os
import unittest
from unittest.mock import MagicMock, patch

from migri_assistant.crawler.crawler import BaseCrawler


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
            start_urls="https://example.com", depth=2, output_dir=self.output_dir
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
            start_urls="https://example.com", output_dir=self.output_dir
        )

        # Test basic URL
        path = crawler._get_file_path_from_url("https://example.com")
        self.assertEqual(
            path, os.path.join(self.output_dir, "example.com", "index.html")
        )

        # Test URL with path
        path = crawler._get_file_path_from_url("https://example.com/page")
        self.assertEqual(
            path, os.path.join(self.output_dir, "example.com", "page.html")
        )

        # Test URL with query parameters
        path = crawler._get_file_path_from_url("https://example.com/page?param=value")
        self.assertTrue(
            path.startswith(
                os.path.join(self.output_dir, "example.com", "page_param_value")
            )
        )
        self.assertTrue(path.endswith(".html"))

    def test_save_html_content(self):
        """Test saving HTML content to file"""
        crawler = BaseCrawler(
            start_urls="https://example.com", output_dir=self.output_dir
        )

        # Test saving content
        url = "https://example.com/test"
        html_content = "<html><body><h1>Test Page</h1></body></html>"
        crawler._save_html_content(url, html_content)

        # Check if file exists and contains the correct content
        expected_path = crawler._get_file_path_from_url(url)
        self.assertTrue(os.path.exists(expected_path))

        with open(expected_path, "r", encoding="utf-8") as f:
            saved_content = f.read()
            self.assertEqual(saved_content, html_content)

    @patch("scrapy.http.Request")
    def test_parse(self, mock_request):
        """Test parsing a web page and extracting content"""
        crawler = BaseCrawler(
            start_urls="https://example.com", output_dir=self.output_dir, depth=1
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
            mock_response.url, mock_response.text
        )

        # Verify the URL was added to visited_urls
        self.assertIn("https://example.com/test", crawler.visited_urls)
