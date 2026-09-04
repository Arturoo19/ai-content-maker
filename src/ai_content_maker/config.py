import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_name: str = "AI Content Maker"
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    telegram_bot_token: str | None = os.getenv("TELEGRAM_BOT_TOKEN")
    database_url: str | None = os.getenv("DATABASE_URL")


settings = Settings()