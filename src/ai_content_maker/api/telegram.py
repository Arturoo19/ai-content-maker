from datetime import UTC

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from ai_content_maker.db.session import get_session
from ai_content_maker.models.topic import Topic
from ai_content_maker.repositories.content_repository import ContentRepository
from ai_content_maker.schemas.telegram import (
    TelegramContentPlanGenerateRequest,
    TelegramContentPlanGenerateResponse,
    TelegramContentResponse,
    TelegramAdminDigestResponse,
    TelegramAdminImageDigestResponse,
    TelegramDraftResponse,
    TelegramGenerateRequest,
    TelegramGenerateResponse,
    TelegramImageCandidateResponse,
    TelegramImageRequest,
    TelegramImageResponse,
    TelegramImageSuggestionsResponse,
    TelegramPublishResponse,
    TelegramReviewResponse,
    TelegramScheduleRequest,
    TelegramScheduleResponse,
    TelegramScheduledPublishItemResponse,
    TelegramScheduledPublishResponse,
)
from ai_content_maker.services.content.telegram_content_plan import (
    TelegramContentPlanError,
    TelegramContentPlanGenerator,
)
from ai_content_maker.services.content.telegram_generator import TelegramContentGenerator
from ai_content_maker.services.images.wikimedia import (
    ImageSearchError,
    WikimediaImageSearchService,
)
from ai_content_maker.services.llm.base import LLMServiceError
from ai_content_maker.services.llm.openai import OpenAILLMService
from ai_content_maker.services.notifications.telegram_admin import (
    TelegramAdminNotificationError,
    TelegramAdminNotifier,
)
from ai_content_maker.services.publishing.telegram import (
    TelegramPublisher,
    TelegramPublisherError,
)
from ai_content_maker.services.publishing.scheduled import ScheduledTelegramPublisher

router = APIRouter(prefix="/telegram", tags=["telegram"])


def _content_response(content, topic: Topic | None) -> TelegramContentResponse:
    return TelegramContentResponse(
        content_id=content.id,
        project_id=content.project_id,
        topic_id=content.topic_id,
        topic=topic.title if topic is not None else None,
        content=content.content,
        status=content.status,
        image_url=content.image_url,
        image_source_url=content.image_source_url,
        image_author=content.image_author,
        image_license=content.image_license,
        scheduled_at=content.scheduled_at,
        published_at=content.published_at,
    )


@router.post("/generate", response_model=TelegramGenerateResponse)
def generate_telegram_post(
    request: TelegramGenerateRequest,
    session: Session = Depends(get_session),
) -> TelegramGenerateResponse:
    try:
        llm_service = OpenAILLMService()
    except ValueError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error

    generator = TelegramContentGenerator(llm_service)
    try:
        content = generator.generate(request)
    except LLMServiceError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

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


@router.post("/content-plan/generate", response_model=TelegramContentPlanGenerateResponse)
def generate_telegram_content_plan(
    request: TelegramContentPlanGenerateRequest,
    session: Session = Depends(get_session),
) -> TelegramContentPlanGenerateResponse:
    try:
        llm_service = OpenAILLMService()
    except ValueError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error

    plan_generator = TelegramContentPlanGenerator(llm_service)
    post_generator = TelegramContentGenerator(llm_service)
    try:
        topics = plan_generator.generate_topics(post_count=request.post_count)
        generated_posts = [
            (
                topic,
                post_generator.generate(
                    TelegramGenerateRequest(project_id=request.project_id, topic=topic)
                ),
            )
            for topic in topics
        ]
    except LLMServiceError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except TelegramContentPlanError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    repository = ContentRepository(session)
    drafts: list[TelegramDraftResponse] = []
    for topic, content in generated_posts:
        draft = repository.create_telegram_draft(
            project_id=request.project_id,
            topic_title=topic,
            content=content,
        )
        drafts.append(
            TelegramDraftResponse(
                content_id=draft.id,
                project_id=draft.project_id,
                topic_id=draft.topic_id,
                topic=topic,
                content=draft.content,
                status=draft.status,
            )
        )

    return TelegramContentPlanGenerateResponse(
        project_id=request.project_id,
        post_count=request.post_count,
        drafts=drafts,
    )


@router.get("/drafts", response_model=list[TelegramDraftResponse])
def list_telegram_drafts(
    project_id: int | None = Query(default=None, gt=0),
    limit: int = Query(default=20, gt=0, le=100),
    session: Session = Depends(get_session),
) -> list[TelegramDraftResponse]:
    repository = ContentRepository(session)
    drafts = repository.list_telegram_drafts(project_id=project_id, limit=limit)

    response: list[TelegramDraftResponse] = []
    for draft in drafts:
        topic = session.get(Topic, draft.topic_id) if draft.topic_id is not None else None
        response.append(
            TelegramDraftResponse(
                content_id=draft.id,
                project_id=draft.project_id,
                topic_id=draft.topic_id,
                topic=topic.title if topic is not None else None,
                content=draft.content,
                status=draft.status,
            )
        )

    return response


