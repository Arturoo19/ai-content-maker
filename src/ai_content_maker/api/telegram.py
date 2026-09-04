from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from ai_content_maker.db.session import get_session
from ai_content_maker.repositories.content_repository import ContentRepository
from ai_content_maker.schemas.telegram import (
    TelegramGenerateRequest,
    TelegramGenerateResponse,
)
from ai_content_maker.services.content.telegram_generator import TelegramContentGenerator

router = APIRouter(prefix="/telegram", tags=["telegram"])


@router.post("/generate", response_model=TelegramGenerateResponse)
def generate_telegram_post(
    request: TelegramGenerateRequest,
    session: Session = Depends(get_session),
) -> TelegramGenerateResponse:
    generator = TelegramContentGenerator()
    content = generator.generate(request)
    repository = ContentRepository(session)
    draft = repository.create_telegram_draft(
        project_id=request.project_id,
        topic_title=request.topic,
        content=content,
    )
    if draft.id is None:
        raise HTTPException(
            status_code=500,
            detail="Generated Telegram draft was saved without an id.",
        )

    return TelegramGenerateResponse(
        content_id=draft.id,
        project_id=request.project_id,
        topic=request.topic,
        content=draft.content,
        status=draft.status,
    )
