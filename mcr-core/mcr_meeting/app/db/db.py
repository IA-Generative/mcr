from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import AsyncGenerator, Iterator, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from mcr_meeting.app.configs.base import DBSettings

DATABASE_URL = DBSettings().DATABASE_URL

# Création de l'engine avec des paramètres de pool
engine = create_engine(
    DATABASE_URL,
    pool_size=50,  # Taille maximale du pool
    max_overflow=10,  # Nombre de connexions supplémentaires au-delà du pool_size
    pool_timeout=30,  # Temps d'attente (en secondes) avant de lever une exception si aucune connexion n'est disponible
    pool_recycle=1800,  # Temps (en secondes) avant qu'une connexion soit fermée et recréée
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


# Context variable for the session
db_session_ctx: ContextVar[Optional[Session]] = ContextVar("db_session_ctx")


def set_db_session_ctx(session: Session) -> Token[Session | None]:
    """
    Set the database session in the context (avoid prop drilling of db session)
    """
    return db_session_ctx.set(session)


def reset_db_session_ctx(context_token: Token[Session | None]) -> None:
    """
    Reset the database session in the context.
    """
    db_session_ctx.reset(context_token)


def get_db_session_ctx() -> Session:
    """
    Get the database session from the context. Used in the repositories.
    """
    session = db_session_ctx.get()
    if session is None:
        raise RuntimeError("No DB session found in context")
    return session


async def router_db_session_context_manager() -> AsyncGenerator[Session, None]:
    """
    Dependency for database sessions. Used in the routers.
    """
    db = SessionLocal()
    context_token = set_db_session_ctx(db)
    try:
        yield db
    finally:
        db.close()
        reset_db_session_ctx(context_token)


@contextmanager
def worker_db_session_context_manager() -> Iterator[Session]:
    """
    Db session provider via context manager. Used in the workers.
    """
    db = SessionLocal()
    context_token = set_db_session_ctx(db)
    try:
        yield db
    finally:
        db.close()
        reset_db_session_ctx(context_token)
