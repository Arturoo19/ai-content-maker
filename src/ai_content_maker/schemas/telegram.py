from pydantic import BaseModel, Field

class TelegramGenerateRequest(BaseModel):
    project_id: int = Field(gt=0)
    topic: str = Field(min_length=3, max_length=300)


class TelegramGenerateResponse(BaseModel):
    project_id: int
    topic: str
    content: str
