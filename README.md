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
Migri example:
```bash
uv run -m migri_assistant.cli crawl https://migri.fi/en/home --depth 2 --output-dir crawled_content
```

Kela example:
```bash
uv run -m migri_assistant.cli crawl https://www.kela.fi/main-page --depth 2 --output-dir crawled_content
```

1. **Parse** the HTML content into structured Markdown:

```bash
uv run -m migri_assistant.cli parse --input-dir crawled_content --output-dir parsed_content --site migri
```

The `--site` parameter specifies which site configuration to use. The parser will:
- Process only files located in the domain directory defined by the site's configuration
- Apply site-specific selectors to extract the relevant content
- Convert relative links to absolute URLs using the site's base URL
- Format the content according to the site's markdown configuration

#### Site-Specific Parsing

Each site configuration defines:
- The domain directory to process (e.g., `migri.fi`)
- The base URL for link conversions (e.g., `https://migri.fi`)
- Selectors for extracting titles and content
- HTML-to-Markdown conversion preferences

For example, to parse content from different sites:

```bash
# Parse the Finnish Immigration Service (Migri) site
uv run -m migri_assistant.cli parse --input-dir crawled_content --output-dir parsed_content --site migri

# Parse the TE Services site
uv run -m migri_assistant.cli parse --input-dir crawled_content --output-dir parsed_content --site te_palvelut

# Parse the Kela site
uv run -m migri_assistant.cli parse --input-dir crawled_content --output-dir parsed_content --site kela
```

Available sites include any defined in the parser configurations (`parser_configs.yaml`). To see all available site configurations:

```bash
uv run -m migri_assistant.cli info --list-site-configs
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

To view available site configurations for parsing:

```bash
# List all available sites
uv run -m migri_assistant.cli info --list-site-configs

# Show detailed configuration for a specific site
uv run -m migri_assistant.cli info --show-site-config migri
```

## End-to-End Workflow Example: Migri Site

Here's a complete workflow for crawling, parsing, and querying the Finnish Immigration Service website:

### 1. Crawl the Migri Website

```bash
uv run -m migri_assistant.cli crawl https://migri.fi/en/home --depth 2 --output-dir crawled_content
```

This will save HTML files in `crawled_content/migri.fi/` and create a URL mappings file.

### 2. Parse the Migri Content

```bash
uv run -m migri_assistant.cli parse --input-dir crawled_content --output-dir parsed_content --site migri
```

This will process only files in the `migri.fi` directory using Migri's content selectors.

### 3. Vectorize and Query

```bash
# Vectorize the content
uv run -m migri_assistant.cli vectorize --input-dir parsed_content --collection migri_docs

# Launch the chatbot
uv run -m migri_assistant.cli gradio-app --collection-name migri_docs
```

## Site Configurations

The parser uses site-specific configurations to extract content correctly from different websites. These configurations are defined in `migri_assistant/config/parser_configs.yaml`.

### Configuration Structure

Each site configuration includes:

```yaml
sites:
  migri:                                    # Site key used with --site
    site_name: "migri"                      # Name for output directories and logs
    base_url: "https://migri.fi"            # Base URL for converting relative links
    base_dir: "migri.fi"                    # Directory name in crawled_content
    title_selector: "//title"               # XPath selector for page title
    content_selectors:                      # Prioritized list of content selectors
      - '//div[@id="main-content"]'
      - "//main"
      - "//article"
      - '//div[@class="content"]'
    fallback_to_body: true                  # Use body if selectors don't match
    description: "Finnish Immigration Service website"
    markdown_config:                        # HTML-to-Markdown settings
      ignore_links: false
      body_width: 0                         # No text wrapping
      protect_links: true
      unicode_snob: true
      ignore_images: false
      ignore_tables: false
```

### Adding a New Site

To add support for a new website:

1. Determine the site's structure by examining a few pages
2. Identify the appropriate XPath selectors for title and main content
3. Add a new entry to `parser_configs.yaml` with the required fields
4. Use the unique site key with the parse command

For example, to add support for a hypothetical "example.com":

```yaml
sites:
  # ... existing site configurations ...
  example:
    site_name: "example"
    base_url: "https://example.com"
    base_dir: "example.com"
    title_selector: "//h1"
    content_selectors:
      - '//div[@class="content"]'
      - '//main'
    fallback_to_body: true
    description: "Example website configuration"
    markdown_config:
      ignore_links: false
      body_width: 0
      protect_links: true
```

Then use it with:

```bash
# Crawl the site
uv run -m migri_assistant.cli crawl https://example.com --depth 2

# Parse using the new configuration
uv run -m migri_assistant.cli parse --site example
```

## Contributing

If you'd like to contribute to this project, please see our [Contributing Guide](CONTRIBUTING.md) for details on our code of conduct, development process, and how to submit pull requests.

## License
This project is licensed under the Apache 2.0 License. See the LICENSE file for more details.
