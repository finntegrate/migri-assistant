import json
import logging
from pathlib import Path
from typing import List, Optional

import typer
from typing_extensions import Annotated

from migri_assistant.scrapers.scrapy_scraper import ScrapyScraper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Suppress the ONNX provider warnings
logging.getLogger("onnxruntime").setLevel(logging.ERROR)  # Suppress ONNX warnings
logging.getLogger("transformers").setLevel(
    logging.ERROR
)  # Suppress potential transformers warnings
logging.getLogger("chromadb").setLevel(logging.WARNING)  # Reduce ChromaDB debug noise

app = typer.Typer(help="Migri Assistant CLI - Web scraping and vector embeddings tool")


@app.command()
def scrape(
    url: str = typer.Argument(..., help="The URL to scrape content from"),
    depth: int = typer.Option(
        1,
        "--depth",
        "-d",
        help="Maximum link-following depth (1 is just the provided URL)",
    ),
    collection: str = typer.Option(
        "migri_documents",
        "--collection",
        "-c",
        help="ChromaDB collection name to store documents",
    ),
    allowed_domains: Optional[List[str]] = typer.Option(
        None,
        "--domain",
        "-D",
        help="Domains to restrict scraping to (defaults to URL's domain)",
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Path to save scraped results as JSON"
    ),
    pdf_output: Optional[Path] = typer.Option(
        "pdfs.json", "--pdf-output", "-p", help="Path to save found PDF URLs as JSON"
    ),
    chunk_size: int = typer.Option(
        1000, "--chunk-size", "-s", help="Maximum size of text chunks in characters"
    ),
    chunk_overlap: int = typer.Option(
        200, "--chunk-overlap", help="Number of characters to overlap between chunks"
    ),
    html_splitter: Annotated[
        str,
        typer.Option(
            "--html-splitter",
            "-H",
            help="HTML splitter type to use for chunking HTML content",
        ),
    ] = "semantic",
    disable_chunking: bool = typer.Option(
        False, "--disable-chunking", help="Disable text chunking"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
):
    """
    Scrape a website to a configurable depth and store content in ChromaDB.

    The scraper is interruptible - press Ctrl+C to stop and save current results.
    PDFs are not parsed but their URLs are saved to a separate file for later processing.

    HTML splitter options:
      - semantic: Preserves semantic structure like tables, lists (default)
      - header: Splits by headers (h1, h2, etc.)
      - section: Splits by document sections

    Example:
        $ python -m migri_assistant.cli scrape https://migri.fi -d 2 -c migri_data
    """
    # Set log level based on verbose flag
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    typer.echo(f"🕸️ Starting web scraper on {url} with depth {depth}")

    # Validate HTML splitter choice
    valid_splitters = ["semantic", "header", "section"]
    if html_splitter not in valid_splitters:
        typer.echo(f"❌ Invalid HTML splitter: {html_splitter}")
        typer.echo(f"Valid options are: {', '.join(valid_splitters)}")
        raise typer.Exit(code=1)

    # Adjust chunk size if chunking is disabled
    final_chunk_size = 0 if disable_chunking else chunk_size

    try:
        # Initialize scraper with chunking parameters
        scraper = ScrapyScraper(
            collection_name=collection,
            output_file=str(output) if output else None,
            pdf_output_file=str(pdf_output),
            chunk_size=final_chunk_size,
            chunk_overlap=chunk_overlap,
            html_splitter=html_splitter,
        )

        # Inform user about chunking settings
        if disable_chunking:
            typer.echo("📄 Text chunking is disabled")
        else:
            typer.echo(
                f"📄 Text will be chunked using {html_splitter} splitter with size={chunk_size}, overlap={chunk_overlap}"
            )

        typer.echo(
            "⚠️ Press Ctrl+C at any time to interrupt crawling and save current results"
        )

        # Start scraping
        results = scraper.scrape(url=url, depth=depth, allowed_domains=allowed_domains)

        # Output information
        typer.echo(f"✅ Scraping completed! Processed {len(results)} documents.")

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
        if output:
            typer.echo(f"📄 Results saved to {output}")

    except KeyboardInterrupt:
        typer.echo("\n🛑 Scraping interrupted by user")
        typer.echo("✅ Partial results have been saved")
        if output:
            typer.echo(f"📄 Results saved to {output}")
        if pdf_output and pdf_output.exists():
            typer.echo(f"📁 PDF URLs saved to {pdf_output}")
    except Exception as e:
        typer.echo(f"❌ Error during scraping: {str(e)}", err=True)
        raise typer.Exit(code=1)


@app.command()
def info():
    """Show information about the Migri Assistant and available commands."""
    typer.echo("Migri Assistant - Web scraping and vector embeddings tool")
    typer.echo("\nAvailable commands:")
    typer.echo("  scrape    - Scrape websites to a configurable depth")
    typer.echo("  info      - Show this information")
    typer.echo("\nRun a command with --help for more information")


if __name__ == "__main__":
    app()
