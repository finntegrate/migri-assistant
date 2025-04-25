# Contributing to Migri Assistant

Thank you for considering contributing to Migri Assistant! This document provides guidelines and instructions for contributing to this project.

## Table of Contents
- [Development Environment Setup](#development-environment-setup)
- [Package Management](#package-management)
- [Code Quality](#code-quality)
- [Testing Guidelines](#testing-guidelines)
- [Project Structure](#project-structure)
- [Ollama for LLM Inference](#ollama-for-llm-inference)
- [Pull Request Process](#pull-request-process)

## Development Environment Setup

1. Clone the repository:
```bash
git clone https://github.com/Finntegrate/migri-assistant.git
cd migri-assistant
```

2. Create and activate a virtual environment with uv:
```bash
uv venv
source .venv/bin/activate  # On Unix/macOS
# OR
.\.venv\Scripts\activate   # On Windows
```

3. Install dependencies:
```bash
uv sync --dev
```

## Package Management

We use the `uv` package manager for this project. To add packages:

```bash
uv add <package-name>
```

Do not use `pip`, `uv pip install`, or `uv pip install -e .` to install packages or this project.

To synchronize dependencies from the lockfile:

```bash
uv sync
```

## Code Quality

### Ruff

We use [Ruff](https://docs.astral.sh/ruff/) for linting and formatting. Please ensure your code passes all checks before submitting a pull request.

You can run the linter with the following command:

```bash
uv run ruff .
```

You can also run the linter with the `--fix` option to automatically fix some issues:

```bash
uv run ruff . --fix
```

Or check for issues without fixing them:

```bash
uv run ruff . --check
```

## Testing Guidelines

### Running Tests

When adding features, always include appropriate tests. Run the entire test suite with:

```bash
uv run pytest
```

### Code Coverage

We aim for high test coverage. When submitting code:

1. Check your coverage with:

```bash
uv run pytest --cov=migri_assistant
```

2. Generate HTML coverage reports for visual inspection:

```bash
uv run pytest --cov=migri_assistant --cov-report=html
```

3. For specific module coverage:

```bash
uv run pytest --cov=migri_assistant.utils tests/utils/
```

Aim for at least 80% coverage for new code. The HTML coverage report can be found in the `htmlcov` directory. Open `htmlcov/index.html` in your browser to view it.

## Project Structure

The project has been designed with a clear separation of concerns:

- `crawler/`: Module responsible for crawling websites and saving HTML content
- `parsers/`: Module responsible for parsing HTML content into structured formats
- `vectorstore/`: Module responsible for vectorizing content and storing in ChromaDB
- `gradio_app.py`: Gradio interface for the RAG chatbot
- `utils/`: Utility modules for embedding generation, markdown processing, etc.
- `tests/`: Test suite for all modules

## Ollama for LLM Inference

We use Ollama for local LLM inference.

The following Ollama models are used in the project:
- `llama3.2`: The base model for text generation.

To query the Ollama models that are installed, use the command:

```bash
ollama list
```

To list all Ollama commands, use the command:

```bash
ollama help
```

To get help for a specific command, use the command:

```bash
ollama <command> --help
```

Ensure you have the required models installed:

```bash
ollama pull llama3.2
```

## Pull Request Process

1. Ensure any install or build dependencies are removed before the end of the layer when doing a build.
2. Update the README.md with details of changes to the interface, if appropriate.
3. Make sure all tests pass and code is properly formatted with Ruff.
4. Check that code coverage meets our standards (minimum 80%).
5. Submit your pull request with a clear description of the changes, related issue numbers, and any special considerations.
6. The pull request will be merged once it receives approval from the maintainers.
