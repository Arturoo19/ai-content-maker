from dataclasses import dataclass, field
from datetime import UTC, datetime

from ai_content_maker.repositories.content_repository import ContentRepository
from ai_content_maker.services.publishing.telegram import (
    TelegramPublisher,
    TelegramPublisherError,
)


@dataclass(frozen=True)
class ScheduledPublishItemResult:
    content_id: int
    status: str
    telegram_message_id: int | None = None
    error: str | None = None


@dataclass(frozen=True)
class ScheduledPublishResult:
    published_count: int = 0
    failed_count: int = 0
    results: list[ScheduledPublishItemResult] = field(default_factory=list)


class ScheduledTelegramPublisher:
    def __init__(
        self,
        repository: ContentRepository,
        publisher: TelegramPublisher,
    ) -> None:
        self.repository = repository
        self.publisher = publisher

    def publish_due(self, *, now: datetime | None = None, limit: int = 20) -> ScheduledPublishResult:
        now = now or datetime.now(UTC)
        due_posts = self.repository.list_due_telegram_posts(now=now, limit=limit)

        published_count = 0
        failed_count = 0
        results: list[ScheduledPublishItemResult] = []

        for post in due_posts:
            if post.id is None:
                continue

            try:
                publish_result = self.publisher.publish(
                    post.content,
                    image_url=post.image_url,
                )
            except TelegramPublisherError as error:
                failed = self.repository.mark_failed(post)
                failed_count += 1
                results.append(
                    ScheduledPublishItemResult(
                        content_id=post.id,
                        status=failed.status,
                        error=str(error),
                    )
                )
                continue

            published = self.repository.mark_published(post)
            published_count += 1
            results.append(
                ScheduledPublishItemResult(
                    content_id=post.id,
                    status=published.status,
                    telegram_message_id=publish_result.message_id,
                )
            )

        return ScheduledPublishResult(
            published_count=published_count,
            failed_count=failed_count,
            results=results,
        )
