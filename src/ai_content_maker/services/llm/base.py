from typing import Protocol


class LLMServiceError(Exception):
    pass


class LLMService(Protocol):
    def generate_text(self, prompt: str) -> str:
        ...
