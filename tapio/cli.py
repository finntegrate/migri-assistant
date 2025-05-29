import logging
from urllib.parse import urlparse

import typer

from tapio.config import ConfigManager
from tapio.config.settings import DEFAULT_CHROMA_COLLECTION, DEFAULT_DIRS
from tapio.crawler.runner import CrawlerRunner
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
    site: str = typer.Argument(..., help="Site configuration to use for crawling (e.g., 'migri')"),
    depth: int = typer.Option(
        1,
        "--depth",
        "-d",
        help="Maximum link-following depth (1 is just the provided URL)",
    ),
    config_path: str | None = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to custom parser configurations file",
    ),
    allowed_domains: list[str] | None = typer.Option(
        None,
        "--domain",
        "-D",
        help="Domains to restrict crawling to (defaults to site's domain)",
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

    This command takes a site identifier and uses the corresponding configuration
    from the site_configs.yaml file to determine the base URL for crawling.

    The crawler is interruptible - press Ctrl+C to stop and save current progress.

    Example:
        $ python -m tapio.cli crawl migri -d 2
    """
    # Set log level based on verbose flag
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Use ConfigManager for site configuration management
    try:
        config_manager = ConfigManager(config_path)
        available_sites = config_manager.list_available_sites()

        if site not in available_sites:
            typer.echo(f"❌ Unsupported site: {site}")
            typer.echo(f"Available sites: {', '.join(available_sites)}")
            raise typer.Exit(code=1)

        # Get the site configuration
        site_config = config_manager.get_site_config(site)
    except ValueError as e:
        typer.echo(f"❌ Error loading site configuration: {str(e)}")
        raise typer.Exit(code=1)

    # Get the base URL from the site configuration
    url = site_config.base_url

    # Extract domain from URL if allowed_domains is not provided
    if allowed_domains is None:
        # Convert HttpUrl to string for urlparse
        url_str = str(url)
        parsed_url = urlparse(url_str)
        allowed_domains = [parsed_url.netloc]

    # Get crawler settings from site configuration
    crawler_config = site_config.crawler_config
    delay = crawler_config.delay_between_requests
    max_concurrent = crawler_config.max_concurrent

    typer.echo(f"🕸️ Starting web crawler for {site} ({url}) with depth {depth}")
    typer.echo(f"💾 Saving HTML content to: {DEFAULT_DIRS['CRAWLED_DIR']}")
    typer.echo(f"⏱️ Using {delay}s delay between requests and max {max_concurrent} concurrent requests")

    try:
        # Initialize crawler runner
        runner = CrawlerRunner()

        typer.echo("⚠️ Press Ctrl+C at any time to interrupt crawling.")

        # Start crawling
        results = runner.run(
            start_urls=[str(url)],  # Convert HttpUrl to string
            depth=depth,
            allowed_domains=allowed_domains,
            output_dir=DEFAULT_DIRS["CRAWLED_DIR"],
            custom_settings={
                "delay_between_requests": delay,
                "max_concurrent": max_concurrent,
            },
        )

        # Output information
        typer.echo(f"✅ Crawling completed! Processed {len(results)} pages.")
        typer.echo(f"💾 Content saved as HTML files in {DEFAULT_DIRS['CRAWLED_DIR']}")

    except KeyboardInterrupt:
        typer.echo("\n🛑 Crawling interrupted by user")
        typer.echo("✅ Partial results have been saved")
        typer.echo(f"💾 Crawled content saved to {DEFAULT_DIRS['CRAWLED_DIR']}")
    except Exception as e:
        typer.echo(f"❌ Error during crawling: {str(e)}", err=True)
        raise typer.Exit(code=1)


@app.command()
def parse(
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
        $ python -m tapio.cli parse --site migri

        # With optional parameters (rarely needed)
        $ python -m tapio.cli parse --site te_palvelut --domain te-palvelut.fi
        $ python -m tapio.cli parse --site kela --config custom_configs.yaml
    """
    # Set log level based on verbose flag
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    typer.echo(f"📝 Starting HTML parsing from {DEFAULT_DIRS['CRAWLED_DIR']}")
    typer.echo(f"📄 Saving parsed content to: {DEFAULT_DIRS['PARSED_DIR']}")

    try:
        # Use ConfigManager for site configuration management
        config_manager = ConfigManager(config_path)
        available_sites = config_manager.list_available_sites()

        if site in available_sites:
            typer.echo(f"🔧 Using configuration for site: {site}")
            parser = Parser(
                site=site,
                input_dir=DEFAULT_DIRS["CRAWLED_DIR"],
                output_dir=DEFAULT_DIRS["PARSED_DIR"],
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
        typer.echo(f"✅ Parsing completed! Processed {len(results)} files.")
        typer.echo(f"📝 Content saved as Markdown files in {DEFAULT_DIRS['PARSED_DIR']}")
        typer.echo(f"📝 Index created at {DEFAULT_DIRS['PARSED_DIR']}/{parser.site}/index.md")

    except Exception as e:
        typer.echo(f"❌ Error during parsing: {str(e)}", err=True)
        raise typer.Exit(code=1)


@app.command()
def vectorize(
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
        $ python -m tapio.cli vectorize
    """
    # Set log level based on verbose flag
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    input_dir = DEFAULT_DIRS["PARSED_DIR"]
    db_dir = DEFAULT_DIRS["CHROMA_DIR"]
    collection_name = DEFAULT_CHROMA_COLLECTION

    typer.echo(f"🧠 Starting vectorization of parsed content from {input_dir}")
    typer.echo(f"💾 Vector database will be stored in: {db_dir}")
    typer.echo(f"🔤 Using embedding model: {embedding_model}")
    typer.echo(f"📑 Using collection name: {collection_name}")

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
    # Use ConfigManager directly instead of going through Parser
    config_manager = ConfigManager()

    if list_site_configs:
        # List all available site configurations
        site_configs = config_manager.list_available_sites()
        typer.echo("Available site configurations for parsing:")
        for site_name in site_configs:
            typer.echo(f"  - {site_name}")
        return

    if show_site_config:
        # Show details for a specific site configuration
        try:
            config = config_manager.get_site_config(show_site_config)
            typer.echo(f"Configuration for site: {show_site_config}")
            typer.echo(f"  Base URL: {config.base_url}")
            typer.echo(f"  Base directory: {config.base_dir}")
            typer.echo(f"  Description: {config.description}")
            typer.echo("  Content selectors:")
            for selector in config.content_selectors:
                typer.echo(f"    - {selector}")
            typer.echo(f"  Fallback to body: {config.fallback_to_body}")
        except ValueError:
            typer.echo(f"Error: Site configuration '{show_site_config}' not found")
        return

    # Show general information
    typer.echo("Tapio Assistant - Web crawling and parsing tool")
    typer.echo("\nAvailable commands:")
    typer.echo("  crawl      - Crawl websites and save HTML content")
    typer.echo("  parse      - Parse HTML files and convert to structured Markdown")
    typer.echo("  vectorize  - Vectorize parsed Markdown files and store in ChromaDB")
    typer.echo("  tapio-app  - Launch the Tapio web interface for querying with the RAG chatbot")
    typer.echo("  info       - Show this information")
    typer.echo("  dev        - Launch the development server for the Tapio Assistant chatbot")
    typer.echo("\nRun a command with --help for more information")


@app.command()
def tapio_app(
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
    """Launch the Tapio web interface for RAG-powered chatbot."""
    try:
        # Import the main function from the gradio_app module
        # TODO: Rename module from gradio_app to tapio_app in future PR
        from tapio.gradio_app import main as launch_gradio

        collection_name = DEFAULT_CHROMA_COLLECTION
        db_dir = DEFAULT_DIRS["CHROMA_DIR"]

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
    # Call the tapio_app function with default settings
    tapio_app(
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
        # Use ConfigManager directly for better configuration handling
        config_manager = ConfigManager(config_path)
        available_sites = config_manager.list_available_sites()

        typer.echo("📋 Available Site Configurations:")

        for site_name in available_sites:
            if verbose:
                try:
                    # Get detailed configuration for the site
                    site_config = config_manager.get_site_config(site_name)
                    typer.echo(f"\n📄 {site_name}:")
                    typer.echo(f"  Description: {site_config.description or 'No description'}")
                    typer.echo(f"  Title selector: {site_config.title_selector}")
                    typer.echo("  Content selectors:")
                    for selector in site_config.content_selectors:
                        typer.echo(f"    - {selector}")
                    typer.echo(f"  Fallback to body: {site_config.fallback_to_body}")
                    typer.echo("  Crawler configuration:")
                    typer.echo(f"    - Delay between requests: {site_config.crawler_config.delay_between_requests}s")
                    typer.echo(f"    - Max concurrent requests: {site_config.crawler_config.max_concurrent}")
                except ValueError:
                    # Skip sites with invalid configurations
                    typer.echo(f"\n❌ {site_name}: Invalid configuration")
            else:
                # Simpler output for non-verbose mode
                site_descriptions = config_manager.get_site_descriptions()
                description = f" - {site_descriptions[site_name]}" if site_name in site_descriptions else ""
                typer.echo(f"  • {site_name}{description}")

        typer.echo("\nUse these sites with the parse command, e.g.:")
        typer.echo(f"  $ python -m tapio.cli parse -s {available_sites[0]}")

    except Exception as e:
        typer.echo(f"❌ Error listing site configurations: {str(e)}", err=True)
        raise typer.Exit(code=1)


def run_tapio_app() -> None:
    """Entry point for the 'dev' command to launch the Tapio app with default settings."""
    # This function calls the tapio_app command with default settings
    tapio_app(
        model_name="llama3.2",
        share=False,
    )


if __name__ == "__main__":
    app()
