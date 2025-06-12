"""RAG orchestrator service that coordinates document retrieval and LLM generation."""

import logging
from collections.abc import Generator
from typing import Any

from tapio.prompts import load_prompt
from tapio.services.document_retrieval_service import DocumentRetrievalService
from tapio.services.llm_service import LLMService

# Configure logging
logger = logging.getLogger(__name__)


class RAGOrchestrator:
    """Orchestrates document retrieval and LLM generation for RAG workflow."""

    def __init__(
        self,
        collection_name: str = "migri_docs",
        persist_directory: str = "chroma_db",
        model_name: str = "llama3.2",
        max_tokens: int = 1024,
        num_results: int = 5,
    ):
        """Initialize the RAG orchestrator.

        Args:
            collection_name: Name of the ChromaDB collection
            persist_directory: Directory where the ChromaDB database is stored
            model_name: Name of the LLM model to use
            max_tokens: Maximum number of tokens to generate
            num_results: Number of documents to retrieve from the vector store
        """
        # Initialize the document retrieval service
        self.doc_retrieval_service = DocumentRetrievalService(
            collection_name=collection_name,
            persist_directory=persist_directory,
            num_results=num_results,
        )

        # Initialize the LLM service
        self.llm_service = LLMService(
            model_name=model_name,
            max_tokens=max_tokens,
        )

        logger.info(
            f"Initialized RAG orchestrator with collection '{collection_name}' and model '{model_name}'",
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
            # Step 1: Retrieve relevant documents
            retrieved_docs = self.doc_retrieval_service.retrieve_documents(
                query_text,
            )

            # Step 2: Format documents as context for LLM
            context_text = self.doc_retrieval_service.format_documents_as_context(
                retrieved_docs,
            )

            # Step 3: Create prompts
            system_prompt = load_prompt("system_prompt")
            user_prompt = load_prompt(
                "user_query",
                context=context_text,
                question=query_text,
            )

            # Step 4: Generate response using LLM service
            logger.info("Generating response with LLM")
            response = self.llm_service.generate_response(
                prompt=user_prompt,
                system_prompt=system_prompt,
            )

            return str(response), retrieved_docs
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
            # Step 1: Retrieve relevant documents up front
            logger.info("Retrieving relevant documents")
            retrieved_docs = self.doc_retrieval_service.retrieve_documents(
                query_text,
            )

            # Step 2: Format documents as context for LLM
            context_text = self.doc_retrieval_service.format_documents_as_context(
                retrieved_docs,
            )

            # Step 3: Create prompts
            system_prompt = load_prompt("system_prompt")
            user_prompt = load_prompt(
                "user_query",
                context=context_text,
                question=query_text,
            )

            # Step 4: Create the streaming generator
            logger.info("Generating streaming response with LLM")

            def stream_generator() -> Generator[str, None, None]:
                llm_response_stream = self.llm_service.generate_response_stream(
                    prompt=user_prompt,
                    system_prompt=system_prompt,
                )
                try:
                    logger.info("Starting to consume LLM response stream")
                    # Stream the LLM response directly using yield from
                    yield from llm_response_stream

                except Exception:
                    logger.exception("Error in stream generator")
                    yield "I encountered an error while processing your query. Please try again."
                finally:
                    # Ensure proper cleanup of upstream generator
                    if hasattr(llm_response_stream, "close"):
                        llm_response_stream.close()

            return stream_generator(), retrieved_docs

        except Exception as e:
            logger.error(f"Error in query_stream setup: {e}")

            def error_generator() -> Generator[str, None, None]:
                yield "I encountered an error while processing your query. Please try again."

            return error_generator(), []

    def check_model_availability(self) -> bool:
        """Check if the LLM model is available.

        Returns:
            bool: True if the model is available, False otherwise
        """
        return self.llm_service.check_model_availability()

    def format_documents_for_display(self, documents: list[Any]) -> str:
        """Format retrieved documents for display.

        Args:
            documents: List of retrieved documents

        Returns:
            Formatted string containing document information
        """
        return self.doc_retrieval_service.format_documents_for_display(documents)
