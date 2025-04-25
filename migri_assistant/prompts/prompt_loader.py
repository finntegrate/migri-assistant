"""Utility functions for loading prompt templates from files."""

import logging
import os
from pathlib import Path
from string import Template

# Configure logging
logger = logging.getLogger(__name__)


def get_prompt_path(prompt_name: str) -> str:
    """Get the file path for a prompt template.

    Args:
        prompt_name: Name of the prompt template without file extension

    Returns:
        Path to the prompt template file
    """
    # Get the directory of this file
    prompts_dir = Path(__file__).parent

    # Check for .md extension first (preferred format)
    md_path = prompts_dir / f"{prompt_name}.md"
    if md_path.exists():
        return str(md_path)

    # Check for .txt extension as fallback
    txt_path = prompts_dir / f"{prompt_name}.txt"
    if txt_path.exists():
        return str(txt_path)

    # Default to md extension if file doesn't exist yet
    return str(md_path)


def load_prompt(prompt_name: str, **kwargs) -> str:
    """Load a prompt template from file and substitute any variables.

    Args:
        prompt_name: Name of the prompt template without extension
        **kwargs: Variables to substitute in the template

    Returns:
        The loaded and formatted prompt text
    """
    prompt_path = get_prompt_path(prompt_name)

    try:
        if not os.path.exists(prompt_path):
            logger.warning(f"Prompt template not found: {prompt_path}")
            return ""

        with open(prompt_path, encoding="utf-8") as file:
            prompt_template = file.read()

        # If kwargs are provided, substitute them in the template
        if kwargs:
            template = Template(prompt_template)
            return template.safe_substitute(**kwargs)

        return prompt_template

    except Exception as e:
        logger.error(f"Error loading prompt template {prompt_name}: {e}")
        return ""
