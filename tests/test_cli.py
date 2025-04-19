"""Tests for the CLI module."""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from migri_assistant.cli import app


@pytest.fixture
def runner():
    """Fixture for creating a CLI runner."""
    return CliRunner()


class TestCli:
    """Tests for the CLI module."""

    def test_info_command(self, runner):
        """Test the info command."""
        result = runner.invoke(app, ["info"])

        # Check that the command ran successfully
        assert result.exit_code == 0

        # Check that expected text is in the output
        assert "Migri Assistant" in result.stdout
        assert "Available commands:" in result.stdout
        assert "crawl" in result.stdout
        assert "parse" in result.stdout
        assert "vectorize" in result.stdout
        assert "info" in result.stdout

    @patch("migri_assistant.cli.ScrapyRunner")
    def test_crawl_command(self, mock_scrapy_runner, runner):
        """Test the crawl command."""
        # Set up mock
        mock_runner_instance = MagicMock()
        mock_runner_instance.run.return_value = ["page1", "page2", "page3"]
        mock_scrapy_runner.return_value = mock_runner_instance

        # Run the command
        result = runner.invoke(
            app,
            [
                "crawl",
                "https://example.com",
                "--depth",
                "2",
                "--output-dir",
                "test_output",
            ],
        )

        # Check that the command ran successfully
        assert result.exit_code == 0

        # Check that the runner was initialized correctly
        mock_scrapy_runner.assert_called_once()

        # Check that run was called with the correct arguments
        mock_runner_instance.run.assert_called_once_with(
            start_urls=["https://example.com"],
            depth=2,
            allowed_domains=["example.com"],
            output_dir="test_output",
        )

        # Check expected output in stdout
        assert "Starting web crawler" in result.stdout
        assert "Crawling completed" in result.stdout
        assert "Processed 3 pages" in result.stdout

    @patch("migri_assistant.cli.ScrapyRunner")
    def test_crawl_command_keyboard_interrupt(self, mock_scrapy_runner, runner):
        """Test handling of keyboard interrupt in crawl command."""
        # Set up mock to raise KeyboardInterrupt
        mock_runner_instance = MagicMock()
        mock_runner_instance.run.side_effect = KeyboardInterrupt()
        mock_scrapy_runner.return_value = mock_runner_instance

        # Run the command
        result = runner.invoke(app, ["crawl", "https://example.com"])

        # Check that the command exited successfully (handled the interrupt)
        assert result.exit_code == 0

        # Check expected output in stdout
        assert "Starting web crawler" in result.stdout
        assert "Crawling interrupted by user" in result.stdout
        assert "Partial results have been saved" in result.stdout

    @patch("migri_assistant.cli.ScrapyRunner")
    def test_crawl_command_exception(self, mock_scrapy_runner, runner):
        """Test handling of exceptions in crawl command."""
        # Set up mock to raise an exception
        mock_runner_instance = MagicMock()
        mock_runner_instance.run.side_effect = Exception("Test error")
        mock_scrapy_runner.return_value = mock_runner_instance

        # Run the command
        result = runner.invoke(app, ["crawl", "https://example.com"])

        # Check that the command exited with error code
        assert result.exit_code == 1

        # Check expected output in stdout
        assert "Starting web crawler" in result.stdout
        assert "Error during crawling: Test error" in result.stdout

    @patch("migri_assistant.cli.MigriParser")
    def test_parse_command(self, mock_migri_parser, runner):
        """Test the parse command."""
        # Set up mock
        mock_parser_instance = MagicMock()
        mock_parser_instance.parse_all.return_value = ["file1", "file2", "file3"]
        mock_migri_parser.return_value = mock_parser_instance

        # Run the command
        result = runner.invoke(
            app,
            ["parse", "--input-dir", "test_input", "--output-dir", "test_output"],
        )

        # Check that the command ran successfully
        assert result.exit_code == 0

        # Check that the parser was initialized correctly
        mock_migri_parser.assert_called_once_with(
            input_dir="test_input",
            output_dir="test_output",
        )

        # Check that parse_all was called correctly
        mock_parser_instance.parse_all.assert_called_once_with(domain=None)

        # Check expected output in stdout
        assert "Starting HTML parsing" in result.stdout
        assert "Using specialized Migri.fi parser" in result.stdout
        assert "Parsing completed" in result.stdout
        assert "Processed 3 files" in result.stdout

    @patch("migri_assistant.cli.MigriParser")
    def test_parse_command_with_domain(self, mock_migri_parser, runner):
        """Test the parse command with a domain filter."""
        # Set up mock
        mock_parser_instance = MagicMock()
        mock_parser_instance.parse_all.return_value = ["file1", "file2"]
        mock_migri_parser.return_value = mock_parser_instance

        # Run the command with domain filter
        result = runner.invoke(app, ["parse", "--domain", "example.com"])

        # Check that the command ran successfully
        assert result.exit_code == 0

        # Check that parse_all was called with the domain filter
        mock_parser_instance.parse_all.assert_called_once_with(domain="example.com")

        # Check expected output in stdout
        assert "Starting HTML parsing" in result.stdout
        assert "Processed 2 files" in result.stdout

    @patch("migri_assistant.cli.MigriParser")
    def test_parse_command_unsupported_site_type(self, mock_migri_parser, runner):
        """Test the parse command with an unsupported site type."""
        # Run the command with an unsupported site type
        result = runner.invoke(app, ["parse", "--site-type", "unsupported"])

        # Check that the command exited with error code
        assert result.exit_code == 1

        # Check expected output in stdout
        assert "Unsupported site type: unsupported" in result.stdout

    @patch("migri_assistant.cli.MigriParser")
    def test_parse_command_exception(self, mock_migri_parser, runner):
        """Test handling of exceptions in parse command."""
        # Set up mock to raise an exception
        mock_parser_instance = MagicMock()
        mock_parser_instance.parse_all.side_effect = Exception("Test error")
        mock_migri_parser.return_value = mock_parser_instance

        # Run the command
        result = runner.invoke(app, ["parse"])

        # Check that the command exited with error code
        assert result.exit_code == 1

        # Check expected output in stdout
        assert "Starting HTML parsing" in result.stdout
        assert "Error during parsing: Test error" in result.stdout

    @patch("migri_assistant.cli.MarkdownVectorizer")
    def test_vectorize_command(self, mock_vectorizer, runner):
        """Test the vectorize command."""
        # Set up mock
        mock_vectorizer_instance = MagicMock()
        mock_vectorizer_instance.process_directory.return_value = 5
        mock_vectorizer.return_value = mock_vectorizer_instance

        # Run the command
        result = runner.invoke(
            app,
            [
                "vectorize",
                "--input-dir",
                "test_input",
                "--db-dir",
                "test_db",
                "--collection",
                "test_collection",
            ],
        )

        # Check that the command ran successfully
        assert result.exit_code == 0

        # Check that the vectorizer was initialized correctly
        mock_vectorizer.assert_called_once_with(
            collection_name="test_collection",
            persist_directory="test_db",
            embedding_model_name="all-MiniLM-L6-v2",
            chunk_size=1000,
            chunk_overlap=200,
        )

        # Check that process_directory was called correctly
        mock_vectorizer_instance.process_directory.assert_called_once_with(
            input_dir="test_input",
            domain_filter=None,
            batch_size=20,
        )

        # Check expected output in stdout
        assert "Starting vectorization" in result.stdout
        assert "Vector database will be stored in: test_db" in result.stdout
        assert "Using embedding model: all-MiniLM-L6-v2" in result.stdout
        assert "Vectorization completed" in result.stdout
        assert "Processed 5 files" in result.stdout

    @patch("migri_assistant.cli.MarkdownVectorizer")
    def test_vectorize_command_with_domain(self, mock_vectorizer, runner):
        """Test the vectorize command with domain filter."""
        # Set up mock
        mock_vectorizer_instance = MagicMock()
        mock_vectorizer_instance.process_directory.return_value = 3
        mock_vectorizer.return_value = mock_vectorizer_instance

        # Run the command with domain filter
        result = runner.invoke(app, ["vectorize", "--domain", "example.com"])

        # Check that the command ran successfully
        assert result.exit_code == 0

        # Check that process_directory was called with the domain filter
        mock_vectorizer_instance.process_directory.assert_called_once_with(
            input_dir="parsed_content",
            domain_filter="example.com",
            batch_size=20,
        )

        # Check expected output in stdout
        assert "Starting vectorization" in result.stdout
        assert "Vectorization completed" in result.stdout
        assert "Processed 3 files" in result.stdout

    @patch("migri_assistant.cli.MarkdownVectorizer")
    def test_vectorize_command_exception(self, mock_vectorizer, runner):
        """Test handling of exceptions in vectorize command."""
        # Set up mock to raise an exception
        mock_vectorizer_instance = MagicMock()
        mock_vectorizer_instance.process_directory.side_effect = Exception("Test error")
        mock_vectorizer.return_value = mock_vectorizer_instance

        # Run the command
        result = runner.invoke(app, ["vectorize"])

        # Check that the command exited with error code
        assert result.exit_code == 1

        # Check expected output in stdout
        assert "Starting vectorization" in result.stdout
        assert "Error during vectorization: Test error" in result.stdout
