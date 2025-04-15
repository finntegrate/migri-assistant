import logging

import chromadb
from chromadb.config import Settings


class ChromaStore:
    def __init__(self, collection_name: str, persist_directory: str = "chroma_db"):
        # Using the new PersistentClient API instead of the deprecated Client with Settings
        self.client = chromadb.PersistentClient(
            path=persist_directory, settings=Settings(anonymized_telemetry=False)
        )

        # Get or create collection
        self.collection = self.client.get_or_create_collection(collection_name)

    def add_document(self, document_id: str, embedding: list, metadata: dict):
        # Extract content from metadata if available and not already in documents
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
            logging.warning(f"No content found for document {document_id}")
            document_text = f"Empty document: {document_id}"

        # Ensure document_text is a string
        if not isinstance(document_text, str):
            document_text = str(document_text)

        try:
            # Handle case where embedding is None (will be added later)
            if embedding is None:
                # Store with document text
                self.collection.add(
                    ids=[document_id], metadatas=[metadata], documents=[document_text]
                )
                logging.debug(f"Added document {document_id} without embeddings")
            else:
                self.collection.add(
                    ids=[document_id],
                    embeddings=[embedding],
                    metadatas=[metadata],
                    documents=[document_text],
                )
                logging.debug(f"Added document {document_id} with embeddings")
        except Exception as e:
            # Handle duplicates gracefully
            if "already exists" in str(e).lower():
                logging.warning(
                    f"Document {document_id} already exists, updating instead"
                )
                try:
                    self.collection.update(
                        ids=[document_id],
                        metadatas=[metadata],
                        documents=[document_text],
                    )
                except Exception as update_error:
                    logging.error(
                        f"Failed to update document {document_id}: {update_error}"
                    )
            else:
                # Re-raise other exceptions
                raise

    def get_document(self, document_id: str):
        return self.collection.get(ids=[document_id])

    def query(self, embedding: list, n_results: int = 5):
        return self.collection.query(query_embeddings=[embedding], n_results=n_results)

    def update_embeddings(self, document_id: str, embedding: list):
        """Update the embedding for an existing document"""
        self.collection.update(ids=[document_id], embeddings=[embedding])
