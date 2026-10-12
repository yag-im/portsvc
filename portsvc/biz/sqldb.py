import json
import os
from collections.abc import Iterator

from sqlalchemy import (
    URL,
    create_engine,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Session,
    sessionmaker,
)


class Base(DeclarativeBase):
    pass


SessionLocal = sessionmaker()


def init_engine() -> None:
    url = URL.create(
        "postgresql+psycopg",
        username=os.environ["SQLDB_USERNAME"],
        password=os.environ["SQLDB_PASSWORD"],
        host=os.environ["SQLDB_HOST"],
        port=int(os.environ["SQLDB_PORT"]),
        database=os.environ["SQLDB_DBNAME"],
    )
    engine_options = json.loads(os.environ.get("SQLDB_ENGINE_OPTIONS", "{}"))
    SessionLocal.configure(bind=create_engine(url, **engine_options))


def get_session() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session
