import json
import logging
import os
import signal
from collections.abc import Generator
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from scrapy import Spider, signals
from scrapy.crawler import Crawler
from scrapy.http import Request, Response
from twisted.python.failure import Failure


class BaseCrawler(Spider):
    name = "base_crawler"  # Changed from web_spider

    @classmethod
    def from_crawler(cls, crawler: Crawler, *args: Any, **kwargs: Any) -> "BaseCrawler":
        """Connect the spider_closed signal before initializing the spider"""
        spider = super().from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)

        # Add a better SIGINT handling without directly using crawler.engine
        def sigint_handler(signum: int, frame: Any) -> None:
            logging.info("Interrupted by Ctrl+C. Shutting down gracefully...")
            # Use reactor to stop instead of trying to close the spider directly
            from twisted.internet import reactor

            if reactor.running:  # type: ignore[attr-defined]
                reactor.callFromThread(reactor.stop)  # type: ignore[attr-defined]

        # Register signal handler
        signal.signal(signal.SIGINT, sigint_handler)

        return spider

    def __init__(
        self,
        start_urls: str | list[str] | None = None,
        allowed_domains: list[str] | None = None,
        depth: int = 1,
        output_dir: str = "crawled_content",
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        # Convert single URL to list if needed
        if isinstance(start_urls, str):
            self.start_urls = [start_urls]
        else:
            self.start_urls = start_urls or []

        # Extract allowed domains from start URLs if not provided
        if allowed_domains is None:
            self.allowed_domains = []
            for url in self.start_urls:
                netloc = urlparse(url).netloc
                if netloc and netloc not in self.allowed_domains:
                    self.allowed_domains.append(netloc)
        else:
            self.allowed_domains = allowed_domains

        self.max_depth = int(depth)
        self.output_dir = output_dir

        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)

        # Track visited URLs
        self.visited_urls: set[str] = set()

        # URL mapping dictionary to store file path -> original URL mappings
        self.url_mappings: dict[str, dict[str, str]] = {}

        # Path for the URL mapping file
        self.mapping_file = os.path.join(self.output_dir, "url_mappings.json")

        # Load existing mappings if they exist
        if os.path.exists(self.mapping_file):
            try:
                with open(self.mapping_file, encoding="utf-8") as f:
                    self.url_mappings = json.load(f)
                logging.info(f"Loaded {len(self.url_mappings)} existing URL mappings")
            except Exception as e:
                logging.error(f"Error loading URL mappings: {str(e)}")

        logging.info(
            f"Starting crawler with max depth {self.max_depth} for URLs: {self.start_urls}",
        )
        logging.info(f"Allowed domains: {self.allowed_domains}")
        logging.info(f"Output directory: {self.output_dir}")

    def start_requests(self) -> Generator[Request, None, None]:
        """
        Start the crawling process with the provided URLs.
        """
        for url in self.start_urls:
            yield Request(url=url, callback=self.parse, cb_kwargs={"current_depth": 0})

    def parse(
        self,
        response: Response,
        current_depth: int = 0,
    ) -> Generator[dict[str, Any] | Request, None, None]:
        """
        Parse a web page, yield its content, and follow links up to the specified depth.
        """
        url = response.url
        if url in self.visited_urls:
            return  # Avoid processing the same URL multiple times

        self.visited_urls.add(url)

        logging.info(f"Processing {url} at depth {current_depth}/{self.max_depth}")

        try:
            # Check if it's HTML content type
            header_value = response.headers.get("Content-Type", b"") or b""
            content_type = header_value.decode("utf-8", errors="ignore").lower()

            # Only process HTML pages
            if "text/html" not in content_type:
                logging.info(
                    f"Skipping non-HTML content type '{content_type}' at {url}",
                )
                return

            # Save the raw HTML content and store URL mapping
            file_path = self._save_html_content(url, response.text)

            # Store the relative path (from output_dir) in the mappings
            rel_path = os.path.relpath(file_path, self.output_dir)
            self.url_mappings[rel_path] = {
                "url": url,
                "timestamp": datetime.now().isoformat(),
                "content_type": content_type,
            }

            # Save the URL mappings file periodically
            self._save_url_mappings()

            # Yield info about the crawled content
            yield {
                "url": url,
                "html": response.text,
                "depth": current_depth,
                "crawl_timestamp": datetime.now().isoformat(),
                "content_type": content_type,
            }

            # Follow links if we haven't reached max depth
            if current_depth < self.max_depth:
                for href in self._extract_links(response):
                    yield response.follow(
                        href,
                        callback=self.parse,
                        cb_kwargs={"current_depth": current_depth + 1},
                        errback=self.errback_handler,
                    )
        except Exception as e:
            logging.error(f"Error processing {url}: {str(e)}")

    def _save_html_content(self, url: str, html_content: str) -> str:
        """Save the HTML content to a file"""
        # Convert the URL to a file path
        file_path = self._get_file_path_from_url(url)

        # Create parent directories if needed
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Save the HTML content
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        logging.info(f"Saved HTML content to {file_path}")

        return file_path

    def _get_file_path_from_url(self, url: str) -> str:
        """Convert a URL to a file path"""
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        path = parsed_url.path

        # Handle empty path or just "/"
        if not path or path == "/":
            path = "index.html"
        elif not path.endswith(".html"):
            # Add .html extension if not present and remove trailing slash
            path = path.rstrip("/") + ".html"

        # Handle query parameters
        if parsed_url.query:
            # Santize query string for filename
            safe_query = parsed_url.query.replace("=", "_").replace("&", "_")
            # Add query to filename (before extension)
            if path.endswith(".html"):
                path = path[:-5] + "_" + safe_query + ".html"
            else:
                path = path + "_" + safe_query + ".html"

        # Create full path with domain as a subdirectory
        full_path = os.path.join(self.output_dir, domain, path.lstrip("/"))

        return full_path

    def _save_url_mappings(self) -> None:
        """Save the URL mappings to a JSON file"""
        try:
            with open(self.mapping_file, "w", encoding="utf-8") as f:
                json.dump(self.url_mappings, f, indent=2, ensure_ascii=False)
            logging.debug(
                f"Saved {len(self.url_mappings)} URL mappings to {self.mapping_file}",
            )
        except Exception as e:
            logging.error(f"Error saving URL mappings: {str(e)}")

    def spider_closed(self, spider: Spider) -> None:
        """Called when the spider is closed"""
        logging.info(f"Crawler closed. Visited {len(self.visited_urls)} pages")

        # Save the URL mappings one final time when spider closes
        self._save_url_mappings()
        logging.info(f"Saved final URL mappings with {len(self.url_mappings)} entries")

    def errback_handler(self, failure: Failure) -> None:
        """Handle request failures gracefully"""
        request = failure.request  # type: ignore[attr-defined]
        logging.warning(f"Error on {request.url}: {failure.value}")

    def _extract_links(self, response: Response) -> list[str]:
        """Extract valid links to follow"""
        # Using a simple approach for now, extracting all links
        links = response.css("a::attr(href)").getall()
        return links
