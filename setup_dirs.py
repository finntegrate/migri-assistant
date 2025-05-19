#!/usr/bin/env python3
"""Utility to create the directory structure for migri-assistant.

This script creates the required directories for storing crawled and parsed content.
It's recommended to run this script after setting up the project.
"""

import logging
import os
from pathlib import Path

from tapio.config.settings import DEFAULT_DIRS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def setup_directories() -> None:
    """Create the required directories for the project."""
    for dir_key, dir_path in DEFAULT_DIRS.items():
        # Skip if the directory already exists
        if os.path.exists(dir_path):
            logger.info(f"Directory '{dir_path}' already exists.")
            continue

        # Create the directory
        try:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {dir_path}")
        except Exception as e:
            logger.error(f"Failed to create directory '{dir_path}': {e}")


if __name__ == "__main__":
    logger.info("Setting up directory structure for migri-assistant...")
    setup_directories()
    logger.info("Directory setup complete!")
