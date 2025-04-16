import logging
from typing import List, Optional
from urllib.parse import urlparse

from migri_assistant.scrapers.scrapy_scraper import ScrapyScraper
from migri_assistant.spiders.migri_spider import MigriSpider


class MigriScraper(ScrapyScraper):
    """
    Specialized scraper for migri.fi website.

    This scraper utilizes the MigriSpider to extract content specifically from
    the main content area of migri.fi pages, avoiding duplication of navigation
    and footer content.
    """

    def __init__(self, **kwargs):
        """
        Initialize the MigriScraper with migri.fi specific settings.
        """
        super().__init__(**kwargs)
        logging.info("Initialized MigriScraper for Migri.fi website")

    def get_spider_class(self):
        """
        Return the specialized spider class for Migri.fi.

        Returns:
            MigriSpider: The spider class to use
        """
        return MigriSpider

    def scrape(
        self,
        url: str,
        depth: int = 1,
        allowed_domains: Optional[List[str]] = None,
        **kwargs,
    ) -> List[dict]:
        """
        Scrape content from Migri.fi website starting from the provided URL.

        If allowed_domains is not provided, it will be inferred from the url.

        Args:
            url: The URL to start scraping from
            depth: How many links deep to follow
            allowed_domains: Optional list of domains to restrict crawling to
            **kwargs: Additional keyword arguments to pass to the spider

        Returns:
            List of document dictionaries containing the scraped content
        """
        # If allowed_domains not provided, infer from start_url
        if allowed_domains is None:
            allowed_domains = []
            parsed_url = urlparse(url)
                domain = parsed_url.netloc
                if domain and domain not in allowed_domains:
                    allowed_domains.append(domain)

            logging.info(f"Inferred allowed domains: {allowed_domains}")

        # Call the parent scrape method with our settings
        return super().scrape(
            url=url, depth=depth, allowed_domains=allowed_domains, **kwargs
        )
