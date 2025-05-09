"""Service for interacting with LLM models through Ollama."""

import logging

import ollama

# Configure logging
logger = logging.getLogger(__name__)


class LLMService:
    """Service for interacting with LLM models through Ollama."""

    def __init__(
        self,
        model_name: str = "llama3.2",
        max_tokens: int = 1024,
        temperature: float = 0.7,
    ):
        """Initialize the LLM service with the given model settings.

        Args:
            model_name: The name of the model to use
            max_tokens: Maximum number of tokens to generate
            temperature: Temperature parameter for generation
        """
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.temperature = temperature
        logger.info(f"Initialized LLM service with model: {model_name}")

    def check_model_availability(self) -> bool:
        """Check if Ollama is running and has the required model.

        Returns:
            bool: True if the model is available, False otherwise
        """
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
                if model_name == self.model_name or model_name.startswith(f"{self.model_name}:"):
                    model_exists = True
                    logger.info(f"Found matching model: {model_name}")
                    break

            if not model_exists:
                logger.warning(
                    f"{self.model_name} model not found in Ollama. "
                    f"Please pull it with 'ollama pull {self.model_name}'",
                )
                return False
            return True
        except Exception as e:
            logger.warning(f"Could not connect to Ollama: {e}")
            logger.warning("Make sure Ollama is running")
            return False

    def generate_response(self, prompt: str, system_prompt: str | None = None) -> str | dict:
        """Generate a response from the LLM model.

        Args:
            prompt: The prompt to generate a response for
            system_prompt: Optional system prompt to set context

        Returns:
            str: The generated response
        """
        try:
            messages = []

            # Add system message if provided
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            # Add user message
            messages.append({"role": "user", "content": prompt})

            response = ollama.chat(
                model=self.model_name,
                messages=messages,
                options={
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens,
                },
            )
            return response["message"]["content"]
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return (
                f"Error: Could not generate a response. "
                f"Please check if Ollama is running with the {self.model_name} model."
            )

    def get_model_name(self) -> str:
        """Get the name of the model being used.

        Returns:
            str: The model name
        """
        return self.model_name
