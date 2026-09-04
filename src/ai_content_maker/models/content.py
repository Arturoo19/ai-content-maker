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
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    scheduled_at: datetime | None = None
    published_at: datetime | None = None
