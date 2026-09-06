import json
import sys
from dataclasses import asdict

from sqlmodel import Session

from ai_content_maker.db.session import create_db_and_tables, engine
from ai_content_maker.repositories.content_repository import ContentRepository
from ai_content_maker.services.publishing.scheduled import ScheduledTelegramPublisher
from ai_content_maker.services.publishing.telegram import TelegramPublisher


def main() -> int:
    create_db_and_tables()

    with Session(engine) as session:
        repository = ContentRepository(session)
        try:
            publisher = TelegramPublisher()
        except ValueError as error:
            print(json.dumps({"error": str(error)}, ensure_ascii=False))
            return 1

        scheduled_publisher = ScheduledTelegramPublisher(repository, publisher)
        result = scheduled_publisher.publish_due()

    print(json.dumps(asdict(result), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
