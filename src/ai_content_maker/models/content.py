from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class Content(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(index=True)
    channel_id: int | None = Field(default=None, index=True)
    topic_id: int | None = Field(default=None, index=True)
    platform: str = Field(index=True, max_length=30)
    content: str
    status: str = Field(default="draft", index=True, max_length=30)
    image_url: str | None = Field(default=None, max_length=1000)
    image_source_url: str | None = Field(default=None, max_length=1000)
    image_author: str | None = Field(default=None, max_length=300)
    image_license: str | None = Field(default=None, max_length=120)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    scheduled_at: datetime | None = None
    published_at: datetime | None = None
