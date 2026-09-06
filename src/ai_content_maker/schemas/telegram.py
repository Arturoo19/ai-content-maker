from datetime import datetime

from pydantic import BaseModel, Field


class TelegramGenerateRequest(BaseModel):
    project_id: int = Field(gt=0)
    topic: str = Field(min_length=3, max_length=300)


class TelegramContentPlanGenerateRequest(BaseModel):
    project_id: int = Field(gt=0)
    post_count: int = Field(default=4, ge=1, le=10)


class TelegramGenerateResponse(BaseModel):
    content_id: int
    project_id: int
    topic: str
    content: str
    status: str


class TelegramPublishResponse(BaseModel):
    content_id: int
    status: str
    telegram_message_id: int


class TelegramDraftResponse(BaseModel):
    content_id: int
    project_id: int
    topic_id: int | None
    topic: str | None
    content: str
    status: str


class TelegramContentResponse(BaseModel):
    content_id: int
    project_id: int
    topic_id: int | None
    topic: str | None
    content: str
    status: str
    image_url: str | None
    image_source_url: str | None
    image_author: str | None
    image_license: str | None
    scheduled_at: datetime | None
    published_at: datetime | None


class TelegramReviewResponse(BaseModel):
    content_id: int
    status: str


class TelegramScheduleRequest(BaseModel):
    scheduled_at: datetime


class TelegramScheduleResponse(BaseModel):
    content_id: int
    status: str
    scheduled_at: datetime


class TelegramScheduledPublishItemResponse(BaseModel):
    content_id: int
    status: str
    telegram_message_id: int | None = None
    error: str | None = None


class TelegramScheduledPublishResponse(BaseModel):
    published_count: int
    failed_count: int
    results: list[TelegramScheduledPublishItemResponse]


class TelegramContentPlanGenerateResponse(BaseModel):
    project_id: int
    post_count: int
    drafts: list[TelegramDraftResponse]


class TelegramAdminDigestResponse(BaseModel):
    status: str
    draft_count: int
    telegram_message_id: int


class TelegramAdminImageDigestResponse(BaseModel):
    status: str
    content_id: int
    candidate_count: int
    telegram_message_ids: list[int]


class TelegramImageRequest(BaseModel):
    image_url: str = Field(min_length=1, max_length=1000)
    image_source_url: str | None = Field(default=None, max_length=1000)
    image_author: str | None = Field(default=None, max_length=300)
    image_license: str | None = Field(default=None, max_length=120)


class TelegramImageResponse(BaseModel):
    content_id: int
    image_url: str
    image_source_url: str | None
    image_author: str | None
    image_license: str | None


class TelegramImageCandidateResponse(BaseModel):
    title: str
    image_url: str
    source_url: str | None = None
    author: str | None = None
    license: str | None = None


class TelegramImageSuggestionsResponse(BaseModel):
    content_id: int
    query: str
    candidates: list[TelegramImageCandidateResponse]
