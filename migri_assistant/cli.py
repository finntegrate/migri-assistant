import json
import logging
from pathlib import Path
from typing import List, Optional

import typer

from migri_assistant.scrapers.scrapy_scraper import ScrapyScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Suppress unnecessary warnings
logging.getLogger("onnxruntime").setLevel(logging.ERROR)  # Suppress ONNX warnings
logging.getLogger("transformers").setLevel(
    logging.ERROR
)  # Suppress potential transformers warnings
logging.getLogger("chromadb").setLevel(logging.WARNING)  # Reduce ChromaDB debug noise

app = typer.Typer(help="Migri Assistant CLI - Web scraping tool")


@app.command()
def scrape(
    url: str = typer.Argument(..., help="The URL to scrape content from"),
    depth: int = typer.Option(
        1,
        "--depth",
        "-d",
        help="Maximum link-following depth (1 is just the provided URL)",
    ),
    allowed_domains: Optional[List[str]] = typer.Option(
        None,
        "--domain",
        "-D",
        help="Domains to restrict scraping to (defaults to URL's domain)",
    ),
    output_dir: str = typer.Option(
        "scraped_content",
        "--output-dir",
        "-o",
        help="Directory to save scraped content as Markdown files",
    ),
    results_json: Optional[Path] = typer.Option(
        None, "--results", "-r", help="Path to save metadata results as JSON"
    ),
    pdf_output: Optional[Path] = typer.Option(
        "pdfs.json", "--pdf-output", "-p", help="Path to save found PDF URLs as JSON"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
):
    """
    Scrape a website to a configurable depth and save content as Markdown files.

    The scraper is interruptible - press Ctrl+C to stop and save current results.
    PDFs are not parsed but their URLs are saved to a separate file for later processing.

    Example:
        $ python -m migri_assistant.cli scrape https://migri.fi -d 2 -o migri_content
    """
    # Set log level based on verbose flag
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    typer.echo(f"🕸️ Starting web scraper on {url} with depth {depth}")
    typer.echo(f"📝 Saving scraped content as Markdown files to: {output_dir}")

    try:
        # Initialize scraper
        scraper = ScrapyScraper(
            output_dir=output_dir,
            output_file=str(results_json) if results_json else None,
            pdf_output_file=str(pdf_output),
        )

        typer.echo(
            "⚠️ Press Ctrl+C at any time to interrupt crawling and save current results"
        )

        # Start scraping
        results = scraper.scrape(url=url, depth=depth, allowed_domains=allowed_domains)

        # Output information
        typer.echo(f"✅ Scraping completed! Processed {len(results)} pages.")
        typer.echo(f"📝 Content saved as Markdown files in {output_dir}")
        typer.echo(f"📝 Index of all pages created at {output_dir}/index.md")

        # Check if PDF file was created and show info
        if pdf_output and pdf_output.exists():
            try:
                with open(pdf_output, "r") as f:
                    pdf_data = json.load(f)
                    pdf_count = pdf_data.get("pdf_count", 0)
                    typer.echo(
                        f"📁 Found {pdf_count} PDF files, URLs saved to {pdf_output}"
                    )
            except (json.JSONDecodeError, FileNotFoundError):
                pass

        # Output information about the results file
        if results_json:
            typer.echo(f"📄 Metadata saved to {results_json}")

    except KeyboardInterrupt:
        typer.echo("\n🛑 Scraping interrupted by user")
        typer.echo("✅ Partial results have been saved")
        typer.echo(f"📝 Scraped content saved to {output_dir}")
        if results_json:
            typer.echo(f"📄 Metadata saved to {results_json}")
        if pdf_output and pdf_output.exists():
            typer.echo(f"📁 PDF URLs saved to {pdf_output}")
    except Exception as e:
        typer.echo(f"❌ Error during scraping: {str(e)}", err=True)
        raise typer.Exit(code=1)


@app.command()
def info():
    """Show information about the Migri Assistant and available commands."""
    typer.echo("Migri Assistant - Web scraping tool")
    typer.echo("\nAvailable commands:")
    typer.echo("  scrape    - Scrape websites and save content as Markdown files")
    typer.echo("  info      - Show this information")
    typer.echo("\nRun a command with --help for more information")


if __name__ == "__main__":
    app()
