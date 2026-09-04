from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class Topic(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(index=True)
    title: str = Field(index=True, min_length=3, max_length=300)
    description: str | None = Field(default=None, max_length=1000)
    source: str = Field(default="manual", max_length=60)
    source_url: str | None = Field(default=None, max_length=500)
    status: str = Field(default="new", max_length=30)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
