"""Gradio interface for the Migri Assistant RAG chatbot."""

import logging

import gradio as gr
import ollama

from migri_assistant.vectorstore.chroma_store import ChromaStore

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
COLLECTION_NAME = "migri_docs"  # Changed to match vectorize command default
CHROMA_DB_PATH = "chroma_db"
MODEL_NAME = "llama3.2"
MAX_TOKENS = 1024
NUM_RESULTS = 5

# Initialize the ChromaDB store
vector_store = ChromaStore(
    collection_name=COLLECTION_NAME,
    persist_directory=CHROMA_DB_PATH,
)


def format_retrieved_documents(documents: list[dict]) -> str:
    """Format retrieved documents for display."""
    if not documents:
        return "No relevant documents found."

    formatted_docs = []
    for i, doc in enumerate(documents):
        # Extract metadata
        metadata = doc.metadata if hasattr(doc, "metadata") else {}
        source = metadata.get("source_url", metadata.get("url", "Unknown source"))
        title = metadata.get("title", f"Document {i + 1}")

        # Format the document with metadata
        doc_content = doc.page_content if hasattr(doc, "page_content") else str(doc)
        formatted_doc = f"### {title}\n**Source**: {source}\n\n{doc_content}\n\n"
        formatted_docs.append(formatted_doc)

    return "\n".join(formatted_docs)


def query_ollama(prompt: str) -> str:
    """Query the Ollama model with a prompt."""
    try:
        response = ollama.chat(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.7, "num_predict": MAX_TOKENS},
        )
        return response["message"]["content"]
    except Exception as e:
        logger.error(f"Error querying Ollama: {e}")
        return (
            f"Error: Could not generate a response. "
            f"Please check if Ollama is running with the {MODEL_NAME} model."
        )


def generate_rag_response(query: str, history: list[dict]) -> tuple[str, str]:
    """Generate a response using RAG and return both the response and retrieved documents."""
    try:
        # Query the vector store for relevant documents
        logger.info(f"Querying vector store with: {query}")
        retrieved_docs = vector_store.query(query_text=query, n_results=NUM_RESULTS)

        # Format documents for the LLM prompt
        context_docs = []
        for doc in retrieved_docs:
            # Extract content and relevant metadata for context
            if hasattr(doc, "page_content"):
                context_docs.append(doc.page_content)

        # Create a prompt with the retrieved context
        context_text = "\n\n".join(context_docs)
        prompt = (
            "You are Migri Assistant, an AI that helps people understand "
            "Finnish immigration processes.\n"
            "Use the following context to answer the question, and acknowledge when "
            "you don't know something.\n"
            "Keep your response concise and informative.\n\n"
            f"CONTEXT:\n{context_text}\n\n"
            f"QUESTION: {query}\n\n"
            "ANSWER:"
        )

        # Generate response using Ollama
        logger.info("Generating response with Ollama")
        response = query_ollama(prompt)

        # Format documents for display
        formatted_docs = format_retrieved_documents(retrieved_docs)

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


def check_ollama():
    """Check if Ollama is running and has the required model."""
    try:
        models = ollama.list()
        if "models" not in models:
            logger.warning("No models found in Ollama")
            return False

        # Check if the model exists - allow for model name variations like llama3.2:latest
        model_exists = False
        available_models = [model.get("name", "") for model in models.get("models", [])]

        # Log available models
        logger.info(f"Available Ollama models: {', '.join(available_models)}")

        # Check for exact match or name:latest pattern
        for model_name in available_models:
            if model_name == MODEL_NAME or model_name.startswith(f"{MODEL_NAME}:"):
                model_exists = True
                # Use the found model name
                logger.info(f"Found matching model: {model_name}")
                break

        if not model_exists:
            logger.warning(
                f"{MODEL_NAME} model not found in Ollama. "
                f"Please pull it with 'ollama pull {MODEL_NAME}'",
            )
            return False
        return True
    except Exception as e:
        logger.warning(f"Could not connect to Ollama: {e}")
        logger.warning("Make sure Ollama is running")
        return False


def main():
    """Run the Gradio app."""
    # Check if Ollama is running and has the required model
    check_ollama()

    # Launch the Gradio app
    demo.launch(share=False)


if __name__ == "__main__":
    main()
