from fastapi import APIRouter

from ai_content_maker.schemas.telegram import (
    TelegramGenerateRequest,
    TelegramGenerateResponse,
)
from ai_content_maker.services.content.telegram_generator import TelegramContentGenerator

router = APIRouter(prefix="/telegram", tags=["telegram"])

@router.post("/generate", response_model=TelegramGenerateResponse)
def generate_telegram_post(
    request: TelegramGenerateRequest,
) -> TelegramGenerateResponse:
    generator = TelegramContentGenerator()
    content = generator.generate(request)

    return TelegramGenerateResponse(
        project_id=request.project_id,
        topic= request.topic,
        content= content,
    )
