import json
import logging
import os
import re
import signal
from datetime import datetime
from typing import Dict, List, Set
from urllib.parse import quote, urlparse

import yaml
from scrapy import Spider, signals
from scrapy.http import Request

from migri_assistant.utils import is_pdf_url


class WebSpider(Spider):
    name = "web_spider"

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        """Connect the spider_closed signal before initializing the spider"""
        spider = super(WebSpider, cls).from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)

        # Add SIGINT handling through Scrapy's shutdown mechanism
        # which is more reliable than direct signal handling
        def sigint_handler(signum, frame):
            crawler.engine.close_spider(spider, reason="SIGINT received")
            logging.info("Interrupted by Ctrl+C. Shutting down gracefully...")
            # After trying the clean shutdown, wait a bit then force exit if needed
            import threading

            def force_exit():
                import time

                time.sleep(3)  # Wait 3 seconds for clean shutdown
                logging.info("Forcing shutdown...")
                os._exit(1)  # Force exit if graceful shutdown doesn't complete

            threading.Thread(target=force_exit).start()

        # Register signal handler
        signal.signal(signal.SIGINT, sigint_handler)

        return spider

    def __init__(
        self,
        start_urls=None,
        allowed_domains=None,
        depth=1,
        output_dir="scraped_content",
        output_file=None,
        pdf_output_file=None,
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

        # Output settings
        self.output_dir = output_dir
        self.output_file = output_file
        self.pdf_output_file = pdf_output_file or "pdfs.json"

        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)

        # Track scraped results to make interruption possible
        self.results = []
        self.pdf_urls: List[Dict] = []
        self.visited_urls: Set[str] = set()

        logging.info(
            f"Starting spider with max depth {self.max_depth} for URLs: {self.start_urls}"
        )
        logging.info(f"Allowed domains: {self.allowed_domains}")
        logging.info(f"Saving Markdown files to: {self.output_dir}")

    def start_requests(self):
        for url in self.start_urls:
            yield Request(url=url, callback=self.parse, cb_kwargs={"current_depth": 0})

    def parse(self, response, current_depth=0):
        """
        Parse a web page, extract content, and follow links up to the specified depth.
        """
        url = response.url
        self.visited_urls.add(url)

        logging.info(f"Parsing {url} at depth {current_depth}/{self.max_depth}")

        try:
            # Check if it's a PDF by content type
            content_type = (
                response.headers.get("Content-Type", b"")
                .decode("utf-8", errors="ignore")
                .lower()
            )

            if "application/pdf" in content_type or is_pdf_url(url):
                logging.info(f"Skipping PDF: {url}")
                self._save_pdf_url(url, current_depth)
                return

            # Extract useful content
            title = self._extract_title(response)
            html_content = self._extract_html_content(response)
            plain_text = self._extract_content(response)

            # Create metadata for frontmatter
            metadata = {
                "url": url,
                "title": title,
                "depth": current_depth,
                "source_domain": urlparse(url).netloc,
                "crawl_timestamp": datetime.now().isoformat(),
                "content_type": content_type,
            }

            # Save the content as Markdown with frontmatter
            self._save_as_markdown(url, title, plain_text, html_content, metadata)

            # Also save basic info to results list for interruptibility
            result_entry = {
                "url": url,
                "title": title,
                "depth": current_depth,
                "timestamp": datetime.now().isoformat(),
            }
            self.results.append(result_entry)

            # Save results after each page to enable interruption
            self._save_results()

            # Follow links if we haven't reached max depth
            if current_depth < self.max_depth:
                for href in self._extract_links(response):
                    if is_pdf_url(href):
                        logging.info(f"Found PDF link: {href}")
                        self._save_pdf_url(href, current_depth + 1)
                        continue

                    yield response.follow(
                        href,
                        callback=self.parse,
                        cb_kwargs={"current_depth": current_depth + 1},
                        errback=self.errback_handler,
                    )
        except Exception as e:
            logging.error(f"Error processing {url}: {str(e)}")

    def _save_as_markdown(self, url, title, plain_text, html_content, metadata):
        """Save the content as Markdown with YAML frontmatter"""
        # Create a safe filename from the URL
        filename = self._url_to_safe_filename(url)

        # Prepare the markdown content with frontmatter
        frontmatter = yaml.dump(metadata, default_flow_style=False)

        # Construct the full markdown content
        markdown_content = f"---\n{frontmatter}---\n\n# {title}\n\n{plain_text}\n"

        # Save the markdown file
        file_path = os.path.join(self.output_dir, f"{filename}.md")

        # Create parent directories if needed
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        # Also save the original HTML if it exists
        if html_content:
            html_path = os.path.join(self.output_dir, f"{filename}.html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)

        logging.info(f"Saved content to {file_path}")

        # Add file path to metadata for tracking
        metadata["file_path"] = file_path
        return file_path

    def _url_to_safe_filename(self, url):
        """Convert a URL to a safe filename"""
        # Parse the URL and remove the scheme
        parsed = urlparse(url)
        path = parsed.path

        # Handle empty path or just "/"
        if not path or path == "/":
            path = "index"

        # Create directory structure based on domain and path
        domain_part = parsed.netloc
        path_part = path.lstrip("/").replace("/", "_")

        # Handle query parameters by appending a hash of them
        if parsed.query:
            path_part += f"_{quote(parsed.query, safe='')[:50]}"  # Limit length

        # Create a filename safe for all operating systems
        safe_name = f"{domain_part}/{path_part}"
        return safe_name

    def _save_pdf_url(self, url, depth):
        """Save PDF URL to the PDF list"""
        pdf_entry = {
            "url": url,
            "depth": depth,
            "source_domain": urlparse(url).netloc,
            "found_timestamp": datetime.now().isoformat(),
        }
        self.pdf_urls.append(pdf_entry)

        # Save PDF list to file
        with open(self.pdf_output_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "timestamp": datetime.now().isoformat(),
                    "pdf_count": len(self.pdf_urls),
                    "pdfs": self.pdf_urls,
                },
                f,
                indent=2,
            )

    def _save_results(self):
        """Save current results to the output file if specified"""
        if not self.output_file:
            return

        # Calculate the first URL from self.start_urls
        url = self.start_urls[0] if self.start_urls else "unknown"

        with open(self.output_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "timestamp": datetime.now().isoformat(),
                    "url": url,
                    "depth": self.max_depth,
                    "pages_scraped": len(self.visited_urls),
                    "results": self.results,
                },
                f,
                indent=2,
            )

    def spider_closed(self, spider):
        """Called when the spider is closed"""
        logging.info(f"Spider closed. Visited {len(self.visited_urls)} pages")
        self._save_results()

        # Save PDFs to file
        if self.pdf_urls:
            logging.info(f"Found {len(self.pdf_urls)} PDF files")
            with open(self.pdf_output_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "timestamp": datetime.now().isoformat(),
                        "pdf_count": len(self.pdf_urls),
                        "pdfs": self.pdf_urls,
                    },
                    f,
                    indent=2,
                )

    def errback_handler(self, failure):
        """Handle request failures gracefully"""
        request = failure.request
        logging.warning(f"Error on {request.url}: {failure.value}")

    def _extract_title(self, response):
        """Extract page title"""
        title = response.css("title::text").get() or ""
        return title.strip()

    def _extract_html_content(self, response):
        """
        Extract the HTML content from the response.
        """
        # Get the HTML content from the body
        body_content = response.css("body").get() or response.text
        return body_content

    def _extract_content(self, response):
        """Extract cleaned main content from the page (used as fallback)"""
        # Try to get main content
        main_content = (
            response.css("main").extract() or response.css("article").extract()
        )

        if main_content:
            # Use the first main content area found
            text = self._clean_html(main_content[0])
        else:
            # Fallback to body content, excluding navigation, footer, etc.
            body_content = response.css("body").extract_first()
            if body_content:
                # Remove common non-content elements
                clean_html = re.sub(
                    r"<(nav|header|footer|script|style|aside)[^>]*>.*?</\1>",
                    "",
                    body_content,
                    flags=re.DOTALL,
                )
                text = self._clean_html(clean_html)
            else:
                # Last resort, just get text from the whole body
                text = " ".join(response.css("body ::text").getall())

        return " ".join(text.split())  # Normalize whitespace

    def _clean_html(self, html_content):
        """Remove HTML tags and normalize whitespace"""
        # Simple regex to remove HTML tags
        clean_text = re.sub(r"<[^>]+>", " ", html_content)
        # Remove extra whitespace
        clean_text = re.sub(r"\s+", " ", clean_text).strip()
        return clean_text

    def _extract_links(self, response):
        """Extract valid links to follow"""
        # Focus on content areas for links when possible
        content_areas = response.css(
            "main a::attr(href), article a::attr(href)"
        ).getall()

        # If no links found in main content, fall back to all links
        if not content_areas:
            content_areas = response.css("a::attr(href)").getall()

        return content_areas
