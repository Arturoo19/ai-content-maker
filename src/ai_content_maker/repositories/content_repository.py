from datetime import UTC, datetime

from sqlmodel import Session, select

from ai_content_maker.models.content import Content
from ai_content_maker.models.topic import Topic


class ContentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_telegram_draft(
        self,
        *,
        project_id: int,
        topic_title: str,
        content: str,
        channel_id: int | None = None,
    ) -> Content:
        topic = Topic(project_id=project_id, title=topic_title)
        self.session.add(topic)
        self.session.flush()

        draft = Content(
            project_id=project_id,
            channel_id=channel_id,
            topic_id=topic.id,
            platform="telegram",
            content=content,
            status="draft",
        )
        self.session.add(draft)
        self.session.commit()
        self.session.refresh(draft)

        return draft

    def get_by_id(self, content_id: int) -> Content | None:
        return self.session.get(Content, content_id)

    def list_telegram_drafts(
        self,
        *,
        project_id: int | None = None,
        limit: int = 20,
    ) -> list[Content]:
        return self.list_telegram_content(
            project_id=project_id,
            status="draft",
            limit=limit,
        )

    def list_telegram_content(
        self,
        *,
        project_id: int | None = None,
        status: str | None = None,
        limit: int = 20,
    ) -> list[Content]:
        statement = (
            select(Content)
            .where(Content.platform == "telegram")
            .order_by(Content.created_at.desc())
            .limit(limit)
        )
        if project_id is not None:
            statement = statement.where(Content.project_id == project_id)
        if status is not None:
            statement = statement.where(Content.status == status)

        return list(self.session.exec(statement))

    def list_due_telegram_posts(
        self,
        *,
        now: datetime,
        limit: int = 20,
    ) -> list[Content]:
        statement = (
            select(Content)
            .where(
                Content.platform == "telegram",
                Content.status == "scheduled",
                Content.scheduled_at <= now,
            )
            .order_by(Content.scheduled_at)
            .limit(limit)
        )

        return list(self.session.exec(statement))

    def mark_published(self, content: Content) -> Content:
        content.status = "published"
        content.published_at = datetime.now(UTC)
        self.session.add(content)
        self.session.commit()
        self.session.refresh(content)

        return content

    def mark_failed(self, content: Content) -> Content:
        content.status = "failed"
        self.session.add(content)
        self.session.commit()
        self.session.refresh(content)

        return content

    def mark_approved(self, content: Content) -> Content:
        content.status = "approved"
        self.session.add(content)
        self.session.commit()
        self.session.refresh(content)

        return content

    def mark_rejected(self, content: Content) -> Content:
        content.status = "rejected"
        self.session.add(content)
        self.session.commit()
        self.session.refresh(content)

        return content

    def mark_scheduled(self, content: Content, scheduled_at: datetime) -> Content:
        content.status = "scheduled"
        content.scheduled_at = scheduled_at
        self.session.add(content)
        self.session.commit()
        self.session.refresh(content)

        return content

    def set_image(
        self,
        content: Content,
        *,
        image_url: str,
        image_source_url: str | None = None,
        image_author: str | None = None,
        image_license: str | None = None,
    ) -> Content:
        content.image_url = image_url
        content.image_source_url = image_source_url
        content.image_author = image_author
        content.image_license = image_license
        self.session.add(content)
        self.session.commit()
        self.session.refresh(content)

        return content
