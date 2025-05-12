"""Tests for the markdown utilities."""

import os
import tempfile
from unittest.mock import mock_open, patch

from migri_assistant.config.settings import DEFAULT_DIRS
from migri_assistant.utils.markdown_utils import find_markdown_files, read_markdown_file


class TestMarkdownUtils:
    """Tests for the markdown utilities."""

    def test_read_markdown_file_with_source_url(self):
        """Test reading a markdown file with source_url in metadata."""
        mock_file_content = """---
title: Test Document
source_url: https://example.com/page.html
---
# Test Content

This is test content.
"""
        with patch("builtins.open", mock_open(read_data=mock_file_content)):
            metadata, content = read_markdown_file("test_file.md")

        assert metadata["title"] == "Test Document"
        assert metadata["source_url"] == "https://example.com/page.html"
        assert metadata["url"] == "https://example.com/page.html"
        assert content == "# Test Content\n\nThis is test content."  # No trailing newline

    def test_read_markdown_file_with_source_file(self):
        """Test reading a markdown file with source_file in metadata."""
        mock_file_content = f"""---
title: Test Document
source_file: {DEFAULT_DIRS["CRAWLED_DIR"]}/example.com/page.html
---
# Test Content

This is test content.
"""
        with patch("builtins.open", mock_open(read_data=mock_file_content)):
            metadata, content = read_markdown_file("test_file.md")

        assert metadata["title"] == "Test Document"
        assert metadata["source_file"] == f"{DEFAULT_DIRS['CRAWLED_DIR']}/example.com/page.html"
        assert metadata["url"] == "example.com/page.html"
        assert content == "# Test Content\n\nThis is test content."  # No trailing newline

    def test_read_markdown_file_error(self):
        """Test error handling when reading a markdown file."""
        with patch("builtins.open", side_effect=FileNotFoundError("File not found")):
            metadata, content = read_markdown_file("non_existent.md")

        assert metadata == {}
        assert content == ""

    def test_find_markdown_files_no_filter(self):
        """Test finding markdown files without domain filter."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create some test files
            os.makedirs(os.path.join(temp_dir, "subdir"), exist_ok=True)
            open(os.path.join(temp_dir, "file1.md"), "w").close()
            open(os.path.join(temp_dir, "file2.txt"), "w").close()
            open(os.path.join(temp_dir, "subdir", "file3.md"), "w").close()

            # Find markdown files
            markdown_files = find_markdown_files(temp_dir)

            # Check that the correct files were found
            assert len(markdown_files) == 2
            assert any(f.endswith("file1.md") for f in markdown_files)
            assert any(f.endswith(os.path.join("subdir", "file3.md")) for f in markdown_files)
            assert not any(f.endswith("file2.txt") for f in markdown_files)

    def test_find_markdown_files_with_domain_filter(self):
        """Test finding markdown files with domain filter."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test file with metadata that matches the domain filter
            file1_path = os.path.join(temp_dir, "file1.md")
            with open(file1_path, "w") as f:
                f.write("""---
domain: migri.fi
title: Test Document
---
# Test Content
""")

            # Create a test file with metadata that doesn't match the domain filter
            file2_path = os.path.join(temp_dir, "file2.md")
            with open(file2_path, "w") as f:
                f.write("""---
domain: other.com
title: Other Document
---
# Other Content
""")

            # Find markdown files with domain filter
            markdown_files = find_markdown_files(temp_dir, domain_filter="migri.fi")

            # Check that only the file with the matching domain was found
            assert len(markdown_files) == 1
            assert any(f.endswith("file1.md") for f in markdown_files)
            assert not any(f.endswith("file2.md") for f in markdown_files)

    def test_find_markdown_files_with_unparseable_file(self):
        """Test finding markdown files with one that can't be parsed."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a valid file
            file1_path = os.path.join(temp_dir, "file1.md")
            with open(file1_path, "w") as f:
                f.write("""---
domain: migri.fi
title: Test Document
---
# Test Content
""")

            # Create an invalid file (invalid YAML frontmatter)
            file2_path = os.path.join(temp_dir, "file2.md")
            with open(file2_path, "w") as f:
                f.write("""---
domain: migri.fi
title: - [Invalid YAML
---
# Invalid Content
""")

            # Find markdown files with domain filter
            markdown_files = find_markdown_files(temp_dir, domain_filter="migri.fi")

            # Check that only the valid file was found
            assert len(markdown_files) == 1
            assert any(f.endswith("file1.md") for f in markdown_files)

    def test_find_markdown_files_error(self):
        """Test error handling when finding markdown files."""
        with patch("os.walk", side_effect=PermissionError("Permission denied")):
            markdown_files = find_markdown_files("non_existent_dir")

        assert markdown_files == []
