# Tapio

## Overview
Tapio is a tool designed to extract, process, and query information from multiple websites, including Migri.fi (Finnish Immigration Service). It provides end-to-end RAG (Retrieval Augmented Gen### Site Configurations

The parser uses site-specific configurations to extract content correctly from different websites. These configurations are defined in `tapio/config/site_configs.yaml`.

When you run the `parse` command with just the `--site` parameter (e.g., `uv run -m tapio.cli parse --site migri`), the parser automatically:
1. Determines the base directory from the site's configuration
2. Processes only HTML files from that directory
3. Applies the appropriate content selectors and markdown conversion rulestion) capabilities including web crawling, content parsing, vectorization, and an interactive chatbot interface.

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
git clone https://github.com/Finntegrate/tapio.git
cd tapio
```

2. Create and activate a virtual environment with uv:
```bash
uv sync
source .venv/bin/activate  # On Unix/macOS
# OR
.\.venv\Scripts\activate   # On Windows
```

3. Ensure you have the required Ollama models:
```bash
ollama pull llama3.2
```

4. Set up the directory structure for content:
```bash
python setup_dirs.py
```
This will create the necessary directories (`content/crawled` and `content/parsed`) for storing crawled and parsed content.

## Usage

### Running the Crawler, Parser, and Vectorizer

The tool follows a three-step process to crawl, parse, and vectorize content:

1. **Crawl** a website to retrieve and save HTML content:
Migri example:
```bash
uv run -m tapio.cli crawl migri --depth 2
```

Kela example:
```bash
uv run -m tapio.cli crawl kela --depth 2
```

1. **Parse** the HTML content into structured Markdown:

```bash
uv run -m tapio.cli parse --site migri
```

The `--site` parameter specifies which site configuration to use. This is the only required parameter, and the parser will automatically:
- Process all files located in the domain directory defined by the site's configuration
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
uv run -m tapio.cli parse --site migri

# Parse the TE Services site
uv run -m tapio.cli parse --site te_palvelut

# Parse the Kela site
uv run -m tapio.cli parse --site kela
```

The parse command has been simplified to require only the site parameter. Additional options such as `--domain` and `--config` are available but not required for most use cases.

Available sites include any defined in the parser configurations (`site_configs.yaml`). To see all available site configurations:

```bash
uv run -m tapio.cli info --list-site-configs
```

3. **Vectorize** the parsed Markdown content into ChromaDB for semantic search:
```bash
uv run -m tapio.cli vectorize
```

4. **Launch the RAG Chatbot** to interactively query the content:
```bash
uv run -m tapio.cli gradio-app
```

### RAG Chatbot Options

The RAG chatbot allows you to query information from your vectorized content using a local LLM through Ollama. The chatbot provides several configuration options:

```bash
# Quick start - launch with development server
uv run -m tapio.cli dev

# Long form - launch with default settings
uv run -m tapio.cli gradio-app

# Use a specific Ollama model
uv run -m tapio.cli gradio-app --model-name llama3.2:latest

# (The collection name is now set to the default from settings)

# Create a shareable link for the app
uv run -m tapio.cli gradio-app --share
```

### Parameters and Options

For detailed information about available parameters and options for any command:

```bash
uv run -m tapio.cli <command> --help
```

Available commands:
- `crawl`: Crawl websites using site configurations and save HTML content
- `parse`: Parse HTML files into structured Markdown (simplified command, requires only `--site` parameter)
- `vectorize`: Vectorize parsed Markdown into ChromaDB (simplified command, uses defaults for directories and collection name)
- `gradio-app`: Launch the Gradio RAG chatbot interface (simplified command, uses defaults for collection name and database directory)
- `info`: Show information about available commands

To view available site configurations for parsing:

```bash
# List all available sites
uv run -m tapio.cli info --list-site-configs

# Show detailed configuration for a specific site
uv run -m tapio.cli info --show-site-config migri
```

## End-to-End Workflow Example: Migri Site

Here's a complete workflow for crawling, parsing, and querying the Finnish Immigration Service website:

### 1. Crawl the Migri Website

```bash
uv run -m tapio.cli crawl migri --depth 2
```

This will use the Migri site configuration to determine the base URL, save HTML files in `content/crawled/migri.fi/`, and create a URL mappings file.

### 2. Parse the Migri Content

```bash
uv run -m tapio.cli parse --site migri
```

This will automatically:
- Process all HTML files in the `migri.fi` directory (determined from the site's base URL)
- Apply Migri's content selectors to extract the relevant content
- Convert the HTML to Markdown using site-specific configuration
- Save the parsed files in `content/parsed/migri/`

### 3. Vectorize and Query

```bash
# Vectorize the content
uv run -m tapio.cli vectorize

# Launch the chatbot
uv run -m tapio.cli gradio-app
```

## Site Configurations

The parser uses site-specific configurations to extract content correctly from different websites. These configurations are defined in `tapio/config/site_configs.yaml`.

### Configuration Structure

Each site configuration includes:

```yaml
sites:
  migri:                                    # Site key used with --site
    site_name: "migri"                      # Name for output directories and logs
    base_url: "https://migri.fi"            # Base URL for converting relative links (optional, default: "https://example.com")
                                            # The base directory is automatically derived from this URL (e.g., "migri.fi")
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

### Required and Optional Fields

The `SiteParserConfig` has the following fields:
- Required fields:
  - `site_name`: A unique identifier for the site
  - `content_selectors`: At least one XPath selector to extract content

- Optional fields with defaults:
  - `base_url`: URL used for converting relative links to absolute URLs (default: "https://example.com").
    The base directory is automatically derived from this URL (e.g., "migri.fi" for "https://migri.fi").
  - `title_selector`: XPath selector for page title (default: "//title")
  - `fallback_to_body`: Whether to use the entire body if no content selectors match (default: true)
  - `description`: Description of the site (default: None)
  - `markdown_config`: HTML-to-Markdown conversion settings (defaults to the base HtmlToMarkdownConfig)

### Adding a New Site

To add support for a new website:

1. Determine the site's structure by examining a few pages
2. Identify the appropriate XPath selectors for title and main content
3. Add a new entry to `site_configs.yaml` with the required fields
4. Use the unique site key with the parse command

For example, to add support for a hypothetical "example.com":

```yaml
sites:
  # ... existing site configurations ...
  example:
    site_name: "example"
    base_url: "https://example.com"  # Base directory will automatically be "example.com"
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
uv run -m tapio.cli crawl https://example.com --depth 2

# Parse using the new configuration
uv run -m tapio.cli parse --site example
```

## Global Configuration Settings

The application uses a central configuration module (`tapio/config/settings.py`) that defines common settings used across different components:

```python
# Default directory paths
DEFAULT_DIRS = {
    "CRAWLED_DIR": "content/crawled",  # Directory for storing crawled HTML content
    "PARSED_DIR": "content/parsed",    # Directory for storing parsed Markdown content
    "CHROMA_DIR": "chroma_db",         # Directory for storing ChromaDB vector database
}
```

To modify these settings, edit the `settings.py` file. This ensures consistent path usage across the codebase.

## Contributing

If you'd like to contribute to this project, please see our [Contributing Guide](CONTRIBUTING.md) for details on our code of conduct, development process, and how to submit pull requests.

## License
This project is licensed under the European Union Public License version 1.2. See the LICENSE file for more details.
