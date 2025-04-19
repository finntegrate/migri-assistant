import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock

from migri_assistant.parsers.migri_parser import MigriParser


class TestMigriParser(unittest.TestCase):
    """Test the Migri-specific parser functionality"""

    def setUp(self):
        # Create temporary directories for testing
        self.temp_dir = tempfile.mkdtemp()
        self.input_dir = os.path.join(self.temp_dir, "input")
        self.output_dir = os.path.join(self.temp_dir, "output")
        os.makedirs(self.input_dir, exist_ok=True)

        # Create test domain directory for migri.fi
        self.domain = "migri.fi"
        self.domain_dir = os.path.join(self.input_dir, self.domain)
        os.makedirs(self.domain_dir, exist_ok=True)

        # Create test HTML files with Migri.fi specific structure
        with open(os.path.join(self.domain_dir, "index.html"), "w") as f:
            f.write("""
            <html>
                <head><title>Finnish Immigration Service</title></head>
                <body>
                    <div id="main-content">
                        <h1>Finnish Immigration Service</h1>
                        <p>Welcome to the Migri website.</p>
                        <ul>
                            <li><a href="/residence-permits">Residence permits</a></li>
                            <li><a href="/citizenship">Citizenship</a></li>
                        </ul>
                    </div>
                </body>
            </html>
            """)

        with open(os.path.join(self.domain_dir, "about.html"), "w") as f:
            f.write("""
            <html>
                <head><title>About Migri</title></head>
                <body>
                    <div id="main-content">
                        <h1>About Finnish Immigration Service</h1>
                        <p>The Finnish Immigration Service is a decision-making organisation in matters
                        related to immigration, asylum, refugee status and citizenship.</p>
                    </div>
                </body>
            </html>
            """)  # noqa: E501

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

        # Create our parser instance
        self.parser = MigriParser(input_dir=self.input_dir, output_dir=self.output_dir)

        # Mock the logger to avoid console output during tests
        self.parser.logger = MagicMock()

    def tearDown(self):
        # Clean up temporary directories
        shutil.rmtree(self.temp_dir)

    def test_init(self):
        """Test MigriParser initialization"""
        self.assertEqual(self.parser.input_dir, self.input_dir)
        self.assertEqual(self.parser.output_dir, os.path.join(self.output_dir, "migri"))
        self.assertEqual(self.parser.site_name, "migri")

    def test_parse_html(self):
        """Test parsing HTML content specific to Migri.fi"""
        # Read test HTML file
        with open(os.path.join(self.domain_dir, "index.html")) as f:
            html_content = f.read()

        # Parse the HTML
        title, content = self.parser._parse_html(html_content)

        # Check results
        self.assertEqual(title, "Finnish Immigration Service")
        self.assertIn("Welcome to the Migri website", content)
        self.assertIn("Residence permits", content)
        self.assertIn("Citizenship", content)

    def test_parse_html_fallback(self):
        """Test fallback selectors when main-content is not found"""
        # Read test HTML file that doesn't have main-content div
        with open(os.path.join(self.domain_dir, "no-main-content.html")) as f:
            html_content = f.read()

        # Parse the HTML
        title, content = self.parser._parse_html(html_content)

        # Check results
        self.assertEqual(title, "No Main Content")
        self.assertIn("Page Without Main Content Div", content)
        self.assertIn("This page doesn't have a main-content div", content)

    def test_html_to_markdown(self):
        """Test HTML to Markdown conversion"""
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
        # html2text wraps the URL in angle brackets, so update our expectation
        self.assertIn("[link](<https://example.com>)", markdown)
        self.assertIn("* Item 1", markdown)
        self.assertIn("* Item 2", markdown)

    def test_parse_all(self):
        """Test parsing all Migri HTML files"""
        # Parse all files
        results = self.parser.parse_all(domain=self.domain)

        # Check that we parsed 3 files
        self.assertEqual(len(results), 3)

        # Verify output directory structure
        output_dir = os.path.join(self.output_dir, "migri")
        self.assertTrue(os.path.exists(output_dir))

        # Verify the index file was created
        index_file = os.path.join(output_dir, "index.md")
        self.assertTrue(os.path.exists(index_file))

        # Validate the content of parsed files
        for result in results:
            output_file = result["output_file"]
            with open(output_file) as f:
                content = f.read()
                # Check that the file contains markup elements
                self.assertIn("# ", content)  # Heading
                self.assertIn("---", content)  # Frontmatter
