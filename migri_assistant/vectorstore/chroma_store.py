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
        # Handle case where embedding is None (will be added later)
        if embedding is None:
            # Store without embeddings for now
            self.collection.add(
                ids=[document_id],
                metadatas=[metadata],
                documents=[metadata.get("content", "")],
            )
        else:
            self.collection.add(
                ids=[document_id],
                embeddings=[embedding],
                metadatas=[metadata],
                documents=[metadata.get("content", "")],
            )

    def get_document(self, document_id: str):
        return self.collection.get(ids=[document_id])

    def query(self, embedding: list, n_results: int = 5):
        return self.collection.query(query_embeddings=[embedding], n_results=n_results)

    def update_embeddings(self, document_id: str, embedding: list):
        """Update the embedding for an existing document"""
        self.collection.update(ids=[document_id], embeddings=[embedding])
