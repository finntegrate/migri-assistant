# Tapio

Tapio is a tool designed to extract, process, and query information from multiple websites, including Migri.fi (Finnish Immigration Service). It provides end-to-end RAG (Retrieval Augmented Generation) capabilities including web crawling, content parsing, vectorization, and an interactive chatbot interface.

- [Tapio](#tapio)
  - [Key Demographics](#key-demographics)
  - [Needs](#needs)
  - [Features](#features)
  - [Installation and Setup](#installation-and-setup)
    - [Prerequisites](#prerequisites)
    - [Setting up](#setting-up)
    - [Configuration](#configuration)
  - [Usage](#usage)
    - [Using the CLI](#using-the-cli)
      - [Discovering CLI Commands](#discovering-cli-commands)
      - [Listing Available Site Configurations](#listing-available-site-configurations)
  - [Basic Workflow Example](#basic-workflow-example)
  - [Site Configurations](#site-configurations)
    - [Configuration Structure](#configuration-structure)
    - [Required and Optional Fields](#required-and-optional-fields)
    - [Adding a New Site](#adding-a-new-site)
  - [Global Configuration Settings](#global-configuration-settings)
  - [Contributing](#contributing)
  - [License](#license)


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
- Provides a Tapio RAG chatbot interface for querying content
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

### Configuration

The parser uses site-specific configurations to extract content correctly from different websites. These configurations are defined in `tapio/config/site_configs.yaml`.

When you run the `parse` command with just the `--site` parameter (e.g., `uv run -m tapio.cli parse --site migri`), the parser automatically:
1. Determines the base directory from the site's configuration
2. Processes only HTML files from that directory
3. Applies the appropriate content selectors and markdown conversion rulestion) capabilities including web crawling, content parsing, vectorization, and an interactive chatbot interface.

## Usage

### Using the CLI

Tapio features a comprehensive CLI with built-in documentation. The basic workflow involves four main steps:

1. **Crawl** websites to collect content
2. **Parse** HTML into structured Markdown
3. **Vectorize** content for semantic search
4. **Query** content using the Tapio app interface

#### Discovering CLI Commands

To see all available commands:

```bash
uv run -m tapio.cli --help
```

For detailed help on any specific command:

```bash
uv run -m tapio.cli <command> --help
```

For example:
```bash
uv run -m tapio.cli tapio-app --help
```

#### Listing Available Site Configurations

To view all sites that can be crawled or parsed:

```bash
uv run -m tapio.cli list-sites
```

For detailed site configuration information:

```bash
uv run -m tapio.cli list-sites --verbose
```

The CLI provides comprehensive help text, default values, and option descriptions, eliminating the need to reference this documentation for command specifics.

## Basic Workflow Example

Here's a simplified example of the end-to-end workflow using the Finnish Immigration Service (Migri) website:

```bash
# Step 1: Crawl website content
uv run -m tapio.cli crawl migri

# Step 2: Parse HTML to structured Markdown
uv run -m tapio.cli parse --site migri

# Step 3: Vectorize content for semantic search
uv run -m tapio.cli vectorize

# Step 4: Launch the chatbot interface
uv run -m tapio.cli tapio-app
```

Each command has additional options that can be discovered using the `--help` flag. The CLI handles default directories and settings automatically.

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
