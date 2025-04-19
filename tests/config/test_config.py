"""Tests for the config module."""

from migri_assistant import config


def test_default_depth():
    """Test that DEFAULT_DEPTH has expected value."""
    assert config.DEFAULT_DEPTH == 2


def test_output_format():
    """Test that OUTPUT_FORMAT has expected value."""
    assert config.OUTPUT_FORMAT == "json"


def test_user_agent():
    """Test that USER_AGENT has expected value."""
    assert config.USER_AGENT == "migri-assistant/0.1.0"


def test_timeout():
    """Test that TIMEOUT has expected value."""
    assert config.TIMEOUT == 10