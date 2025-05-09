# Migri Assistant

## Overview
Migri Assistant is a tool designed to extract, process, and query information from multiple websites, including Migri.fi (Finnish Immigration Service). It provides end-to-end RAG (Retrieval Augmented Generation) capabilities including web crawling, content parsing, vectorization, and an interactive chatbot interface.

##  Key Demographics

- EU citizens
- Non-EU citizens
- Target Audience
    - Students
    - Workers
    - Families
    - Refugees
    - Asylum Seekers

## Needs

- Finding relevant information
- Conversation practice based on the topics they search (e.g. family reunification, work, studies)

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

### Setting up

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
uv sync
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
uv run -m migri_assistant.cli parse --input-dir crawled_content --output-dir parsed_content --site-type migri
```

The `--site-type` parameter specifies which site configuration to use. Available site types include `migri`, `te_palvelut`, `kela`, and any others defined in the parser configurations.

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
# Quick start - launch with development server
uv run -m migri_assistant.cli dev

# Long form - launch with default settings
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

## Contributing

If you'd like to contribute to this project, please see our [Contributing Guide](CONTRIBUTING.md) for details on our code of conduct, development process, and how to submit pull requests.

## License
This project is licensed under the Apache 2.0 License. See the LICENSE file for more details.
