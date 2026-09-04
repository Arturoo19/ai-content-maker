from sqlmodel import Session

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
