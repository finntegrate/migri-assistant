# Migri Assistant

## Overview
Migri Assistant is an AI-powered web scraping tool designed to extract information from websites, specifically tailored for knowledge from Migri.fi. It utilizes Scrapy for efficient web scraping and ChromaDB for managing vector embeddings of the scraped data.

## Features
- Scrapes web pages to a configurable depth
- Intelligently extracts main content from web pages
- Outputs results in a structured format suitable for vector embeddings
- Integrates with ChromaDB for storing and retrieving embeddings
- Configurable domain restrictions and depth control

## Installation and Setup

### Prerequisites
- Python 3.12 or higher
- [uv](https://github.com/astral-sh/uv) - Fast Python package installer and resolver

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
uv sync
```

## Usage

### Running the CLI

After installation, you can use the CLI in two ways:

1. Using the entry point:
```bash
migri-scrape scrape https://migri.fi/en/home
```

2. Using uv run:
```bash
uv run -m migri_assistant.cli scrape https://migri.fi/en/home
```

### Getting Help with CLI Commands

The CLI is self-documenting. To view available commands and options:

1. Show general help and available commands:
```bash
uv run -m migri_assistant.cli --help
```

2. Get detailed help for a specific command (e.g., the "scrape" command):
```bash
uv run -m migri_assistant.cli scrape --help
```

This will display all available options, their descriptions, default values, and usage examples.

### Examples

1. Scrape a website with depth 2 (initial page plus links from that page):
```bash
uv run -m migri_assistant.cli scrape https://migri.fi --depth 2
```

2. Scrape with domain restriction and save results:
```bash
uv run -m migri_assistant.cli scrape https://migri.fi --depth 3 --domain migri.fi --output migri_data.json
```

3. Get information about available commands:
```bash
uv run -m migri_assistant.cli info
```

## Project Structure
```
migri-assistant
├── migri_assistant
│   ├── __init__.py
│   ├── cli.py
│   ├── config.py
│   ├── settings.py
│   ├── scrapers
│   │   ├── __init__.py
│   │   ├── base_scraper.py
│   │   └── scrapy_scraper.py
│   ├── spiders
│   │   ├── __init__.py
│   │   └── web_spider.py
│   ├── models
│   │   ├── __init__.py
│   │   └── document.py
│   └── vectorstore
│       ├── __init__.py
│       └── chroma_store.py
├── scrapy.cfg
├── pyproject.toml
└── README.md
```

## Further Development

After scraping, you can use the stored data with the ChromaDB integration:

```python
from migri_assistant.vectorstore.chroma_store import ChromaStore

# Initialize the ChromaDB store
store = ChromaStore(collection_name="migri_documents")

# Query the store
results = store.query(embedding=your_embedding_vector, n_results=5)
```

## Contributing
Contributions are welcome! Please open an issue or submit a pull request for any enhancements or bug fixes.

## License
This project is licensed under the MIT License. See the LICENSE file for more details.
