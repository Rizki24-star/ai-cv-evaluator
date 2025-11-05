import google.generativeai as genai
import json
import logging
from typing import Dict, Any, Optional
from src.config import get_settings
from src.utils.validator import validate_and_repair_json, clean_json_string
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

settings = get_settings()

class GeminiServices:
    """Gemini API service"""

    def __init__(self):
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel(settings.gemini_model)

        self.generation_config = {
            "temperature": settings.gemini_temperature,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": settings.gemini_max_tokens,
        }

        self.safety_settings = [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_NONE"
            }
        ]

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=4, max=30),
        retry=retry_if_exception_type((Exception)),
        reraise=True
    )

    async def generate_with_retry(
        self,
        prompt: str,
         system_instruction: Optional[str] = None,
        temperature: Optional[float] = None,
        json_mode: bool = True
    )-> str:
        """Generate text with automatic retry on failures"""

        try:
            config = self.generation_config.copy()
            if temperature is not None:
                config["temperature"] = temperature

            if json_mode:
                prompt = self._add_json_instruction(prompt)

            if system_instruction:
                model = genai.GenerativeModel(
                    settings.gemini_model,
                    system_instruction=system_instruction
                )
            else:
                model= self.model

            logging.info("Prompt: " + prompt)

            # Generate content
            response = model.generate_content(
                prompt,
                generation_config=config,
                safety_settings=self.safety_settings
            )

            logging.info("Gemini response: " + str(response))

            if not response.parts:
                raise ValueError("Empty response from Gemini")

            text = response.text
            logging.info(f"Gemini generated {len(text)} characters")

            # If JSON mode, sanitize common LLM artifacts like code fences before returning
            if json_mode and isinstance(text, str):
                cleaned = clean_json_string(text)
                if cleaned != text:
                    logging.warning("Sanitized LLM output by removing code fences/formatting artifacts for JSON parsing")
                text = cleaned

            return text

        except Exception as e:
            logging.error(f"Gemini API error: {str(e)}")
            raise

    async def generate_structured_output(
        self,
        prompt: str,
        expected_model: Any,
        system_instruction: Optional[str] = None,
        temperature: Optional[float] = None
    ) -> Dict:
        """
        Generate and validate structured JSON output
        """
        # Generate with JSON mode
        text_response = await self.generate_with_retry(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=temperature,
            json_mode=True
        )

        logging.info("Text response: " + text_response)

        # Validate and repair if needed
        validated_data = validate_and_repair_json(
            text_response,
            expected_model
        )

        logging.info("Text response validate and repair json: " + json.dumps(validated_data, indent=2))

        return validated_data


    def _add_json_instruction(self, prompt: str) -> str:
        """Add JSON instruction to prompt"""

        json_instruction = """
        CRITICAL: You MUST respond with ONLY valid JSON. No markdown, no explanation, no code blocks.
        Your entire response should be parseable by json.loads().
        """

        return prompt + json_instruction

    async def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for text chunks
        """
        try:
            embeddings = []

            # Process in batches of 10
            batch_size = 10
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]

                # Generate embeddings
                batch_embeddings = []
                for text in batch:
                    result = genai.embed_content(
                        model=settings.gemini_embedding_model,
                        content=text,
                        task_type="retrieval_document"
                    )
                    batch_embeddings.append(result['embedding'])

                embeddings.extend(batch_embeddings)
                logging.info(f"Generated embeddings for batch {i//batch_size + 1}")

            return embeddings

        except Exception as e:
            logging.error(f"Embedding generation error: {str(e)}")
            raise

    async def generate_query_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for text chunks"""

        try:
            embeddings = []

            # Process in batches of 10
            batch_size = 10
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]

                # Generate embeddings
                batch_embeddings =  []
                for text in batch:
                    result = genai.embed_content(
                        model=settings.gemini_embedding_model,
                        content=text,
                        task_type="retrieval_document"
                    )
                    batch_embeddings.append(result["embedding"])

                embeddings.extend(batch_embeddings)
                logging.info(f"Generated embeddings for batch {i//batch_size + 1}")

            return embeddings

        except Exception as e:
            logging.error(f"Embedding generation error: {str(e)}")
            raise

# Singleton instance
_gemini_service = None

def get_gemini_service() -> GeminiServices:
    """
    Get or create GeminiServices singleton
    """

    global _gemini_service
    if _gemini_service is None:
        _gemini_service = GeminiServices()
    return _gemini_service
