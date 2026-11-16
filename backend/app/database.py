"""Conexión a la base de datos con SQLAlchemy."""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_database_url


class Base(DeclarativeBase):  # pylint: disable=too-few-public-methods
    """Clase base de los modelos ORM."""


engine = create_engine(get_database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(  # pylint: disable=invalid-name
    bind=engine, autoflush=False, expire_on_commit=False
)


def get_db() -> Iterator[Session]:
    """Dependencia de FastAPI: abre una sesión por petición y la cierra al final."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
