"""Tests for the Gradio app module."""

import unittest
from unittest.mock import Mock, patch

import pytest

from migri_assistant.gradio_app import (
    DEFAULT_CHROMA_DB_PATH,
    DEFAULT_COLLECTION_NAME,
    DEFAULT_MAX_TOKENS,
    DEFAULT_MODEL_NAME,
    DEFAULT_NUM_RESULTS,
    generate_rag_response,
    init_rag_service,
    main,
)


@pytest.fixture
def mock_rag_service():
    """Create a mock RAG service."""
    mock_service = Mock()
    mock_service.query.return_value = ("Test response", ["doc1", "doc2"])
    mock_service.format_retrieved_documents.return_value = "Formatted docs"
    mock_service.check_model_availability.return_value = True
    return mock_service


class TestGradioApp(unittest.TestCase):
    """Tests for the Gradio app module."""

    @patch("migri_assistant.gradio_app.RAGService")
    def test_init_rag_service(self, mock_rag_service_class):
        """Test that the RAG service is initialized correctly."""
        # Setup
        mock_instance = Mock()
        mock_rag_service_class.return_value = mock_instance

        # Call the function
        service = init_rag_service()

        # Assertions
        mock_rag_service_class.assert_called_once_with(
            collection_name=DEFAULT_COLLECTION_NAME,
            persist_directory=DEFAULT_CHROMA_DB_PATH,
            model_name=DEFAULT_MODEL_NAME,
            max_tokens=DEFAULT_MAX_TOKENS,
            num_results=DEFAULT_NUM_RESULTS,
        )
        assert service == mock_instance

        # Test the singleton behavior - calling again should not create a new instance
        _ = init_rag_service()
        assert mock_rag_service_class.call_count == 1

    @patch("migri_assistant.gradio_app.init_rag_service")
    def test_generate_rag_response(self, mock_init_rag_service):
        """Test generating a RAG response."""
        # Setup
        mock_service = Mock()
        mock_service.query.return_value = ("Test response", ["doc1", "doc2"])
        mock_service.format_retrieved_documents.return_value = "Formatted docs"
        mock_init_rag_service.return_value = mock_service

        # Call the function
        response, formatted_docs = generate_rag_response("test query")

        # Assertions
        mock_service.query.assert_called_once_with(query_text="test query", history=None)
        mock_service.format_retrieved_documents.assert_called_once_with(["doc1", "doc2"])
        assert response == "Test response"
        assert formatted_docs == "Formatted docs"

    @patch("migri_assistant.gradio_app.init_rag_service")
    def test_generate_rag_response_with_error(self, mock_init_rag_service):
        """Test error handling in generate_rag_response."""
        # Setup
        mock_init_rag_service.side_effect = Exception("Test error")

        # Call the function
        response, formatted_docs = generate_rag_response("test query")

        # Assertions
        assert "error" in response.lower()
        assert "Error retrieving" in formatted_docs

    @patch("migri_assistant.gradio_app.demo")
    @patch("migri_assistant.gradio_app.init_rag_service")
    def test_main_function(self, mock_init_rag_service, mock_demo):
        """Test the main function that launches the Gradio app."""
        # Setup
        mock_service = Mock()
        mock_service.check_model_availability.return_value = True
        mock_init_rag_service.return_value = mock_service

        # Call the function
        main(share=True)

        # Assertions
        mock_init_rag_service.assert_called_once()
        mock_service.check_model_availability.assert_called_once()
        mock_demo.launch.assert_called_once_with(share=True)

    @patch("migri_assistant.gradio_app.demo")
    @patch("migri_assistant.gradio_app.init_rag_service")
    def test_main_function_model_unavailable(self, mock_init_rag_service, mock_demo):
        """Test the main function when the model is unavailable."""
        # Setup
        mock_service = Mock()
        mock_service.check_model_availability.return_value = False
        mock_init_rag_service.return_value = mock_service

        # Call the function
        main()

        # Assertions
        mock_service.check_model_availability.assert_called_once()
        # Even with model unavailable, the app should launch
        mock_demo.launch.assert_called_once()
