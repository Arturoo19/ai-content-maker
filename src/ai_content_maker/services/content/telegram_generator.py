from pathlib import Path

from ai_content_maker.schemas.telegram import TelegramGenerateRequest
from ai_content_maker.services.llm.base import LLMService


DEFAULT_PROMPT_TEMPLATE_PATH = (
    Path(__file__).resolve().parents[4] / "prompts" / "telegram" / "default.txt"
)


class TelegramContentGenerator:
    def __init__(self, llm_service: LLMService) -> None:
        self.llm_service = llm_service

    def generate(self, request: TelegramGenerateRequest) -> str:
        prompt_template = DEFAULT_PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8")

        prompt = prompt_template.format(
            project_id=request.project_id,
            topic=request.topic,
        )

        return self.llm_service.generate_text(prompt)
