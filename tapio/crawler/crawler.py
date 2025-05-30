import asyncio
import json
import logging
import os
from datetime import datetime
from typing import TypedDict
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from tapio.config.settings import DEFAULT_DIRS


class UrlMappingData(TypedDict):
    """Type definition for URL mapping data."""

    url: str
    timestamp: str
    content_type: str


class CrawlResult(TypedDict):
    """Type definition for crawl result data."""

    url: str
    html: str
    depth: int
    crawl_timestamp: str
    content_type: str


class BaseCrawler:
    """
    Base crawler implementation for web scraping using httpx and BeautifulSoup.

    This crawler is responsible for fetching web pages, storing their content,
    and following links up to a specified depth using async/await patterns.
    """

    def __init__(
        self,
        start_urls: str | list[str] | None = None,
        allowed_domains: list[str] | None = None,
        depth: int = 1,
        output_dir: str = DEFAULT_DIRS["CRAWLED_DIR"],
        timeout: int = 30,
        max_concurrent: int = 10,
        delay_between_requests: float = 1.0,
    ) -> None:
        """
        Initialize the crawler with configuration parameters.

        Args:
            start_urls: URL or list of URLs to start crawling from.
            allowed_domains: List of domains to restrict crawling to.
                If None, domains are extracted from start_urls.
            depth: How many links deep to follow from the starting URLs.
            output_dir: Directory to save crawled HTML files.
            timeout: HTTP request timeout in seconds.
            max_concurrent: Maximum number of concurrent requests.
            delay_between_requests: Delay in seconds between requests to avoid rate limiting.
        """
        # Convert single URL to list if needed
        if isinstance(start_urls, str):
            self.start_urls = [start_urls]
        else:
            self.start_urls = start_urls or []

        # Extract allowed domains from start URLs if not provided
        if allowed_domains is None:
            self.allowed_domains: list[str] = []
            for url in self.start_urls:
                netloc = urlparse(url).netloc
                if netloc and netloc not in self.allowed_domains:
                    self.allowed_domains.append(netloc)
        else:
            self.allowed_domains = allowed_domains

        self.max_depth = int(depth)
        self.output_dir = output_dir
        self.timeout = timeout
        self.max_concurrent = max_concurrent
        self.delay_between_requests = delay_between_requests

        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)

        # Track visited URLs to avoid duplicates
        self.visited_urls: set[str] = set()

        # URL mapping dictionary to store file path -> original URL mappings
        self.url_mappings: dict[str, UrlMappingData] = {}

        # Path for the URL mapping file
        self.mapping_file = os.path.join(self.output_dir, "url_mappings.json")

        # Semaphore will be created in async context
        self._semaphore: asyncio.Semaphore | None = None

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

    @property
    def semaphore(self) -> asyncio.Semaphore:
        """Get or create the semaphore for concurrent request limiting."""
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.max_concurrent)
        return self._semaphore

    async def crawl(self) -> list[CrawlResult]:
        """
        Start the crawling process and return the results.

        Returns:
            List of CrawlResult dictionaries containing page data.
        """
        results: list[CrawlResult] = []

        # Use a timeout for the entire client session
        timeout = httpx.Timeout(self.timeout)

        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            # Create initial tasks for all starting URLs
            tasks = [self._crawl_url(client, url, 0, results) for url in self.start_urls]

            # Process all tasks
            await asyncio.gather(*tasks, return_exceptions=True)

        # Save final URL mappings
        self._save_url_mappings()
        logging.info(f"Crawling completed. Processed {len(results)} pages.")

        return results

    async def _crawl_url(
        self,
        client: httpx.AsyncClient,
        url: str,
        current_depth: int,
        results: list[CrawlResult],
    ) -> None:
        """
        Crawl a single URL and recursively crawl linked pages.

        Args:
            client: httpx async client for making requests.
            url: URL to crawl.
            current_depth: Current crawling depth.
            results: List to append crawl results to.
        """
        # Check if URL was already visited
        if url in self.visited_urls:
            return

        # Check depth limit
        if current_depth > self.max_depth:
            return

        # Check domain restrictions
        if not self._is_allowed_domain(url):
            logging.debug(f"Skipping URL outside allowed domains: {url}")
            return

        # Use semaphore to limit concurrent requests
        async with self.semaphore:
            try:
                logging.info(f"Processing {url} at depth {current_depth}/{self.max_depth}")

                # Add delay between requests to avoid rate limiting
                if self.delay_between_requests > 0:
                    await asyncio.sleep(self.delay_between_requests)

                # Mark URL as visited
                self.visited_urls.add(url)

                # Make HTTP request
                response = await client.get(url)
                response.raise_for_status()

                # Check content type
                content_type = response.headers.get("content-type", "").lower()
                if "text/html" not in content_type:
                    logging.info(f"Skipping non-HTML content type '{content_type}' at {url}")
                    return

                # Parse HTML content
                html_content = response.text
                soup = BeautifulSoup(html_content, "lxml")

                # Save the HTML content and store URL mapping
                file_path = self._save_html_content(url, html_content)
                rel_path = os.path.relpath(file_path, self.output_dir)

                self.url_mappings[rel_path] = UrlMappingData(
                    url=url,
                    timestamp=datetime.now().isoformat(),
                    content_type=content_type,
                )

                # Create crawl result
                crawl_result: CrawlResult = {
                    "url": url,
                    "html": html_content,
                    "depth": current_depth,
                    "crawl_timestamp": datetime.now().isoformat(),
                    "content_type": content_type,
                }
                results.append(crawl_result)

                # Save URL mappings periodically
                self._save_url_mappings()

                # Extract links for following if we haven't reached max depth
                links_to_follow = []
                if current_depth < self.max_depth:
                    links = self._extract_links(soup, url)
                    links_to_follow = [link for link in links if link not in self.visited_urls]

            except httpx.HTTPStatusError as e:
                logging.warning(f"HTTP error for {url}: {e.response.status_code}")
                return
            except httpx.RequestError as e:
                logging.warning(f"Request error for {url}: {str(e)}")
                return
            except Exception as e:
                logging.error(f"Error processing {url}: {str(e)}")
                return

        # Process child links OUTSIDE the semaphore context to avoid deadlock
        if links_to_follow:
            link_tasks = [self._crawl_url(client, link, current_depth + 1, results) for link in links_to_follow]
            # Process link tasks concurrently
            await asyncio.gather(*link_tasks, return_exceptions=True)

    def _is_allowed_domain(self, url: str) -> bool:
        """
        Check if a URL belongs to an allowed domain.

        Args:
            url: URL to check.

        Returns:
            True if the URL domain is allowed, False otherwise.
        """
        if not self.allowed_domains:
            return True

        parsed_url = urlparse(url)
        return parsed_url.netloc in self.allowed_domains

    def _save_html_content(self, url: str, html_content: str) -> str:
        """
        Save the HTML content to a file.

        Args:
            url: The URL of the page.
            html_content: The HTML content to save.

        Returns:
            The absolute path to the saved file.
        """
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
        """
        Convert a URL to a file path.

        Args:
            url: The URL to convert.

        Returns:
            The absolute path for saving the URL content.
        """
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
            # Sanitize query string for filename
            safe_query = parsed_url.query.replace("=", "_").replace("&", "_")
            # Add query to filename (before extension)
            if path.endswith(".html"):
                path = path[:-5] + "_" + safe_query + ".html"
            else:
                path = path + "_" + safe_query + ".html"

        # Create full path with domain as a subdirectory
        full_path = os.path.join(self.output_dir, domain, path.lstrip("/"))

        # Ensure the path stays within output_dir (security check for path traversal)
        abs_full_path = os.path.abspath(full_path)
        abs_output_dir = os.path.abspath(self.output_dir)
        if not abs_full_path.startswith(abs_output_dir):
            raise ValueError(f"Invalid URL results in path outside output directory: {url}")

        return full_path

    def _save_url_mappings(self) -> None:
        """
        Save the URL mappings to a JSON file.

        This allows future reference of which file corresponds to which URL.
        """
        try:
            with open(self.mapping_file, "w", encoding="utf-8") as f:
                json.dump(self.url_mappings, f, indent=2, ensure_ascii=False)
            logging.debug(
                f"Saved {len(self.url_mappings)} URL mappings to {self.mapping_file}",
            )
        except Exception as e:
            logging.error(f"Error saving URL mappings: {str(e)}")

    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> list[str]:
        """
        Extract valid links to follow from a BeautifulSoup object.

        Args:
            soup: BeautifulSoup object of the parsed HTML.
            base_url: Base URL for resolving relative links.

        Returns:
            A list of absolute URLs to follow.
        """
        links = []

        # Extract all href attributes from anchor tags
        for anchor in soup.find_all("a", href=True):
            # Get href attribute - BeautifulSoup guarantees it exists due to href=True filter
            href = anchor["href"]  # type: ignore[index]

            # Skip if href is None or empty
            if not href:
                continue

            # Convert to string (BeautifulSoup can return different types)
            href = str(href)

            # Convert relative URLs to absolute URLs
            absolute_url = urljoin(base_url, href)

            # Filter out non-http(s) schemes and fragments
            if absolute_url.startswith(("http://", "https://")) and "#" not in absolute_url:
                # Check if the domain is allowed
                if self._is_allowed_domain(absolute_url):
                    links.append(absolute_url)

        return links
