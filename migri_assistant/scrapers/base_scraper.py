from abc import ABC, abstractmethod


class BaseScraper(ABC):
    """
    Abstract base class for web scrapers
    """

    @abstractmethod
    def scrape(
        self,
        url: str,
        depth: int = 1,
        allowed_domains: list[str] | None = None,
    ) -> list[dict]:
        """
        Scrape content from a URL up to specified depth

        Args:
            url: The URL to start scraping from
            depth: How many links deep to follow
            allowed_domains: List of domains to restrict scraping to

        Returns:
            List of document dictionaries containing the scraped content
        """
        pass
