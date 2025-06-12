"""Document retrieval service for the Tapio Assistant."""

import logging
from typing import Any

from tapio.vectorstore.chroma_store import ChromaStore

# Configure logging
logger = logging.getLogger(__name__)


class DocumentRetrievalService:
    """Service for retrieving relevant documents from the vector store."""

    def __init__(
        self,
        collection_name: str = "migri_docs",
        persist_directory: str = "chroma_db",
        num_results: int = 5,
    ):
        """Initialize the document retrieval service.

        Args:
            collection_name: Name of the ChromaDB collection
            persist_directory: Directory where the ChromaDB database is stored
            num_results: Number of documents to retrieve from the vector store
        """
        self.num_results = num_results

        # Initialize the vector store
        self.vector_store = ChromaStore(
            collection_name=collection_name,
            persist_directory=persist_directory,
        )

        logger.info(
            f"Initialized document retrieval service with collection '{collection_name}'",
        )

    def retrieve_documents(self, query_text: str) -> list[Any]:
        """Retrieve relevant documents for the given query.

        Args:
            query_text: The user's query

        Returns:
            List of retrieved documents
        """
        try:
            logger.info(f"Retrieving documents for query: {query_text}")
            retrieved_docs = self.vector_store.query(
                query_text=query_text,
                n_results=self.num_results,
            )
            logger.info(f"Retrieved {len(retrieved_docs)} documents")
            return retrieved_docs
        except Exception as e:
            logger.error(f"Error retrieving documents: {e}")
            return []

    def format_documents_as_context(self, documents: list[Any]) -> str:
        """Format retrieved documents as context for LLM input.

        Args:
            documents: List of retrieved documents

        Returns:
            Formatted string containing document content for LLM context
        """
        if not documents:
            return ""

        context_docs = []
        for doc in documents:
            # Extract content for context
            if hasattr(doc, "page_content"):
                context_docs.append(doc.page_content)

        return "\n\n".join(context_docs)

    def format_documents_for_display(self, documents: list[Any]) -> str:
        """Format retrieved documents for user display.

        Args:
            documents: List of retrieved documents

        Returns:
            Formatted string containing document information for display
        """
        if not documents:
            return "No relevant documents found."

        formatted_docs = []
        for i, doc in enumerate(documents):
            # Extract metadata
            metadata = doc.metadata if hasattr(doc, "metadata") else {}
            source = metadata.get(
                "source_url",
                metadata.get("url", "Unknown source"),
            )
            title = metadata.get("title", f"Document {i + 1}")

            # Format the document with metadata
            doc_content = (
                doc.page_content
                if hasattr(
                    doc,
                    "page_content",
                )
                else str(doc)
            )
            formatted_doc = f"### {title}\n**Source**: {source}\n\n{doc_content}\n\n"
            formatted_docs.append(formatted_doc)

        return "\n".join(formatted_docs)
