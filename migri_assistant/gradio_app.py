"""Gradio interface for the Migri Assistant RAG chatbot."""

import logging

import gradio as gr

from migri_assistant.models.rag_service import RAGService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default constants (can be overridden by CLI)
DEFAULT_COLLECTION_NAME = "migri_docs"
DEFAULT_CHROMA_DB_PATH = "chroma_db"
DEFAULT_MODEL_NAME = "llama3.2"
DEFAULT_MAX_TOKENS = 1024
DEFAULT_NUM_RESULTS = 5

# Global RAG service instance - will be initialized when needed
rag_service = None


def init_rag_service(
    collection_name: str = DEFAULT_COLLECTION_NAME,
    persist_directory: str = DEFAULT_CHROMA_DB_PATH,
    model_name: str = DEFAULT_MODEL_NAME,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    num_results: int = DEFAULT_NUM_RESULTS,
) -> RAGService:
    """Initialize the RAG service with the given parameters.

    Args:
        collection_name: Name of the ChromaDB collection
        persist_directory: Directory where the ChromaDB database is stored
        model_name: Name of the LLM model to use
        max_tokens: Maximum number of tokens to generate
        num_results: Number of documents to retrieve from the vector store

    Returns:
        Initialized RAGService instance
    """
    global rag_service

    if rag_service is None:
        logger.info(f"Initializing RAG service with {model_name} model")
        rag_service = RAGService(
            collection_name=collection_name,
            persist_directory=persist_directory,
            model_name=model_name,
            max_tokens=max_tokens,
            num_results=num_results,
        )

    return rag_service


def generate_rag_response(
    query: str,
    history: list[dict] | None = None,
    collection_name: str = DEFAULT_COLLECTION_NAME,
    persist_directory: str = DEFAULT_CHROMA_DB_PATH,
    model_name: str = DEFAULT_MODEL_NAME,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    num_results: int = DEFAULT_NUM_RESULTS,
) -> tuple[str, str]:
    """Generate a response using RAG and return both the response and retrieved documents.

    Args:
        query: The user's query
        history: Chat history
        collection_name: Name of the ChromaDB collection
        persist_directory: Directory where the ChromaDB database is stored
        model_name: Name of the LLM model to use
        max_tokens: Maximum number of tokens to generate
        num_results: Number of documents to retrieve from the vector store

    Returns:
        Tuple containing the response and formatted documents for display
    """
    try:
        # Initialize RAG service if not already done
        service = init_rag_service(
            collection_name=collection_name,
            persist_directory=persist_directory,
            model_name=model_name,
            max_tokens=max_tokens,
            num_results=num_results,
        )

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


# Gradio app setup
with gr.Blocks(title="Migri Assistant") as demo:
    gr.Markdown("# Migri Assistant")
    gr.Markdown(
        "Ask questions about Finnish immigration processes. "
        "The assistant uses RAG to find and use relevant information.",
    )

    with gr.Row():
        with gr.Column(scale=7):
            chatbot = gr.Chatbot(
                label="Conversation",
                height=500,
                bubble_full_width=False,
                type="messages",  # Use messages format to avoid deprecation warning
            )
            msg = gr.Textbox(
                label="Your question",
                placeholder="Ask about Finnish immigration processes...",
                lines=2,
            )

            # Add disclaimer text above the buttons using HTML component for proper rendering
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

    # Define app logic
    def respond(message, chat_history):
        # Update for 'messages' type chatbot
        if not chat_history:
            chat_history = []

        response, docs = generate_rag_response(message, chat_history)

        # Add the new messages
        chat_history.append({"role": "user", "content": message})
        chat_history.append({"role": "assistant", "content": response})

        return "", chat_history, docs

    msg.submit(respond, [msg, chatbot], [msg, chatbot, docs_display])
    submit.click(respond, [msg, chatbot], [msg, chatbot, docs_display])
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


def main(
    collection_name: str = DEFAULT_COLLECTION_NAME,
    persist_directory: str = DEFAULT_CHROMA_DB_PATH,
    model_name: str = DEFAULT_MODEL_NAME,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    num_results: int = DEFAULT_NUM_RESULTS,
    share: bool = False,
):
    """Run the Gradio app with the specified parameters.

    Args:
        collection_name: Name of the ChromaDB collection
        persist_directory: Directory where the ChromaDB database is stored
        model_name: Name of the LLM model to use
        max_tokens: Maximum number of tokens to generate
        num_results: Number of documents to retrieve from the vector store
        share: Whether to create a shareable link for the app
    """
    # Initialize the RAG service
    service = init_rag_service(
        collection_name=collection_name,
        persist_directory=persist_directory,
        model_name=model_name,
        max_tokens=max_tokens,
        num_results=num_results,
    )

    # Check if Ollama is running and has the required model
    if not service.check_model_availability():
        logger.warning(
            f"Could not find {model_name} model in Ollama. "
            f"The app will start, but responses may not work correctly.",
        )

    # Launch the Gradio app
    demo.launch(share=share)


if __name__ == "__main__":
    main()
