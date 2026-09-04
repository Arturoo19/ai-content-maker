from fastapi import FastAPI

from ai_content_maker.api.health import router as health_router
from ai_content_maker.api.telegram import router as telegram_router


app = FastAPI(title="AI Content Maker")

app.include_router(health_router)
app.include_router(telegram_router)