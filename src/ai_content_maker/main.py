from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI

from ai_content_maker.api.health import router as health_router
from ai_content_maker.api.telegram import router as telegram_router
from ai_content_maker.db.session import create_db_and_tables


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    create_db_and_tables()
    yield


app = FastAPI(title="AI Content Maker", lifespan=lifespan)

app.include_router(health_router)
app.include_router(telegram_router)
