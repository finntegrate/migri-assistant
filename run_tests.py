#!/usr/bin/env python
"""Utility script to run tests without installing the package."""

import os
import sys

import pytest

# Add the project root to the path so tests can import modules
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

if __name__ == "__main__":
    # Run pytest with the specified arguments
    sys.exit(pytest.main(sys.argv[1:]))
