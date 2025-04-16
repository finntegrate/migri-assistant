# Migri Assistant

## Overview
Migri Assistant is a web scraping tool designed to extract information from websites, specifically tailored for knowledge from Migri.fi. It utilizes Scrapy for efficient web scraping and outputs content as Markdown files with frontmatter metadata for easy processing.

## Features
- Scrapes web pages to a configurable depth
- Intelligently extracts main content from web pages
- Outputs results as Markdown files with YAML frontmatter metadata
- Also preserves original HTML content for reference
- Generates an index of all scraped pages
- Configurable domain restrictions and depth control
- Tracks PDF links for later processing

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
uv run -m migri_assistant.cli scrape https://migri.fi/en/home -d 1 -o scraped_pages
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

2. Scrape with domain restriction and custom output directory:
```bash
uv run -m migri_assistant.cli scrape https://migri.fi --depth 3 --domain migri.fi --output-dir migri_content
```

3. Scrape and save metadata results separately:
```bash
uv run -m migri_assistant.cli scrape https://migri.fi --output-dir content --results metadata.json
```

4. Get information about available commands:
```bash
uv run -m migri_assistant.cli info
```

5. Scrape a specific website, like Migri.fi

```bash
python -m migri_assistant.cli scrape https://migri.fi --use-migri-scraper -o scraped_pages/migri.fi
```

## Output Format

The scraper creates:

1. **Markdown files** with YAML frontmatter containing:
   - URL
   - Title
   - Source domain
   - Crawl timestamp
   - Content type
   - Depth of the page in the crawl

   Example:
   ```markdown
   ---
   url: https://example.com/page
   title: Example Page
   source_domain: example.com
   crawl_timestamp: 2023-04-15T12:34:56
   content_type: text/html
   depth: 1
   ---

   # Example Page

   This is the content of the page...
   ```

2. **HTML files** containing the original HTML content for reference
3. **Index file** (index.md) linking to all scraped pages
4. **PDF tracking file** listing URLs of PDF documents found during scraping

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

## Processing the Output

After scraping, you can process the Markdown files for various purposes:

```python
from pathlib import Path
import yaml
import markdown

# Read a Markdown file with frontmatter
def read_markdown_with_frontmatter(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split frontmatter and markdown content
    if content.startswith('---'):
        _, frontmatter, markdown_content = content.split('---', 2)
        metadata = yaml.safe_load(frontmatter)
        return metadata, markdown_content.strip()
    else:
        return {}, content

# Process all markdown files in a directory
def process_markdown_files(directory):
    markdown_files = Path(directory).glob('**/*.md')
    
    for file_path in markdown_files:
        # Skip the index file
        if file_path.name == 'index.md':
            continue
            
        metadata, content = read_markdown_with_frontmatter(file_path)
        
        # Now you can process the content and metadata
        print(f"Processing {metadata.get('title')}, URL: {metadata.get('url')}")
        
        # Example: Convert markdown to HTML
        html_content = markdown.markdown(content)
        
        # Do something with the content...
```

## Contributing
Contributions are welcome! Please open an issue or submit a pull request for any enhancements or bug fixes.

## License
This project is licensed under the MIT License. See the LICENSE file for more details.
