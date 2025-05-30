"""Tests for the Parser class."""

import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock

import yaml

from tapio.parser import Parser


class TestParser(unittest.TestCase):
    """Test the Parser functionality."""

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
                    "base_url": f"https://{self.domain}",
                    "base_dir": self.domain,
                    "description": "Example Website for Testing",
                    "parser_config": {
                        "title_selector": "//title",
                        "content_selectors": [
                            '//div[@id="main-content"]',
                            '//div[@class="content"]',
                            "//main",
                        ],
                        "fallback_to_body": True,
                        "markdown_config": {"ignore_links": False, "body_width": 0},
                    },
                },
                "no_fallback": {
                    "base_url": f"https://{self.domain}",
                    "base_dir": self.domain,
                    "parser_config": {
                        "title_selector": "//h1",
                        "content_selectors": ['//div[@id="does-not-exist"]'],
                        "fallback_to_body": False,
                    },
                },
            },
        }

        # Save test configuration
        self.config_path = os.path.join(self.config_dir, "test_config.yaml")
        with open(self.config_path, "w") as f:
            yaml.dump(self.test_config, f)

        # Create default parser
        self.parser = Parser(
            site_name="example",
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
        self.assertEqual(self.parser.site, "example")
        self.assertEqual(self.parser.input_dir, self.input_dir)
        self.assertEqual(self.parser.output_dir, os.path.join(self.output_dir, "example"))

        # Test config loaded correctly
        self.assertEqual(self.parser.config.parser_config.title_selector, "//title")
        self.assertEqual(len(self.parser.config.parser_config.content_selectors), 3)
        self.assertTrue(self.parser.config.parser_config.fallback_to_body)
        self.assertEqual(self.parser.config.description, "Example Website for Testing")

    def test_init_with_invalid_site(self):
        """Test initialization with invalid site."""
        with self.assertRaises(ValueError):
            Parser(
                site_name="nonexistent",
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
        no_fallback_parser = Parser(
            site_name="no_fallback",
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
        results = self.parser.parse_all()

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
        available_sites = Parser.list_available_site_configs(self.config_path)
        self.assertEqual(len(available_sites), 2)
        self.assertIn("example", available_sites)
        self.assertIn("no_fallback", available_sites)

    def test_get_site_config(self):
        """Test getting site configuration."""
        config = Parser.get_site_config("example", self.config_path)
        self.assertIsNotNone(config)
        if config:  # Check if config is not None before accessing attributes
            self.assertEqual(config.description, "Example Website for Testing")

        # Test getting non-existent site config
        config = Parser.get_site_config("nonexistent", self.config_path)
        self.assertIsNone(config)

    def test_convert_element_link_to_absolute(self):
        """Test converting a single element's link attribute to absolute URL."""
        from lxml import html as lxml_html

        # Setup test cases
        base_url = "https://example.com/path/"
        absolute_prefixes = ("http://", "https://", "//", "mailto:", "#")

        # Case 1: Relative link that should be converted
        element1 = lxml_html.fromstring('<a href="page.html">Link</a>')
        result1 = Parser._convert_element_link_to_absolute(
            element1,
            "href",
            base_url,
            absolute_prefixes,
        )
        self.assertTrue(result1)
        self.assertEqual(element1.get("href"), "https://example.com/path/page.html")

        # Case 2: Relative link with leading slash
        element2 = lxml_html.fromstring('<a href="/another-page.html">Link</a>')
        result2 = Parser._convert_element_link_to_absolute(
            element2,
            "href",
            base_url,
            absolute_prefixes,
        )
        self.assertTrue(result2)
        self.assertEqual(element2.get("href"), "https://example.com/another-page.html")

        # Case 3: Absolute link that should not be converted (http://)
        element3 = lxml_html.fromstring('<a href="http://other-domain.com/page">Link</a>')
        result3 = Parser._convert_element_link_to_absolute(
            element3,
            "href",
            base_url,
            absolute_prefixes,
        )
        self.assertFalse(result3)
        self.assertEqual(element3.get("href"), "http://other-domain.com/page")

        # Case 4: Protocol-relative URL that should not be converted (//)
        element4 = lxml_html.fromstring('<a href="//cdn.example.com/script.js">Link</a>')
        result4 = Parser._convert_element_link_to_absolute(
            element4,
            "href",
            base_url,
            absolute_prefixes,
        )
        self.assertFalse(result4)
        self.assertEqual(element4.get("href"), "//cdn.example.com/script.js")

        # Case 5: Empty link
        element5 = lxml_html.fromstring('<a href="">Link</a>')
        result5 = Parser._convert_element_link_to_absolute(
            element5,
            "href",
            base_url,
            absolute_prefixes,
        )
        self.assertFalse(result5)  # Empty links are not considered for conversion
        self.assertEqual(element5.get("href"), "")

        # Case 6: Missing attribute
        element6 = lxml_html.fromstring("<a>Link</a>")
        result6 = Parser._convert_element_link_to_absolute(
            element6,
            "href",
            base_url,
            absolute_prefixes,
        )
        self.assertFalse(result6)
        self.assertIsNone(element6.get("href"))

    def test_convert_relative_links_to_absolute(self):
        """Test converting all relative links in HTML content to absolute URLs."""
        # Create HTML with various link types
        html_content = """
        <html>
            <body>
                <a href="relative.html">Relative Link</a>
                <a href="/root-relative.html">Root Relative Link</a>
                <a href="http://example.org/absolute">Absolute Link</a>
                <a href="https://example.org/secure">Secure Link</a>
                <a href="//cdn.example.org/script.js">Protocol Relative Link</a>
                <a href="mailto:test@example.com">Email Link</a>
                <a href="#section">Anchor Link</a>
                <img src="image.jpg">
                <img src="/images/logo.png">
                <img src="http://example.org/image.jpg">
                <img src="https://example.org/secure.jpg">
                <img src="//cdn.example.org/image.jpg">
                <img src="data:image/png;base64,abc123">
            </body>
        </html>
        """

        # Set the base URL
        self.parser.current_base_url = "https://test.com/subdir/"

        # Convert links
        result = self.parser._convert_relative_links_to_absolute(html_content)

        # Check that the conversion was successful
        self.assertIn('href="https://test.com/subdir/relative.html"', result)
        self.assertIn('href="https://test.com/root-relative.html"', result)
        self.assertIn('href="http://example.org/absolute"', result)  # Unchanged
        self.assertIn('href="https://example.org/secure"', result)  # Unchanged
        self.assertIn('href="//cdn.example.org/script.js"', result)  # Unchanged
        self.assertIn('href="mailto:test@example.com"', result)  # Unchanged
        self.assertIn('href="#section"', result)  # Unchanged
        self.assertIn('src="https://test.com/subdir/image.jpg"', result)
        self.assertIn('src="https://test.com/images/logo.png"', result)
        self.assertIn('src="http://example.org/image.jpg"', result)  # Unchanged
        self.assertIn('src="https://example.org/secure.jpg"', result)  # Unchanged
        self.assertIn('src="//cdn.example.org/image.jpg"', result)  # Unchanged
        self.assertIn('src="data:image/png;base64,abc123"', result)  # Unchanged

    def test_convert_relative_links_no_base_url(self):
        """Test that conversion is skipped when no base URL is available."""
        html_content = '<a href="page.html">Link</a>'
        self.parser.current_base_url = None
        result = self.parser._convert_relative_links_to_absolute(html_content)
        self.assertEqual(result, html_content)  # Should be unchanged