@router.get("/content", response_model=list[TelegramContentResponse])
def list_telegram_content(
    project_id: int | None = Query(default=None, gt=0),
    status: str | None = Query(default=None),
    limit: int = Query(default=20, gt=0, le=100),
    session: Session = Depends(get_session),
) -> list[TelegramContentResponse]:
    repository = ContentRepository(session)
    content_items = repository.list_telegram_content(
        project_id=project_id,
        status=status,
        limit=limit,
    )

    response: list[TelegramContentResponse] = []
    for content in content_items:
        topic = session.get(Topic, content.topic_id) if content.topic_id is not None else None
        response.append(_content_response(content, topic))

    return response


@router.post("/review/send-digest", response_model=TelegramAdminDigestResponse)
def send_telegram_review_digest(
    project_id: int | None = Query(default=None, gt=0),
    limit: int = Query(default=4, gt=0, le=10),
    session: Session = Depends(get_session),
) -> TelegramAdminDigestResponse:
    repository = ContentRepository(session)
    drafts = repository.list_telegram_drafts(project_id=project_id, limit=limit)
    topics_by_content_id: dict[int, str | None] = {}
    for draft in drafts:
        topic = session.get(Topic, draft.topic_id) if draft.topic_id is not None else None
        topics_by_content_id[draft.id] = topic.title if topic is not None else None

    try:
        notifier = TelegramAdminNotifier()
    except ValueError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error

    try:
        result = notifier.send_review_digest(
            drafts=drafts,
            topics_by_content_id=topics_by_content_id,
        )
    except TelegramAdminNotificationError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    return TelegramAdminDigestResponse(
        status="sent",
        draft_count=len(drafts),
        telegram_message_id=result.message_id,
    )


@router.post(
    "/review/{content_id}/send-images",
    response_model=TelegramAdminImageDigestResponse,
)
def send_telegram_review_images(
    content_id: int,
    query: str | None = Query(default=None, min_length=1, max_length=300),
    limit: int = Query(default=3, gt=0, le=5),
    session: Session = Depends(get_session),
) -> TelegramAdminImageDigestResponse:
    content = ContentRepository(session).get_by_id(content_id)
    if content is None:
        raise HTTPException(status_code=404, detail="Content was not found.")
    if content.platform != "telegram":
        raise HTTPException(status_code=400, detail="Content is not a Telegram post.")
    if content.status not in {"draft", "approved", "scheduled"}:
        raise HTTPException(
            status_code=400,
            detail="Image candidates can only be sent before content is published.",
        )

    topic = session.get(Topic, content.topic_id) if content.topic_id is not None else None
    image_query = query or (topic.title if topic is not None else content.content[:120])

    try:
        candidates = WikimediaImageSearchService().search(query=image_query, limit=limit)
    except ImageSearchError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    try:
        notifier = TelegramAdminNotifier()
    except ValueError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error

    try:
        results = notifier.send_image_candidates(
            content=content,
            topic=topic.title if topic is not None else None,
            candidates=candidates,
        )
    except TelegramAdminNotificationError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    return TelegramAdminImageDigestResponse(
        status="sent",
        content_id=content.id,
        candidate_count=len(candidates),
        telegram_message_ids=[result.message_id for result in results],
    )


@router.post("/{content_id}/suggest-images", response_model=TelegramImageSuggestionsResponse)
def suggest_telegram_images(
    content_id: int,
    query: str | None = Query(default=None, min_length=1, max_length=300),
    limit: int = Query(default=5, gt=0, le=10),
    session: Session = Depends(get_session),
) -> TelegramImageSuggestionsResponse:
    content = ContentRepository(session).get_by_id(content_id)
    if content is None:
        raise HTTPException(status_code=404, detail="Content was not found.")
    if content.platform != "telegram":
        raise HTTPException(status_code=400, detail="Content is not a Telegram post.")

    topic = session.get(Topic, content.topic_id) if content.topic_id is not None else None
    image_query = query or (topic.title if topic is not None else content.content[:120])

    try:
        candidates = WikimediaImageSearchService().search(query=image_query, limit=limit)
    except ImageSearchError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    return TelegramImageSuggestionsResponse(
        content_id=content.id,
        query=image_query,
        candidates=[
            TelegramImageCandidateResponse(
                title=candidate.title,
                image_url=candidate.image_url,
                source_url=candidate.source_url,
                author=candidate.author,
                license=candidate.license,
            )
            for candidate in candidates
        ],
    )


