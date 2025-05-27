"""Tests for the ConfigManager class."""

from unittest.mock import mock_open, patch

import pytest
import yaml
from pydantic import ValidationError

from tapio.config import ConfigManager
from tapio.config.config_models import SiteParserConfig


class TestConfigManager:
    """Tests for the ConfigManager class."""

    def test_init_default_path(self):
        """Test initialization with default config path."""
        with patch(
            "tapio.config.config_manager.open",
            mock_open(
                read_data="""
                sites:
                  test_site:
                    site_name: "test"
                    base_url: "https://example.com"
                    content_selectors:
                      - "//main"
            """,
            ),
        ) as mock_file:
            config_manager = ConfigManager()

            # Verify the file was opened
            mock_file.assert_called()

            # Check that at least one site was loaded
            assert len(config_manager.list_available_sites()) > 0

    def test_init_custom_path(self):
        """Test initialization with custom config path."""
        test_config_path = "/path/to/custom/config.yaml"
        test_yaml_content = """
            sites:
              custom_site:
                site_name: "custom"
                base_url: "https://custom-example.com"
                content_selectors:
                  - "//main"
        """

        with patch("tapio.config.config_manager.open", mock_open(read_data=test_yaml_content)) as mock_file:
            config_manager = ConfigManager(config_path=test_config_path)
            mock_file.assert_called_with(test_config_path, encoding="utf-8")

            # Test the loaded site data
            assert "custom_site" in config_manager.list_available_sites()

    def test_from_file_class_method(self):
        """Test the from_file class method."""
        test_config_path = "/path/to/custom/config.yaml"

        with patch("tapio.config.config_manager.ConfigManager.__init__", return_value=None) as mock_init:
            ConfigManager.from_file(test_config_path)
            mock_init.assert_called_with(config_path=test_config_path)

    def test_file_not_found(self):
        """Test handling of non-existent configuration file."""
        with patch("tapio.config.config_manager.open", side_effect=FileNotFoundError()):
            with pytest.raises(FileNotFoundError):
                ConfigManager(config_path="nonexistent_file.yaml")

    def test_invalid_yaml(self):
        """Test handling of invalid YAML file."""
        with patch("tapio.config.config_manager.open", mock_open(read_data=": invalid: yaml: content")):
            with patch("yaml.safe_load", side_effect=yaml.YAMLError("Invalid YAML")):
                with pytest.raises(yaml.YAMLError):
                    ConfigManager(config_path="invalid_yaml.yaml")

    def test_invalid_config_structure(self):
        """Test handling of invalid configuration structure."""
        with patch("tapio.config.config_manager.open", mock_open(read_data="not_sites: {}")):
            with pytest.raises(ValidationError):
                ConfigManager(config_path="invalid_structure.yaml")

    def test_get_site_config(self):
        """Test retrieving a specific site configuration."""
        with patch(
            "tapio.config.config_manager.open",
            mock_open(
                read_data="""
                sites:
                  test_site:
                    site_name: "test"
                    base_url: "https://example.com"
                    content_selectors:
                      - "//main"
            """,
            ),
        ):
            config_manager = ConfigManager()
            site_config = config_manager.get_site_config("test_site")
            assert isinstance(site_config, SiteParserConfig)
            assert site_config.site_name == "test"
            assert str(site_config.base_url) == "https://example.com/"
            assert "//main" in site_config.content_selectors

    def test_get_nonexistent_site_config(self):
        """Test retrieving a non-existent site configuration."""
        with patch(
            "tapio.config.config_manager.open",
            mock_open(
                read_data="""
                sites:
                  test_site:
                    site_name: "test"
                    base_url: "https://example.com"
                    content_selectors:
                      - "//main"
            """,
            ),
        ):
            config_manager = ConfigManager()
            with pytest.raises(ValueError, match="Site 'nonexistent' not found in configuration"):
                config_manager.get_site_config("nonexistent")

    def test_get_site_with_invalid_url(self):
        """Test retrieving site configuration with invalid base_url."""
        with patch(
            "tapio.config.config_manager.open",
            mock_open(
                read_data="""
                sites:
                  invalid_url_site:
                    site_name: "invalid"
                    base_url: "invalid-url"
                    content_selectors:
                      - "//main"
            """,
            ),
        ):
            # Now the validation happens at model creation time via Pydantic
            with pytest.raises(ValidationError):
                _ = ConfigManager()

    def test_list_available_sites(self):
        """Test listing all available site configurations."""
        test_config = """
            sites:
              site1:
                site_name: "Site 1"
                base_url: "https://site1.com"
                content_selectors:
                  - "//main"
              site2:
                site_name: "Site 2"
                base_url: "https://site2.com"
                content_selectors:
                  - "//main"
              site3:
                site_name: "Site 3"
                base_url: "https://site3.com"
                content_selectors:
                  - "//main"
        """

        with patch("tapio.config.config_manager.open", mock_open(read_data=test_config)):
            config_manager = ConfigManager()
            available_sites = config_manager.list_available_sites()
            assert len(available_sites) == 3
            assert "site1" in available_sites
            assert "site2" in available_sites
            assert "site3" in available_sites

    def test_get_site_descriptions(self):
        """Test getting descriptions for all site configurations."""
        test_config = """
            sites:
              site1:
                site_name: "Site 1"
                base_url: "https://site1.com"
                content_selectors:
                  - "//main"
                description: "First site description"
              site2:
                site_name: "Site 2"
                base_url: "https://site2.com"
                content_selectors:
                  - "//main"
                description: "Second site description"
              site3:
                site_name: "Site 3"
                base_url: "https://site3.com"
                content_selectors:
                  - "//main"
        """

        with patch("tapio.config.config_manager.open", mock_open(read_data=test_config)):
            config_manager = ConfigManager()
            site_descriptions = config_manager.get_site_descriptions()

            assert len(site_descriptions) == 3
            assert site_descriptions["site1"] == "First site description"
            assert site_descriptions["site2"] == "Second site description"
            # Test that default description is generated for sites without a description
            assert site_descriptions["site3"] == "Configuration for site3"
