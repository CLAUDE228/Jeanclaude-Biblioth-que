from collections.abc import Generator
import os

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./books.db")

engine_options = {"connect_args": {"check_same_thread": False}} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, **engine_options)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def initialize_database() -> None:
    Base.metadata.create_all(bind=engine)
    columns = {column["name"] for column in inspect(engine).get_columns("books")}
    migrations = {
        "date_publication": "DATE",
        "description": "TEXT",
        "fichier_livre": "VARCHAR(255)",
        "image_livre": "VARCHAR(255)",
    }
    with engine.begin() as connection:
        for column, sql_type in migrations.items():
            if column not in columns:
                connection.execute(
                    text(f"ALTER TABLE books ADD COLUMN {column} {sql_type}")
                )
