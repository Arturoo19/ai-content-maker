from ai_content_maker.schemas.telegram import TelegramGenerateRequest

class TelegramContentGenerator:
    def generate(self, request: TelegramGenerateRequest) -> str:
        return(
            f"Draft Telegram post for project #{request.project_id}\n\n"
            f"Topic: {request.topic}\n\n"
            "This is a placeholder. Later, this service will call the LLM."
        )
    
