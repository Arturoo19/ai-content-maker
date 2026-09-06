import unittest
import json
from collections.abc import Generator
from datetime import UTC, datetime
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from ai_content_maker.db.session import get_session
from ai_content_maker.main import app
from ai_content_maker.models.content import Content
from ai_content_maker.models.topic import Topic
from ai_content_maker.repositories.content_repository import ContentRepository
from ai_content_maker.schemas.telegram import TelegramGenerateRequest
from ai_content_maker.services.content.telegram_content_plan import (
    TelegramContentPlanGenerator,
)
from ai_content_maker.services.content.telegram_generator import TelegramContentGenerator
from ai_content_maker.services.llm.base import LLMServiceError
from ai_content_maker.services.images.wikimedia import ImageCandidate
from ai_content_maker.services.notifications.telegram_admin import (
    TelegramAdminNotificationResult,
)
from ai_content_maker.services.publishing.telegram import (
    TelegramPublisherError,
    TelegramPublishResult,
)


class FakeLLMService:
    def generate_text(self, prompt: str) -> str:
        return f"Generated from prompt: {prompt.splitlines()[0]}"


class FakePlanLLMService:
    def generate_text(self, prompt: str) -> str:
        if "Generate 3 post topics." in prompt:
            return json.dumps(
                [
                    "Чому Nokia починала не з телефонів, а з паперової фабрики",
                    "Як випадкова помилка трейдера може обвалити ринок на мільярди",
                    "Чому Wi-Fi насправді не означає Wireless Fidelity",
                ],
                ensure_ascii=False,
            )

        return f"Generated post from topic prompt: {prompt.splitlines()[2]}"


class FailingLLMService:
    def generate_text(self, prompt: str) -> str:
        raise LLMServiceError("fake LLM failure")


class FakeTelegramPublisher:
    last_image_url: str | None = None

    def publish(
        self,
        content: str,
        *,
        image_url: str | None = None,
    ) -> TelegramPublishResult:
        FakeTelegramPublisher.last_image_url = image_url
        return TelegramPublishResult(message_id=123)


class FailingTelegramPublisher:
    def publish(
        self,
        content: str,
        *,
        image_url: str | None = None,
    ) -> TelegramPublishResult:
        raise TelegramPublisherError("fake Telegram failure")


class FakeImageSearchService:
    def search(self, *, query: str, limit: int = 5) -> list[ImageCandidate]:
        return [
            ImageCandidate(
                title="File:Example.jpg",
                image_url="https://example.com/image.jpg",
                source_url="https://commons.wikimedia.org/wiki/File:Example.jpg",
                author="Example author",
                license="CC BY-SA 4.0",
            )
        ][:limit]


class FakeAdminNotifier:
    last_topics_by_content_id: dict[int, str | None] = {}
    last_image_candidate_count: int = 0

    def send_review_digest(
        self,
        *,
        drafts: list[Content],
        topics_by_content_id: dict[int, str | None],
    ) -> TelegramAdminNotificationResult:
        FakeAdminNotifier.last_topics_by_content_id = topics_by_content_id
        return TelegramAdminNotificationResult(message_id=456)

    def send_image_candidates(
        self,
        *,
        content: Content,
        topic: str | None,
        candidates: list[ImageCandidate],
    ) -> list[TelegramAdminNotificationResult]:
        FakeAdminNotifier.last_image_candidate_count = len(candidates)
        return [TelegramAdminNotificationResult(message_id=789)]


class TelegramGenerationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(self.engine)

        def get_test_session() -> Generator[Session, None, None]:
            with Session(self.engine) as session:
                yield session

        app.dependency_overrides[get_session] = get_test_session
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        self.engine.dispose()

    def test_telegram_generator_renders_prompt_and_calls_llm(self) -> None:
        request = TelegramGenerateRequest(
            project_id=7,
            topic="How to write better hooks",
        )

        content = TelegramContentGenerator(FakeLLMService()).generate(request)

        self.assertEqual(
            content,
            "Generated from prompt: Write a short Ukrainian Telegram post for project #7.",
        )

    def test_content_plan_generator_returns_topics(self) -> None:
        topics = TelegramContentPlanGenerator(FakePlanLLMService()).generate_topics(
            post_count=3
        )

        self.assertEqual(
            topics,
            [
                "Чому Nokia починала не з телефонів, а з паперової фабрики",
                "Як випадкова помилка трейдера може обвалити ринок на мільярди",
                "Чому Wi-Fi насправді не означає Wireless Fidelity",
            ],
        )

    def test_generate_endpoint_saves_generated_draft(self) -> None:
        with patch(
            "ai_content_maker.api.telegram.OpenAILLMService",
            return_value=FakeLLMService(),
        ):
            response = self.client.post(
                "/telegram/generate",
                json={
                    "project_id": 1,
                    "topic": "One useful writing habit",
                },
            )

        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data["status"], "draft")
        self.assertEqual(response_data["project_id"], 1)
        self.assertEqual(response_data["topic"], "One useful writing habit")
        self.assertTrue(response_data["content_id"] > 0)

        with Session(self.engine) as session:
            draft = session.get(Content, response_data["content_id"])
            topic = session.exec(select(Topic)).one()

        self.assertIsNotNone(draft)
        self.assertEqual(draft.status, "draft")
        self.assertEqual(draft.content, response_data["content"])
        self.assertEqual(topic.title, "One useful writing habit")

    def test_content_plan_endpoint_generates_multiple_drafts(self) -> None:
        with patch(
            "ai_content_maker.api.telegram.OpenAILLMService",
            return_value=FakePlanLLMService(),
        ):
            response = self.client.post(
                "/telegram/content-plan/generate",
                json={"project_id": 1, "post_count": 3},
            )

        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data["project_id"], 1)
        self.assertEqual(response_data["post_count"], 3)
        self.assertEqual(len(response_data["drafts"]), 3)
        self.assertEqual({draft["status"] for draft in response_data["drafts"]}, {"draft"})

        with Session(self.engine) as session:
            drafts = session.exec(select(Content).where(Content.status == "draft")).all()
            topics = session.exec(select(Topic)).all()

        self.assertEqual(len(drafts), 3)
        self.assertEqual(len(topics), 3)

    def test_generate_endpoint_returns_502_when_llm_fails(self) -> None:
        with patch(
            "ai_content_maker.api.telegram.OpenAILLMService",
            return_value=FailingLLMService(),
        ):
            response = self.client.post(
                "/telegram/generate",
                json={
                    "project_id": 1,
                    "topic": "One useful writing habit",
                },
            )

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json(), {"detail": "fake LLM failure"})

    def test_drafts_endpoint_returns_only_telegram_drafts(self) -> None:
        with Session(self.engine) as session:
            repository = ContentRepository(session)
            first_draft = repository.create_telegram_draft(
                project_id=1,
                topic_title="First draft",
                content="First draft content",
            )
            second_draft = repository.create_telegram_draft(
                project_id=1,
                topic_title="Second draft",
                content="Second draft content",
            )
            published = repository.create_telegram_draft(
                project_id=1,
                topic_title="Already published",
                content="Published content",
            )
            repository.mark_published(published)
            first_draft_id = first_draft.id
            second_draft_id = second_draft.id
            published_id = published.id

        response = self.client.get("/telegram/drafts", params={"project_id": 1})

        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        content_ids = {item["content_id"] for item in response_data}

        self.assertEqual(len(response_data), 2)
        self.assertIn(first_draft_id, content_ids)
        self.assertIn(second_draft_id, content_ids)
        self.assertNotIn(published_id, content_ids)
        self.assertEqual({item["status"] for item in response_data}, {"draft"})

    def test_content_endpoint_filters_by_status(self) -> None:
        with Session(self.engine) as session:
            repository = ContentRepository(session)
            draft = repository.create_telegram_draft(
                project_id=1,
                topic_title="Draft content",
                content="Draft content",
            )
            approved = repository.mark_approved(
                repository.create_telegram_draft(
                    project_id=1,
                    topic_title="Approved content",
                    content="Approved content",
                )
            )
            draft_id = draft.id
            approved_id = approved.id

        response = self.client.get(
            "/telegram/content",
            params={"project_id": 1, "status": "approved"},
        )

        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(len(response_data), 1)
        self.assertEqual(response_data[0]["content_id"], approved_id)
        self.assertEqual(response_data[0]["status"], "approved")
        self.assertNotEqual(response_data[0]["content_id"], draft_id)

    def test_review_digest_endpoint_sends_drafts_to_admin_chat(self) -> None:
        FakeAdminNotifier.last_topics_by_content_id = {}
        with Session(self.engine) as session:
            repository = ContentRepository(session)
            first_draft = repository.create_telegram_draft(
                project_id=1,
                topic_title="First review topic",
                content="First review content",
            )
            second_draft = repository.create_telegram_draft(
                project_id=1,
                topic_title="Second review topic",
                content="Second review content",
            )
            repository.mark_published(
                repository.create_telegram_draft(
                    project_id=1,
                    topic_title="Already published",
                    content="Published content",
                )
            )
            first_draft_id = first_draft.id
            second_draft_id = second_draft.id

        self.assertIsNotNone(first_draft_id)
        self.assertIsNotNone(second_draft_id)

        with patch(
            "ai_content_maker.api.telegram.TelegramAdminNotifier",
            return_value=FakeAdminNotifier(),
        ):
            response = self.client.post(
                "/telegram/review/send-digest",
                params={"project_id": 1},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "status": "sent",
                "draft_count": 2,
                "telegram_message_id": 456,
            },
        )
        self.assertEqual(
            set(FakeAdminNotifier.last_topics_by_content_id.values()),
            {"First review topic", "Second review topic"},
        )

    def test_review_images_endpoint_sends_image_candidates_to_admin_chat(self) -> None:
        FakeAdminNotifier.last_image_candidate_count = 0
        with Session(self.engine) as session:
            draft = ContentRepository(session).create_telegram_draft(
                project_id=1,
                topic_title="Nokia paper mill fact",
                content="Draft with fact",
            )
            draft_id = draft.id

        self.assertIsNotNone(draft_id)

        with patch(
            "ai_content_maker.api.telegram.WikimediaImageSearchService",
            return_value=FakeImageSearchService(),
        ), patch(
            "ai_content_maker.api.telegram.TelegramAdminNotifier",
            return_value=FakeAdminNotifier(),
        ):
            response = self.client.post(f"/telegram/review/{draft_id}/send-images")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "status": "sent",
                "content_id": draft_id,
                "candidate_count": 1,
                "telegram_message_ids": [789],
            },
        )
        self.assertEqual(FakeAdminNotifier.last_image_candidate_count, 1)

    def test_set_image_endpoint_attaches_image_to_content(self) -> None:
        with Session(self.engine) as session:
            draft = ContentRepository(session).create_telegram_draft(
                project_id=1,
                topic_title="Image draft",
                content="Draft with image",
            )
            draft_id = draft.id

        self.assertIsNotNone(draft_id)

        response = self.client.post(
            f"/telegram/{draft_id}/image",
            json={
                "image_url": "https://example.com/image.jpg",
                "image_source_url": "https://commons.wikimedia.org/wiki/File:Example.jpg",
                "image_author": "Example author",
                "image_license": "CC BY-SA 4.0",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["image_url"], "https://example.com/image.jpg")

        with Session(self.engine) as session:
            updated = session.get(Content, draft_id)

        self.assertIsNotNone(updated)
        self.assertEqual(updated.image_url, "https://example.com/image.jpg")
        self.assertEqual(updated.image_license, "CC BY-SA 4.0")

    def test_suggest_images_endpoint_returns_candidates(self) -> None:
        with Session(self.engine) as session:
            draft = ContentRepository(session).create_telegram_draft(
                project_id=1,
                topic_title="Nokia paper mill fact",
                content="Draft with fact",
            )
            draft_id = draft.id

        self.assertIsNotNone(draft_id)

        with patch(
            "ai_content_maker.api.telegram.WikimediaImageSearchService",
            return_value=FakeImageSearchService(),
        ):
            response = self.client.post(f"/telegram/{draft_id}/suggest-images")

        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data["content_id"], draft_id)
        self.assertEqual(response_data["query"], "Nokia paper mill fact")
        self.assertEqual(response_data["candidates"][0]["image_url"], "https://example.com/image.jpg")
        self.assertEqual(response_data["candidates"][0]["license"], "CC BY-SA 4.0")

    def test_suggest_images_endpoint_accepts_search_query_override(self) -> None:
        with Session(self.engine) as session:
            draft = ContentRepository(session).create_telegram_draft(
                project_id=1,
                topic_title="Українська тема",
                content="Draft with fact",
            )
            draft_id = draft.id

        self.assertIsNotNone(draft_id)

        with patch(
            "ai_content_maker.api.telegram.WikimediaImageSearchService",
            return_value=FakeImageSearchService(),
        ):
            response = self.client.post(
                f"/telegram/{draft_id}/suggest-images",
                params={"query": "English search query"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["query"], "English search query")

    def test_publish_endpoint_publishes_approved_content(self) -> None:
        with Session(self.engine) as session:
            draft = ContentRepository(session).create_telegram_draft(
                project_id=1,
                topic_title="Publish this post",
                content="Ready to publish",
            )
            draft_id = draft.id

        self.assertIsNotNone(draft_id)
        approve_response = self.client.post(f"/telegram/{draft_id}/approve")
        self.assertEqual(approve_response.status_code, 200)

        with patch(
            "ai_content_maker.api.telegram.TelegramPublisher",
            return_value=FakeTelegramPublisher(),
        ):
            response = self.client.post(f"/telegram/{draft_id}/publish")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "content_id": draft_id,
                "status": "published",
                "telegram_message_id": 123,
            },
        )

        with Session(self.engine) as session:
            published = session.get(Content, draft_id)

        self.assertIsNotNone(published)
        self.assertEqual(published.status, "published")
        self.assertIsNotNone(published.published_at)

    def test_publish_endpoint_sends_image_url_when_present(self) -> None:
        FakeTelegramPublisher.last_image_url = None
        with Session(self.engine) as session:
            repository = ContentRepository(session)
            draft = repository.create_telegram_draft(
                project_id=1,
                topic_title="Publish with image",
                content="Ready to publish with image",
            )
            repository.set_image(draft, image_url="https://example.com/image.jpg")
            draft_id = draft.id

        self.assertIsNotNone(draft_id)
        approve_response = self.client.post(f"/telegram/{draft_id}/approve")
        self.assertEqual(approve_response.status_code, 200)

        with patch(
            "ai_content_maker.api.telegram.TelegramPublisher",
            return_value=FakeTelegramPublisher(),
        ):
            response = self.client.post(f"/telegram/{draft_id}/publish")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(FakeTelegramPublisher.last_image_url, "https://example.com/image.jpg")

    def test_publish_endpoint_requires_approved_or_scheduled_content(self) -> None:
        with Session(self.engine) as session:
            draft = ContentRepository(session).create_telegram_draft(
                project_id=1,
                topic_title="Not approved yet",
                content="Ready to publish",
            )
            draft_id = draft.id

        self.assertIsNotNone(draft_id)

        response = self.client.post(f"/telegram/{draft_id}/publish")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            {"detail": "Only approved or scheduled content can be published."},
        )

    def test_approve_endpoint_marks_draft_approved(self) -> None:
        with Session(self.engine) as session:
            draft = ContentRepository(session).create_telegram_draft(
                project_id=1,
                topic_title="Approve this post",
                content="Ready for review",
            )
            draft_id = draft.id

        self.assertIsNotNone(draft_id)

        response = self.client.post(f"/telegram/{draft_id}/approve")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"content_id": draft_id, "status": "approved"})

        with Session(self.engine) as session:
            approved = session.get(Content, draft_id)

        self.assertIsNotNone(approved)
        self.assertEqual(approved.status, "approved")

    def test_reject_endpoint_marks_draft_rejected(self) -> None:
        with Session(self.engine) as session:
            draft = ContentRepository(session).create_telegram_draft(
                project_id=1,
                topic_title="Reject this post",
                content="Not good enough",
            )
            draft_id = draft.id

        self.assertIsNotNone(draft_id)

        response = self.client.post(f"/telegram/{draft_id}/reject")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"content_id": draft_id, "status": "rejected"})

        with Session(self.engine) as session:
            rejected = session.get(Content, draft_id)

        self.assertIsNotNone(rejected)
        self.assertEqual(rejected.status, "rejected")

    def test_schedule_endpoint_marks_approved_content_scheduled(self) -> None:
        scheduled_at = "2026-09-07T10:00:00Z"
        with Session(self.engine) as session:
            draft = ContentRepository(session).create_telegram_draft(
                project_id=1,
                topic_title="Schedule this post",
                content="Ready to schedule",
            )
            draft_id = draft.id

        self.assertIsNotNone(draft_id)
        approve_response = self.client.post(f"/telegram/{draft_id}/approve")
        self.assertEqual(approve_response.status_code, 200)

        response = self.client.post(
            f"/telegram/{draft_id}/schedule",
            json={"scheduled_at": scheduled_at},
        )

        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data["content_id"], draft_id)
        self.assertEqual(response_data["status"], "scheduled")
        self.assertEqual(response_data["scheduled_at"], "2026-09-07T10:00:00Z")

        with Session(self.engine) as session:
            scheduled = session.get(Content, draft_id)

        self.assertIsNotNone(scheduled)
        self.assertEqual(scheduled.status, "scheduled")
        self.assertEqual(scheduled.scheduled_at, datetime(2026, 9, 7, 10))

    def test_schedule_endpoint_requires_approved_content(self) -> None:
        with Session(self.engine) as session:
            draft = ContentRepository(session).create_telegram_draft(
                project_id=1,
                topic_title="Schedule draft",
                content="Not approved yet",
            )
            draft_id = draft.id

        self.assertIsNotNone(draft_id)

        response = self.client.post(
            f"/telegram/{draft_id}/schedule",
            json={"scheduled_at": "2026-09-07T10:00:00Z"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"detail": "Only approved content can be scheduled."})

    def test_schedule_endpoint_requires_timezone(self) -> None:
        with Session(self.engine) as session:
            draft = ContentRepository(session).create_telegram_draft(
                project_id=1,
                topic_title="Schedule without timezone",
                content="Ready to schedule",
            )
            draft_id = draft.id

        self.assertIsNotNone(draft_id)
        approve_response = self.client.post(f"/telegram/{draft_id}/approve")
        self.assertEqual(approve_response.status_code, 200)

        response = self.client.post(
            f"/telegram/{draft_id}/schedule",
            json={"scheduled_at": "2026-09-07T10:00:00"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"detail": "scheduled_at must include a timezone."})

    def test_publish_endpoint_allows_scheduled_content(self) -> None:
        with Session(self.engine) as session:
            draft = ContentRepository(session).create_telegram_draft(
                project_id=1,
                topic_title="Publish scheduled post",
                content="Scheduled content",
            )
            scheduled = ContentRepository(session).mark_scheduled(
                ContentRepository(session).mark_approved(draft),
                datetime(2026, 9, 7, 10, tzinfo=UTC),
            )
            scheduled_id = scheduled.id

        self.assertIsNotNone(scheduled_id)

        with patch(
            "ai_content_maker.api.telegram.TelegramPublisher",
            return_value=FakeTelegramPublisher(),
        ):
            response = self.client.post(f"/telegram/{scheduled_id}/publish")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "published")

    def test_publish_due_endpoint_publishes_only_due_scheduled_content(self) -> None:
        with Session(self.engine) as session:
            repository = ContentRepository(session)
            due_draft = repository.create_telegram_draft(
                project_id=1,
                topic_title="Due post",
                content="Due content",
            )
            future_draft = repository.create_telegram_draft(
                project_id=1,
                topic_title="Future post",
                content="Future content",
            )
            due = repository.mark_scheduled(
                repository.mark_approved(due_draft),
                datetime(2020, 1, 1, 10, tzinfo=UTC),
            )
            future = repository.mark_scheduled(
                repository.mark_approved(future_draft),
                datetime(2099, 1, 1, 10, tzinfo=UTC),
            )
            due_id = due.id
            future_id = future.id

        self.assertIsNotNone(due_id)
        self.assertIsNotNone(future_id)

        with patch(
            "ai_content_maker.api.telegram.TelegramPublisher",
            return_value=FakeTelegramPublisher(),
        ):
            response = self.client.post("/telegram/scheduled/publish-due")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["published_count"], 1)
        self.assertEqual(response.json()["failed_count"], 0)
        self.assertEqual(response.json()["results"][0]["content_id"], due_id)
        self.assertEqual(response.json()["results"][0]["status"], "published")

        with Session(self.engine) as session:
            published = session.get(Content, due_id)
            still_scheduled = session.get(Content, future_id)

        self.assertIsNotNone(published)
        self.assertIsNotNone(still_scheduled)
        self.assertEqual(published.status, "published")
        self.assertEqual(still_scheduled.status, "scheduled")

    def test_publish_due_endpoint_marks_due_content_failed_when_telegram_fails(self) -> None:
        with Session(self.engine) as session:
            repository = ContentRepository(session)
            draft = repository.create_telegram_draft(
                project_id=1,
                topic_title="Due failure",
                content="Due content",
            )
            due = repository.mark_scheduled(
                repository.mark_approved(draft),
                datetime(2020, 1, 1, 10, tzinfo=UTC),
            )
            due_id = due.id

        self.assertIsNotNone(due_id)

        with patch(
            "ai_content_maker.api.telegram.TelegramPublisher",
            return_value=FailingTelegramPublisher(),
        ):
            response = self.client.post("/telegram/scheduled/publish-due")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["published_count"], 0)
        self.assertEqual(response.json()["failed_count"], 1)
        self.assertEqual(response.json()["results"][0]["content_id"], due_id)
        self.assertEqual(response.json()["results"][0]["status"], "failed")
        self.assertEqual(response.json()["results"][0]["error"], "fake Telegram failure")

        with Session(self.engine) as session:
            failed = session.get(Content, due_id)

        self.assertIsNotNone(failed)
        self.assertEqual(failed.status, "failed")

    def test_publish_endpoint_marks_draft_failed_when_telegram_fails(self) -> None:
        with Session(self.engine) as session:
            draft = ContentRepository(session).create_telegram_draft(
                project_id=1,
                topic_title="Publish failure",
                content="Ready to publish",
            )
            draft_id = draft.id

        self.assertIsNotNone(draft_id)
        approve_response = self.client.post(f"/telegram/{draft_id}/approve")
        self.assertEqual(approve_response.status_code, 200)

        with patch(
            "ai_content_maker.api.telegram.TelegramPublisher",
            return_value=FailingTelegramPublisher(),
        ):
            response = self.client.post(f"/telegram/{draft_id}/publish")

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json(), {"detail": "fake Telegram failure"})

        with Session(self.engine) as session:
            failed = session.get(Content, draft_id)

        self.assertIsNotNone(failed)
        self.assertEqual(failed.status, "failed")


if __name__ == "__main__":
    unittest.main()
