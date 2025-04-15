import json
import logging
from datetime import datetime
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
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose output"
    ),
):
    """
    Scrape a website to a configurable depth and store content in ChromaDB.

    Example:
        $ python -m migri_assistant.cli scrape https://migri.fi -d 2 -c migri_data
    """
    # Set log level based on verbose flag
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    typer.echo(f"🕸️ Starting web scraper on {url} with depth {depth}")

    try:
        # Initialize scraper
        scraper = ScrapyScraper(collection_name=collection)

        # Start scraping
        with typer.progressbar(length=100, label="Scraping website") as progress:
            # Update progress periodically (approximate since we don't know total pages)
            progress.update(10)
            results = scraper.scrape(
                url=url, depth=depth, allowed_domains=allowed_domains
            )
            progress.update(90)

        # Output information
        typer.echo(f"✅ Scraping completed! Processed {len(results)} pages.")

        # Save results to file if requested
        if output:
            # Create directory if it doesn't exist
            output.parent.mkdir(parents=True, exist_ok=True)

            # Add timestamp to results
            results_with_meta = {
                "timestamp": datetime.now().isoformat(),
                "url": url,
                "depth": depth,
                "collection": collection,
                "pages_scraped": len(results),
                "results": results,
            }

            # Save to file
            with open(output, "w", encoding="utf-8") as f:
                json.dump(results_with_meta, f, indent=2, ensure_ascii=False)

            typer.echo(f"📄 Results saved to {output}")

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
