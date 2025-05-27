"""Tests for the config_models module."""

import pytest

from tapio.config.config_models import HtmlToMarkdownConfig, SiteParserConfig


class TestSiteParserConfigBaseDir:
    """Tests for the SiteParserConfig base_dir property."""

    def test_normal_url(self):
        """Test base_dir with normal URL."""
        config = SiteParserConfig(
            site_name="test",
            base_url="https://example.com",
            content_selectors=['//div[@id="main"]'],
        )
        assert config.base_dir == "example.com"

    def test_url_with_subdomain(self):
        """Test base_dir with URL containing subdomain."""
        config = SiteParserConfig(
            site_name="test",
            base_url="https://docs.example.com",
            content_selectors=['//div[@id="main"]'],
        )
        assert config.base_dir == "docs.example.com"

    def test_url_with_port(self):
        """Test base_dir with URL containing port number."""
        config = SiteParserConfig(
            site_name="test",
            base_url="https://example.com:8080",
            content_selectors=['//div[@id="main"]'],
        )
        assert config.base_dir == "example.com"  # should exclude port

    def test_url_with_path(self):
        """Test base_dir with URL containing path."""
        config = SiteParserConfig(
            site_name="test",
            base_url="https://example.com/path/to/page",
            content_selectors=['//div[@id="main"]'],
        )
        assert config.base_dir == "example.com"  # should exclude path

    def test_url_with_query_params(self):
        """Test base_dir with URL containing query parameters."""
        config = SiteParserConfig(
            site_name="test",
            base_url="https://example.com?param=value",
            content_selectors=['//div[@id="main"]'],
        )
        assert config.base_dir == "example.com"  # should exclude query params

    def test_url_with_fragments(self):
        """Test base_dir with URL containing fragments."""
        config = SiteParserConfig(
            site_name="test",
            base_url="https://example.com#section",
            content_selectors=['//div[@id="main"]'],
        )
        assert config.base_dir == "example.com"  # should exclude fragments

    def test_localhost_url(self):
        """Test base_dir with localhost URL."""
        config = SiteParserConfig(
            site_name="test",
            base_url="http://localhost:3000",
            content_selectors=['//div[@id="main"]'],
        )
        assert config.base_dir == "localhost"  # should exclude port

    def test_ip_address_url(self):
        """Test base_dir with IP address URL."""
        config = SiteParserConfig(
            site_name="test",
            base_url="http://127.0.0.1:8080",
            content_selectors=['//div[@id="main"]'],
        )
        assert config.base_dir == "127.0.0.1"  # should exclude port

    def test_empty_base_url(self):
        """Test base_dir with empty base_url."""
        config = SiteParserConfig(
            site_name="test",
            base_url="",  # Empty string
            content_selectors=['//div[@id="main"]'],
        )
        # Should raise ValueError when accessing base_dir
        with pytest.raises(ValueError, match=r"Invalid base_url: ''"):
            _ = config.base_dir

    def test_invalid_url_scheme(self):
        """Test base_dir with invalid URL scheme."""
        config = SiteParserConfig(
            site_name="test",
            base_url="invalid-url",  # No scheme
            content_selectors=['//div[@id="main"]'],
        )
        # Should fail because the URL has no hostname
        with pytest.raises(ValueError, match=r"Invalid base_url: 'invalid-url'"):
            _ = config.base_dir

    def test_file_url(self):
        """Test base_dir with file URL."""
        config = SiteParserConfig(
            site_name="test",
            base_url="file:///path/to/file.html",
            content_selectors=['//div[@id="main"]'],
        )
        # file URLs don't have a hostname, so this should raise an error
        with pytest.raises(ValueError):
            _ = config.base_dir


class TestSiteParserConfig:
    """Tests for other aspects of SiteParserConfig."""

    def test_default_values(self):
        """Test default values for SiteParserConfig."""
        config = SiteParserConfig(
            site_name="test",
            base_url="https://example.com",  # Explicitly provide base_url
            content_selectors=['//div[@id="main"]'],
        )
        assert config.site_name == "test"
        assert config.base_url == "https://example.com"
        assert config.title_selector == "//title"
        assert config.fallback_to_body is True
        assert config.description is None
        assert isinstance(config.markdown_config, HtmlToMarkdownConfig)
