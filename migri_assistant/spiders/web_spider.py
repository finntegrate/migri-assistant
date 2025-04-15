import logging
import re
from datetime import datetime
from urllib.parse import urlparse

from scrapy import Spider
from scrapy.http import Request

from migri_assistant.models.document import Document
from migri_assistant.vectorstore.chroma_store import ChromaStore


class WebSpider(Spider):
    name = "web_spider"

    def __init__(
        self,
        start_urls=None,
        allowed_domains=None,
        depth=1,
        collection_name="migri_documents",
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
        self.chroma_store = ChromaStore(collection_name=collection_name)
        logging.info(
            f"Starting spider with max depth {self.max_depth} for URLs: {self.start_urls}"
        )
        logging.info(f"Allowed domains: {self.allowed_domains}")

    def start_requests(self):
        for url in self.start_urls:
            yield Request(url=url, callback=self.parse, cb_kwargs={"current_depth": 0})

    def parse(self, response, current_depth=0):
        """
        Parse a web page, extract content, and follow links up to the specified depth.
        """
        logging.info(
            f"Parsing {response.url} at depth {current_depth}/{self.max_depth}"
        )

        try:
            # Extract useful content
            title = self._extract_title(response)
            content = self._extract_content(response)

            # Create metadata
            metadata = {
                "url": response.url,
                "title": title,
                "depth": current_depth,
                "source_domain": urlparse(response.url).netloc,
                "crawl_timestamp": datetime.now().isoformat(),
                "content_type": response.headers.get("Content-Type", b"").decode(
                    "utf-8", errors="ignore"
                ),
            }

            # Create document and store it
            document = Document(url=response.url, content=content, metadata=metadata)
            self._store_document(document)

            # Follow links if we haven't reached max depth
            if current_depth < self.max_depth:
                for href in self._extract_links(response):
                    yield response.follow(
                        href,
                        callback=self.parse,
                        cb_kwargs={"current_depth": current_depth + 1},
                    )
        except Exception as e:
            logging.error(f"Error processing {response.url}: {str(e)}")

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
