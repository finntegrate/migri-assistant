# Tapio

Tapio is a RAG (Retrieval Augmented Generation) tool for extracting, processing, and querying information from websites like Migri.fi (Finnish Immigration Service). It provides complete workflow capabilities including web crawling, content parsing, vectorization, and an interactive chatbot interface.

## Features
- **Multi-site support** - Configurable site-specific crawling and parsing
- **End-to-end pipeline** - Crawl → Parse → Vectorize → Query workflow
- **Local LLM integration** - Uses Ollama for private, local inference
- **Semantic search** - ChromaDB vector database for relevant content retrieval
- **Interactive chatbot** - Web interface for natural language queries
- **Flexible crawling** - Configurable depth and domain restrictions
- **Comprehensive testing** - Full test suite for reliability

## Target Use Cases

**Primary Users:** EU and non-EU citizens navigating Finnish immigration processes
- Students seeking education information
- Workers exploring employment options
- Families pursuing reunification
- Refugees and asylum seekers needing guidance

**Core Needs:**
- Finding relevant, accurate information quickly
- Practice conversations on specific topics (family reunification, work permits, etc.)

## Installation and Setup

### Prerequisites
- Python 3.10 or higher
- [uv](https://github.com/astral-sh/uv) - Fast Python package installer
- [Ollama](https://ollama.ai/) - For local LLM inference

### Quick Start

1. Clone and setup:
```bash
git clone https://github.com/Finntegrate/tapio.git
cd tapio
uv sync
```

2. Install required Ollama model:
```bash
ollama pull llama3.2
```

## Usage

### CLI Overview

Tapio provides a four-step workflow:

1. **crawl** - Collect HTML content from websites
2. **parse** - Convert HTML to structured Markdown
3. **vectorize** - Create vector embeddings for semantic search
4. **tapio-app** - Launch the interactive chatbot interface

Use `uv run -m tapio.cli --help` to see all commands or `uv run -m tapio.cli <command> --help` for command-specific options.

### Quick Example

Complete workflow for the Migri website:

```bash
# 1. Crawl content (uses site configuration)
uv run -m tapio.cli crawl migri --depth 2

# 2. Parse HTML to Markdown
uv run -m tapio.cli parse --site migri

# 3. Create vector embeddings
uv run -m tapio.cli vectorize

# 4. Launch chatbot interface
uv run -m tapio.cli tapio-app
```

### Available Sites

List configured sites:
```bash
uv run -m tapio.cli list-sites
```

View detailed site configurations:
```bash
uv run -m tapio.cli list-sites --verbose
```

## Site Configurations

Site configurations define how to crawl and parse specific websites. They're stored in `tapio/config/site_configs.yaml` and used by both crawl and parse commands.

### Configuration Structure

```yaml
sites:
  migri:
    base_url: "https://migri.fi"                # Used for crawling and converting relative links
    title_selector: "//title"                   # XPath for page titles
    content_selectors:                          # Priority-ordered content extraction
      - '//div[@id="main-content"]'
      - "//main"
      - "//article"
      - '//div[@class="content"]'
    fallback_to_body: true                      # Use <body> if selectors fail
    description: "Finnish Immigration Service website"
    markdown_config:                            # HTML-to-Markdown options
      ignore_links: false
      body_width: 0                             # No text wrapping
      protect_links: true
      unicode_snob: true
      ignore_images: false
      ignore_tables: false
    crawler_config:                             # Crawling behavior
      delay_between_requests: 1.0               # Seconds between requests
      max_concurrent: 3                         # Concurrent request limit
```

### Required vs Optional Fields

**Required:**
- `base_url` - Base URL for the site (used for crawling and link resolution)
- `content_selectors` - At least one XPath selector for content extraction

**Optional (with defaults):**
- `title_selector` - Page title XPath (default: "//title")
- `fallback_to_body` - Use full body content if selectors fail (default: true)
- `description` - Human-readable description
- `markdown_config` - HTML conversion settings (uses defaults if omitted)
- `crawler_config` - Crawling behavior settings (uses defaults if omitted)

### Adding New Sites

1. Analyze the target website's structure
2. Identify XPath selectors for content extraction
3. Add configuration to `site_configs.yaml`:

```yaml
sites:
  my_site:
    base_url: "https://example.com"
    content_selectors:
      - '//div[@class="main-content"]'
    description: "Example site configuration"
```

4. Use with commands:
```bash
uv run -m tapio.cli crawl my_site
uv run -m tapio.cli parse --site my_site
```

## Configuration

Tapio uses centralized configuration in `tapio/config/settings.py`:

```python
DEFAULT_DIRS = {
    "CRAWLED_DIR": "content/crawled",   # HTML storage
    "PARSED_DIR": "content/parsed",     # Markdown storage
    "CHROMA_DIR": "chroma_db",          # Vector database
}

DEFAULT_CHROMA_COLLECTION = "tapio"     # ChromaDB collection name
```

Site-specific configurations are in `tapio/config/site_configs.yaml` and automatically handle content extraction and directory organization based on the site's domain.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines, code style requirements, and how to submit pull requests.

## License

Licensed under the European Union Public License version 1.2. See LICENSE for details.
