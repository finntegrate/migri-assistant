"""Gradio interface for the Tapio Assistant RAG chatbot."""

import logging
from collections.abc import Generator
from typing import Any

import gradio as gr

from tapio.models.rag_service import RAGService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default constants (can be overridden by CLI)
DEFAULT_COLLECTION_NAME = "migri_docs"
DEFAULT_CHROMA_DB_PATH = "chroma_db"
DEFAULT_MODEL_NAME = "llama3.2"
DEFAULT_MAX_TOKENS = 1024
DEFAULT_NUM_RESULTS = 5


class TapioAssistantApp:
    """Class representing the Tapio Assistant Gradio application."""

    def __init__(
        self,
        collection_name: str = DEFAULT_COLLECTION_NAME,
        persist_directory: str = DEFAULT_CHROMA_DB_PATH,
        model_name: str = DEFAULT_MODEL_NAME,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        num_results: int = DEFAULT_NUM_RESULTS,
    ) -> None:
        """Initialize the Tapio Assistant application.

        Args:
            collection_name: Name of the ChromaDB collection
            persist_directory: Directory where the ChromaDB database is stored
            model_name: Name of the LLM model to use
            max_tokens: Maximum number of tokens to generate
            num_results: Number of documents to retrieve from the vector store
        """
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.num_results = num_results
        self.rag_service: RAGService | None = None
        self.demo = self._build_interface()

    def _init_rag_service(self) -> RAGService:
        """Initialize the RAG service if not already done.

        Returns:
            Initialized RAGService instance
        """
        if self.rag_service is None:
            logger.info(f"Initializing RAG service with {self.model_name} model")
            self.rag_service = RAGService(
                collection_name=self.collection_name,
                persist_directory=self.persist_directory,
                model_name=self.model_name,
                max_tokens=self.max_tokens,
                num_results=self.num_results,
            )

        return self.rag_service

    def generate_rag_response(
        self,
        query: str,
        history: list[dict[str, Any]] | None = None,
    ) -> tuple[str, str]:
        """Generate a response using RAG and return both the response and retrieved documents.

        Args:
            query: The user's query
            history: Chat history

        Returns:
            Tuple containing the response and formatted documents for display
        """
        try:
            # Initialize RAG service if not already done
            service = self._init_rag_service()

            # Get response and retrieved docs from the RAG service
            response, retrieved_docs = service.query(query_text=query, history=history)

            # Format documents for display
            formatted_docs = service.format_retrieved_documents(retrieved_docs)

            return response, formatted_docs
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return (
                "I encountered an error while processing your query. Please try again.",
                "Error retrieving documents.",
            )

    def respond_stream(
        self,
        message: str,
        chat_history: list[dict[str, str]],
    ) -> Generator[tuple[str, list[dict[str, str]], str], None, None]:
        """Process user message and stream the response.

        Args:
            message: User's message
            chat_history: Current chat history

        Yields:
            Tuple containing empty message (to clear input), updated chat history,
            and document display content
        """
        # Initialize chat history if empty
        if not chat_history:
            chat_history = []

        # Add user message immediately
        chat_history.append({"role": "user", "content": message})

        # Clear input and show user message
        yield "", chat_history, "Retrieving relevant documents..."

        try:
            # Initialize RAG service if not already done
            service = self._init_rag_service()

            # Get streaming response and retrieved docs from the RAG service
            response_stream, retrieved_docs = service.query_stream(query_text=message, history=chat_history)

            # Format documents for display
            formatted_docs = service.format_retrieved_documents(retrieved_docs)

            # Start building the assistant response
            assistant_response = ""

            # Stream the response
            for chunk in response_stream:
                assistant_response += chunk

                # Update chat history with current response
                current_history = chat_history.copy()
                current_history.append({"role": "assistant", "content": assistant_response})

                yield "", current_history, formatted_docs

            # Final update with complete response
            chat_history.append({"role": "assistant", "content": assistant_response})
            yield "", chat_history, formatted_docs

        except Exception as e:
            logger.error(f"Error in streaming response: {e}")
            error_message = "I encountered an error while processing your query. Please try again."
            chat_history.append({"role": "assistant", "content": error_message})
            yield "", chat_history, "Error retrieving documents."

    def respond(
        self,
        message: str,
        chat_history: list[dict[str, str]],
    ) -> tuple[str, list[dict[str, str]], str]:
        """Process user message and update the chat history.

        Args:
            message: User's message
            chat_history: Current chat history

        Returns:
            Tuple containing empty message (to clear input), updated chat history,
            and document display content
        """
        # Update for 'messages' type chatbot
        if not chat_history:
            chat_history = []

        response, docs = self.generate_rag_response(message, chat_history)

        # Add the new messages
        chat_history.append({"role": "user", "content": message})
        chat_history.append({"role": "assistant", "content": response})

        return "", chat_history, docs

    def _build_interface(self) -> gr.Blocks:
        """Build the Gradio interface components.

        Returns:
            Configured Gradio Blocks interface
        """
        with gr.Blocks(title="Tapio Assistant") as demo:
            gr.Markdown("# Tapio Assistant")
            gr.Markdown(
                "Ask questions about Finnish immigration processes. "
                "The assistant uses RAG to find and use relevant information.",
            )

            with gr.Row():
                with gr.Column(scale=7):
                    chatbot = gr.Chatbot(
                        label="Conversation",
                        height=500,
                        type="messages",
                    )
                    msg = gr.Textbox(
                        label="Your question",
                        placeholder="Ask about Finnish immigration processes...",
                        lines=2,
                    )

                    gr.HTML(
                        """<p style="font-size: 0.8em; color: #666; margin-top: 0.5em; margin-bottom: 0.5em;">
                            ⚠️ Disclaimer: Information provided may contain errors.
                            Always verify with official sources at <a href="https://migri.fi" target="_blank">migri.fi</a>.
                        </p>""",  # noqa: E501
                    )

                    with gr.Row():
                        submit = gr.Button("Submit")
                        clear = gr.Button("Clear")

                with gr.Column(scale=3):
                    docs_display = gr.Markdown(
                        label="Retrieved Documents",
                        value="Documents will appear here when you ask a question.",
                        height=500,
                    )

            # Define app logic - use streaming for better user experience
            msg.submit(self.respond_stream, [msg, chatbot], [msg, chatbot, docs_display])
            submit.click(self.respond_stream, [msg, chatbot], [msg, chatbot, docs_display])
            clear.click(lambda: ([], None), None, [chatbot, docs_display])

            # Add some example queries
            gr.Examples(
                examples=[
                    "How do I apply for a residence permit?",
                    "What documents do I need for family reunification?",
                    "How long does it take to process a work permit application?",
                    "What are the requirements for Finnish citizenship?",
                ],
                inputs=msg,
            )

        return demo

    def check_model_availability(self) -> bool:
        """Check if the Ollama model is available.

        Returns:
            True if the model is available, False otherwise
        """
        service = self._init_rag_service()
        return service.check_model_availability()

    def launch(self, share: bool = False) -> None:
        """Launch the Gradio app.

        Args:
            share: Whether to create a shareable link for the app
        """
        # Check model availability
        if not self.check_model_availability():
            logger.warning(
                f"Could not find {self.model_name} model in Ollama. "
                f"The app will start, but responses may not work correctly.",
            )

        # Launch the Gradio app
        self.demo.launch(share=share)


def main(
    collection_name: str = DEFAULT_COLLECTION_NAME,
    persist_directory: str = DEFAULT_CHROMA_DB_PATH,
    model_name: str = DEFAULT_MODEL_NAME,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    num_results: int = DEFAULT_NUM_RESULTS,
    share: bool = False,
) -> None:
    """Run the Tapio Assistant app with the specified parameters.

    Args:
        collection_name: Name of the ChromaDB collection
        persist_directory: Directory where the ChromaDB database is stored
        model_name: Name of the LLM model to use
        max_tokens: Maximum number of tokens to generate
        num_results: Number of documents to retrieve from the vector store
        share: Whether to create a shareable link for the app
    """
    # Create the app
    app = TapioAssistantApp(
        collection_name=collection_name,
        persist_directory=persist_directory,
        model_name=model_name,
        max_tokens=max_tokens,
        num_results=num_results,
    )

    # Check model availability
    app.check_model_availability()

    # Launch the app
    app.launch(share=share)


if __name__ == "__main__":
    main()
