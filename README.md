# Migri Assistant

## Overview
Migri Assistant is a tool designed to extract, process, and query information from websites, with specific functionality tailored for the Migri.fi website. It provides end-to-end RAG (Retrieval Augmented Generation) capabilities including web crawling, content parsing, vectorization, and an interactive chatbot interface.

## Features
- Crawls web pages to a configurable depth
- Saves raw HTML content with domain-based organization
- Parses HTML content into structured Markdown files
- Vectorizes parsed content into ChromaDB for semantic search
- Provides a Gradio-based RAG chatbot interface for querying content
- Integrates with Ollama for local LLM inference
- Clean separation between crawling, parsing, vectorization, and querying
- Domain restriction and crawl depth control
- Comprehensive test suite

## Installation and Setup

### Prerequisites
- Python 3.10 or higher
- [uv](https://github.com/astral-sh/uv) - Fast Python package installer and resolver
- [Ollama](https://ollama.ai/) - For local LLM inference (required for the chatbot)

### Setting up with uv

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

4. Ensure you have the required Ollama models:
```bash
ollama pull llama3.2
```

## Usage

### Running the Crawler, Parser, and Vectorizer

The tool follows a three-step process to crawl, parse, and vectorize content:

1. **Crawl** a website to retrieve and save HTML content:
```bash
uv run -m migri_assistant.cli crawl https://migri.fi/en/home --depth 2 --output-dir crawled_content
```

2. **Parse** the HTML content into structured Markdown:
```bash
uv run -m migri_assistant.cli parse --input-dir crawled_content --output-dir parsed_content
```

3. **Vectorize** the parsed Markdown content into ChromaDB for semantic search:
```bash
uv run -m migri_assistant.cli vectorize --input-dir parsed_content --db-dir chroma_db --collection migri_docs
```

4. **Launch the RAG Chatbot** to interactively query the content:
```bash
uv run -m migri_assistant.cli gradio-app
```

### RAG Chatbot Options

The RAG chatbot allows you to query information from your vectorized content using a local LLM through Ollama. The chatbot provides several configuration options:

```bash
# Launch with default settings
uv run -m migri_assistant.cli gradio-app

# Use a specific Ollama model
uv run -m migri_assistant.cli gradio-app --model-name llama3.2:latest

# Specify a different ChromaDB collection
uv run -m migri_assistant.cli gradio-app --collection-name my_collection

# Create a shareable link for the app
uv run -m migri_assistant.cli gradio-app --share
```

### Parameters and Options

For detailed information about available parameters and options for any command:

```bash
uv run -m migri_assistant.cli <command> --help
```

Available commands:
- `crawl`: Crawl websites and save HTML content
- `parse`: Parse HTML files into structured Markdown
- `vectorize`: Vectorize parsed Markdown into ChromaDB
- `gradio-app`: Launch the Gradio RAG chatbot interface
- `info`: Show information about available commands

## Development

### Code Quality

We use [Ruff](https://docs.astral.sh/ruff/) for linting and formatting. To run the linter:

```bash
uv run ruff .
```

To automatically fix issues:

```bash
uv run ruff . --fix
```

To check formatting without fixing:

```bash
uv run ruff . --check
```

### Running Tests

```bash
uv run pytest
```

To run tests with code coverage reports:

```bash
# Generate coverage report in the terminal
uv run pytest --cov=migri_assistant

# Generate HTML coverage report
uv run pytest --cov=migri_assistant --cov-report=html

# Get coverage for specific modules
uv run pytest --cov=migri_assistant.utils tests/utils/
```

The HTML coverage report will be generated in the `htmlcov` directory. Open `htmlcov/index.html` in your browser to view it.

## Project Structure

The project has been designed with a clear separation of concerns:

- `crawler/`: Module responsible for crawling websites and saving HTML content
- `parsers/`: Module responsible for parsing HTML content into structured formats
- `vectorstore/`: Module responsible for vectorizing content and storing in ChromaDB
- `gradio_app.py`: Gradio interface for the RAG chatbot
- `utils/`: Utility modules for embedding generation, markdown processing, etc.
- `tests/`: Test suite for all modules

## License
This project is licensed under the Apache 2.0 License. See the LICENSE file for more details.
