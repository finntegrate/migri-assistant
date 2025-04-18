import logging
import os
import signal
from datetime import datetime
from typing import Set
from urllib.parse import urlparse

from scrapy import Spider, signals
from scrapy.http import Request


class BaseCrawler(Spider):
    name = "base_crawler"  # Changed from web_spider

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        """Connect the spider_closed signal before initializing the spider"""
        spider = super(BaseCrawler, cls).from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)

        # Add a better SIGINT handling without directly using crawler.engine
        def sigint_handler(signum, frame):
            logging.info("Interrupted by Ctrl+C. Shutting down gracefully...")
            # Use reactor to stop instead of trying to close the spider directly
            from twisted.internet import reactor

            if reactor.running:
                reactor.callFromThread(reactor.stop)

        # Register signal handler
        signal.signal(signal.SIGINT, sigint_handler)

        return spider

    def __init__(
        self,
        start_urls=None,
        allowed_domains=None,
        depth=1,
        output_dir="crawled_content",
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
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
        self.visited_urls: Set[str] = set()

        logging.info(
            f"Starting crawler with max depth {self.max_depth} for URLs: {self.start_urls}"
        )
        logging.info(f"Allowed domains: {self.allowed_domains}")
        logging.info(f"Output directory: {self.output_dir}")

    def start_requests(self):
        """
        Start the crawling process with the provided URLs.
        """
        for url in self.start_urls:
            yield Request(url=url, callback=self.parse, cb_kwargs={"current_depth": 0})

    def parse(self, response, current_depth=0):
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
            content_type = (
                response.headers.get("Content-Type", b"")
                .decode("utf-8", errors="ignore")
                .lower()
            )

            # Only process HTML pages
            if "text/html" not in content_type:
                logging.info(
                    f"Skipping non-HTML content type '{content_type}' at {url}"
                )
                return

            # Save the raw HTML content
            self._save_html_content(url, response.text)

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

    def _save_html_content(self, url, html_content):
        """Save the HTML content to a file"""
        # Convert the URL to a file path
        file_path = self._get_file_path_from_url(url)

        # Create parent directories if needed
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Save the HTML content
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        logging.info(f"Saved HTML content to {file_path}")

    def _get_file_path_from_url(self, url):
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

    def spider_closed(self, spider):
        """Called when the spider is closed"""
        logging.info(f"Crawler closed. Visited {len(self.visited_urls)} pages")

    def errback_handler(self, failure):
        """Handle request failures gracefully"""
        request = failure.request
        logging.warning(f"Error on {request.url}: {failure.value}")

    def _extract_links(self, response):
        """Extract valid links to follow"""
        # Using a simple approach for now, extracting all links
        links = response.css("a::attr(href)").getall()
        return links
