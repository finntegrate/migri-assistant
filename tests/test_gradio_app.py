"""Tests for the Gradio app module."""

import unittest
from unittest.mock import Mock, patch

import pytest

from tapio.app import (
    DEFAULT_CHROMA_DB_PATH,
    DEFAULT_COLLECTION_NAME,
    DEFAULT_MAX_TOKENS,
    DEFAULT_MODEL_NAME,
    DEFAULT_NUM_RESULTS,
    TapioAssistantApp,
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

    @patch("tapio.app.RAGService")
    def test_init_rag_service(self, mock_rag_service_class):
        """Test that the RAG service is initialized correctly."""
        # Setup
        mock_instance = Mock()
        mock_rag_service_class.return_value = mock_instance

        # Create app and initialize RAG service
        app = TapioAssistantApp()
        service = app._init_rag_service()

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
        _ = app._init_rag_service()
        assert mock_rag_service_class.call_count == 1

    def test_generate_rag_response(self):
        """Test generating a RAG response."""
        # Setup
        app = TapioAssistantApp()
        app.rag_service = Mock()
        app.rag_service.query.return_value = ("Test response", ["doc1", "doc2"])
        app.rag_service.format_retrieved_documents.return_value = "Formatted docs"

        # Call the method
        response, formatted_docs = app.generate_rag_response("test query")

        # Assertions
        app.rag_service.query.assert_called_once_with(query_text="test query", history=None)
        app.rag_service.format_retrieved_documents.assert_called_once_with(["doc1", "doc2"])
        assert response == "Test response"
        assert formatted_docs == "Formatted docs"

    @patch("tapio.app.RAGService")
    def test_generate_rag_response_with_error(self, mock_rag_service_class):
        """Test error handling in generate_rag_response."""
        # Setup
        mock_rag_service_class.side_effect = Exception("Test error")
        app = TapioAssistantApp()

        # Call the method - need to patch _init_rag_service first
        with patch.object(app, "_init_rag_service", side_effect=Exception("Test error")):
            response, formatted_docs = app.generate_rag_response("test query")

        # Assertions
        assert "error" in response.lower()
        assert "Error retrieving" in formatted_docs

    @patch("tapio.app.TapioAssistantApp")
    def test_main_function(self, mock_app_class):
        """Test the main function that launches the Gradio app."""
        # Setup
        mock_app_instance = Mock()
        mock_app_class.return_value = mock_app_instance
        mock_app_instance.check_model_availability.return_value = True

        # Call the function
        main(share=True)

        # Assertions
        mock_app_class.assert_called_once_with(
            collection_name=DEFAULT_COLLECTION_NAME,
            persist_directory=DEFAULT_CHROMA_DB_PATH,
            model_name=DEFAULT_MODEL_NAME,
            max_tokens=DEFAULT_MAX_TOKENS,
            num_results=DEFAULT_NUM_RESULTS,
        )
        mock_app_instance.check_model_availability.assert_called_once()
        mock_app_instance.launch.assert_called_once_with(share=True)

    @patch("tapio.app.TapioAssistantApp")
    def test_main_function_model_unavailable(self, mock_app_class):
        """Test the main function when the model is unavailable."""
        # Setup
        mock_app_instance = Mock()
        mock_app_class.return_value = mock_app_instance
        mock_app_instance.check_model_availability.return_value = False

        # Call the function
        main()

        # Assertions
        mock_app_instance.check_model_availability.assert_called_once()
        # Even with model unavailable, the app should launch
        mock_app_instance.launch.assert_called_once()
