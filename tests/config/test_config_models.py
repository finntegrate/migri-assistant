"""Tests for the config_models module."""

import pytest
from pydantic import HttpUrl, ValidationError

from tapio.config.config_models import HtmlToMarkdownConfig, ParserConfigRegistry, SiteParserConfig


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
        # Now validation happens at initialization time with Pydantic HttpUrl
        with pytest.raises(ValidationError, match=r"Input should be a valid URL"):
            _ = SiteParserConfig(
                site_name="test",
                base_url="",  # Empty string
                content_selectors=['//div[@id="main"]'],
            )

    def test_invalid_url_scheme(self):
        """Test base_dir with invalid URL scheme."""
        # Now validation happens at initialization time with Pydantic HttpUrl
        with pytest.raises(ValidationError, match=r"Input should be a valid URL"):
            _ = SiteParserConfig(
                site_name="test",
                base_url="invalid-url",  # No scheme
                content_selectors=['//div[@id="main"]'],
            )

    def test_file_url(self):
        """Test base_dir with file URL."""
        # Now validation happens at initialization time with Pydantic HttpUrl
        with pytest.raises(ValidationError, match=r"URL scheme should be 'http' or 'https'"):
            _ = SiteParserConfig(
                site_name="test",
                base_url="file:///path/to/file.html",
                content_selectors=['//div[@id="main"]'],
            )


class TestSiteParserConfig:
    """Test the SiteParserConfig model."""

    def test_default_values(self):
        """Test default values for SiteParserConfig."""
        config = SiteParserConfig(
            base_url=HttpUrl("https://example.com"),
            content_selectors=['//div[@id="main"]'],
        )
        assert str(config.base_url) == "https://example.com/"
        assert config.title_selector == "//title"
        assert config.fallback_to_body is True
        assert config.description is None
        assert isinstance(config.markdown_config, HtmlToMarkdownConfig)

    def test_get_content_selector(self):
        """Test the get_content_selector method."""
        from lxml import html as lxml_html

        # Create a test config
        config = SiteParserConfig(
            site_name="test",
            base_url="https://example.com",
            content_selectors=['//div[@id="main"]', '//div[@class="content"]', "//article"],
        )

        # Create a test HTML tree
        html_content = """
        <html>
            <body>
                <div class="content">Content here</div>
                <article>Article content</article>
            </body>
        </html>
        """
        tree = lxml_html.fromstring(html_content)

        # Test first selector not found, second matches
        element = config.get_content_selector(tree)
        assert element is not None
        assert element.text == "Content here"

        # Test when first selector matches
        html_content = """
        <html>
            <body>
                <div id="main">Main content</div>
                <div class="content">Secondary content</div>
            </body>
        </html>
        """
        tree = lxml_html.fromstring(html_content)
        element = config.get_content_selector(tree)
        assert element is not None
        assert element.text == "Main content"

        # Test when no selectors match
        html_content = """
        <html>
            <body>
                <div class="other">Other content</div>
            </body>
        </html>
        """
        tree = lxml_html.fromstring(html_content)
        element = config.get_content_selector(tree)
        assert element is None


class TestHtmlToMarkdownConfig:
    """Test the HtmlToMarkdownConfig model."""

    def test_default_values(self):
        """Test default values."""
        config = HtmlToMarkdownConfig()
        assert config.ignore_links is False
        assert config.body_width == 0
        assert config.protect_links is True
        assert config.unicode_snob is True
        assert config.ignore_images is False
        assert config.ignore_tables is False

    def test_custom_values(self):
        """Test custom values."""
        config = HtmlToMarkdownConfig(
            ignore_links=True,
            body_width=80,
            protect_links=False,
            unicode_snob=False,
        )
        assert config.ignore_links is True
        assert config.body_width == 80
        assert config.protect_links is False
        assert config.unicode_snob is False


class TestParserConfigRegistry:
    """Test the ParserConfigRegistry model."""

    def test_model_validation(self):
        """Test model validation."""
        # Valid config with all required fields
        config_data = {
            "sites": {
                "test": {
                    "base_url": "https://example.com",
                    "content_selectors": ["//div"],
                },
            },
        }
        registry = ParserConfigRegistry.model_validate(config_data)
        assert "test" in registry.sites
        assert str(registry.sites["test"].base_url) == "https://example.com/"

        # Invalid config (missing required fields)
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ParserConfigRegistry.model_validate(
                {
                    "sites": {
                        "test": {"site_name": "test"},
                    },
                },
            )
