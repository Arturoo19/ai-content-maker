from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from ai_content_maker.config import settings


def _connect_args(database_url: str) -> dict[str, bool]:
    if database_url.startswith("sqlite"):
        return {"check_same_thread": False}

    return {}


database_url = settings.database_url or "sqlite:///./ai_content_maker.db"
engine = create_engine(database_url, connect_args=_connect_args(database_url))


def create_db_and_tables() -> None:
    from ai_content_maker import models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
