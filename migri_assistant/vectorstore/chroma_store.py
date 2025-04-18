"""ChromaDB vector store abstraction using LangChain."""

import logging
from typing import Any

from langchain.vectorstores.chroma import Chroma
from langchain_community.embeddings import SentenceTransformerEmbeddings

logger = logging.getLogger(__name__)


class ChromaStore:
    """LangChain-based ChromaDB vector store abstraction."""

    def __init__(self, collection_name: str, persist_directory: str = "chroma_db"):
        """
        Initialize the ChromaDB vector store.

        Args:
            collection_name: Name of the ChromaDB collection
            persist_directory: Directory to persist the ChromaDB database
        """
        # Initialize embeddings
        self.embeddings = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")

        # Initialize the vector store
        self.vector_db = Chroma(
            collection_name=collection_name,
            embedding_function=self.embeddings,
            persist_directory=persist_directory,
        )

        logger.debug(f"Initialized ChromaStore with collection: {collection_name}")

    def add_document(
        self,
        document_id: str,
        embedding: list[float] | None = None,
        metadata: dict[str, Any] = None,
    ):
        """
        Add a document to the vector store.

        This method is maintained for backward compatibility but uses the langchain Chroma
        implementation internally.

        Args:
            document_id: Unique identifier for the document
            embedding: Optional pre-computed embedding vector
            metadata: Document metadata
        """
        try:
            # Extract content from metadata if available
            document_text = metadata.get("content", "")

            # If content is missing from metadata but available elsewhere, try to find it
            if not document_text and hasattr(metadata, "get"):
                # Look for content in other common field names
                for field in ["text", "body", "page_content", "full_text"]:
                    if field in metadata:
                        document_text = metadata[field]
                        break

            # Ensure we have some text content
            if not document_text:
                logger.warning(f"No content found for document {document_id}")
                document_text = f"Empty document: {document_id}"

            # Create document dictionary with IDs
            # Note: LangChain's Chroma will compute embeddings automatically if not provided
            self.vector_db.add_texts(
                texts=[document_text], metadatas=[metadata], ids=[document_id]
            )

            logger.debug(f"Added document {document_id} to vector store")

        except Exception as e:
            logger.error(f"Failed to add document {document_id}: {e}")
            raise

    def query(self, query_text: str, n_results: int = 5):
        """
        Query the vector store by text.

        Args:
            query_text: Text to search for
            n_results: Number of results to return

        Returns:
            List of documents most similar to the query
        """
        try:
            results = self.vector_db.similarity_search(query=query_text, k=n_results)
            return results
        except Exception as e:
            logger.error(f"Failed to query vector store: {e}")
            return []

    def query_with_embedding(self, embedding: list[float], n_results: int = 5):
        """
        Query the vector store by embedding.

        Args:
            embedding: Embedding vector to search with
            n_results: Number of results to return

        Returns:
            List of documents most similar to the query
        """
        try:
            # Use the underlying Chroma client for this more specialized query
            collection = self.vector_db._collection
            results = collection.query(
                query_embeddings=[embedding], n_results=n_results
            )
            return results
        except Exception as e:
            logger.error(f"Failed to query vector store with embedding: {e}")
            return []

    def get_document(self, document_id: str):
        """
        Get a document by ID.

        Args:
            document_id: ID of the document to retrieve

        Returns:
            The document if found
        """
        try:
            # Use the underlying Chroma collection
            collection = self.vector_db._collection
            return collection.get(ids=[document_id])
        except Exception as e:
            logger.error(f"Failed to get document {document_id}: {e}")
            return None
