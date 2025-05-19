"""
Scrapy settings for migri-assistant project.
"""

BOT_NAME = "tapio"

# Crawl responsibly by identifying yourself to websites
USER_AGENT = "migri-assistant (+http://migri.fi)"

# Obey robots.txt rules
ROBOTSTXT_OBEY = True

# Configure maximum concurrent requests
CONCURRENT_REQUESTS = 4

# Configure a delay for requests for the same website
DOWNLOAD_DELAY = 1

# Disable cookies
COOKIES_ENABLED = False

# Configure item pipelines
ITEM_PIPELINES: dict[str, int] = {}

# Enable and configure the AutoThrottle extension
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 5
AUTOTHROTTLE_MAX_DELAY = 60
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
AUTOTHROTTLE_DEBUG = False

# Set settings whose default value is deprecated to a future-proof value
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"

# Additional default settings used by the ScrapyRunner
DEFAULT_SETTINGS = {
    "LOG_LEVEL": "INFO",
    "DOWNLOAD_DELAY": 1,
    "ROBOTSTXT_OBEY": True,
    "COOKIES_ENABLED": False,  # Added to help with stability
    "RETRY_ENABLED": True,  # Added to improve reliability
    "RETRY_TIMES": 2,  # Added to improve reliability
    "DOWNLOAD_TIMEOUT": 30,  # Added to prevent hanging
    "TWISTED_REACTOR": "twisted.internet.selectreactor.SelectReactor",
}
