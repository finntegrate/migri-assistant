"""Tests for the UniversalParser class."""

import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock

import pytest
import yaml

from migri_assistant.parsers.config_models import (
    HtmlToMarkdownConfig,
    ParserConfigRegistry,
    SiteParserConfig,
)
from migri_assistant.parsers.universal_parser import UniversalParser


class TestUniversalParser(unittest.TestCase):
    """Test the Universal Parser functionality."""

    def setUp(self):
        """Set up test environment."""
        # Create temporary directories for testing
        self.temp_dir = tempfile.mkdtemp()
        self.input_dir = os.path.join(self.temp_dir, "input")
        self.output_dir = os.path.join(self.temp_dir, "output")
        self.config_dir = os.path.join(self.temp_dir, "config")

        # Create directories
        os.makedirs(self.input_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.config_dir, exist_ok=True)

        # Create test domain directories
        self.domain = "example.com"
        self.domain_dir = os.path.join(self.input_dir, self.domain)
        os.makedirs(self.domain_dir, exist_ok=True)

        # Create test HTML files
        with open(os.path.join(self.domain_dir, "index.html"), "w") as f:
            f.write("""
            <html>
                <head><title>Example Website</title></head>
                <body>
                    <div id="main-content">
                        <h1>Example Website</h1>
                        <p>Welcome to the example website.</p>
                        <ul>
                            <li><a href="/page1">Page 1</a></li>
                            <li><a href="/page2">Page 2</a></li>
                        </ul>
                    </div>
                </body>
            </html>
            """)

        with open(os.path.join(self.domain_dir, "about.html"), "w") as f:
            f.write("""
            <html>
                <head><title>About Example</title></head>
                <body>
                    <div class="content">
                        <h1>About Example</h1>
                        <p>This is the about page for the example website.</p>
                    </div>
                </body>
            </html>
            """)

        # Create HTML file without main-content div to test fallback selectors
        with open(os.path.join(self.domain_dir, "no-main-content.html"), "w") as f:
            f.write("""
            <html>
                <head><title>No Main Content</title></head>
                <body>
                    <main>
                        <h1>Page Without Main Content Div</h1>
                        <p>This page doesn't have a main-content div.</p>
                    </main>
                </body>
            </html>
            """)

        # Create custom test configuration
        self.test_config = {
            "sites": {
                "example": {
                    "site_name": "example",
                    "base_url": f"https://{self.domain}",
                    "base_dir": self.domain,
                    "title_selector": "//title",
                    "content_selectors": [
                        '//div[@id="main-content"]',
                        '//div[@class="content"]',
                        "//main",
                    ],
                    "fallback_to_body": True,
                    "description": "Example Website for Testing",
                    "markdown_config": {"ignore_links": False, "body_width": 0},
                },
                "no_fallback": {
                    "site_name": "no_fallback",
                    "base_url": f"https://{self.domain}",
                    "base_dir": self.domain,
                    "title_selector": "//h1",
                    "content_selectors": ['//div[@id="does-not-exist"]'],
                    "fallback_to_body": False,
                },
            },
        }

        # Save test configuration
        self.config_path = os.path.join(self.config_dir, "test_config.yaml")
        with open(self.config_path, "w") as f:
            yaml.dump(self.test_config, f)

        # Create default parser
        self.parser = UniversalParser(
            site_type="example",
            input_dir=self.input_dir,
            output_dir=self.output_dir,
            config_path=self.config_path,
        )

        # Mock the logger
        self.parser.logger = MagicMock()

    def tearDown(self):
        """Clean up after tests."""
        shutil.rmtree(self.temp_dir)

    def test_init(self):
        """Test parser initialization."""
        self.assertEqual(self.parser.site_type, "example")
        self.assertEqual(self.parser.input_dir, self.input_dir)
        self.assertEqual(self.parser.output_dir, os.path.join(self.output_dir, "example"))
        self.assertEqual(self.parser.site_name, "example")

        # Test config loaded correctly
        self.assertEqual(self.parser.config.site_name, "example")
        self.assertEqual(self.parser.config.title_selector, "//title")
        self.assertEqual(len(self.parser.config.content_selectors), 3)
        self.assertTrue(self.parser.config.fallback_to_body)
        self.assertEqual(self.parser.config.description, "Example Website for Testing")

    def test_init_with_invalid_site_type(self):
        """Test initialization with invalid site type."""
        with self.assertRaises(ValueError):
            UniversalParser(
                site_type="nonexistent",
                input_dir=self.input_dir,
                output_dir=self.output_dir,
                config_path=self.config_path,
            )

    def test_parse_html_with_main_content(self):
        """Test parsing HTML with main-content div."""
        with open(os.path.join(self.domain_dir, "index.html")) as f:
            html_content = f.read()

        title, content = self.parser._parse_html(html_content)

        self.assertEqual(title, "Example Website")
        self.assertIn("# Example Website", content)
        self.assertIn("Welcome to the example website", content)
        self.assertIn("Page 1", content)
        self.assertIn("Page 2", content)

    def test_parse_html_with_secondary_selector(self):
        """Test parsing HTML with secondary content selector."""
        with open(os.path.join(self.domain_dir, "about.html")) as f:
            html_content = f.read()

        title, content = self.parser._parse_html(html_content)

        self.assertEqual(title, "About Example")
        self.assertIn("# About Example", content)
        self.assertIn("This is the about page", content)

    def test_parse_html_with_fallback(self):
        """Test fallback selector when primary selectors don't match."""
        with open(os.path.join(self.domain_dir, "no-main-content.html")) as f:
            html_content = f.read()

        title, content = self.parser._parse_html(html_content)

        self.assertEqual(title, "No Main Content")
        self.assertIn("Page Without Main Content Div", content)
        self.assertIn("This page doesn't have a main-content div", content)

    def test_parse_html_without_fallback(self):
        """Test behavior when no selectors match and fallback is disabled."""
        # Create parser with no fallback config
        no_fallback_parser = UniversalParser(
            site_type="no_fallback",
            input_dir=self.input_dir,
            output_dir=self.output_dir,
            config_path=self.config_path,
        )
        no_fallback_parser.logger = MagicMock()

        with open(os.path.join(self.domain_dir, "index.html")) as f:
            html_content = f.read()

        title, content = no_fallback_parser._parse_html(html_content)

        # It should use the h1 selector for the title and return empty content
        self.assertEqual(title, "Example Website")
        self.assertEqual(content.strip(), "")
        no_fallback_parser.logger.warning.assert_called_with(
            "No content found and no fallback configured",
        )

    def test_html_to_markdown(self):
        """Test HTML to Markdown conversion with configs."""
        html = """
        <div>
            <h1>Test Header</h1>
            <p>This is a <strong>test</strong> paragraph with a <a href="https://example.com">link</a>.</p>
            <ul>
                <li>Item 1</li>
                <li>Item 2</li>
            </ul>
        </div>
        """

        markdown = self.parser._html_to_markdown(html)

        # Check for Markdown elements
        self.assertIn("# Test Header", markdown)
        self.assertIn("**test**", markdown)
        self.assertIn("[link]", markdown)
        self.assertIn("* Item 1", markdown)
        self.assertIn("* Item 2", markdown)

    def test_parse_all(self):
        """Test parsing all HTML files."""
        # Parse all files
        results = self.parser.parse_all(domain=self.domain)

        # Check that we parsed 3 files
        self.assertEqual(len(results), 3)

        # Verify output directory structure
        output_dir = os.path.join(self.output_dir, "example")
        self.assertTrue(os.path.exists(output_dir))

        # Verify the index file was created
        index_file = os.path.join(output_dir, "index.md")
        self.assertTrue(os.path.exists(index_file))

        # Validate the content of parsed files
        titles = [result["title"] for result in results]
        self.assertIn("Example Website", titles)
        self.assertIn("About Example", titles)
        self.assertIn("No Main Content", titles)

    def test_list_available_site_configs(self):
        """Test listing available site configurations."""
        available_sites = UniversalParser.list_available_site_configs(self.config_path)
        self.assertEqual(len(available_sites), 2)
        self.assertIn("example", available_sites)
        self.assertIn("no_fallback", available_sites)

    def test_get_site_config(self):
        """Test getting site configuration."""
        config = UniversalParser.get_site_config("example", self.config_path)
        self.assertEqual(config.site_name, "example")
        self.assertEqual(config.description, "Example Website for Testing")

        # Test getting non-existent site config
        config = UniversalParser.get_site_config("nonexistent", self.config_path)
        self.assertIsNone(config)


class TestSiteParserConfig:
    """Test the SiteParserConfig model."""

    def test_get_content_selector(self):
        """Test the get_content_selector method."""
        from lxml import html as lxml_html

        # Create a test config
        config = SiteParserConfig(
            site_name="test",
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


class TestParserConfigRegistry:
    """Test the ParserConfigRegistry model."""

    def test_model_validation(self):
        """Test model validation."""
        # Valid config
        config_data = {"sites": {"test": {"site_name": "test", "content_selectors": ["//div"]}}}
        registry = ParserConfigRegistry.model_validate(config_data)
        assert "test" in registry.sites
        assert registry.sites["test"].site_name == "test"

        # Invalid config (missing required fields)
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ParserConfigRegistry.model_validate({"sites": {"test": {"site_name": "test"}}})


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
