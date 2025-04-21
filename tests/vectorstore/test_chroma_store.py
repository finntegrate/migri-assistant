"""Tests for the ChromaDB vector store abstraction."""

from unittest.mock import Mock, patch

import pytest

from migri_assistant.vectorstore.chroma_store import ChromaStore


class TestChromaStore:
    """Tests for the ChromaStore class."""

    @patch("migri_assistant.vectorstore.chroma_store.Chroma")
    @patch("migri_assistant.vectorstore.chroma_store.HuggingFaceEmbeddings")
    def test_init(self, mock_embeddings, mock_chroma):
        """Test initialization of the ChromaStore."""
        # Set up mocks
        mock_embedding_instance = Mock()
        mock_embeddings.return_value = mock_embedding_instance

        # Initialize ChromaStore
        _ = ChromaStore(
            collection_name="test_collection",
            persist_directory="test_dir",
        )

        # Check if embeddings and vector_db were initialized correctly
        mock_embeddings.assert_called_once_with(model_name="all-MiniLM-L6-v2")
        mock_chroma.assert_called_once_with(
            collection_name="test_collection",
            embedding_function=mock_embedding_instance,
            persist_directory="test_dir",
        )

    @patch("migri_assistant.vectorstore.chroma_store.Chroma")
    @patch("migri_assistant.vectorstore.chroma_store.HuggingFaceEmbeddings")
    def test_add_document_with_content(self, mock_embeddings, mock_chroma):
        """Test adding a document with content in metadata."""
        # Set up mocks
        mock_vector_db = Mock()
        mock_chroma.return_value = mock_vector_db

        # Initialize ChromaStore
        store = ChromaStore(collection_name="test_collection")

        # Test adding document with content in metadata
        metadata = {"content": "Test document content"}
        store.add_document(document_id="test_doc_1", metadata=metadata)

        # Check if vector_db.add_texts was called with correct arguments
        mock_vector_db.add_texts.assert_called_once_with(
            texts=["Test document content"],
            metadatas=[metadata],
            ids=["test_doc_1"],
        )

    @patch("migri_assistant.vectorstore.chroma_store.Chroma")
    @patch("migri_assistant.vectorstore.chroma_store.HuggingFaceEmbeddings")
    def test_add_document_alternate_content_fields(self, mock_embeddings, mock_chroma):
        """Test adding a document with content in alternate metadata fields."""
        # Set up mocks
        mock_vector_db = Mock()
        mock_chroma.return_value = mock_vector_db

        # Initialize ChromaStore
        store = ChromaStore(collection_name="test_collection")

        # Test with different content field names
        for field in ["text", "body", "page_content", "full_text"]:
            mock_vector_db.reset_mock()
            metadata = {field: f"Content in {field} field"}
            store.add_document(document_id=f"test_doc_{field}", metadata=metadata)

            # Check if vector_db.add_texts was called with correct arguments
            mock_vector_db.add_texts.assert_called_once_with(
                texts=[f"Content in {field} field"],
                metadatas=[metadata],
                ids=[f"test_doc_{field}"],
            )

    @patch("migri_assistant.vectorstore.chroma_store.Chroma")
    @patch("migri_assistant.vectorstore.chroma_store.HuggingFaceEmbeddings")
    def test_add_document_no_content(self, mock_embeddings, mock_chroma):
        """Test adding a document with no content in metadata."""
        # Set up mocks
        mock_vector_db = Mock()
        mock_chroma.return_value = mock_vector_db

        # Initialize ChromaStore
        store = ChromaStore(collection_name="test_collection")

        # Test adding document with no content in metadata
        metadata = {"other_field": "Other value"}
        store.add_document(document_id="test_doc_empty", metadata=metadata)

        # Check if empty document message was used
        mock_vector_db.add_texts.assert_called_once_with(
            texts=["Empty document: test_doc_empty"],
            metadatas=[metadata],
            ids=["test_doc_empty"],
        )

    @patch("migri_assistant.vectorstore.chroma_store.Chroma")
    @patch("migri_assistant.vectorstore.chroma_store.HuggingFaceEmbeddings")
    def test_add_document_exception(self, mock_embeddings, mock_chroma):
        """Test handling exceptions when adding a document."""
        # Set up mocks
        mock_vector_db = Mock()
        mock_vector_db.add_texts.side_effect = Exception("Test error")
        mock_chroma.return_value = mock_vector_db

        # Initialize ChromaStore
        store = ChromaStore(collection_name="test_collection")

        # Test adding document with exception
        metadata = {"content": "Test document content"}
        with pytest.raises(Exception, match="Test error"):
            store.add_document(document_id="test_doc", metadata=metadata)

    @patch("migri_assistant.vectorstore.chroma_store.Chroma")
    @patch("migri_assistant.vectorstore.chroma_store.HuggingFaceEmbeddings")
    def test_query(self, mock_embeddings, mock_chroma):
        """Test querying the vector store by text."""
        # Set up mocks
        mock_vector_db = Mock()
        mock_doc1 = Mock()
        mock_doc1.metadata = {}
        mock_doc2 = Mock()
        mock_doc2.metadata = {"source_url": "https://example.com/doc2"}
        mock_vector_db.similarity_search.return_value = [mock_doc1, mock_doc2]
        mock_chroma.return_value = mock_vector_db

        # Initialize ChromaStore
        store = ChromaStore(collection_name="test_collection")

        # Test query
        results = store.query(query_text="test query", n_results=2)

        # Check if similarity_search was called with correct arguments
        mock_vector_db.similarity_search.assert_called_once_with(
            query="test query",
            k=2,
        )

        # Check if citation URL was added
        assert results == [mock_doc1, mock_doc2]
        assert "citation_url" in mock_doc2.metadata
        assert mock_doc2.metadata["citation_url"] == "https://example.com/doc2"

    @patch("migri_assistant.vectorstore.chroma_store.Chroma")
    @patch("migri_assistant.vectorstore.chroma_store.HuggingFaceEmbeddings")
    def test_query_exception(self, mock_embeddings, mock_chroma):
        """Test handling exceptions when querying the vector store."""
        # Set up mocks
        mock_vector_db = Mock()
        mock_vector_db.similarity_search.side_effect = Exception("Test error")
        mock_chroma.return_value = mock_vector_db

        # Initialize ChromaStore
        store = ChromaStore(collection_name="test_collection")

        # Test query with exception
        results = store.query(query_text="test query")

        # Check if empty list was returned
        assert results == []

    @patch("migri_assistant.vectorstore.chroma_store.Chroma")
    @patch("migri_assistant.vectorstore.chroma_store.HuggingFaceEmbeddings")
    def test_query_with_embedding(self, mock_embeddings, mock_chroma):
        """Test querying the vector store with embedding."""
        # Set up mocks
        mock_collection = Mock()
        mock_collection.query.return_value = {
            "documents": [["Test content"]],
            "metadatas": [[{"source_url": "https://example.com/doc"}]],
            "distances": [[0.1]],
        }
        mock_vector_db = Mock()
        mock_vector_db._collection = mock_collection
        mock_chroma.return_value = mock_vector_db

        # Initialize ChromaStore
        store = ChromaStore(collection_name="test_collection")

        # Test query with embedding
        embedding = [0.1, 0.2, 0.3]
        results = store.query_with_embedding(embedding=embedding, n_results=3)

        # Check if query was called with correct arguments
        mock_collection.query.assert_called_once_with(
            query_embeddings=[embedding],
            n_results=3,
            include=["documents", "metadatas", "distances"],
        )

        # Check if citation URL was added
        assert "citation_url" in results["metadatas"][0][0]
        assert results["metadatas"][0][0]["citation_url"] == "https://example.com/doc"

    @patch("migri_assistant.vectorstore.chroma_store.Chroma")
    @patch("migri_assistant.vectorstore.chroma_store.HuggingFaceEmbeddings")
    def test_get_document(self, mock_embeddings, mock_chroma):
        """Test getting a document by ID."""
        # Set up mocks
        mock_collection = Mock()
        mock_collection.get.return_value = {
            "documents": ["Test content"],
            "metadatas": [{"url": "https://example.com/doc"}],
        }
        mock_vector_db = Mock()
        mock_vector_db._collection = mock_collection
        mock_chroma.return_value = mock_vector_db

        # Initialize ChromaStore
        store = ChromaStore(collection_name="test_collection")

        # Test get document
        result = store.get_document(document_id="test_doc")

        # Check if get was called with correct arguments
        mock_collection.get.assert_called_once_with(
            ids=["test_doc"],
            include=["documents", "metadatas"],
        )

        # Check if citation URL was added
        assert "citation_url" in result["metadatas"][0]
        assert result["metadatas"][0]["citation_url"] == "https://example.com/doc"

    @patch("migri_assistant.vectorstore.chroma_store.Chroma")
    @patch("migri_assistant.vectorstore.chroma_store.HuggingFaceEmbeddings")
    def test_enhance_document_with_citation(self, mock_embeddings, mock_chroma):
        """Test enhancing a document with citation information."""
        # Initialize ChromaStore
        store = ChromaStore(collection_name="test_collection")

        # Test with source_url
        doc1 = Mock()
        doc1.metadata = {"source_url": "https://example.com/doc1"}
        store._enhance_document_with_citation(doc1)
        assert doc1.metadata["citation_url"] == "https://example.com/doc1"

        # Test with url
        doc2 = Mock()
        doc2.metadata = {"url": "https://example.com/doc2"}
        store._enhance_document_with_citation(doc2)
        assert doc2.metadata["citation_url"] == "https://example.com/doc2"

        # Test with neither
        doc3 = Mock()
        doc3.metadata = {"other_field": "value"}
        store._enhance_document_with_citation(doc3)
        assert "citation_url" not in doc3.metadata

        # Test with no metadata attribute
        doc4 = Mock(spec=[])  # No metadata attribute
        store._enhance_document_with_citation(doc4)
        assert not hasattr(doc4, "metadata")
