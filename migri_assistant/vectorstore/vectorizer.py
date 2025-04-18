"""Vectorize markdown content into ChromaDB."""

import logging
import os

from migri_assistant.utils.embedding_utils import EmbeddingGenerator
from migri_assistant.utils.markdown_utils import find_markdown_files, read_markdown_file
from migri_assistant.vectorstore.chroma_store import ChromaStore

logger = logging.getLogger(__name__)


class MarkdownVectorizer:
    """Vectorize markdown content and store in ChromaDB."""

    def __init__(
        self,
        collection_name: str,
        persist_directory: str = "chroma_db",
        model_name: str = "all-MiniLM-L6-v2",
    ):
        """
        Initialize the vectorizer.

        Args:
            collection_name: Name of the ChromaDB collection to use
            persist_directory: Directory to persist the ChromaDB database
            model_name: Name of the embedding model to use
        """
        self.embedding_generator = EmbeddingGenerator(model_name=model_name)
        self.store = ChromaStore(
            collection_name=collection_name, persist_directory=persist_directory
        )

    def process_directory(
        self, input_dir: str, domain_filter: str | None = None, batch_size: int = 20
    ) -> int:
        """
        Process all markdown files in a directory.

        Args:
            input_dir: Directory containing markdown files
            domain_filter: Optional filter for domain
            batch_size: Number of files to process in a batch

        Returns:
            Number of files successfully processed
        """
        # Find all markdown files
        markdown_files = find_markdown_files(input_dir, domain_filter)
        total_files = len(markdown_files)

        logger.info(f"Found {total_files} markdown files to process")

        # Process files in batches
        processed_count = 0
        for i in range(0, total_files, batch_size):
            batch = markdown_files[i : i + batch_size]
            self._process_batch(batch)
            processed_count += len(batch)
            logger.info(f"Processed {processed_count}/{total_files} files")

        return processed_count

    def _process_batch(self, file_paths: list[str]):
        """
        Process a batch of markdown files.

        Args:
            file_paths: List of paths to markdown files
        """
        contents = []
        metadatas = []
        ids = []

        for file_path in file_paths:
            # Extract document ID from filename
            doc_id = os.path.splitext(os.path.basename(file_path))[0]

            # Read markdown file
            metadata, content = read_markdown_file(file_path)

            if content:
                ids.append(doc_id)
                contents.append(content)
                metadatas.append(metadata)

        if not contents:
            return

        # Generate embeddings in batch
        embeddings = self.embedding_generator.generate_batch(contents)

        # Store documents with embeddings in ChromaDB
        for i, (doc_id, content, embedding, metadata) in enumerate(
            zip(ids, contents, embeddings, metadatas)
        ):
            metadata["content"] = content  # Store content in metadata for retrieval
            self.store.add_document(
                document_id=doc_id, embedding=embedding, metadata=metadata
            )

    def process_file(self, file_path: str) -> bool:
        """
        Process a single markdown file.

        Args:
            file_path: Path to markdown file

        Returns:
            True if successful, False otherwise
        """
        try:
            # Extract document ID from filename
            doc_id = os.path.splitext(os.path.basename(file_path))[0]

            # Read markdown file
            metadata, content = read_markdown_file(file_path)

            if not content:
                logger.warning(f"Empty content in {file_path}")
                return False

            # Generate embedding
            embedding = self.embedding_generator.generate(content)

            if not embedding:
                logger.warning(f"Failed to generate embedding for {file_path}")
                return False

            # Store in ChromaDB
            metadata["content"] = content  # Store content in metadata for retrieval
            self.store.add_document(
                document_id=doc_id, embedding=embedding, metadata=metadata
            )

            return True
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            return False
