"""Tests for the markdown vectorizer."""

from unittest.mock import Mock, call, patch

from tapio.vectorstore.vectorizer import MarkdownVectorizer


class TestMarkdownVectorizer:
    """Tests for the MarkdownVectorizer class."""

    @patch("migri_assistant.vectorstore.vectorizer.Chroma")
    @patch("migri_assistant.vectorstore.vectorizer.HuggingFaceEmbeddings")
    @patch("migri_assistant.vectorstore.vectorizer.MarkdownTextSplitter")
    def test_init(self, mock_splitter_class, mock_embeddings_class, mock_chroma):
        """Test initialization of the vectorizer."""
        # Set up mocks
        mock_embeddings_instance = Mock()
        mock_embeddings_class.return_value = mock_embeddings_instance
        mock_splitter_instance = Mock()
        mock_splitter_class.return_value = mock_splitter_instance

        # Initialize vectorizer
        vectorizer = MarkdownVectorizer(
            collection_name="test_collection",
            persist_directory="test_dir",
            embedding_model_name="test-model",
            chunk_size=500,
            chunk_overlap=100,
        )

        # Check if components were initialized correctly
        mock_embeddings_class.assert_called_once_with(model_name="test-model")
        mock_splitter_class.assert_called_once_with(chunk_size=500, chunk_overlap=100)
        mock_chroma.assert_called_once_with(
            collection_name="test_collection",
            embedding_function=mock_embeddings_instance,
            persist_directory="test_dir",
        )

        # Check if configuration was saved
        assert vectorizer.collection_name == "test_collection"
        assert vectorizer.persist_directory == "test_dir"
        assert vectorizer.embedding_model_name == "test-model"
        assert vectorizer.chunk_size == 500
        assert vectorizer.chunk_overlap == 100

    @patch("migri_assistant.vectorstore.vectorizer.find_markdown_files")
    @patch("migri_assistant.vectorstore.vectorizer.Chroma")
    @patch("migri_assistant.vectorstore.vectorizer.HuggingFaceEmbeddings")
    @patch("migri_assistant.vectorstore.vectorizer.MarkdownTextSplitter")
    def test_process_directory(
        self,
        mock_splitter_class,
        mock_embeddings_class,
        mock_chroma,
        mock_find_files,
    ):
        """Test processing a directory of markdown files."""
        # Set up mocks
        mock_vector_db = Mock()
        mock_chroma.return_value = mock_vector_db

        # Set up mock for find_markdown_files to return some test files
        test_files = [
            "test_dir/file1.md",
            "test_dir/file2.md",
            "test_dir/file3.md",
        ]
        mock_find_files.return_value = test_files

        # Initialize vectorizer with mocked _process_batch
        vectorizer = MarkdownVectorizer(collection_name="test_collection")
        vectorizer._process_batch = Mock(return_value=2)  # 2 chunks per batch

        # Process directory
        processed_count = vectorizer.process_directory(
            input_dir="test_dir",
            domain_filter="example.com",
            batch_size=2,
        )

        # Verify find_markdown_files was called correctly
        mock_find_files.assert_called_once_with("test_dir", "example.com")

        # Verify _process_batch was called correctly for each batch
        assert vectorizer._process_batch.call_count == 2
        vectorizer._process_batch.assert_has_calls(
            [
                call(["test_dir/file1.md", "test_dir/file2.md"]),
                call(["test_dir/file3.md"]),
            ],
        )

        # Verify correct number of files was returned
        assert processed_count == 3

    @patch("migri_assistant.vectorstore.vectorizer.read_markdown_file")
    @patch("migri_assistant.vectorstore.vectorizer.Document")
    @patch("migri_assistant.vectorstore.vectorizer.Chroma")
    @patch("migri_assistant.vectorstore.vectorizer.HuggingFaceEmbeddings")
    @patch("migri_assistant.vectorstore.vectorizer.MarkdownTextSplitter")
    def test_process_batch(
        self,
        mock_splitter_class,
        mock_embeddings_class,
        mock_chroma,
        mock_document_class,
        mock_read_file,
    ):
        """Test processing a batch of markdown files."""
        # Set up mocks
        mock_vector_db = Mock()
        mock_chroma.return_value = mock_vector_db

        mock_splitter = Mock()
        mock_splitter_class.return_value = mock_splitter

        # Set up read_markdown_file to return test data
        mock_read_file.side_effect = [
            ({"title": "Test 1"}, "Content 1"),
            ({"title": "Test 2"}, "Content 2"),
        ]

        # Set up Document
        mock_doc1 = Mock()
        mock_doc2 = Mock()
        mock_document_class.side_effect = [mock_doc1, mock_doc2]

        # Set up text splitter
        mock_chunk1 = Mock()
        mock_chunk1.metadata = {}
        mock_chunk2 = Mock()
        mock_chunk2.metadata = {}
        mock_chunk3 = Mock()
        mock_chunk3.metadata = {}
        mock_splitter.split_documents.side_effect = [
            [mock_chunk1, mock_chunk2],  # First document splits into 2 chunks
            [mock_chunk3],  # Second document splits into 1 chunk
        ]

        # Initialize vectorizer
        vectorizer = MarkdownVectorizer(collection_name="test_collection")

        # Set up _prepare_metadata to return test metadata
        vectorizer._prepare_metadata = Mock(
            side_effect=[
                {"source_id": "file1", "title": "Test 1"},
                {"source_id": "file2", "title": "Test 2"},
            ],
        )

        # Process batch
        chunk_count = vectorizer._process_batch(
            [
                "test_dir/file1.md",
                "test_dir/file2.md",
            ],
        )

        # Verify read_markdown_file was called for each file
        mock_read_file.assert_has_calls(
            [
                call("test_dir/file1.md"),
                call("test_dir/file2.md"),
            ],
        )

        # Verify Document was created for each file
        mock_document_class.assert_has_calls(
            [
                call(
                    page_content="Content 1",
                    metadata={"source_id": "file1", "title": "Test 1"},
                ),
                call(
                    page_content="Content 2",
                    metadata={"source_id": "file2", "title": "Test 2"},
                ),
            ],
        )

        # Verify text splitter was called for each document
        mock_splitter.split_documents.assert_has_calls(
            [
                call([mock_doc1]),
                call([mock_doc2]),
            ],
        )

        # Verify chunk metadata was updated
        assert mock_chunk1.metadata["chunk_index"] == 0
        assert mock_chunk1.metadata["total_chunks"] == 2
        assert mock_chunk2.metadata["chunk_index"] == 1
        assert mock_chunk2.metadata["total_chunks"] == 2
        assert mock_chunk3.metadata["chunk_index"] == 0
        assert mock_chunk3.metadata["total_chunks"] == 1

        # Verify add_documents was called with all chunks
        mock_vector_db.add_documents.assert_called_once_with(
            [mock_chunk1, mock_chunk2, mock_chunk3],
        )

        # Verify correct number of chunks was returned
        assert chunk_count == 3

    @patch("migri_assistant.vectorstore.vectorizer.read_markdown_file")
    @patch("migri_assistant.vectorstore.vectorizer.Document")
    @patch("migri_assistant.vectorstore.vectorizer.Chroma")
    @patch("migri_assistant.vectorstore.vectorizer.HuggingFaceEmbeddings")
    @patch("migri_assistant.vectorstore.vectorizer.MarkdownTextSplitter")
    def test_process_file(
        self,
        mock_splitter_class,
        mock_embeddings_class,
        mock_chroma,
        mock_document_class,
        mock_read_file,
    ):
        """Test processing a single markdown file."""
        # Set up mocks
        mock_vector_db = Mock()
        mock_chroma.return_value = mock_vector_db

        mock_splitter = Mock()
        mock_splitter_class.return_value = mock_splitter

        # Set up read_markdown_file to return test data
        mock_read_file.return_value = ({"title": "Test"}, "Content")

        # Set up Document
        mock_doc = Mock()
        mock_document_class.return_value = mock_doc

        # Set up text splitter
        mock_chunk1 = Mock()
        mock_chunk1.metadata = {}
        mock_chunk2 = Mock()
        mock_chunk2.metadata = {}
        mock_splitter.split_documents.return_value = [mock_chunk1, mock_chunk2]

        # Initialize vectorizer
        vectorizer = MarkdownVectorizer(collection_name="test_collection")

        # Set up _prepare_metadata to return test metadata
        test_metadata = {"source_id": "file", "title": "Test"}
        vectorizer._prepare_metadata = Mock(return_value=test_metadata)

        # Process file
        chunk_count = vectorizer.process_file("test_dir/file.md")

        # Verify read_markdown_file was called
        mock_read_file.assert_called_once_with("test_dir/file.md")

        # Verify Document was created
        mock_document_class.assert_called_once_with(
            page_content="Content",
            metadata=test_metadata,
        )

        # Verify text splitter was called
        mock_splitter.split_documents.assert_called_once_with([mock_doc])

        # Verify chunk metadata was updated
        assert mock_chunk1.metadata["chunk_index"] == 0
        assert mock_chunk1.metadata["total_chunks"] == 2
        assert mock_chunk2.metadata["chunk_index"] == 1
        assert mock_chunk2.metadata["total_chunks"] == 2

        # Verify add_documents was called
        mock_vector_db.add_documents.assert_called_once_with([mock_chunk1, mock_chunk2])

        # Verify correct number of chunks was returned
        assert chunk_count == 2

    @patch("migri_assistant.vectorstore.vectorizer.os.path.basename")
    @patch("migri_assistant.vectorstore.vectorizer.os.path.splitext")
    def test_prepare_metadata(self, mock_splitext, mock_basename):
        """Test preparing metadata for a document."""
        # Set up mocks
        mock_basename.return_value = "file.md"
        mock_splitext.return_value = ("file", ".md")

        # Initialize vectorizer
        vectorizer = MarkdownVectorizer(collection_name="test_collection")

        # Test with source_url
        metadata = {
            "title": "Test Document",
            "source_url": "https://example.com/doc",
        }

        enriched = vectorizer._prepare_metadata(metadata, "test_dir/file.md")

        # Verify metadata was enriched correctly
        assert enriched["title"] == "Test Document"
        assert enriched["source_url"] == "https://example.com/doc"
        assert enriched["url"] == "https://example.com/doc"
        assert enriched["citation_url"] == "https://example.com/doc"
        assert enriched["source_id"] == "file"
        assert enriched["source_path"] == "test_dir/file.md"
        assert enriched["file_name"] == "file.md"

        # Test with url but no source_url
        metadata = {
            "title": "Test Document",
            "url": "https://example.com/doc",
        }

        enriched = vectorizer._prepare_metadata(metadata, "test_dir/file.md")

        # Verify metadata was enriched correctly
        assert enriched["title"] == "Test Document"
        assert enriched["url"] == "https://example.com/doc"
        assert enriched["source_url"] == "https://example.com/doc"
        assert enriched["citation_url"] == "https://example.com/doc"

    @patch("migri_assistant.vectorstore.vectorizer.read_markdown_file")
    @patch("migri_assistant.vectorstore.vectorizer.Chroma")
    @patch("migri_assistant.vectorstore.vectorizer.HuggingFaceEmbeddings")
    @patch("migri_assistant.vectorstore.vectorizer.MarkdownTextSplitter")
    def test_process_batch_error_handling(
        self,
        mock_splitter_class,
        mock_embeddings_class,
        mock_chroma,
        mock_read_file,
    ):
        """Test error handling in process_batch."""
        # Set up mocks
        mock_vector_db = Mock()
        mock_chroma.return_value = mock_vector_db

        # Set up read_markdown_file to raise an exception
        mock_read_file.side_effect = Exception("Test error")

        # Initialize vectorizer
        vectorizer = MarkdownVectorizer(collection_name="test_collection")

        # Process batch with error
        chunk_count = vectorizer._process_batch(["test_dir/file.md"])

        # Verify read_markdown_file was called
        mock_read_file.assert_called_once_with("test_dir/file.md")

        # Verify no chunks were returned
        assert chunk_count == 0

        # Verify add_documents was not called
        mock_vector_db.add_documents.assert_not_called()

    @patch("migri_assistant.vectorstore.vectorizer.read_markdown_file")
    @patch("migri_assistant.vectorstore.vectorizer.Chroma")
    @patch("migri_assistant.vectorstore.vectorizer.HuggingFaceEmbeddings")
    @patch("migri_assistant.vectorstore.vectorizer.MarkdownTextSplitter")
    def test_process_file_empty_content(
        self,
        mock_splitter_class,
        mock_embeddings_class,
        mock_chroma,
        mock_read_file,
    ):
        """Test processing a file with empty content."""
        # Set up read_markdown_file to return empty content
        mock_read_file.return_value = ({"title": "Test"}, "")

        # Initialize vectorizer
        vectorizer = MarkdownVectorizer(collection_name="test_collection")

        # Process file with empty content
        chunk_count = vectorizer.process_file("test_dir/file.md")

        # Verify read_markdown_file was called
        mock_read_file.assert_called_once_with("test_dir/file.md")

        # Verify no chunks were processed
        assert chunk_count == 0
