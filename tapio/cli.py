import logging
from urllib.parse import urlparse

import typer

from tapio.config.settings import DEFAULT_DIRS
from tapio.crawler.runner import ScrapyRunner
from tapio.parser import Parser
from tapio.vectorstore.vectorizer import MarkdownVectorizer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Suppress unnecessary warnings
logging.getLogger("onnxruntime").setLevel(logging.ERROR)  # Suppress ONNX warnings
logging.getLogger("transformers").setLevel(
    logging.ERROR,
)  # Suppress potential transformers warnings
logging.getLogger("chromadb").setLevel(logging.WARNING)  # Reduce ChromaDB debug noise

app = typer.Typer(help="Tapio Assistant CLI - Web crawling and parsing tool")


@app.command()
def crawl(
    url: str = typer.Argument(..., help="The URL to crawl content from"),
    depth: int = typer.Option(
        1,
        "--depth",
        "-d",
        help="Maximum link-following depth (1 is just the provided URL)",
    ),
    allowed_domains: list[str] | None = typer.Option(
        None,
        "--domain",
        "-D",
        help="Domains to restrict crawling to (defaults to URL's domain)",
    ),
    output_dir: str = typer.Option(
        DEFAULT_DIRS["CRAWLED_DIR"],
        "--output-dir",
        "-o",
        help="Directory to save crawled HTML files",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose output",
    ),
) -> None:
    """
    Crawl a website to a configurable depth and save raw HTML content.

    The crawler is interruptible - press Ctrl+C to stop and save current progress.

    Example:
        $ python -m tapio.cli crawl https://migri.fi -d 2 -o migri_content
    """
    # Set log level based on verbose flag
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Extract domain from URL if allowed_domains is not provided
    if allowed_domains is None:
        parsed_url = urlparse(url)
        allowed_domains = [parsed_url.netloc]

    typer.echo(f"🕸️ Starting web crawler on {url} with depth {depth}")
    typer.echo(f"💾 Saving HTML content to: {output_dir}")

    try:
        # Initialize crawler runner
        runner = ScrapyRunner()

        typer.echo("⚠️ Press Ctrl+C at any time to interrupt crawling.")

        # Start crawling
        results = runner.run(
            start_urls=[url],
            depth=depth,
            allowed_domains=allowed_domains,
            output_dir=output_dir,
        )

        # Output information
        typer.echo(f"✅ Crawling completed! Processed {len(results)} pages.")
        typer.echo(f"💾 Content saved as HTML files in {output_dir}")

    except KeyboardInterrupt:
        typer.echo("\n🛑 Crawling interrupted by user")
        typer.echo("✅ Partial results have been saved")
        typer.echo(f"💾 Crawled content saved to {output_dir}")
    except Exception as e:
        typer.echo(f"❌ Error during crawling: {str(e)}", err=True)
        raise typer.Exit(code=1)


@app.command()
def parse(
    input_dir: str = typer.Option(
        DEFAULT_DIRS["CRAWLED_DIR"],
        "--input-dir",
        "-i",
        help="Directory containing HTML files to parse",
    ),
    output_dir: str = typer.Option(
        DEFAULT_DIRS["PARSED_DIR"],
        "--output-dir",
        "-o",
        help="Directory to save parsed content as Markdown files",
    ),
    domain: str | None = typer.Option(
        None,
        "--domain",
        "-d",
        help="Domain to parse (e.g. 'migri.fi'). If not provided, all domains are parsed.",
    ),
    site: str = typer.Option(
        "migri",
        "--site",
        "-s",
        help="Site to parse (loads appropriate configuration for content extraction)",
    ),
    config_path: str | None = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to custom parser configurations file",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose output",
    ),
) -> None:
    """
    Parse HTML files previously crawled and convert to structured Markdown.

    This command reads HTML files from the specified input directory, extracts meaningful content
    based on site-specific configurations, and saves it as Markdown files with YAML frontmatter.

    Configurations define which XPath selectors to use for extracting content and how to convert
    HTML to Markdown for different website types.

    Examples:
        $ python -m tapio.cli parse -s migri
        $ python -m tapio.cli parse -s te_palvelut -d te-palvelut.fi
        $ python -m tapio.cli parse -s kela -c custom_configs.yaml
    """
    # Set log level based on verbose flag
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    typer.echo(f"📝 Starting HTML parsing from {input_dir}")
    typer.echo(f"📄 Saving parsed content to: {output_dir}")

    try:
        # Check if the site is supported by listing available configurations
        available_sites = Parser.list_available_site_configs(config_path)

        if site in available_sites:
            typer.echo(f"🔧 Using configuration for site: {site}")
            parser = Parser(
                site=site,
                input_dir=input_dir,
                output_dir=output_dir,
                config_path=config_path,
            )
        else:
            typer.echo(f"❌ Unsupported site: {site}")
            typer.echo(f"Available sites: {', '.join(available_sites)}")
            raise typer.Exit(code=1)

        # Start parsing
        # Domain filtering is now handled by the parser based on its configuration
        results = parser.parse_all()

        # Output information
        site_name = parser.config.site_name if hasattr(parser, "config") else parser.site_name
        typer.echo(f"✅ Parsing completed! Processed {len(results)} files.")
        typer.echo(f"📝 Content saved as Markdown files in {output_dir}")
        typer.echo(f"📝 Index created at {output_dir}/{site_name}/index.md")

    except Exception as e:
        typer.echo(f"❌ Error during parsing: {str(e)}", err=True)
        raise typer.Exit(code=1)


