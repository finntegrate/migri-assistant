"""Tests for the CLI module."""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from tapio.cli import app
from tapio.config.settings import DEFAULT_DIRS


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
        assert "Tapio Assistant" in result.stdout
        assert "Available commands:" in result.stdout
        assert "crawl" in result.stdout
        assert "parse" in result.stdout
        assert "vectorize" in result.stdout
        assert "info" in result.stdout

    @patch("tapio.cli.ScrapyRunner")
    @patch("tapio.cli.Parser")
    def test_crawl_command(self, mock_parser, mock_scrapy_runner, runner):
        """Test the crawl command."""
        # Set up mocks
        mock_runner_instance = MagicMock()
        mock_runner_instance.run.return_value = ["page1", "page2", "page3"]
        mock_scrapy_runner.return_value = mock_runner_instance

        # Mock parser site config
        mock_site_config = MagicMock()
        mock_site_config.base_url = "https://example.com"
        mock_parser.get_site_config.return_value = mock_site_config
        mock_parser.list_available_site_configs.return_value = ["migri"]

        # Run the command
        result = runner.invoke(
            app,
            [
                "crawl",
                "migri",
                "--depth",
                "2",
                "--output-dir",
                "test_output",
            ],
        )

        # Check that the command ran successfully
        assert result.exit_code == 0

        # Check that list_available_site_configs was called
        mock_parser.list_available_site_configs.assert_called_once_with(None)

        # Check that get_site_config was called with the correct site name
        mock_parser.get_site_config.assert_called_once_with("migri", None)

        # Check that the runner was initialized correctly
        mock_scrapy_runner.assert_called_once()

        # Check that run was called with the correct arguments
        mock_runner_instance.run.assert_called_once_with(
            start_urls=["https://example.com"],  # URL from site config
            depth=2,
            allowed_domains=["example.com"],  # Domain extracted from URL
            output_dir="test_output",
        )

        # Check expected output in stdout
        assert "Starting web crawler" in result.stdout
        assert "Crawling completed" in result.stdout
        assert "Processed 3 pages" in result.stdout

    @patch("tapio.cli.ScrapyRunner")
    @patch("tapio.cli.Parser")
    def test_crawl_command_keyboard_interrupt(self, mock_parser, mock_scrapy_runner, runner):
        """Test handling of keyboard interrupt in crawl command."""
        # Set up mock site configuration
        mock_site_config = MagicMock()
        mock_site_config.base_url = "https://example.com"
        mock_parser.get_site_config.return_value = mock_site_config
        mock_parser.list_available_site_configs.return_value = ["migri"]

        # Set up mock to raise KeyboardInterrupt
        mock_runner_instance = MagicMock()
        mock_runner_instance.run.side_effect = KeyboardInterrupt()
        mock_scrapy_runner.return_value = mock_runner_instance

        # Run the command
        result = runner.invoke(app, ["crawl", "migri"])

        # Check that the command exited successfully (handled the interrupt)
        assert result.exit_code == 0

        # Check expected output in stdout
        assert "Starting web crawler for migri" in result.stdout
        assert "Crawling interrupted by user" in result.stdout
        assert "Partial results have been saved" in result.stdout

    @patch("tapio.cli.ScrapyRunner")
    @patch("tapio.cli.Parser")
    def test_crawl_command_exception(self, mock_parser, mock_scrapy_runner, runner):
        """Test handling of exceptions in crawl command."""
        # Set up mock site configuration
        mock_site_config = MagicMock()
        mock_site_config.base_url = "https://example.com"
        mock_parser.get_site_config.return_value = mock_site_config
        mock_parser.list_available_site_configs.return_value = ["migri"]

        # Set up mock to raise an exception
        mock_runner_instance = MagicMock()
        mock_runner_instance.run.side_effect = Exception("Test error")
        mock_scrapy_runner.return_value = mock_runner_instance

        # Run the command
        result = runner.invoke(app, ["crawl", "migri"])

        # Check that the command exited with error code
        assert result.exit_code == 1

        # Check expected output in stdout
        assert "Starting web crawler for migri" in result.stdout
        assert "Error during crawling: Test error" in result.stdout

    @patch("tapio.cli.Parser")
    def test_crawl_command_invalid_site(self, mock_parser, runner):
        """Test the crawl command with an invalid site name."""
        # Mock the list_available_site_configs method to return only valid sites
        mock_parser.list_available_site_configs.return_value = ["migri", "kela"]

        # Run the command with an unsupported site
        result = runner.invoke(app, ["crawl", "unsupported_site"])

        # Check that the command exited with error code
        assert result.exit_code == 1

        # Check expected output in stdout
        assert "Unsupported site: unsupported_site" in result.stdout
        assert "Available sites: migri, kela" in result.stdout

    @patch("tapio.cli.Parser")
    def test_parse_command(self, mock_parser, runner):
        """Test the parse command."""
        # Set up mock
        mock_parser_instance = MagicMock()
        mock_parser_instance.parse_all.return_value = ["file1", "file2", "file3"]
        mock_parser.return_value = mock_parser_instance
        # Mock the list_available_site_configs method
        mock_parser.list_available_site_configs.return_value = ["migri"]

        # Run the command
        result = runner.invoke(
            app,
            [
                "parse",
                "--input-dir",
                "test_input",
                "--output-dir",
                "test_output",
                "--site",
                "migri",
            ],
        )

        # Check that the command ran successfully
        assert result.exit_code == 0

        # Check that the parser was initialized correctly
        mock_parser.assert_called_once_with(
            site="migri",
            input_dir="test_input",
            output_dir="test_output",
            config_path=None,
        )

        # Check that list_available_site_configs was called with the correct parameter
        mock_parser.list_available_site_configs.assert_called_once_with(None)

        # Check that parse_all was called correctly (without domain parameter)
        mock_parser_instance.parse_all.assert_called_once_with()

        # Check expected output in stdout
        assert "Starting HTML parsing" in result.stdout
        assert "Using configuration for site: migri" in result.stdout
        assert "Parsing completed" in result.stdout
        assert "Processed 3 files" in result.stdout

    @patch("tapio.cli.Parser")
    def test_parse_command_with_domain(self, mock_parser, runner):
        """Test the parse command with a domain filter."""
        # Set up mock
        mock_parser_instance = MagicMock()
        mock_parser_instance.parse_all.return_value = ["file1", "file2"]
        mock_parser.return_value = mock_parser_instance
        mock_parser.list_available_site_configs.return_value = ["migri"]

        # Run the command with domain filter
        result = runner.invoke(app, ["parse", "--domain", "example.com", "--site", "migri"])

        # Check that the command ran successfully
        assert result.exit_code == 0

        # Check that parse_all was called correctly (domain is now handled internally)
        mock_parser_instance.parse_all.assert_called_once_with()

        # Check that list_available_site_configs was called with the correct parameter
        mock_parser.list_available_site_configs.assert_called_once_with(None)

        # Check expected output in stdout
        assert "Starting HTML parsing" in result.stdout
        assert "Processed 2 files" in result.stdout

    @patch("tapio.cli.Parser")
    def test_parse_command_unsupported_site(self, mock_parser, runner):
        """Test the parse command with an unsupported site."""
        # Mock the list_available_site_configs method to return only valid sites
        mock_parser.list_available_site_configs.return_value = ["migri", "kela"]
        # Run the command with an unsupported site
        result = runner.invoke(app, ["parse", "--site", "unsupported"])

        # Check that the command exited with error code
        assert result.exit_code == 1

        # Check expected output in stdout
        assert "Unsupported site: unsupported" in result.stdout

        # Check that list_available_site_configs was called with the correct parameter
        mock_parser.list_available_site_configs.assert_called_once_with(None)

    @patch("tapio.cli.Parser")
    def test_parse_command_exception(self, mock_parser, runner):
        """Test handling of exceptions in parse command."""
        # Set up mock to raise an exception
        mock_parser_instance = MagicMock()
        mock_parser_instance.parse_all.side_effect = Exception("Test error")
        mock_parser.return_value = mock_parser_instance
        mock_parser.list_available_site_configs.return_value = ["migri"]

        # Run the command
        result = runner.invoke(app, ["parse", "--site", "migri"])

        # Check that the command exited with error code
        assert result.exit_code == 1

        # Check expected output in stdout
        assert "Starting HTML parsing" in result.stdout
        assert "Error during parsing: Test error" in result.stdout

        # Check that list_available_site_configs was called with the correct parameter
        mock_parser.list_available_site_configs.assert_called_once_with(None)

    @patch("tapio.cli.Parser")
    def test_parse_command_custom_config(self, mock_parser, runner):
        """Test the parse command with a custom config path."""
        # Set up mock
        mock_parser_instance = MagicMock()
        mock_parser_instance.parse_all.return_value = ["file1", "file2"]
        mock_parser.return_value = mock_parser_instance
        # Mock the list_available_site_configs method
        mock_parser.list_available_site_configs.return_value = ["custom_site"]

        # Run the command with a custom config
        result = runner.invoke(
            app,
            [
                "parse",
                "--site",
                "custom_site",
                "--config",
                "custom_configs.yaml",
            ],
        )

        # Check that the command ran successfully
        assert result.exit_code == 0

        # Check that list_available_site_configs was called with the custom config path
        mock_parser.list_available_site_configs.assert_called_once_with(
            "custom_configs.yaml",
        )

        # Check that the parser was initialized correctly with the custom config
        mock_parser.assert_called_once_with(
            site="custom_site",
            input_dir=DEFAULT_DIRS["CRAWLED_DIR"],
            output_dir=DEFAULT_DIRS["PARSED_DIR"],
            config_path="custom_configs.yaml",
        )

        # Check that parse_all was called correctly (without domain parameter)
        mock_parser_instance.parse_all.assert_called_once_with()

    @patch("tapio.cli.MarkdownVectorizer")
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

    @patch("tapio.cli.MarkdownVectorizer")
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
            input_dir=DEFAULT_DIRS["PARSED_DIR"],
            domain_filter="example.com",
            batch_size=20,
        )

        # Check expected output in stdout
        assert "Starting vectorization" in result.stdout
        assert "Vectorization completed" in result.stdout
        assert "Processed 3 files" in result.stdout

    @patch("tapio.cli.MarkdownVectorizer")
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
