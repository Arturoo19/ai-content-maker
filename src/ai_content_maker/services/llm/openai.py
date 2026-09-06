from openai import OpenAI, OpenAIError

from ai_content_maker.config import settings
from ai_content_maker.services.llm.base import LLMServiceError


class OpenAILLMService:
    def __init__(self) -> None:
        if settings.openai_api_key is None:
            raise ValueError("OPENAI_API_KEY is not configured.")

        self.client = OpenAI(api_key=settings.openai_api_key)

    def generate_text(self, prompt: str) -> str:
        try:
            response = self.client.responses.create(
                model=settings.openai_model,
                input=prompt,
            )
        except OpenAIError as error:
            raise LLMServiceError("OpenAI text generation failed.") from error

        return response.output_text
