import json
import logging
import re
import signal
from datetime import datetime
from typing import Dict, List, Set
from urllib.parse import urlparse

from scrapy import Spider, signals
from scrapy.http import Request

from migri_assistant.models.document import Document
from migri_assistant.utils import chunk_text, is_pdf_url
from migri_assistant.vectorstore.chroma_store import ChromaStore


class WebSpider(Spider):
    name = "web_spider"

    def __init__(
        self,
        start_urls=None,
        allowed_domains=None,
        depth=1,
        collection_name="migri_documents",
        output_file=None,
        pdf_output_file=None,
        chunk_size=1000,
        chunk_overlap=200,
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
        self.collection_name = collection_name
        self.chroma_store = ChromaStore(collection_name=collection_name)

        # Chunking parameters
        self.chunk_size = int(chunk_size)
        self.chunk_overlap = int(chunk_overlap)

        # Output file settings
        self.output_file = output_file
        self.pdf_output_file = pdf_output_file or "pdfs.json"

        # Track scraped results to make interruption possible
        self.results = []
        self.pdf_urls: List[Dict] = []
        self.visited_urls: Set[str] = set()

        # Register the spider_closed signal handler
        self.crawler.signals.connect(self.spider_closed, signal=signals.spider_closed)

        # Register SIGINT handler for graceful shutdown on Ctrl+C
        signal.signal(signal.SIGINT, self.handle_sigint)

        logging.info(
            f"Starting spider with max depth {self.max_depth} for URLs: {self.start_urls}"
        )
        logging.info(f"Allowed domains: {self.allowed_domains}")
        logging.info(
            f"Text chunking: size={self.chunk_size}, overlap={self.chunk_overlap}"
        )

    def handle_sigint(self, sig, frame):
        """Handle SIGINT (Ctrl+C) by closing the spider gracefully"""
        logging.info("Received interrupt signal. Shutting down gracefully...")
        self.crawler.engine.close_spider(self, "Interrupted by user")

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
            content = self._extract_content(response)

            # Create metadata
            metadata = {
                "url": url,
                "title": title,
                "depth": current_depth,
                "source_domain": urlparse(url).netloc,
                "crawl_timestamp": datetime.now().isoformat(),
                "content_type": content_type,
            }

            # Create document with chunked content if needed
            if content and self.chunk_size > 0 and len(content) > self.chunk_size:
                chunks = chunk_text(content, self.chunk_size, self.chunk_overlap)
                logging.info(f"Split content into {len(chunks)} chunks")

                for i, chunk in enumerate(chunks):
                    chunk_metadata = metadata.copy()
                    chunk_metadata["chunk_index"] = i
                    chunk_metadata["chunk_count"] = len(chunks)

                    document = Document(
                        url=f"{url}#chunk{i}", content=chunk, metadata=chunk_metadata
                    )
                    self._store_document(document)

                    # Also save to results list for interruptibility
                    doc_dict = document.to_dict()
                    self.results.append(doc_dict)
            else:
                # Store as a single document
                document = Document(url=url, content=content, metadata=metadata)
                self._store_document(document)

                # Also save to results list for interruptibility
                doc_dict = document.to_dict()
                self.results.append(doc_dict)

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

    def errback_handler(self, failure):
        """Handle request failures gracefully"""
        request = failure.request
        logging.warning(f"Error on {request.url}: {failure.value}")

    def _extract_title(self, response):
        """Extract page title"""
        title = response.css("title::text").get() or ""
        return title.strip()

    def _extract_content(self, response):
        """Extract cleaned main content from the page"""
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

    def _store_document(self, document):
        """Store the document in ChromaDB"""
        try:
            self.chroma_store.add_document(
                document_id=document.url,
                embedding=None,  # We'll generate embeddings later
                metadata=document.metadata,
            )
            logging.info(f"Successfully stored document: {document.url}")
        except Exception as e:
            logging.error(f"Failed to store document {document.url}: {str(e)}")

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
                    "collection": self.collection_name,
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
