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
        # Now validation happens at initialization time
        with pytest.raises(ValueError, match=r"base_url cannot be empty"):
            _ = SiteParserConfig(
                site_name="test",
                base_url="",  # Empty string
                content_selectors=['//div[@id="main"]'],
            )

    def test_invalid_url_scheme(self):
        """Test base_dir with invalid URL scheme."""
        # Now validation happens at initialization time
        with pytest.raises(ValueError, match=r"Invalid URL: invalid-url"):
            _ = SiteParserConfig(
                site_name="test",
                base_url="invalid-url",  # No scheme
                content_selectors=['//div[@id="main"]'],
            )

    def test_file_url(self):
        """Test base_dir with file URL."""
        # Now validation happens at initialization time
        with pytest.raises(ValueError, match=r"Invalid URL: file:///path/to/file.html"):
            _ = SiteParserConfig(
                site_name="test",
                base_url="file:///path/to/file.html",
                content_selectors=['//div[@id="main"]'],
            )


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
