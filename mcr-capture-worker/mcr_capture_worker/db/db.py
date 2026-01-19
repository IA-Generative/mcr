from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from mcr_capture_worker.settings.settings import PgSettings

DATABASE_URL = PgSettings().DATABASE_URL

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


@contextmanager
def get_db_session() -> Iterator[Session]:
    """
    Open a database session.
    """
    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()
