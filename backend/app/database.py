from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from .config import settings


def _normalized_database_url(url: str) -> str:
    """Some providers (Neon, old-style Heroku URLs) hand out a
    'postgres://...' connection string, but SQLAlchemy 2.x rejects that
    scheme and requires 'postgresql://'. Normalize it so either form works
    without the person deploying this having to notice and fix it."""
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://"):]
    return url


engine = create_engine(_normalized_database_url(settings.database_url), pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
