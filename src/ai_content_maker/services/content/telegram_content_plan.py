import json
from pathlib import Path

from ai_content_maker.services.llm.base import LLMService, LLMServiceError


CONTENT_PLAN_PROMPT_TEMPLATE_PATH = (
    Path(__file__).resolve().parents[4] / "prompts" / "telegram" / "content_plan.txt"
)


class TelegramContentPlanError(Exception):
    pass


class TelegramContentPlanGenerator:
    def __init__(self, llm_service: LLMService) -> None:
        self.llm_service = llm_service

    def generate_topics(self, *, post_count: int) -> list[str]:
        prompt_template = CONTENT_PLAN_PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8")
        prompt = prompt_template.format(post_count=post_count)

        try:
            response_text = self.llm_service.generate_text(prompt)
        except LLMServiceError:
            raise

        try:
            topics = json.loads(response_text)
        except json.JSONDecodeError as error:
            raise TelegramContentPlanError("LLM returned an invalid content plan.") from error

        if not isinstance(topics, list):
            raise TelegramContentPlanError("LLM content plan must be a JSON array.")

        clean_topics: list[str] = []
        for topic in topics:
            if not isinstance(topic, str):
                raise TelegramContentPlanError("Every content plan item must be a string.")

            clean_topic = topic.strip()
            if clean_topic:
                clean_topics.append(clean_topic)

        if len(clean_topics) != post_count:
            raise TelegramContentPlanError("LLM returned the wrong number of content topics.")

        return clean_topics
