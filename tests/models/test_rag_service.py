"""Tests for the RAG service."""

from unittest import mock

import pytest

from migri_assistant.models.rag_service import RAGService


@pytest.fixture
def rag_service():
    """Create a RAG service with mocked dependencies for testing."""
    # Mock the ChromaStore and LLMService
    with mock.patch("migri_assistant.models.rag_service.ChromaStore") as mock_chroma:
        with mock.patch("migri_assistant.models.rag_service.LLMService") as mock_llm:
            # Configure mock instance behavior
            mock_chroma_instance = mock_chroma.return_value
            mock_llm_instance = mock_llm.return_value

            # Create RAGService with mocked dependencies
            service = RAGService(
                collection_name="test_collection",
                persist_directory="test_db",
                model_name="test_model",
            )

            # Set mocked properties for access in tests
            service.mock_vector_store = mock_chroma_instance
            service.mock_llm_service = mock_llm_instance

            yield service


def test_rag_service_loads_prompts(rag_service):
    """Test that RAG service correctly loads prompt templates."""
    # Mock the prompt loading functions
    with mock.patch("migri_assistant.models.rag_service.load_prompt") as mock_load_prompt:
        # Configure mock return values
        mock_load_prompt.side_effect = [
            "Mocked system prompt",  # For system_prompt
            "Mocked user prompt with context",  # For user_query
        ]

        # Mock vector store query to return some document
        mock_doc = mock.MagicMock()
        mock_doc.page_content = "Test document content"
        rag_service.mock_vector_store.query.return_value = [mock_doc]

        # Call the method under test
        rag_service.query("Test query")

        # Check that the prompts were loaded
        assert mock_load_prompt.call_count == 2
        mock_load_prompt.assert_any_call("system_prompt")

        # Check that the user prompt was loaded with the correct variables
        user_prompt_calls = [
            call for call in mock_load_prompt.call_args_list if call[0][0] == "user_query"
        ]
        assert len(user_prompt_calls) == 1

        # Get the kwargs passed to load_prompt for user_query
        user_prompt_kwargs = user_prompt_calls[0][1]
        assert "context" in user_prompt_kwargs
        assert "question" in user_prompt_kwargs
        assert user_prompt_kwargs["question"] == "Test query"

        # Verify the LLM was called with the correct prompts
        rag_service.mock_llm_service.generate_response.assert_called_once()
        call_args = rag_service.mock_llm_service.generate_response.call_args[1]
        assert call_args["system_prompt"] == "Mocked system prompt"
        assert call_args["prompt"] == "Mocked user prompt with context"
