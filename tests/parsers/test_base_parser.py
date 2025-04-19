import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from migri_assistant.parsers.base_parser import BaseParser


class MockParser(BaseParser):
    """Mock implementation of BaseParser for testing purposes"""

    def _parse_html(self, html_content):
        """Simple implementation for testing"""
        # Extract a simple title from h1 if available, otherwise use "Untitled"
        import re

        title_match = re.search(r"<h1>(.*?)</h1>", html_content)
        title = title_match.group(1) if title_match else "Untitled"

        # Return title and content without HTML tags
        content = re.sub(r"<[^>]*>", "", html_content).strip()
        return title, content


class TestBaseParser(unittest.TestCase):
    """Test the BaseParser abstract base class functionality"""

    def setUp(self):
        # Create temporary directories for testing
        self.temp_dir = tempfile.mkdtemp()
        self.input_dir = os.path.join(self.temp_dir, "input")
        self.output_dir = os.path.join(self.temp_dir, "output")
        os.makedirs(self.input_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

        # Create test HTML files
        self.domain1 = "example.com"
        self.domain2 = "test.com"

        # Create domain directories
        os.makedirs(os.path.join(self.input_dir, self.domain1), exist_ok=True)
        os.makedirs(os.path.join(self.input_dir, self.domain2), exist_ok=True)

        # Create test HTML files in domain1
        with open(os.path.join(self.input_dir, self.domain1, "index.html"), "w") as f:
            f.write(
                "<html><body><h1>Example Home</h1><p>This is the home page.</p></body></html>",
            )

        with open(os.path.join(self.input_dir, self.domain1, "about.html"), "w") as f:
            f.write(
                "<html><body><h1>About Us</h1><p>This is the about page.</p></body></html>",
            )

        # Create test HTML file in domain2
        with open(os.path.join(self.input_dir, self.domain2, "index.html"), "w") as f:
            f.write(
                "<html><body><h1>Test Home</h1><p>This is a test page.</p></body></html>",
            )

        # Create our test parser instance
        self.parser = MockParser(
            input_dir=self.input_dir,
            output_dir=self.output_dir,
            site_name="test_site",
        )

        # Mock the logger to avoid console output during tests
        self.parser.logger = MagicMock()

    def tearDown(self):
        # Clean up temporary directories
        shutil.rmtree(self.temp_dir)

    def test_init(self):
        """Test parser initialization"""
        self.assertEqual(self.parser.input_dir, self.input_dir)
        self.assertEqual(
            self.parser.output_dir,
            os.path.join(self.output_dir, "test_site"),
        )
        self.assertEqual(self.parser.site_name, "test_site")

    def test_parse_file(self):
        """Test parsing a single HTML file"""
        # Parse the example.com index.html file
        result = self.parser.parse_file(
            os.path.join(self.input_dir, self.domain1, "index.html"),
        )

        # Check the result
        self.assertEqual(result["title"], "Example Home")
        self.assertEqual(result["domain"], self.domain1)
        self.assertTrue("output_file" in result)
        self.assertTrue("source_file" in result)

        # Verify the output file exists and contains the correct content
        output_file = result["output_file"]
        self.assertTrue(os.path.exists(output_file))

        with open(output_file) as f:
            content = f.read()
            self.assertIn("Example Home", content)
            self.assertIn("This is the home page.", content)

    def test_parse_all(self):
        """Test parsing all HTML files"""
        # Parse all files
        results = self.parser.parse_all()

        # Check that we parsed 3 files
        self.assertEqual(len(results), 3)

        # Verify output directory structure
        output_dir = os.path.join(self.output_dir, "test_site")
        self.assertTrue(os.path.exists(output_dir))

        # Verify the index file was created
        index_file = os.path.join(output_dir, "index.md")
        self.assertTrue(os.path.exists(index_file))

        # Check index file content
        with open(index_file) as f:
            content = f.read()
            self.assertIn("Total pages parsed: 3", content)

    def test_parse_all_with_domain_filter(self):
        """Test parsing HTML files with domain filter"""
        # Parse only domain1 files
        results = self.parser.parse_all(domain=self.domain1)

        # Check that we parsed 2 files (domain1 has 2 files)
        self.assertEqual(len(results), 2)

        # Verify the titles match what we expect
        titles = [result["title"] for result in results]
        self.assertIn("Example Home", titles)
        self.assertIn("About Us", titles)

        # Test nonexistent domain
        results = self.parser.parse_all(domain="nonexistent.com")
        self.assertEqual(len(results), 0)

    def test_get_output_filename(self):
        """Test generating output filenames"""
        # Test file inside the input directory
        file_path = Path(os.path.join(self.input_dir, self.domain1, "test.html"))
        filename = self.parser._get_output_filename(file_path)
        self.assertEqual(filename, "test")

        # Test file with subdirectories
        file_path = Path(
            os.path.join(self.input_dir, self.domain1, "subdir", "page.html"),
        )
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w") as f:
            f.write("<html><body><h1>Subdir Page</h1></body></html>")

        filename = self.parser._get_output_filename(file_path)
        self.assertEqual(filename, "subdir_page")

        # Test file outside the input directory
        outside_file = os.path.join(self.temp_dir, "outside.html")
        with open(outside_file, "w") as f:
            f.write("<html><body><h1>Outside</h1></body></html>")

        filename = self.parser._get_output_filename(Path(outside_file))
        self.assertEqual(filename, "outside")
