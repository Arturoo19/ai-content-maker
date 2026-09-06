from dataclasses import dataclass

from ai_content_maker.config import settings
from ai_content_maker.models.content import Content
from ai_content_maker.services.images.wikimedia import ImageCandidate
from ai_content_maker.services.publishing.telegram import (
    TelegramPublisher,
    TelegramPublisherError,
)


class TelegramAdminNotificationError(Exception):
    pass


@dataclass(frozen=True)
class TelegramAdminNotificationResult:
    message_id: int


class TelegramAdminNotifier:
    def __init__(self) -> None:
        if settings.telegram_admin_chat_id is None:
            raise ValueError("TELEGRAM_ADMIN_CHAT_ID is not configured.")

        self.publisher = TelegramPublisher(chat_id=settings.telegram_admin_chat_id)

    def send_review_digest(
        self,
        *,
        drafts: list[Content],
        topics_by_content_id: dict[int, str | None],
    ) -> TelegramAdminNotificationResult:
        message = self._format_review_digest(
            drafts=drafts,
            topics_by_content_id=topics_by_content_id,
        )

        try:
            result = self.publisher.publish(message)
        except TelegramPublisherError as error:
            raise TelegramAdminNotificationError(str(error)) from error

        return TelegramAdminNotificationResult(message_id=result.message_id)

    def send_image_candidates(
        self,
        *,
        content: Content,
        topic: str | None,
        candidates: list[ImageCandidate],
    ) -> list[TelegramAdminNotificationResult]:
        if content.id is None:
            raise TelegramAdminNotificationError("Content does not have an id.")

        if not candidates:
            message = (
                f"Для ID {content.id} не знайшов нормальних фото.\n"
                "Можеш надіслати своє фото в цей чат."
            )
            try:
                result = self.publisher.publish(message)
            except TelegramPublisherError as error:
                raise TelegramAdminNotificationError(str(error)) from error

            return [TelegramAdminNotificationResult(message_id=result.message_id)]

        results: list[TelegramAdminNotificationResult] = []
        for index, candidate in enumerate(candidates, start=1):
            caption = self._format_image_candidate_caption(
                content_id=content.id,
                topic=topic,
                index=index,
                candidate=candidate,
            )
            try:
                result = self.publisher.publish(caption, image_url=candidate.image_url)
            except TelegramPublisherError as error:
                raise TelegramAdminNotificationError(str(error)) from error

            results.append(TelegramAdminNotificationResult(message_id=result.message_id))

        return results

    def _format_review_digest(
        self,
        *,
        drafts: list[Content],
        topics_by_content_id: dict[int, str | None],
    ) -> str:
        if not drafts:
            return "Нових чернеток на рев'ю поки немає."

        lines = [
            "План постів на рев'ю",
            "",
            "Переглянь з телефону і вибери, що робимо далі.",
        ]

        for index, draft in enumerate(drafts, start=1):
            topic = topics_by_content_id.get(draft.id) or "Без теми"
            image_status = "фото додано" if draft.image_url else "фото ще не вибрано"
            preview = self._shorten(draft.content)
            lines.extend(
                [
                    "",
                    f"{index}. ID {draft.id}: {topic}",
                    f"Фото: {image_status}",
                    preview,
                    "",
                    f"Команди: /approve {draft.id} | /reject {draft.id} | /images {draft.id}",
                ]
            )

        lines.extend(
            [
                "",
                "Якщо фото не підходить, надішли мені своє фото в цей чат.",
            ]
        )

        return "\n".join(lines)

    def _format_image_candidate_caption(
        self,
        *,
        content_id: int,
        topic: str | None,
        index: int,
        candidate: ImageCandidate,
    ) -> str:
        lines = [
            f"Фото {index} для ID {content_id}",
            topic or "Без теми",
            "",
            candidate.title,
        ]
        if candidate.license:
            lines.append(f"Ліцензія: {candidate.license}")
        if candidate.source_url:
            lines.append(f"Джерело: {candidate.source_url}")

        lines.extend(
            [
                "",
                f"Щоб вибрати: /set_image {content_id} {candidate.image_url}",
            ]
        )

        return "\n".join(lines)

    def _shorten(self, text: str, max_length: int = 550) -> str:
        normalized = " ".join(text.split())
        if len(normalized) <= max_length:
            return normalized

        return f"{normalized[: max_length - 1].rstrip()}..."
