import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ai_content_maker.config import settings


class TelegramPublisherError(Exception):
    pass


@dataclass(frozen=True)
class TelegramPublishResult:
    message_id: int


class TelegramPublisher:
    def __init__(self, chat_id: str | None = None) -> None:
        if settings.telegram_bot_token is None:
            raise ValueError("TELEGRAM_BOT_TOKEN is not configured.")
        if chat_id is None and settings.telegram_chat_id is None:
            raise ValueError("TELEGRAM_CHAT_ID is not configured.")

        self.bot_token = settings.telegram_bot_token
        self.chat_id = chat_id or settings.telegram_chat_id

    def publish(
        self,
        content: str,
        *,
        image_url: str | None = None,
    ) -> TelegramPublishResult:
        if image_url is None:
            method = "sendMessage"
            payload_data = {
                "chat_id": self.chat_id,
                "text": content,
            }
        else:
            method = "sendPhoto"
            payload_data = {
                "chat_id": self.chat_id,
                "photo": image_url,
                "caption": content,
            }

        url = f"https://api.telegram.org/bot{self.bot_token}/{method}"
        payload = urlencode(payload_data).encode("utf-8")
        request = Request(url, data=payload, method="POST")

        try:
            with urlopen(request, timeout=20) as response:
                response_data = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            error_body = error.read().decode("utf-8", errors="replace")
            try:
                error_data = json.loads(error_body)
            except json.JSONDecodeError:
                error_description = error.reason
            else:
                error_description = error_data.get("description", error.reason)

            raise TelegramPublisherError(
                f"Telegram API rejected the message: {error_description}"
            ) from error
        except URLError as error:
            raise TelegramPublisherError("Telegram API is unavailable.") from error
        except json.JSONDecodeError as error:
            raise TelegramPublisherError("Telegram API returned an invalid response.") from error

        if not response_data.get("ok"):
            raise TelegramPublisherError("Telegram API returned an unsuccessful response.")

        message_id = response_data.get("result", {}).get("message_id")
        if not isinstance(message_id, int):
            raise TelegramPublisherError("Telegram API response did not include a message id.")

        return TelegramPublishResult(message_id=message_id)
