"""RAG (Retrieval Augmented Generation) service for the Tapio Assistant."""

import logging
from collections.abc import Generator
from typing import Any

from tapio.prompts import load_prompt
from tapio.services.llm_service import LLMService
from tapio.vectorstore.chroma_store import ChromaStore

# Configure logging
logger = logging.getLogger(__name__)


class RAGService:
    """RAG service for retrieving documents and generating responses."""

    def __init__(
        self,
        collection_name: str = "migri_docs",
        persist_directory: str = "chroma_db",
        model_name: str = "llama3.2",
        max_tokens: int = 1024,
        num_results: int = 5,
    ):
        """Initialize the RAG service.

        Args:
            collection_name: Name of the ChromaDB collection
            persist_directory: Directory where the ChromaDB database is stored
            model_name: Name of the LLM model to use
            max_tokens: Maximum number of tokens to generate
            num_results: Number of documents to retrieve from the vector store
        """
        self.num_results = num_results

        # Initialize the vector store
        self.vector_store = ChromaStore(
            collection_name=collection_name,
            persist_directory=persist_directory,
        )

        # Initialize the LLM service
        self.llm_service = LLMService(
            model_name=model_name,
            max_tokens=max_tokens,
        )

        logger.info(
            f"Initialized RAG service with collection '{collection_name}' and model '{model_name}'",
        )

    def query(
        self,
        query_text: str,
        history: list[dict[str, Any]] | None = None,
    ) -> tuple[str, list[Any]]:
        """Generate a response using RAG.

        Args:
            query_text: The user's query
            history: Chat history (optional)

        Returns:
            Tuple containing the response and the retrieved documents
        """
        try:
            # Query the vector store for relevant documents
            logger.info(f"Querying vector store with: {query_text}")
            retrieved_docs = self.vector_store.query(
                query_text=query_text,
                n_results=self.num_results,
            )

            # Format documents for the LLM prompt
            context_docs = []
            for doc in retrieved_docs:
                # Extract content and relevant metadata for context
                if hasattr(doc, "page_content"):
                    context_docs.append(doc.page_content)

            # Create a context-rich prompt
            context_text = "\n\n".join(context_docs)

            # Load the system prompt from the template file
            system_prompt = load_prompt("system_prompt")

            # Load the user query template and fill in the variables
            user_prompt = load_prompt("user_query", context=context_text, question=query_text)

            # Generate response using LLM service
            logger.info("Generating response with LLM")
            response = self.llm_service.generate_response(
                prompt=user_prompt,
                system_prompt=system_prompt,
            )

            # Cast the response to str to satisfy the return type
            return str(response), retrieved_docs  # type: ignore[return-value]
        except Exception as e:
            logger.error(f"Error generating RAG response: {e}")
            return (
                "I encountered an error while processing your query. Please try again.",
                [],
            )

    def query_stream(
        self,
        query_text: str,
        history: list[dict[str, Any]] | None = None,
    ) -> tuple[Generator[str, None, None], list[Any]]:
        """Generate a streaming response using RAG.

        Args:
            query_text: The user's query
            history: Chat history (optional)

        Returns:
            Tuple containing the response generator and the retrieved documents
        """
        try:
            # Query the vector store for relevant documents
            logger.info(f"Querying vector store with: {query_text}")
            retrieved_docs = self.vector_store.query(
                query_text=query_text,
                n_results=self.num_results,
            )

            # Format documents for the LLM prompt
            context_docs = []
            for doc in retrieved_docs:
                # Extract content and relevant metadata for context
                if hasattr(doc, "page_content"):
                    context_docs.append(doc.page_content)

            # Create a context-rich prompt
            context_text = "\n\n".join(context_docs)

            # Load the system prompt from the template file
            system_prompt = load_prompt("system_prompt")

            # Load the user query template and fill in the variables
            user_prompt = load_prompt("user_query", context=context_text, question=query_text)

            # Generate streaming response using LLM service
            logger.info("Generating streaming response with LLM")
            response_stream = self.llm_service.generate_response_stream(
                prompt=user_prompt,
                system_prompt=system_prompt,
            )

            return response_stream, retrieved_docs
        except Exception as e:
            logger.error(f"Error generating streaming RAG response: {e}")

            def error_generator() -> Generator[str, None, None]:
                yield "I encountered an error while processing your query. Please try again."

            return error_generator(), []

    def format_retrieved_documents(self, documents: list[Any]) -> str:
        """Format retrieved documents for display.

        Args:
            documents: List of retrieved documents

        Returns:
            Formatted string containing document information
        """
        if not documents:
            return "No relevant documents found."

        formatted_docs = []
        for i, doc in enumerate(documents):
            # Extract metadata
            metadata = doc.metadata if hasattr(doc, "metadata") else {}
            source = metadata.get("source_url", metadata.get("url", "Unknown source"))
            title = metadata.get("title", f"Document {i + 1}")

            # Format the document with metadata
            doc_content = doc.page_content if hasattr(doc, "page_content") else str(doc)
            formatted_doc = f"### {title}\n**Source**: {source}\n\n{doc_content}\n\n"
            formatted_docs.append(formatted_doc)

        return "\n".join(formatted_docs)

    def check_model_availability(self) -> bool:
        """Check if the LLM model is available.

        Returns:
            bool: True if the model is available, False otherwise
        """
        return self.llm_service.check_model_availability()
