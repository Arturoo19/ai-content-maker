from collections.abc import Generator

from sqlalchemy import text
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
    _ensure_sqlite_content_image_columns()


def _ensure_sqlite_content_image_columns() -> None:
    if not database_url.startswith("sqlite"):
        return

    image_columns = {
        "image_url": "VARCHAR(1000)",
        "image_source_url": "VARCHAR(1000)",
        "image_author": "VARCHAR(300)",
        "image_license": "VARCHAR(120)",
    }

    with engine.begin() as connection:
        existing_columns = {
            row[1] for row in connection.execute(text("PRAGMA table_info(content)"))
        }
        for column_name, column_type in image_columns.items():
            if column_name not in existing_columns:
                connection.execute(
                    text(f"ALTER TABLE content ADD COLUMN {column_name} {column_type}")
                )


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
