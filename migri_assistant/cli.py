import logging
from urllib.parse import urlparse

import typer

from migri_assistant.crawler.runner import ScrapyRunner
from migri_assistant.parsers.migri_parser import MigriParser
from migri_assistant.vectorstore.vectorizer import MarkdownVectorizer

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

app = typer.Typer(help="Migri Assistant CLI - Web crawling and parsing tool")


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
        "crawled_content",
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
):
    """
    Crawl a website to a configurable depth and save raw HTML content.

    The crawler is interruptible - press Ctrl+C to stop and save current progress.

    Example:
        $ python -m migri_assistant.cli crawl https://migri.fi -d 2 -o migri_content
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
        "crawled_content",
        "--input-dir",
        "-i",
        help="Directory containing HTML files to parse",
    ),
    output_dir: str = typer.Option(
        "parsed_content",
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
    site_type: str = typer.Option(
        "migri",
        "--site-type",
        "-s",
        help="Type of site to parse (determines which parser to use)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose output",
    ),
):
    """
    Parse HTML files previously crawled and convert to structured Markdown.

    This command reads HTML files from the specified input directory,
    extracts meaningful content, and saves it as Markdown files.

    Example:
        $ python -m migri_assistant.cli parse -i crawled_content -o parsed_content -s migri
    """
    # Set log level based on verbose flag
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    typer.echo(f"📝 Starting HTML parsing from {input_dir}")
    typer.echo(f"📄 Saving parsed content to: {output_dir}")

    try:
        # Initialize appropriate parser based on site_type
        if site_type == "migri":
            typer.echo("🔧 Using specialized Migri.fi parser")
            parser = MigriParser(input_dir=input_dir, output_dir=output_dir)
        else:
            typer.echo(f"❌ Unsupported site type: {site_type}")
            raise typer.Exit(code=1)

        # Start parsing
        results = parser.parse_all(domain=domain)

        # Output information
        typer.echo(f"✅ Parsing completed! Processed {len(results)} files.")
        typer.echo(f"📝 Content saved as Markdown files in {output_dir}")
        typer.echo(f"📝 Index created at {output_dir}/{site_type}/index.md")

    except Exception as e:
        typer.echo(f"❌ Error during parsing: {str(e)}", err=True)
        raise typer.Exit(code=1)


@app.command()
def vectorize(
    input_dir: str = typer.Option(
        "parsed_content",
        "--input-dir",
        "-i",
        help="Directory containing parsed Markdown files to vectorize",
    ),
    db_dir: str = typer.Option(
        "chroma_db",
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
):
    """
    Vectorize parsed Markdown files and store in a vector database (ChromaDB).

    This command reads parsed Markdown files with frontmatter, generates embeddings,
    and stores them in ChromaDB with associated metadata from the original source.

    Example:
        $ python -m migri_assistant.cli vectorize -i parsed_content -d chroma_db -c migri_docs
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
def info():
    """Show information about the Migri Assistant and available commands."""
    typer.echo("Migri Assistant - Web crawling and parsing tool")
    typer.echo("\nAvailable commands:")
    typer.echo("  crawl      - Crawl websites and save HTML content")
    typer.echo("  parse      - Parse HTML files and convert to structured Markdown")
    typer.echo("  vectorize  - Vectorize parsed Markdown files and store in ChromaDB")
    typer.echo("  gradio_app - Launch the Gradio web interface for querying with the RAG chatbot")
    typer.echo("  info       - Show this information")
    typer.echo("  dev        - Launch the development server for the Migri Assistant chatbot")
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
):
    """Launch the Gradio web interface for RAG-powered chatbot."""
    try:
        # Import the main function from the gradio_app module
        from migri_assistant.gradio_app import main as launch_gradio

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
def dev():
    """Launch the development server for the Migri Assistant chatbot."""
    typer.echo("🚀 Launching Migri Assistant chatbot development server...")
    # Call the gradio_app function with default settings
    gradio_app(
        collection_name="migri_docs",
        persist_directory="chroma_db",
        model_name="llama3.2",
        share=False,
    )


def run_gradio_app():
    """Entry point for the 'dev' command to launch the Gradio app with default settings."""
    # This function calls the gradio_app command with default settings
    gradio_app(
        collection_name="migri_docs",
        persist_directory="chroma_db",
        model_name="llama3.2",
        share=False,
    )


if __name__ == "__main__":
    app()