@app.command()
def vectorize(
    input_dir: str = typer.Option(
        DEFAULT_DIRS["PARSED_DIR"],
        "--input-dir",
        "-i",
        help="Directory containing parsed Markdown files to vectorize",
    ),
    db_dir: str = typer.Option(
        DEFAULT_DIRS["CHROMA_DIR"],
        "--db-dir",
        "-d",
        help="Directory to store the ChromaDB database",
    ),
    collection_name: str = typer.Option(
        "migri_docs",
        "--collection",
        "-c",
        help="Name of the ChromaDB collection to create",
    ),
    domain: str | None = typer.Option(
        None,
        "--domain",
        "-D",
        help="Domain to filter by (e.g. 'migri.fi'). If not provided, all domains are processed.",
    ),
    embedding_model: str = typer.Option(
        "all-MiniLM-L6-v2",
        "--model",
        "-m",
        help="Name of the sentence-transformers model to use",
    ),
    batch_size: int = typer.Option(
        20,
        "--batch-size",
        "-b",
        help="Number of documents to process in each batch",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose output",
    ),
) -> None:
    """
    Vectorize parsed Markdown files and store in a vector database (ChromaDB).

    This command reads parsed Markdown files with frontmatter, generates embeddings,
    and stores them in ChromaDB with associated metadata from the original source.

    Example:
        $ python -m tapio.cli vectorize -i parsed_content -d chroma_db -c migri_docs
    """
    # Set log level based on verbose flag
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    typer.echo(f"🧠 Starting vectorization of parsed content from {input_dir}")
    typer.echo(f"💾 Vector database will be stored in: {db_dir}")
    typer.echo(f"🔤 Using embedding model: {embedding_model}")

    try:
        # Initialize vectorizer
        vectorizer = MarkdownVectorizer(
            collection_name=collection_name,
            persist_directory=db_dir,
            embedding_model_name=embedding_model,
            chunk_size=1000,
            chunk_overlap=200,
        )

        # Process all files in the directory
        typer.echo("⚙️ Processing markdown files...")
        count = vectorizer.process_directory(
            input_dir=input_dir,
            domain_filter=domain,
            batch_size=batch_size,
        )

        # Output information
        typer.echo(f"✅ Vectorization completed! Processed {count} files.")
        typer.echo(f"🔍 Vector database is ready for similarity search in {db_dir}")

    except Exception as e:
        typer.echo(f"❌ Error during vectorization: {str(e)}", err=True)
        raise typer.Exit(code=1)


@app.command()
def info(
    list_site_configs: bool = typer.Option(
        False,
        "--list-site-configs",
        "-l",
        help="List all available site configurations for parsing",
    ),
    show_site_config: str = typer.Option(
        None,
        "--show-site-config",
        "-s",
        help="Show detailed configuration for a specific site",
    ),
) -> None:
    """Show information about the Tapio Assistant and available commands."""
    if list_site_configs:
        # List all available site configurations
        site_configs = Parser.list_available_site_configs()
        typer.echo("Available site configurations for parsing:")
        for site_name in site_configs:
            typer.echo(f"  - {site_name}")
        return

    if show_site_config:
        # Show details for a specific site configuration
        config = Parser.get_site_config(show_site_config)
        if config:
            typer.echo(f"Configuration for site: {show_site_config}")
            typer.echo(f"  Site name: {config.site_name}")
            typer.echo(f"  Base URL: {config.base_url}")
            typer.echo(f"  Base directory: {config.base_dir}")
            typer.echo(f"  Description: {config.description}")
            typer.echo("  Content selectors:")
            for selector in config.content_selectors:
                typer.echo(f"    - {selector}")
            typer.echo(f"  Fallback to body: {config.fallback_to_body}")
        else:
            typer.echo(f"Error: Site configuration '{show_site_config}' not found")
        return

    # Show general information
    typer.echo("Tapio Assistant - Web crawling and parsing tool")
    typer.echo("\nAvailable commands:")
    typer.echo("  crawl      - Crawl websites and save HTML content")
    typer.echo("  parse      - Parse HTML files and convert to structured Markdown")
    typer.echo("  vectorize  - Vectorize parsed Markdown files and store in ChromaDB")
    typer.echo("  gradio_app - Launch the Gradio web interface for querying with the RAG chatbot")
    typer.echo("  info       - Show this information")
    typer.echo("  dev        - Launch the development server for the Tapio Assistant chatbot")
    typer.echo("\nRun a command with --help for more information")