@router.post("/{content_id}/image", response_model=TelegramImageResponse)
def set_telegram_image(
    content_id: int,
    request: TelegramImageRequest,
    session: Session = Depends(get_session),
) -> TelegramImageResponse:
    repository = ContentRepository(session)
    content = repository.get_by_id(content_id)
    if content is None:
        raise HTTPException(status_code=404, detail="Content was not found.")
    if content.platform != "telegram":
        raise HTTPException(status_code=400, detail="Content is not a Telegram post.")
    if content.status not in {"draft", "approved", "scheduled"}:
        raise HTTPException(
            status_code=400,
            detail="Images can only be attached before content is published.",
        )

    updated = repository.set_image(
        content,
        image_url=request.image_url,
        image_source_url=request.image_source_url,
        image_author=request.image_author,
        image_license=request.image_license,
    )

    return TelegramImageResponse(
        content_id=updated.id,
        image_url=updated.image_url,
        image_source_url=updated.image_source_url,
        image_author=updated.image_author,
        image_license=updated.image_license,
    )


@router.post("/{content_id}/publish", response_model=TelegramPublishResponse)
def publish_telegram_post(
    content_id: int,
    session: Session = Depends(get_session),
) -> TelegramPublishResponse:
    repository = ContentRepository(session)
    draft = repository.get_by_id(content_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Content was not found.")
    if draft.platform != "telegram":
        raise HTTPException(status_code=400, detail="Content is not a Telegram post.")
    if draft.status not in {"approved", "scheduled"}:
        raise HTTPException(
            status_code=400,
            detail="Only approved or scheduled content can be published.",
        )

    try:
        publisher = TelegramPublisher()
    except ValueError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error

    try:
        publish_result = publisher.publish(
            draft.content,
            image_url=draft.image_url,
        )
    except TelegramPublisherError as error:
        repository.mark_failed(draft)
        raise HTTPException(status_code=502, detail=str(error)) from error

    published = repository.mark_published(draft)

    return TelegramPublishResponse(
        content_id=published.id,
        status=published.status,
        telegram_message_id=publish_result.message_id,
    )


@router.post("/{content_id}/approve", response_model=TelegramReviewResponse)
def approve_telegram_post(
    content_id: int,
    session: Session = Depends(get_session),
) -> TelegramReviewResponse:
    repository = ContentRepository(session)
    draft = repository.get_by_id(content_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Content was not found.")
    if draft.platform != "telegram":
        raise HTTPException(status_code=400, detail="Content is not a Telegram post.")
    if draft.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft content can be approved.")

    approved = repository.mark_approved(draft)

    return TelegramReviewResponse(
        content_id=approved.id,
        status=approved.status,
    )


@router.post("/{content_id}/reject", response_model=TelegramReviewResponse)
def reject_telegram_post(
    content_id: int,
    session: Session = Depends(get_session),
) -> TelegramReviewResponse:
    repository = ContentRepository(session)
    draft = repository.get_by_id(content_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Content was not found.")
    if draft.platform != "telegram":
        raise HTTPException(status_code=400, detail="Content is not a Telegram post.")
    if draft.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft content can be rejected.")

    rejected = repository.mark_rejected(draft)

    return TelegramReviewResponse(
        content_id=rejected.id,
        status=rejected.status,
    )


@router.post("/{content_id}/schedule", response_model=TelegramScheduleResponse)
def schedule_telegram_post(
    content_id: int,
    request: TelegramScheduleRequest,
    session: Session = Depends(get_session),
) -> TelegramScheduleResponse:
    repository = ContentRepository(session)
    approved = repository.get_by_id(content_id)
    if approved is None:
        raise HTTPException(status_code=404, detail="Content was not found.")
    if approved.platform != "telegram":
        raise HTTPException(status_code=400, detail="Content is not a Telegram post.")
    if approved.status != "approved":
        raise HTTPException(status_code=400, detail="Only approved content can be scheduled.")
    if request.scheduled_at.tzinfo is None:
        raise HTTPException(status_code=400, detail="scheduled_at must include a timezone.")

    scheduled_at = request.scheduled_at.astimezone(UTC)
    scheduled = repository.mark_scheduled(approved, scheduled_at)
    response_scheduled_at = scheduled.scheduled_at
    if response_scheduled_at.tzinfo is None:
        response_scheduled_at = response_scheduled_at.replace(tzinfo=UTC)

    return TelegramScheduleResponse(
        content_id=scheduled.id,
        status=scheduled.status,
        scheduled_at=response_scheduled_at,
    )


@router.post("/scheduled/publish-due", response_model=TelegramScheduledPublishResponse)
def publish_due_scheduled_telegram_posts(
    limit: int = Query(default=20, gt=0, le=100),
    session: Session = Depends(get_session),
) -> TelegramScheduledPublishResponse:
    repository = ContentRepository(session)
    try:
        publisher = TelegramPublisher()
    except ValueError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error

    scheduled_publisher = ScheduledTelegramPublisher(repository, publisher)
    result = scheduled_publisher.publish_due(limit=limit)

    return TelegramScheduledPublishResponse(
        published_count=result.published_count,
        failed_count=result.failed_count,
        results=[
            TelegramScheduledPublishItemResponse(
                content_id=item.content_id,
                status=item.status,
                telegram_message_id=item.telegram_message_id,
                error=item.error,
            )
            for item in result.results
        ],
    )
