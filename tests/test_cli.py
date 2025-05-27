"""Tests for the CLI module."""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from tapio.cli import app
from tapio.config.settings import DEFAULT_CHROMA_COLLECTION, DEFAULT_DIRS


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
    @patch("tapio.cli.ConfigManager")
    def test_crawl_command(self, mock_config_manager, mock_scrapy_runner, runner):
        """Test the crawl command."""
        # Set up mocks
        mock_runner_instance = MagicMock()
        mock_runner_instance.run.return_value = ["page1", "page2", "page3"]
        mock_scrapy_runner.return_value = mock_runner_instance

        # Mock ConfigManager
        mock_config_instance = MagicMock()
        mock_site_config = MagicMock()
        mock_site_config.base_url = "https://example.com"
        mock_config_instance.get_site_config.return_value = mock_site_config
        mock_config_instance.list_available_sites.return_value = ["migri"]
        mock_config_manager.return_value = mock_config_instance

        # Run the command
        result = runner.invoke(
            app,
            [
                "crawl",
                "migri",
                "--depth",
                "2",
            ],
        )

        # Check that the command ran successfully
        assert result.exit_code == 0

        # Check that list_available_sites was called
        mock_config_instance.list_available_sites.assert_called_once()

        # Check that get_site_config was called with the correct site name
        mock_config_instance.get_site_config.assert_called_once_with("migri")

        # Check that the runner was initialized correctly
        mock_scrapy_runner.assert_called_once()

        # Check that run was called with the correct arguments
        mock_runner_instance.run.assert_called_once_with(
            start_urls=["https://example.com"],  # URL from site config
            depth=2,
            allowed_domains=["example.com"],  # Domain extracted from URL
            output_dir=DEFAULT_DIRS["CRAWLED_DIR"],
        )

        # Check expected output in stdout
        assert "Starting web crawler" in result.stdout
        assert "Crawling completed" in result.stdout
        assert "Processed 3 pages" in result.stdout

    @patch("tapio.cli.ScrapyRunner")
    @patch("tapio.cli.ConfigManager")
    def test_crawl_command_keyboard_interrupt(self, mock_config_manager, mock_scrapy_runner, runner):
        """Test handling of keyboard interrupt in crawl command."""
        # Mock ConfigManager
        mock_config_instance = MagicMock()
        mock_site_config = MagicMock()
        mock_site_config.base_url = "https://example.com"
        mock_config_instance.get_site_config.return_value = mock_site_config
        mock_config_instance.list_available_sites.return_value = ["migri"]
        mock_config_manager.return_value = mock_config_instance

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
    @patch("tapio.cli.ConfigManager")
    def test_crawl_command_exception(self, mock_config_manager, mock_scrapy_runner, runner):
        """Test handling of exceptions in crawl command."""
        # Mock ConfigManager
        mock_config_instance = MagicMock()
        mock_site_config = MagicMock()
        mock_site_config.base_url = "https://example.com"
        mock_config_instance.get_site_config.return_value = mock_site_config
        mock_config_instance.list_available_sites.return_value = ["migri"]
        mock_config_manager.return_value = mock_config_instance

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

    @patch("tapio.cli.ConfigManager")
    def test_crawl_command_invalid_site(self, mock_config_manager, runner):
        """Test the crawl command with an invalid site name."""
        # Mock the ConfigManager
        mock_config_instance = MagicMock()
        mock_config_instance.list_available_sites.return_value = ["migri", "te_palvelut", "kela"]
        mock_config_manager.return_value = mock_config_instance

        # Run the command with an unsupported site
        result = runner.invoke(app, ["crawl", "unsupported_site"])

        # Check that the command exited with error code
        assert result.exit_code == 1

        # Check expected output in stdout
        assert "Unsupported site: unsupported_site" in result.stdout
        assert "Available sites: migri, te_palvelut, kela" in result.stdout

    @patch("tapio.cli.ConfigManager")
    @patch("tapio.cli.Parser")
    def test_parse_command(self, mock_parser, mock_config_manager, runner):
        """Test the parse command."""
        # Set up mock parser
        mock_parser_instance = MagicMock()
        mock_parser_instance.parse_all.return_value = ["file1", "file2", "file3"]
        mock_parser.return_value = mock_parser_instance

        # Set up mock config manager
        mock_config_instance = MagicMock()
        mock_config_instance.list_available_sites.return_value = ["migri"]
        mock_config_manager.return_value = mock_config_instance

        # Run the command
        result = runner.invoke(
            app,
            [
                "parse",
                "--site",
                "migri",
            ],
        )

        # Check that the command ran successfully
        assert result.exit_code == 0

        # Check that the parser was initialized correctly
        mock_parser.assert_called_once_with(
            site="migri",
            input_dir=DEFAULT_DIRS["CRAWLED_DIR"],
            output_dir=DEFAULT_DIRS["PARSED_DIR"],
            config_path=None,
        )

        # Check that list_available_sites was called
        mock_config_instance.list_available_sites.assert_called_once()

        # Check that parse_all was called correctly (without domain parameter)
        mock_parser_instance.parse_all.assert_called_once_with()

        # Check expected output in stdout
        assert "Starting HTML parsing" in result.stdout
        assert "Using configuration for site: migri" in result.stdout
        assert "Parsing completed" in result.stdout
        assert "Processed 3 files" in result.stdout

    @patch("tapio.cli.ConfigManager")
    @patch("tapio.cli.Parser")
    def test_parse_command_with_domain(self, mock_parser, mock_config_manager, runner):
        """Test the parse command with a domain filter."""
        # Set up mock parser
        mock_parser_instance = MagicMock()
        mock_parser_instance.parse_all.return_value = ["file1", "file2"]
        mock_parser.return_value = mock_parser_instance

        # Set up mock config manager
        mock_config_instance = MagicMock()
        mock_config_instance.list_available_sites.return_value = ["migri"]
        mock_config_manager.return_value = mock_config_instance

        # Run the command with domain filter
        result = runner.invoke(app, ["parse", "--domain", "example.com", "--site", "migri"])

        # Check that the command ran successfully
        assert result.exit_code == 0

        # Check that parse_all was called correctly (domain is now handled internally)
        mock_parser_instance.parse_all.assert_called_once_with()

        # Check that list_available_sites was called
        mock_config_instance.list_available_sites.assert_called_once()

        # Check expected output in stdout
        assert "Starting HTML parsing" in result.stdout
        assert "Processed 2 files" in result.stdout

    @patch("tapio.cli.ConfigManager")
    def test_parse_command_unsupported_site(self, mock_config_manager, runner):
        """Test the parse command with an unsupported site."""
        # Set up mock config manager
        mock_config_instance = MagicMock()
        mock_config_instance.list_available_sites.return_value = ["migri", "te_palvelut", "kela"]
        mock_config_manager.return_value = mock_config_instance

        # Run the command with an unsupported site
        result = runner.invoke(app, ["parse", "--site", "unsupported"])

        # Check that the command exited with error code
        assert result.exit_code == 1

        # Check expected output in stdout
        assert "Unsupported site: unsupported" in result.stdout
        assert "Available sites: migri, te_palvelut, kela" in result.stdout

        # Check that list_available_sites was called
        mock_config_instance.list_available_sites.assert_called_once()

    @patch("tapio.cli.ConfigManager")
    @patch("tapio.cli.Parser")
    def test_parse_command_exception(self, mock_parser, mock_config_manager, runner):
        """Test handling of exceptions in parse command."""
        # Set up mock parser that raises an exception
        mock_parser_instance = MagicMock()
        mock_parser_instance.parse_all.side_effect = Exception("Test error")
        mock_parser.return_value = mock_parser_instance

        # Set up mock config manager
        mock_config_instance = MagicMock()
        mock_config_instance.list_available_sites.return_value = ["migri"]
        mock_config_manager.return_value = mock_config_instance

        # Run the command
        result = runner.invoke(app, ["parse", "--site", "migri"])

        # Check that the command exited with error code
        assert result.exit_code == 1

        # Check expected output in stdout
        assert "Starting HTML parsing" in result.stdout
        assert "Error during parsing: Test error" in result.stdout

        # Check that list_available_sites was called
        mock_config_instance.list_available_sites.assert_called_once()

    @patch("tapio.cli.ConfigManager")
    @patch("tapio.cli.Parser")
    @patch("os.path.exists")
    def test_parse_command_custom_config(self, mock_exists, mock_parser, mock_config_manager, runner):
        """Test the parse command with a custom config path."""
        # Setup mock for file existence check
        mock_exists.return_value = True

        # Set up mock parser
        mock_parser_instance = MagicMock()
        mock_parser_instance.parse_all.return_value = ["file1", "file2"]
        mock_parser.return_value = mock_parser_instance

        # Set up mock config manager
        mock_config_instance = MagicMock()
        mock_config_instance.list_available_sites.return_value = ["custom_site"]
        mock_config_manager.return_value = mock_config_instance

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

        # Check that ConfigManager was instantiated with the correct custom config path
        mock_config_manager.assert_called_with("custom_configs.yaml")

        # Check that list_available_sites was called
        mock_config_instance.list_available_sites.assert_called_once()

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
            ],
        )

        # Check that the command ran successfully
        assert result.exit_code == 0

        # Check that the vectorizer was initialized correctly
        mock_vectorizer.assert_called_once_with(
            collection_name=DEFAULT_CHROMA_COLLECTION,
            persist_directory=DEFAULT_DIRS["CHROMA_DIR"],
            embedding_model_name="all-MiniLM-L6-v2",
            chunk_size=1000,
            chunk_overlap=200,
        )

        # Check that process_directory was called correctly
        mock_vectorizer_instance.process_directory.assert_called_once_with(
            input_dir=DEFAULT_DIRS["PARSED_DIR"],
            domain_filter=None,
            batch_size=20,
        )

        # Check expected output in stdout
        assert "Starting vectorization" in result.stdout
        assert f"Vector database will be stored in: {DEFAULT_DIRS['CHROMA_DIR']}" in result.stdout
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

    @patch("tapio.gradio_app.main")
    def test_gradio_app_command(self, mock_launch_gradio, runner):
        """Test the gradio-app command."""
        # Run the command
        result = runner.invoke(app, ["gradio-app"])

        # Check that the command ran successfully
        assert result.exit_code == 0

        # Check that launch_gradio was called correctly
        mock_launch_gradio.assert_called_once_with(
            collection_name=DEFAULT_CHROMA_COLLECTION,
            persist_directory=DEFAULT_DIRS["CHROMA_DIR"],
            model_name="llama3.2",
            max_tokens=1024,
            share=False,
        )

    @patch("tapio.gradio_app.main")
    def test_gradio_app_command_with_options(self, mock_launch_gradio, runner):
        """Test the gradio-app command with custom options."""
        # Run the command with options
        result = runner.invoke(
            app,
            [
                "gradio-app",
                "--model-name",
                "llama3.2:latest",
                "--max-tokens",
                "2048",
                "--share",
            ],
        )

        # Check that the command ran successfully
        assert result.exit_code == 0

        # Check that launch_gradio was called correctly with the custom options
        mock_launch_gradio.assert_called_once_with(
            collection_name=DEFAULT_CHROMA_COLLECTION,
            persist_directory=DEFAULT_DIRS["CHROMA_DIR"],
            model_name="llama3.2:latest",
            max_tokens=2048,
            share=True,
        )

    @patch("tapio.cli.gradio_app")
    def test_dev_command(self, mock_gradio_app, runner):
        """Test the dev command."""
        # Run the command
        result = runner.invoke(app, ["dev"])

        # Check that the command ran successfully
        assert result.exit_code == 0

        # Check that gradio_app was called correctly
        mock_gradio_app.assert_called_once_with(
            model_name="llama3.2",
            share=False,
        )

        # Check expected output in stdout
        assert "Launching Tapio Assistant chatbot development server" in result.stdout

    @patch("tapio.cli.ConfigManager")
    def test_list_sites_command(self, mock_config_manager, runner):
        """Test the list-sites command."""
        # Set up mock config manager
        mock_config_instance = MagicMock()
        mock_config_instance.list_available_sites.return_value = ["migri", "te_palvelut", "kela"]
        mock_config_instance.get_site_descriptions.return_value = {
            "migri": "Finnish Immigration Service",
            "te_palvelut": "Employment Services",
            "kela": "Social Insurance Institution",
        }
        mock_config_manager.return_value = mock_config_instance

        # Run the command
        result = runner.invoke(app, ["list-sites"])

        # Check that the command ran successfully
        assert result.exit_code == 0

        # Check that list_available_sites was called
        mock_config_instance.list_available_sites.assert_called_once()

        # Check that get_site_descriptions was called (may be called multiple times)
        assert mock_config_instance.get_site_descriptions.called

        # Check expected output in stdout
        assert "Available Site Configurations:" in result.stdout
        assert "migri" in result.stdout
        assert "te_palvelut" in result.stdout
        assert "kela" in result.stdout
        assert "Finnish Immigration Service" in result.stdout

    @patch("tapio.cli.ConfigManager")
    def test_list_sites_command_verbose(self, mock_config_manager, runner):
        """Test the list-sites command with verbose flag."""
        # Set up mock config manager
        mock_config_instance = MagicMock()
        mock_config_instance.list_available_sites.return_value = ["migri"]

        # Mock site config
        mock_site_config = MagicMock()
        mock_site_config.site_name = "migri"
        mock_site_config.description = "Finnish Immigration Service"
        mock_site_config.title_selector = "h1"
        mock_site_config.content_selectors = ["main", "article"]
        mock_site_config.fallback_to_body = True

        mock_config_instance.get_site_config.return_value = mock_site_config
        mock_config_manager.return_value = mock_config_instance

        # Run the command with verbose flag
        result = runner.invoke(app, ["list-sites", "--verbose"])

        # Check that the command ran successfully
        assert result.exit_code == 0

        # Check that list_available_sites was called
        mock_config_instance.list_available_sites.assert_called_once()

        # Check that get_site_config was called with the right site
        mock_config_instance.get_site_config.assert_called_with("migri")

        # Check expected output in stdout
        assert "Available Site Configurations:" in result.stdout
        assert "Site name: migri" in result.stdout
        assert "Description: Finnish Immigration Service" in result.stdout
        assert "Title selector: h1" in result.stdout
        assert "Content selectors:" in result.stdout
        assert "Fallback to body: True" in result.stdout

    @patch("tapio.cli.ConfigManager")
    def test_list_sites_command_exception(self, mock_config_manager, runner):
        """Test handling of exceptions in list-sites command."""
        # Set up mock to raise an exception
        mock_config_instance = MagicMock()
        mock_config_instance.list_available_sites.side_effect = Exception("Test error")
        mock_config_manager.return_value = mock_config_instance

        # Run the command
        result = runner.invoke(app, ["list-sites"])

        # Check that the command exited with error code
        assert result.exit_code == 1

        # Check expected output in stdout
        assert "Error listing site configurations: Test error" in result.stdout
