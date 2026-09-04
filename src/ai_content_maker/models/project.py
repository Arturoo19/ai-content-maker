from datetime import UTC, datetime

from sqlmodel import Field, SQLModel


class Project(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    niche: str | None = Field(default=None, max_length=120)
    language: str = Field(default="en", max_length=10)
    status: str = Field(default="active", max_length=30)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
