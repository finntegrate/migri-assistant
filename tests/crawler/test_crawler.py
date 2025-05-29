"""Test cases for the async BaseCrawler implementation."""

import os
import unittest
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import httpx
import pytest
from bs4 import BeautifulSoup

from tapio.crawler.crawler import BaseCrawler


class TestBaseCrawler(unittest.TestCase):
    """Test cases for BaseCrawler class."""

    def setUp(self):
        """Set up test fixtures."""
        self.output_dir = "test_crawler_output"
        os.makedirs(self.output_dir, exist_ok=True)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)

    def test_init(self):
        """Test crawler initialization."""
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
        """Test URL to file path conversion."""
        crawler = BaseCrawler(
            start_urls="https://example.com",
            output_dir=self.output_dir,
        )

        # Test basic URL
        path = crawler._get_file_path_from_url("https://example.com")
        expected = os.path.join(self.output_dir, "example.com", "index.html")
        self.assertEqual(path, expected)

        # Test URL with path
        path = crawler._get_file_path_from_url("https://example.com/page")
        expected = os.path.join(self.output_dir, "example.com", "page.html")
        self.assertEqual(path, expected)

        # Test URL with query parameters
        path = crawler._get_file_path_from_url("https://example.com/page?param=value")
        expected_start = os.path.join(self.output_dir, "example.com", "page_param_value")
        self.assertTrue(path.startswith(expected_start))
        self.assertTrue(path.endswith(".html"))

    def test_get_file_path_from_url_with_trailing_slash(self):
        """Test URL to file path conversion with trailing slash."""
        crawler = BaseCrawler(
            start_urls="https://example.com",
            output_dir=self.output_dir,
        )

        path = crawler._get_file_path_from_url("https://example.com/path/")
        expected = os.path.join(self.output_dir, "example.com", "path.html")
        self.assertEqual(path, expected)

    def test_save_html_content(self):
        """Test saving HTML content to file."""
        crawler = BaseCrawler(
            start_urls="https://example.com",
            output_dir=self.output_dir,
        )

        url = "https://example.com/test"
        html_content = "<html><body><h1>Test Page</h1></body></html>"
        crawler._save_html_content(url, html_content)

        expected_path = crawler._get_file_path_from_url(url)
        self.assertTrue(os.path.exists(expected_path))

        with open(expected_path, encoding="utf-8") as f:
            saved_content = f.read()
            self.assertEqual(saved_content, html_content)

    def test_is_allowed_domain(self):
        """Test domain filtering."""
        crawler = BaseCrawler(
            start_urls=["https://example.com"],
            allowed_domains=["example.com", "test.com"],
            output_dir=self.output_dir,
        )

        self.assertTrue(crawler._is_allowed_domain("https://example.com/page"))
        self.assertTrue(crawler._is_allowed_domain("https://test.com/page"))
        self.assertFalse(crawler._is_allowed_domain("https://other.com/page"))

    def test_extract_links(self):
        """Test extracting links from BeautifulSoup."""
        crawler = BaseCrawler(
            start_urls=["https://example.com"],
            output_dir=self.output_dir,
        )

        html = """
        <html>
            <body>
                <a href="/page1">Page 1</a>
                <a href="https://example.com/page2">Page 2</a>
                <a href="https://other.com/page3">Page 3</a>
                <a href="#fragment">Fragment</a>
                <a href="mailto:test@example.com">Email</a>
            </body>
        </html>
        """

        soup = BeautifulSoup(html, "lxml")
        base_url = "https://example.com"

        links = crawler._extract_links(soup, base_url)

        expected_links = ["https://example.com/page1", "https://example.com/page2"]

        self.assertEqual(sorted(links), sorted(expected_links))

    def test_save_url_mappings(self):
        """Test saving URL mappings to a JSON file."""
        crawler = BaseCrawler(
            start_urls="https://example.com",
            output_dir=self.output_dir,
        )

        crawler.url_mappings = {
            "example.com/page1.html": {
                "url": "https://example.com/page1",
                "timestamp": "2023-01-01T00:00:00",
                "content_type": "text/html",
            },
        }

        with patch("builtins.open", mock_open()) as mock_file:
            crawler._save_url_mappings()
            expected_path = os.path.join(self.output_dir, "url_mappings.json")
            mock_file.assert_called_once_with(expected_path, "w", encoding="utf-8")

    def test_save_url_mappings_exception(self):
        """Test handling exceptions when saving URL mappings."""
        crawler = BaseCrawler(
            start_urls="https://example.com",
            output_dir=self.output_dir,
        )

        crawler.url_mappings = {
            "test.html": {
                "url": "https://example.com/test",
                "timestamp": "2023-01-01T00:00:00",
                "content_type": "text/html",
            },
        }

        with (
            patch("builtins.open", side_effect=Exception("Test error")),
            patch("logging.error") as mock_log,
        ):
            crawler._save_url_mappings()
            mock_log.assert_called_once_with("Error saving URL mappings: Test error")

    @pytest.mark.asyncio
    async def test_crawl_url_success(self):
        """Test successful crawling of a single URL."""
        crawler = BaseCrawler(
            start_urls=["https://example.com"],
            output_dir=self.output_dir,
            max_concurrent=1,
        )

        mock_response = MagicMock()
        mock_response.text = "<html><body><h1>Test</h1><a href='/page2'>Link</a></body></html>"
        mock_response.headers = {"content-type": "text/html; charset=utf-8"}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch.object(crawler, "_save_html_content", return_value="/fake/path.html"):
            results = []
            await crawler._crawl_url(mock_client, "https://example.com", 0, results)

            mock_client.get.assert_called_once_with("https://example.com")

            self.assertEqual(len(results), 1)
            result = results[0]
            self.assertEqual(result["url"], "https://example.com")
            self.assertEqual(result["depth"], 0)
            self.assertIn("Test", result["html"])

    @pytest.mark.asyncio
    async def test_crawl_url_http_error(self):
        """Test handling HTTP errors during crawling."""
        crawler = BaseCrawler(
            start_urls=["https://example.com"],
            output_dir=self.output_dir,
        )

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=httpx.HTTPStatusError(
                "404 Not Found",
                request=MagicMock(),
                response=MagicMock(status_code=404),
            ),
        )

        results = []
        with patch("logging.warning") as mock_log:
            await crawler._crawl_url(mock_client, "https://example.com/404", 0, results)

            mock_log.assert_called()
            self.assertEqual(len(results), 0)

    @pytest.mark.asyncio
    async def test_crawl_url_non_html_content(self):
        """Test handling non-HTML content."""
        crawler = BaseCrawler(
            start_urls=["https://example.com"],
            output_dir=self.output_dir,
        )

        mock_response = MagicMock()
        mock_response.headers = {"content-type": "application/pdf"}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        results = []
        await crawler._crawl_url(mock_client, "https://example.com/doc.pdf", 0, results)

        self.assertEqual(len(results), 0)

    @pytest.mark.asyncio
    async def test_crawl_full_integration(self):
        """Test the full crawl method with mocked HTTP client."""
        crawler = BaseCrawler(
            start_urls=["https://example.com"],
            output_dir=self.output_dir,
            depth=1,
            max_concurrent=1,
        )

        html_content = """
        <html>
            <body>
                <h1>Main Page</h1>
                <a href="/page1">Page 1</a>
            </body>
        </html>
        """

        mock_response = MagicMock()
        mock_response.text = html_content
        mock_response.headers = {"content-type": "text/html; charset=utf-8"}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        # Mock the async context manager
        mock_client_context = AsyncMock()
        mock_client_context.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_context.__aexit__ = AsyncMock(return_value=None)

        with patch("httpx.AsyncClient", return_value=mock_client_context):
            with patch.object(crawler, "_save_html_content"):
                results = await crawler.crawl()

                self.assertGreater(len(results), 0)
                self.assertEqual(results[0]["url"], "https://example.com")


if __name__ == "__main__":
    unittest.main()