@app.command()
def gradio_app(
    collection_name: str = typer.Option(
        "migri_docs",
        "--collection-name",
        "-c",
        help="Name of the ChromaDB collection to query",
    ),
    db_dir: str = typer.Option(
        "chroma_db",
        "--db-dir",
        "-d",
        help="Directory containing the ChromaDB database",
    ),
    model_name: str = typer.Option(
        "llama3.2",
        "--model-name",
        "-m",
        help="Ollama model to use for LLM inference",
    ),
    max_tokens: int = typer.Option(
        1024,
        "--max-tokens",
        "-t",
        help="Maximum number of tokens to generate",
    ),
    share: bool = typer.Option(
        False,
        "--share",
        help="Create a shareable link for the app",
    ),
) -> None:
    """Launch the Gradio web interface for RAG-powered chatbot."""
    try:
        # Import the main function from the gradio_app module
        from tapio.gradio_app import main as launch_gradio

        typer.echo(f"🚀 Starting Gradio app with {model_name} model")
        typer.echo(f"📚 Using ChromaDB collection '{collection_name}' from '{db_dir}'")

        if share:
            typer.echo("🔗 Creating a shareable link")

        # Launch the Gradio app with CLI parameters
        launch_gradio(
            collection_name=collection_name,
            persist_directory=db_dir,
            model_name=model_name,
            max_tokens=max_tokens,
            share=share,
        )

    except ImportError as e:
        typer.echo(f"❌ Error importing Gradio: {str(e)}", err=True)
        typer.echo("Make sure Gradio is installed with 'uv add gradio'")
        raise typer.Exit(code=1)
    except Exception as e:
        typer.echo(f"❌ Error launching Gradio app: {str(e)}", err=True)
        raise typer.Exit(code=1)


@app.command()
def dev() -> None:
    """Launch the development server for the Tapio Assistant chatbot."""
    typer.echo("🚀 Launching Tapio Assistant chatbot development server...")
    # Call the gradio_app function with default settings
    gradio_app(
        collection_name="migri_docs",
        db_dir="chroma_db",
        model_name="llama3.2",
        share=False,
    )


@app.command()
def list_sites(
    config_path: str | None = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to custom parser configurations file",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed information about each site configuration",
    ),
) -> None:
    """
    List available site configurations for the parser.

    This command lists all the available sites that can be used with the parse command.
    Use the --verbose flag to see detailed information about each site's configuration.
    """
    try:
        # Get available site configurations
        available_sites = Parser.list_available_site_configs(config_path)

        typer.echo("📋 Available Site Configurations:")

        for site_name in available_sites:
            if verbose:
                # Get detailed configuration for the site
                site_config = Parser.get_site_config(site_name, config_path)
                if site_config:
                    typer.echo(f"\n📄 {site_name}:")
                    typer.echo(f"  Site name: {site_config.site_name}")
                    typer.echo(f"  Description: {site_config.description or 'No description'}")
                    typer.echo(f"  Title selector: {site_config.title_selector}")
                    typer.echo("  Content selectors:")
                    for selector in site_config.content_selectors:
                        typer.echo(f"    - {selector}")
                    typer.echo(f"  Fallback to body: {site_config.fallback_to_body}")
            else:
                site_config = Parser.get_site_config(site_name, config_path)
                description = ""
                if site_config and site_config.description:
                    description = f" - {site_config.description}"
                typer.echo(f"  • {site_name}{description}")

        typer.echo("\nUse these sites with the parse command, e.g.:")
        typer.echo(f"  $ python -m tapio.cli parse -s {available_sites[0]}")

    except Exception as e:
        typer.echo(f"❌ Error listing site configurations: {str(e)}", err=True)
        raise typer.Exit(code=1)


def run_gradio_app() -> None:
    """Entry point for the 'dev' command to launch the Gradio app with default settings."""
    # This function calls the gradio_app command with default settings
    gradio_app(
        collection_name="migri_docs",
        db_dir="chroma_db",
        model_name="llama3.2",
        share=False,
    )


if __name__ == "__main__":
    app()
