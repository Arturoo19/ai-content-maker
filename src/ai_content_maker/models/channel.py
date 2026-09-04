from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class Channel(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    project_id: int = Field(index=True)
    platform: str = Field(index=True, max_length=30)
    name: str = Field(max_length=120)
    external_id: str | None = Field(default=None, max_length=200)
    settings: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
