"""Tests for the Scrapy settings module."""

from tapio.crawler import settings


def test_bot_name():
    """Test that BOT_NAME has expected value."""
    assert settings.BOT_NAME == "migri_assistant"


def test_user_agent():
    """Test that USER_AGENT has expected value."""
    assert settings.USER_AGENT == "migri-assistant (+http://migri.fi)"


def test_robotstxt_obey():
    """Test that ROBOTSTXT_OBEY has expected value."""
    assert settings.ROBOTSTXT_OBEY is True


def test_concurrency_settings():
    """Test that concurrency settings have expected values."""
    assert settings.CONCURRENT_REQUESTS == 4
    assert settings.DOWNLOAD_DELAY == 1


def test_cookies_disabled():
    """Test that cookies are disabled."""
    assert settings.COOKIES_ENABLED is False


def test_autothrottle_settings():
    """Test that autothrottle settings have expected values."""
    assert settings.AUTOTHROTTLE_ENABLED is True
    assert settings.AUTOTHROTTLE_START_DELAY == 5
    assert settings.AUTOTHROTTLE_MAX_DELAY == 60
    assert settings.AUTOTHROTTLE_TARGET_CONCURRENCY == 1.0
    assert settings.AUTOTHROTTLE_DEBUG is False


def test_future_proof_settings():
    """Test that future-proof settings have expected values."""
    assert settings.REQUEST_FINGERPRINTER_IMPLEMENTATION == "2.7"
    assert settings.TWISTED_REACTOR == "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
    assert settings.FEED_EXPORT_ENCODING == "utf-8"
