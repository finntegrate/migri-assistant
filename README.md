# Migri Assistant

## Overview
Migri Assistant is a web crawling and parsing tool designed to extract information from websites, with specific functionality tailored for the Migri.fi website. It utilizes Scrapy for efficient web crawling and outputs content as HTML files with separate parsing capabilities.

## Features
- Crawls web pages to a configurable depth
- Saves raw HTML content with domain-based organization
- Parses HTML content into structured Markdown files
- Clean separation between crawling and parsing functionality
- Domain restriction and crawl depth control
- Comprehensive test suite

## Installation and Setup

### Prerequisites
- Python 3.10 or higher
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
uv sync --dev
```

## Usage

### Running the Crawler and Parser

The crawler and parser are separate commands, following a two-step process:

1. **Crawl** a website to retrieve and save HTML content:
```bash
uv run -m migri_assistant.cli crawl https://migri.fi/en/home --depth 2 --output-dir crawled_content
```

2. **Parse** the HTML content into structured Markdown:
```bash
uv run -m migri_assistant.cli parse --input-dir crawled_content --output-dir parsed_content
```

### Parameters and Options

For detailed information about available parameters and options:

```bash
uv run -m migri_assistant.cli crawl --help
uv run -m migri_assistant.cli parse --help
```

## Development

### Code Quality

We use [Ruff](https://docs.astral.sh/ruff/) for linting and formatting. To run the linter:

```bash
uv ruff .
```

To automatically fix issues:

```bash
uv ruff . --fix
```

To check formatting without fixing:

```bash
uv ruff . --check
```

### Running Tests

```bash
uv run pytest
```

## Project Structure

The project has been designed with a clear separation of concerns:

- `crawler/`: Module responsible for crawling websites and saving HTML content
- `parsers/`: Module responsible for parsing HTML content into structured formats
- `tests/`: Test suite for both crawler and parser modules

## License
This project is licensed under the Apache 2.0 License. See the LICENSE file for more details.
