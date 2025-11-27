from __future__ import annotations

from collections.abc import Generator
from os import getenv

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker


SQLALCHEMY_DATABASE_URL = getenv("DATABASE_URL", "sqlite:///./app.db")


engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    future=True,
    echo=False,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    """Базовый класс для моделей SQLAlchemy."""


def get_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
