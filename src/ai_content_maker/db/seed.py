from sqlmodel import Session, select

from ai_content_maker.db.session import create_db_and_tables, engine
from ai_content_maker.models.channel import Channel
from ai_content_maker.models.project import Project


OLD_AI_TOOLS_PROJECT_NAME = "AI Tools Daily"
FACTS_PROJECT_NAME = "Curious Facts Daily"
FACTS_CHANNEL_NAME = "Curious Facts Telegram"


def seed_facts_channel() -> tuple[Project, Channel]:
    create_db_and_tables()

    with Session(engine, expire_on_commit=False) as session:
        project = session.exec(
            select(Project).where(Project.name == FACTS_PROJECT_NAME)
        ).first()
        if project is None:
            project = session.exec(
                select(Project).where(Project.name == OLD_AI_TOOLS_PROJECT_NAME)
            ).first()

        if project is None:
            project = Project(
                name=FACTS_PROJECT_NAME,
            )
            session.add(project)

        project.name = FACTS_PROJECT_NAME
        project.description = (
            "A Ukrainian Telegram channel with short, non-obvious facts about "
            "history, money, business, technology, science, and everyday systems."
        )
        project.niche = "interesting facts about history, finance, technology, science, and business"
        project.language = "uk"
        project.status = "active"
        session.add(project)
        session.commit()
        session.refresh(project)

        channel = session.exec(
            select(Channel).where(
                Channel.project_id == project.id,
                Channel.platform == "telegram",
            )
        ).first()
        if channel is None:
            channel = Channel(
                project_id=project.id,
                platform="telegram",
            )
            session.add(channel)

        channel.name = FACTS_CHANNEL_NAME
        channel.settings = {
            "tone": "curious, concise, smart, lively, not childish",
            "audience": (
                "Ukrainian-speaking readers who like surprising facts, useful context, "
                "and short explanations that make the world feel more understandable"
            ),
            "content_mix": [
                "history facts",
                "money and finance facts",
                "technology facts",
                "science facts",
                "business and company origin stories",
            ],
            "cadence": "1 post every 2 days",
        }
        channel.is_active = True
        session.add(channel)
        session.commit()
        session.refresh(channel)

        return project, channel


if __name__ == "__main__":
    seeded_project, seeded_channel = seed_facts_channel()
    print(
        {
            "project_id": seeded_project.id,
            "project_name": seeded_project.name,
            "channel_id": seeded_channel.id,
            "channel_name": seeded_channel.name,
        }
    )
